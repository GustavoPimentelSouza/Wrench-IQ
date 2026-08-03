import json
from dataclasses import dataclass, field
from datetime import datetime, time, timezone
from typing import Any
from uuid import UUID, uuid4

from application.agendamento_use_cases import AgendamentoUseCases
from application.chat_service import ChatService, ChamadaFerramenta, RespostaChat
from application.configuracao_oficina_use_cases import ConfiguracaoOficinaUseCases
from application.peca_repository import PecaRepository
from application.pedido_use_cases import (
    EnderecoObrigatorioError,
    EstoqueInsuficienteError,
    PecaNaoEncontradaError,
    PedidoUseCases,
)
from domain.agendamento import Agendamento, StatusAgendamento
from domain.configuracao_oficina import ConfiguracaoOficina
from domain.mensagem import CategoriaMensagem, Mensagem
from domain.pedido import TipoEntrega

_CONSULTAR_PRECO_PECA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "consultar_preco_peca",
        "description": "Consulta preço e estoque de uma peça pelo nome ou descrição.",
        "parameters": {
            "type": "object",
            "properties": {
                "nome": {"type": "string", "description": "Nome ou descrição da peça buscada"},
            },
            "required": ["nome"],
        },
    },
}

_CRIAR_PEDIDO: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "criar_pedido",
        "description": (
            "Cria um pedido de venda direta. Só chame depois que o cliente "
            "confirmar explicitamente que quer comprar — nunca só por ter "
            "perguntado o preço."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "peca_id": {
                    "type": "string",
                    "description": "ID interno da peça, obtido via consultar_preco_peca — nunca mostre esse valor ao cliente",
                },
                "quantidade": {"type": "integer", "description": "Quantidade de unidades"},
                "tipo_entrega": {
                    "type": "string",
                    "enum": ["retirada_local", "envio_remoto"],
                },
                "endereco_entrega": {
                    "type": "string",
                    "description": "Endereço completo — obrigatório só se tipo_entrega for envio_remoto",
                },
            },
            "required": ["peca_id", "quantidade", "tipo_entrega"],
        },
    },
}

_AGENDAR_VISITA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "agendar_visita",
        "description": (
            "Agenda uma visita presencial pra avaliação de dano estrutural "
            "(batida, amassado, pintura, lanternagem). Só chame depois que o "
            "cliente confirmar a data e horário desejados."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "data_hora": {
                    "type": "string",
                    "description": "Data e hora da visita em ISO 8601 (ex: 2026-08-10T14:00:00)",
                },
            },
            "required": ["data_hora"],
        },
    },
}

# Regra 1 do CLAUDE.md: dano estrutural nunca pode virar venda de peça nem
# orçamento pela IA — por isso essa categoria tem sua PRÓPRIA lista de
# ferramentas (só agendar_visita), nunca consultar_preco_peca/criar_pedido.
# Sem essa separação, a IA tratava "bati o carro" como pedido de peça.
_FERRAMENTAS_VENDA = [_CONSULTAR_PRECO_PECA, _CRIAR_PEDIDO]
_FERRAMENTAS_DANO_ESTRUTURAL = [_AGENDAR_VISITA]

_PROMPT_DANO_ESTRUTURAL = (
    "O cliente relatou um dano estrutural (batida, amassado, pintura, "
    "lanternagem). REGRA INEGOCIÁVEL: você NUNCA estima valor de conserto "
    "nem prazo — isso só um mecânico avalia presencialmente. Seja solidário "
    "e ofereça agendar uma visita. Pergunte a data e horário que o cliente "
    "prefere e só chame agendar_visita depois que ele confirmar. Não "
    "pergunte sobre peças nem tente vender nada nessa conversa."
)

_PROMPT_BASE = (
    "Você é o assistente de atendimento de uma oficina mecânica. Seja breve. "
    "Só chame consultar_preco_peca se o cliente já disse qual peça quer; se "
    "a mensagem for vaga, pergunte qual peça antes de chamar qualquer "
    "ferramenta. Nunca informe a quantidade exata em estoque, só se está "
    "disponível ou não. consultar_preco_peca sempre devolve a peça mais "
    "parecida do catálogo, nunca uma garantia — sempre pergunte ao cliente "
    "se é essa mesma peça antes de fechar qualquer venda. IMPORTANTE: use "
    "SEMPRE o nome exato da peça que a ferramenta devolveu — nunca "
    "substitua pelo nome que o cliente usou. Só chame criar_pedido depois "
    "que o cliente confirmar explicitamente a compra, a peça certa, a "
    "quantidade e o tipo de entrega (retirada na loja ou envio remoto); se "
    "for envio remoto, pergunte o endereço antes de chamar a ferramenta. "
    "Nunca informe preço de cabeça — sempre confie no valor que as "
    "ferramentas devolvem, nunca no que já foi dito antes na conversa. "
    "IMPORTANTE: nunca invente informação institucional que você não tem "
    "certeza (política de garantia, prazo de conserto, forma de pagamento "
    "aceita etc.) — se não souber, diga que vai confirmar com a equipe. O "
    "único dado institucional que você recebe de verdade é o horário de "
    "funcionamento abaixo; fora isso, não chute nada."
)


