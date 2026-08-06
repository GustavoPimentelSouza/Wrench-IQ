import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from application.agendamento_use_cases import AgendamentoUseCases
from application.chat_service import ChatService, RespostaChat
from application.configuracao_oficina_use_cases import ConfiguracaoOficinaUseCases
from application.conversa_executor_ferramentas import ExecutorFerramentasConversa
from application.conversa_ferramentas import (
    FERRAMENTAS_AGENDAMENTO,
    FERRAMENTAS_RECLAMACAO_SENSIVEL,
    FERRAMENTAS_VENDA,
)
from application.conversa_prompts import (
    MAX_RODADAS_FERRAMENTA,
    MENSAGEM_FALLBACK_ERRO,
    MENSAGEM_PRECO_NAO_VERIFICADO,
    MENSAGEM_SAUDACAO,
    construir_prompt_sistema,
    eh_saudacao,
)
from application.peca_repository import PecaRepository
from application.pedido_use_cases import PedidoUseCases
from application.protocolo_use_cases import ProtocoloUseCases
from domain.mensagem import CategoriaMensagem, Mensagem, MotivoAtendimento

_logger = logging.getLogger(__name__)


# Regra 3 do CLAUDE.md: nunca confiar em preço vindo da conversa. Já vimos
# a IA confirmar um valor sugerido pelo próprio cliente ("não custa 45
# reais?") sem checar nada. Detecta "R$" na resposta pra travar isso —
# `_cita_preco_sem_verificar` só dispara quando nenhuma ferramenta foi
# chamada no turno inteiro, então não bloqueia os casos normais (peça já
# consultada em rodada anterior, preço real repassado pela IA).
_PADRAO_PRECO = re.compile(r"R\$\s*[\d.,]+")


def _cita_preco_sem_verificar(texto: str, ferramentas_chamadas: list[str]) -> bool:
    return not ferramentas_chamadas and bool(_PADRAO_PRECO.search(texto))


@dataclass
class ResultadoConversa:
    """`ferramentas_chamadas` existe pra depuração/simulador — mostra o que a
    IA decidiu fazer por trás, não só o texto final. `imagem_url` é da peça
    encontrada por consultar_preco_peca, se houver — a IA nunca vê a imagem
    em si, só repassamos a URL que já existe no catálogo."""

    texto: str
    ferramentas_chamadas: list[str] = field(default_factory=list)
    imagem_url: str | None = None
    # Regra 4 do CLAUDE.md: falha técnica cai pro atendente humano — True
    # quando o texto acima é o fallback genérico, não uma resposta real.
    precisa_atendimento_humano: bool = False
    # Por que precisou de humano — None quando precisa_atendimento_humano é
    # False. Sem isso, falha técnica e reclamação real ficavam idênticas na
    # fila de atendimento (ver AtendimentoPage), sem jeito de distinguir.
    motivo_atendimento: MotivoAtendimento | None = None


