from dataclasses import dataclass, field
from typing import Any, Protocol

# Interface pra "converse com um LLM que sabe usar ferramentas", implementada
# por adapters/groq_adapter.py. Ainda sem use case consumindo isso — falta
# a peça de tool calling na triagem.


@dataclass
class ChamadaFerramenta:
    """Preenchido quando o modelo decide chamar uma função em vez de
    responder em texto. `argumentos` já vem parseado de JSON pra dict.
    `id` identifica essa chamada específica — necessário pra devolver o
    resultado da ferramenta numa mensagem "tool" que o modelo consiga
    associar de volta, no próximo turno."""

    id: str
    nome: str
    argumentos: dict[str, Any]


@dataclass
class RespostaChat:
    """`texto` é opcional: um turno que só chama ferramenta pode não ter texto."""

    texto: str | None
    # default_factory evita lista mutável compartilhada entre instâncias.
    chamadas_ferramentas: list[ChamadaFerramenta] = field(default_factory=list)


class ChatService(Protocol):
    async def gerar_resposta(
        self, mensagens: list[dict[str, Any]], ferramentas_disponiveis: list[dict[str, Any]]
    ) -> RespostaChat: ...
    # mensagens e ferramentas_disponiveis seguem o formato cru da OpenAI/Groq
    # (messages/tools) — dict, pra não acoplar a interface a um SDK específico.
    # Ser uma lista (não uma string única) é o que permite tanto o vai-e-volta
    # de tool calling (anexar a chamada + o resultado antes de pedir a
    # resposta final) quanto, no futuro, memória de conversa de verdade.