def _formatar_periodo(abertura: time | None, fechamento: time | None) -> str:
    if abertura is None or fechamento is None:
        return "fechado"
    return f"{abertura.strftime('%H:%M')} às {fechamento.strftime('%H:%M')}"


def _construir_prompt_sistema(configuracao: ConfiguracaoOficina, categoria: CategoriaMensagem) -> str:
    # Sem isso, a IA não tinha nenhum dado real de horário e inventava um
    # (já vimos ela responder um horário completo do nada). Agora o valor
    # vem sempre do banco (ConfiguracaoOficina), nunca da conversa.
    horario = (
        f"Horário de funcionamento: segunda a sexta "
        f"{_formatar_periodo(configuracao.horario_semana_abertura, configuracao.horario_semana_fechamento)}, "
        f"sábado {_formatar_periodo(configuracao.horario_sabado_abertura, configuracao.horario_sabado_fechamento)}, "
        f"domingo {_formatar_periodo(configuracao.horario_domingo_abertura, configuracao.horario_domingo_fechamento)}."
    )
    base = _PROMPT_DANO_ESTRUTURAL if categoria == CategoriaMensagem.DANO_ESTRUTURAL else _PROMPT_BASE
    return f"{base} {horario}"

# Rede de segurança: nunca deixa erro técnico do Groq (rede, tool_use_failed,
# etc.) vazar como 500 pro cliente. Handoff pro atendente humano (regra 4 do
# CLAUDE.md) ainda não existe — quando existir, é aqui que entra.
_MENSAGEM_FALLBACK_ERRO = "Não consegui processar sua mensagem agora, pode tentar de outro jeito?"

# Limite de segurança pro loop de tool calling (ex: consultar preço, depois
# criar pedido, são duas rodadas) — nunca deixa entrar num loop infinito se o
# modelo insistir em pedir ferramenta pra sempre.
_MAX_RODADAS_FERRAMENTA = 3

# Saudação pura (sem mais nada na mensagem) é tratada aqui, sem chamar a IA —
# determinístico, sem custo, e sem depender do modelo "decidir" responder uma
# mensagem tão simples (não é confiável 100% das vezes, como o tool calling
# de verdade precisa ser).
_SAUDACOES = {
    "oi", "ola", "olá", "opa", "eae", "e ai", "e aí", "salve",
    "bom dia", "boa tarde", "boa noite", "tudo bem", "tudo bom",
}
_MENSAGEM_SAUDACAO = "Olá! Me conta qual peça você está procurando ou o que você precisa."

# Reclamação sensível (regra 4) também é atalho, igual saudação — mas pelo
# motivo oposto: aqui não é "simples demais pra IA", é "grave demais pra
# deixar a IA tentar resolver". O prompt de vendas da IA não é adequado pra
# uma reclamação (já vimos ela tentar oferecer peça pra quem só queria
# reclamar) — melhor nem chamar o modelo pra isso.
_MENSAGEM_RECLAMACAO = (
    "Sinto muito pelo ocorrido. Já registrei sua mensagem e um atendente "
    "humano vai te responder em breve."
)


def _eh_saudacao(mensagem: str) -> bool:
    normalizado = mensagem.strip().lower().rstrip("!?.,")
    return normalizado in _SAUDACOES


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


