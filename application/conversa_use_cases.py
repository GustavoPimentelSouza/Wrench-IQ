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
    MENSAGEM_ENCERRAMENTO_PADRAO,
    MENSAGEM_FALLBACK_ERRO,
    MENSAGEM_LIMITE_TROCAS,
    MENSAGEM_PRECO_NAO_VERIFICADO,
    MENSAGEM_SAUDACAO,
    construir_prompt_sistema,
    eh_confirmacao_encerramento,
    eh_saudacao,
)
from application.peca_repository import PecaRepository
from application.pedido_use_cases import PedidoUseCases
from application.protocolo_use_cases import ProtocoloUseCases
from domain.configuracao_oficina import ConfiguracaoOficina
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
    # Nome da ferramenta que encerrou o turno (criar_pedido, cancelar_pedido,
    # agendar_visita), quando foi o caso — persistido em Mensagem.
    # acao_finalizadora pra ConversaUseCases saber, no PRÓXIMO turno, que
    # uma ação real acabou de ser concluída (ver responder() abaixo).
    acao_finalizadora: str | None = None


# Ferramentas que representam uma transação concluída de verdade (algo que
# não pode ser repetido sem querer). transferir_atendimento fica de fora —
# depois de um handoff pra humano não faz sentido "fechar a conversa" pela
# IA, então não participa dessa checagem.
_ACOES_TRANSACIONAIS = {"criar_pedido", "cancelar_pedido", "agendar_visita"}


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
        historico = historico or []
        configuracao = await self._configuracao_oficina.buscar()
        # Alta confiança, decidido sem chamar o modelo: cliente confirmando
        # que não quer mais nada, logo depois de uma ação concluída (pedido
        # criado, agendamento marcado, etc.). Já vimos o modelo, nesse
        # exato cenário, chamar criar_pedido de novo pra mesma compra em
        # vez de encerrar — não é algo que deva depender dele acertar toda
        # vez, então nem chega a chamar a IA aqui.
        se_encerrando = (
            historico
            and historico[-1].acao_finalizadora in _ACOES_TRANSACIONAIS
            and eh_confirmacao_encerramento(mensagem)
        )
        if se_encerrando:
            return ResultadoConversa(
                texto=configuracao.mensagem_encerramento or MENSAGEM_ENCERRAMENTO_PADRAO
            )
        # Nenhuma IA acerta 100% das vezes — depois de N trocas seguidas sem
        # nenhuma ação concluída (configurável, ver ConfiguracaoOficina.
        # limite_trocas_sem_resolucao), corta e transfere pra humano em vez
        # de deixar a IA tentando de novo sozinha. Cobre tanto "a IA está
        # capengando numa conversa confusa" quanto "o cliente está
        # insistindo em algo que não deveria ser resolvido pelo chat" (ex:
        # tentando negociar preço se passando por dono da oficina) —
        # decidido ANTES de chamar o modelo, sem gastar mais uma chamada de
        # API à toa. Reseta sozinho: acao_finalizadora inclui
        # transferir_atendimento, então depois de um handoff o contador
        # volta a zero pro próximo assunto.
        trocas_sem_resolucao = 0
        for anterior in reversed(historico):
            if anterior.acao_finalizadora is not None:
                break
            trocas_sem_resolucao += 1
        if trocas_sem_resolucao >= configuracao.limite_trocas_sem_resolucao:
            return ResultadoConversa(
                texto=MENSAGEM_LIMITE_TROCAS,
                precisa_atendimento_humano=True,
                motivo_atendimento=MotivoAtendimento.LIMITE_TROCAS_ATINGIDO,
            )
        try:
            resultado = await self._responder_ou_falhar(
                mensagem, cliente_id, categoria, historico, configuracao
            )
            return self._sem_imagem_repetida(resultado, historico)
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
        self,
        mensagem: str,
        cliente_id: UUID,
        categoria: CategoriaMensagem,
        historico: list[Mensagem],
        configuracao: ConfiguracaoOficina,
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
        # Mesma ideia de "gruda", só que usada aqui apenas pra decidir
        # quando FORÇAR consultar_preco_peca (ver forcar_ferramenta mais
        # abaixo) — não muda qual ferramenta/prompt é oferecido, porque
        # consulta_peca já cai no mesmo FERRAMENTAS_VENDA/_PROMPT_BASE que
        # duvida_geral e nao_identificado.
        em_fluxo_consulta_peca = categoria == CategoriaMensagem.CONSULTA_PECA or any(
            anterior.categoria == CategoriaMensagem.CONSULTA_PECA for anterior in historico
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
        prompt_sistema = construir_prompt_sistema(configuracao, categoria_efetiva)
        mensagens: list[dict[str, Any]] = [{"role": "system", "content": prompt_sistema}]
        for anterior in historico:
            mensagens.append({"role": "user", "content": anterior.texto})
            if anterior.resposta_ia:
                mensagens.append({"role": "assistant", "content": anterior.resposta_ia})
        mensagens.append({"role": "user", "content": mensagem})

        # Direto do log estruturado (Mensagem.ferramentas_chamadas), nunca
        # inferido do texto — bug real visto ao vivo: a IA parafraseia o
        # resultado da ferramenta antes de responder ao cliente, e um
        # marcador interno tipo "[peca_id: ...]" quase nunca sobrevive
        # nessa reescrita. Checar o texto concluía (errado) "ainda não
        # consultou nada" e forçava reconsultar pra sempre, sem nunca
        # deixar a venda chegar em criar_pedido.
        peca_ja_consultada_no_historico = any(
            "consultar_preco_peca" in anterior.ferramentas_chamadas for anterior in historico
        )

        ferramentas_chamadas: list[str] = []
        imagem_url: str | None = None

        for _ in range(MAX_RODADAS_FERRAMENTA):
            # Visto ao vivo: depois de algumas trocas confusas, a IA
            # "confirmou" que uma peça existe/está em estoque sem NUNCA ter
            # chamado consultar_preco_peca na conversa inteira. A 1ª
            # pergunta de esclarecimento continua livre (regra "se vago,
            # pergunte antes" — bool(historico) cobre isso, ainda vazio na
            # primeira mensagem do cliente sobre o assunto), mas a partir da
            # 2ª mensagem em diante, se ainda não teve consulta real, a
            # resposta é OBRIGATORIAMENTE uma chamada de ferramenta —
            # garantia de API (tool_choice="required"), não sugestão de
            # prompt (ver application/chat_service.py).
            forcar_ferramenta = (
                ferramentas is FERRAMENTAS_VENDA
                and em_fluxo_consulta_peca
                and bool(historico)
                and not peca_ja_consultada_no_historico
                and "consultar_preco_peca" not in ferramentas_chamadas
            )
            resposta = await self._chat.gerar_resposta(mensagens, ferramentas, forcar_ferramenta)

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
                        acao_finalizadora=chamada.nome,
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

    def _sem_imagem_repetida(
        self, resultado: ResultadoConversa, historico: list[Mensagem]
    ) -> ResultadoConversa:
        # Bug real encontrado em teste manual: a IA rechamando
        # consultar_preco_peca pra confirmar a MESMA peça (o que já vimos
        # acontecer, mesmo com a extração de dados funcionando na maioria
        # das vezes) reenviava a mesma foto de novo a cada turno, poluindo o
        # chat sem necessidade. Em vez de confiar que a IA "lembra" que já
        # mandou a imagem, checa direto contra o histórico persistido — só
        # sai uma imagem por URL, uma vez, por conversa.
        if resultado.imagem_url and any(
            m.imagem_url == resultado.imagem_url for m in historico
        ):
            resultado.imagem_url = None
        return resultado


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