# Único caso de uso que de fato chama ChatService.gerar_resposta() — o
# outro que falta (visao_service/transcricao_service) ainda não tem
# equivalente. Os schemas das ferramentas e os prompts moraram aqui antes,
# mas foram pra conversa_ferramentas.py/conversa_prompts.py — mudam por
# motivo de "conteúdo" (novo tool, texto novo), não de lógica de orquestração,
# então ficam separados pra não misturar os dois tipos de mudança no mesmo
# arquivo/diff.
class ConversaUseCases:
    def __init__(
        self,
        chat_service: ChatService,
        peca_repository: PecaRepository,
        pedido_use_cases: PedidoUseCases,
        configuracao_oficina_use_cases: ConfiguracaoOficinaUseCases,
        agendamento_use_cases: AgendamentoUseCases,
        protocolo_use_cases: ProtocoloUseCases,
    ):
        self._chat = chat_service
        self._configuracao_oficina = configuracao_oficina_use_cases
        self._executor = ExecutorFerramentasConversa(
            peca_repository, pedido_use_cases, agendamento_use_cases, protocolo_use_cases
        )

    async def responder(
        self,
        mensagem: str,
        cliente_id: UUID,
        categoria: CategoriaMensagem,
        historico: list[Mensagem] | None = None,
    ) -> ResultadoConversa:
        if eh_saudacao(mensagem):
            return ResultadoConversa(texto=MENSAGEM_SAUDACAO)
        try:
            return await self._responder_ou_falhar(mensagem, cliente_id, categoria, historico or [])
        except Exception:
            # Sem isso, falha técnica virava caixa-preta: cliente recebia o
            # fallback genérico e ninguém sabia o motivo real — nem dava pra
            # saber se era bug nosso ou instabilidade do Groq.
            _logger.exception("Falha ao processar mensagem do cliente %s", cliente_id)
            return ResultadoConversa(
                texto=MENSAGEM_FALLBACK_ERRO,
                precisa_atendimento_humano=True,
                motivo_atendimento=MotivoAtendimento.FALHA_TECNICA,
            )

    async def _responder_ou_falhar(
        self, mensagem: str, cliente_id: UUID, categoria: CategoriaMensagem, historico: list[Mensagem]
    ) -> ResultadoConversa:
        # Classificação é por mensagem isolada, sem memória de conversa —
        # uma resposta curta tipo "pode ser dia 10 às 14h" não menciona
        # dano estrutural, então seria classificada como agendamento
        # genérico, e a regra 1 (nunca vender peça durante um caso de dano
        # estrutural) deixaria de valer nesse turno. Por isso a categoria
        # "gruda": se qualquer mensagem recente da conversa já foi dano
        # estrutural, o turno atual continua nesse fluxo, não só quando a
        # mensagem em si menciona o dano.
        em_fluxo_dano_estrutural = categoria == CategoriaMensagem.DANO_ESTRUTURAL or any(
            anterior.categoria == CategoriaMensagem.DANO_ESTRUTURAL for anterior in historico
        )
        # Agendamento comum "gruda" pelo mesmo motivo que dano estrutural —
        # e usa a MESMA ferramenta (agendar_visita). Sem isso, um pedido de
        # agendamento (ou dano estrutural mal classificado como outra
        # categoria numa mensagem curta) caía no fluxo de venda, sem
        # ferramenta nenhuma pra criar o agendamento de verdade — a IA
        # "confirmava" data e horário de boca, sem nada salvo no banco.
        em_fluxo_agendamento = categoria == CategoriaMensagem.AGENDAMENTO or any(
            anterior.categoria == CategoriaMensagem.AGENDAMENTO for anterior in historico
        )
        # Reclamação não "gruda" nos turnos seguintes que nem dano estrutural
        # — se ainda for reclamação de verdade, o classificador ou a própria
        # IA (vendo o histórico) reconhece de novo; não precisa forçar.
        if em_fluxo_dano_estrutural:
            categoria_efetiva = CategoriaMensagem.DANO_ESTRUTURAL
            ferramentas = FERRAMENTAS_AGENDAMENTO
        elif em_fluxo_agendamento:
            categoria_efetiva = CategoriaMensagem.AGENDAMENTO
            ferramentas = FERRAMENTAS_AGENDAMENTO
        elif categoria == CategoriaMensagem.RECLAMACAO_SENSIVEL:
            categoria_efetiva = CategoriaMensagem.RECLAMACAO_SENSIVEL
            ferramentas = FERRAMENTAS_RECLAMACAO_SENSIVEL
        else:
            categoria_efetiva = categoria
            ferramentas = FERRAMENTAS_VENDA
        configuracao = await self._configuracao_oficina.buscar()
        prompt_sistema = construir_prompt_sistema(configuracao, categoria_efetiva)
        mensagens: list[dict[str, Any]] = [{"role": "system", "content": prompt_sistema}]
        for anterior in historico:
            mensagens.append({"role": "user", "content": anterior.texto})
            if anterior.resposta_ia:
                mensagens.append({"role": "assistant", "content": anterior.resposta_ia})
        mensagens.append({"role": "user", "content": mensagem})

        ferramentas_chamadas: list[str] = []
        imagem_url: str | None = None

        for _ in range(MAX_RODADAS_FERRAMENTA):
            resposta = await self._chat.gerar_resposta(mensagens, ferramentas)

            if not resposta.chamadas_ferramentas:
                if resposta.texto and _cita_preco_sem_verificar(resposta.texto, ferramentas_chamadas):
                    return ResultadoConversa(
                        texto=MENSAGEM_PRECO_NAO_VERIFICADO,
                        ferramentas_chamadas=ferramentas_chamadas,
                        imagem_url=imagem_url,
                    )
                sem_resposta = not resposta.texto
                return ResultadoConversa(
                    texto=resposta.texto or MENSAGEM_FALLBACK_ERRO,
                    ferramentas_chamadas=ferramentas_chamadas,
                    imagem_url=imagem_url,
                    precisa_atendimento_humano=sem_resposta,
                    motivo_atendimento=MotivoAtendimento.FALHA_TECNICA if sem_resposta else None,
                )

            ferramentas_chamadas += [chamada.nome for chamada in resposta.chamadas_ferramentas]
            mensagens.append(_mensagem_assistente(resposta))
            for chamada in resposta.chamadas_ferramentas:
                resultado, url_encontrada, finalizar, motivo = await self._executor.executar(
                    chamada, cliente_id
                )
                imagem_url = imagem_url or url_encontrada
                mensagens.append(
                    {"role": "tool", "tool_call_id": chamada.id, "content": resultado}
                )
                if finalizar:
                    # Pedido criado com sucesso, ou a IA pediu transferência:
                    # manda a resposta direto pro cliente, sem deixar a IA
                    # reescrever — já vimos ela "esquecer" de repassar
                    # número/preço ao parafrasear a resposta final.
                    return ResultadoConversa(
                        texto=resultado,
                        ferramentas_chamadas=ferramentas_chamadas,
                        imagem_url=imagem_url,
                        precisa_atendimento_humano=motivo is not None,
                        motivo_atendimento=motivo,
                    )

        # Esgotou as rodadas sem o modelo parar de pedir ferramenta sozinho —
        # mas o resultado da última (ex: pedido criado com sucesso) já está
        # no contexto. Uma chamada final sem ferramentas força um resumo em
        # texto, em vez de jogar fora o que já aconteceu.
        resposta_final = await self._chat.gerar_resposta(mensagens, [])
        if resposta_final.texto and _cita_preco_sem_verificar(resposta_final.texto, ferramentas_chamadas):
            return ResultadoConversa(
                texto=MENSAGEM_PRECO_NAO_VERIFICADO,
                ferramentas_chamadas=ferramentas_chamadas,
                imagem_url=imagem_url,
            )
        sem_resposta_final = not resposta_final.texto
        return ResultadoConversa(
            texto=resposta_final.texto or MENSAGEM_FALLBACK_ERRO,
            ferramentas_chamadas=ferramentas_chamadas,
            imagem_url=imagem_url,
            precisa_atendimento_humano=sem_resposta_final,
            motivo_atendimento=MotivoAtendimento.FALHA_TECNICA if sem_resposta_final else None,
        )


def _mensagem_assistente(resposta: RespostaChat) -> dict[str, Any]:
    return {
        "role": "assistant",
        "content": resposta.texto,
        "tool_calls": [
            {
                "id": chamada.id,
                "type": "function",
                "function": {"name": chamada.nome, "arguments": json.dumps(chamada.argumentos)},
            }
            for chamada in resposta.chamadas_ferramentas
        ],
    }