# Único caso de uso que de fato chama ChatService.gerar_resposta() — o
# outro que falta (visao_service/transcricao_service) ainda não tem
# equivalente.
class ConversaUseCases:
    def __init__(
        self,
        chat_service: ChatService,
        peca_repository: PecaRepository,
        pedido_use_cases: PedidoUseCases,
        configuracao_oficina_use_cases: ConfiguracaoOficinaUseCases,
        agendamento_use_cases: AgendamentoUseCases,
    ):
        self._chat = chat_service
        self._pecas = peca_repository
        self._pedidos = pedido_use_cases
        self._configuracao_oficina = configuracao_oficina_use_cases
        self._agendamentos = agendamento_use_cases

    async def responder(
        self,
        mensagem: str,
        cliente_id: UUID,
        categoria: CategoriaMensagem,
        historico: list[Mensagem] | None = None,
    ) -> ResultadoConversa:
        if _eh_saudacao(mensagem):
            return ResultadoConversa(texto=_MENSAGEM_SAUDACAO)
        if categoria == CategoriaMensagem.RECLAMACAO_SENSIVEL:
            return ResultadoConversa(texto=_MENSAGEM_RECLAMACAO, precisa_atendimento_humano=True)
        try:
            return await self._responder_ou_falhar(mensagem, cliente_id, categoria, historico or [])
        except Exception:
            return ResultadoConversa(
                texto=_MENSAGEM_FALLBACK_ERRO, precisa_atendimento_humano=True
            )

    async def _responder_ou_falhar(
        self, mensagem: str, cliente_id: UUID, categoria: CategoriaMensagem, historico: list[Mensagem]
    ) -> ResultadoConversa:
        # A classificação é por mensagem, sem memória — "pode ser dia 10 às
        # 14h", sozinha, parece agendamento genérico. Sem isso, a segunda
        # mensagem de uma conversa de dano estrutural perdia a categoria e a
        # IA voltava a perguntar sobre peça (regra 1 quebrando de novo, só
        # que no segundo turno). Por isso "gruda" no fluxo de dano
        # estrutural se qualquer mensagem recente da conversa já foi
        # classificada assim, não só a atual.
        em_fluxo_dano_estrutural = categoria == CategoriaMensagem.DANO_ESTRUTURAL or any(
            anterior.categoria == CategoriaMensagem.DANO_ESTRUTURAL for anterior in historico
        )
        categoria_efetiva = (
            CategoriaMensagem.DANO_ESTRUTURAL if em_fluxo_dano_estrutural else categoria
        )
        configuracao = await self._configuracao_oficina.buscar()
        prompt_sistema = _construir_prompt_sistema(configuracao, categoria_efetiva)
        ferramentas = _FERRAMENTAS_DANO_ESTRUTURAL if em_fluxo_dano_estrutural else _FERRAMENTAS_VENDA
        mensagens: list[dict[str, Any]] = [{"role": "system", "content": prompt_sistema}]
        for anterior in historico:
            mensagens.append({"role": "user", "content": anterior.texto})
            if anterior.resposta_ia:
                mensagens.append({"role": "assistant", "content": anterior.resposta_ia})
        mensagens.append({"role": "user", "content": mensagem})

        ferramentas_chamadas: list[str] = []
        imagem_url: str | None = None

        for _ in range(_MAX_RODADAS_FERRAMENTA):
            resposta = await self._chat.gerar_resposta(mensagens, ferramentas)

            if not resposta.chamadas_ferramentas:
                return ResultadoConversa(
                    texto=resposta.texto or _MENSAGEM_FALLBACK_ERRO,
                    ferramentas_chamadas=ferramentas_chamadas,
                    imagem_url=imagem_url,
                    precisa_atendimento_humano=not resposta.texto,
                )

            ferramentas_chamadas += [chamada.nome for chamada in resposta.chamadas_ferramentas]
            mensagens.append(_mensagem_assistente(resposta))
            for chamada in resposta.chamadas_ferramentas:
                resultado, url_encontrada = await self._executar_ferramenta(chamada, cliente_id)
                imagem_url = imagem_url or url_encontrada
                mensagens.append(
                    {"role": "tool", "tool_call_id": chamada.id, "content": resultado}
                )

        # Esgotou as rodadas sem o modelo parar de pedir ferramenta sozinho —
        # mas o resultado da última (ex: pedido criado com sucesso) já está
        # no contexto. Uma chamada final sem ferramentas força um resumo em
        # texto, em vez de jogar fora o que já aconteceu.
        resposta_final = await self._chat.gerar_resposta(mensagens, [])
        return ResultadoConversa(
            texto=resposta_final.texto or _MENSAGEM_FALLBACK_ERRO,
            ferramentas_chamadas=ferramentas_chamadas,
            imagem_url=imagem_url,
            precisa_atendimento_humano=not resposta_final.texto,
        )

    async def _executar_ferramenta(
        self, chamada: ChamadaFerramenta, cliente_id: UUID
    ) -> tuple[str, str | None]:
        if chamada.nome == "consultar_preco_peca":
            return await self._consultar_preco_peca(chamada.argumentos)
        if chamada.nome == "criar_pedido":
            return await self._criar_pedido(chamada.argumentos, cliente_id), None
        if chamada.nome == "agendar_visita":
            return await self._agendar_visita(chamada.argumentos, cliente_id), None
        return "Ferramenta desconhecida.", None

    async def _agendar_visita(self, argumentos: dict[str, Any], cliente_id: UUID) -> str:
        try:
            data_hora = datetime.fromisoformat(argumentos["data_hora"])
            if data_hora.tzinfo is None:
                data_hora = data_hora.replace(tzinfo=timezone.utc)
            agendamento = await self._agendamentos.criar(
                Agendamento(
                    id=uuid4(),
                    cliente_id=cliente_id,
                    data_hora=data_hora,
                    status=StatusAgendamento.AGENDADO,
                    criado_em=datetime.now(timezone.utc),
                )
            )
        except ValueError as erro:
            return f"Não foi possível agendar: {erro}. Pergunte ao cliente uma data válida, no futuro."

        data_formatada = agendamento.data_hora.strftime("%d/%m/%Y às %H:%M")
        return (
            f"Visita agendada para {data_formatada}. Informe ao cliente que um "
            "mecânico vai avaliar o dano presencialmente e que não é possível "
            "estimar valor de conserto pelo chat."
        )

    async def _consultar_preco_peca(self, argumentos: dict[str, Any]) -> tuple[str, str | None]:
        termo = argumentos["nome"]
        pecas = await self._pecas.buscar_por_nome_aproximado(termo)
        if not pecas:
            return (
                "Nenhuma peça parecida encontrada no catálogo. Pergunte ao "
                "cliente o nome da peça de outro jeito.",
                None,
            )

        # Busca semântica sempre devolve o candidato mais próximo (nunca uma
        # garantia exata) — por isso sempre pede confirmação, em vez de tentar
        # adivinhar "confiança" checando palavra por palavra (isso não existe
        # mais com embeddings; a peça pode ser a certa mesmo sem nenhuma
        # palavra em comum com o que o cliente digitou).
        peca = pecas[0]
        disponibilidade = "disponível" if peca.quantidade_estoque > 0 else "sem estoque no momento"
        texto = (
            f"Peça mais parecida encontrada: {peca.nome} ({peca.marca_modelo_compativel}, "
            f"{peca.ano_compativel}): R$ {peca.preco}, {disponibilidade}. "
            f"[peca_id: {peca.id}] Confirme com o cliente se é essa a peça certa "
            "antes de fechar qualquer venda."
        )
        return texto, peca.imagem_url

    async def _criar_pedido(self, argumentos: dict[str, Any], cliente_id: UUID) -> str:
        try:
            tipo_entrega = TipoEntrega(argumentos["tipo_entrega"])
            endereco = argumentos.get("endereco_entrega")
            # O prompt já pede pra IA perguntar o endereço antes de chamar essa
            # ferramenta, mas isso não é 100% confiável (já vimos o modelo
            # inventar uma frase tipo "por favor, forneça o endereço" e mandar
            # isso como se fosse o endereço real). Regra 3 do CLAUDE.md: nunca
            # confiar só na conversa — endereço real de entrega quase sempre
            # tem número, então isso funciona como checagem determinística.
            if tipo_entrega == TipoEntrega.ENVIO_REMOTO and not _endereco_parece_valido(endereco):
                return (
                    "Endereço de entrega ausente ou incompleto — pergunte ao "
                    "cliente o endereço completo (rua, número, bairro, cidade) "
                    "e só chame essa ferramenta de novo depois que ele responder."
                )
            pedido = await self._pedidos.criar(
                cliente_id=cliente_id,
                peca_id=UUID(argumentos["peca_id"]),
                quantidade=int(argumentos["quantidade"]),
                tipo_entrega=tipo_entrega,
                endereco_entrega=endereco,
            )
        except PecaNaoEncontradaError:
            return "peca_id inválido — chame consultar_preco_peca de novo antes de criar o pedido."
        except EstoqueInsuficienteError:
            return "Estoque insuficiente pra essa quantidade. Avise o cliente."
        except EnderecoObrigatorioError:
            return "Faltou o endereço de entrega — pergunte ao cliente antes de tentar de novo."
        except ValueError:
            return "peca_id ou tipo_entrega inválido — chame consultar_preco_peca de novo."

        texto = f"Pedido #{pedido.numero} criado com sucesso. Valor total: R$ {pedido.valor_total}."
        if pedido.tipo_entrega == TipoEntrega.ENVIO_REMOTO:
            texto += (
                f" Link de pagamento: {pedido.link_pagamento}. Informe ao cliente que ele "
                "tem 7 dias de direito de arrependimento após a entrega (CDC)."
            )
        else:
            texto += " Retirada na loja, pagamento presencial na hora."
        return texto


def _endereco_parece_valido(endereco: str | None) -> bool:
    if endereco is None:
        return False
    texto = endereco.strip()
    return len(texto) >= 10 and any(c.isdigit() for c in texto)


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
