from dataclasses import dataclass, field
from typing import Any, Protocol

# Interface pra "converse com um LLM que sabe usar ferramentas" — hoje
# implementada por adapters/groq_adapter.py, mas nenhuma linha aqui sabe
# que é Groq. Poderia trocar pra outro provedor amanhã sem mexer em quem
# usa isso (ainda ninguém usa — ver o comentário no final do arquivo).


@dataclass
class ChamadaFerramenta:
    """Quando o modelo decide que precisa "chamar uma função" em vez de
    responder direto em texto (ex: "consultar_preco_peca"), é isso que
    vem preenchido. `argumentos` já vem parseado de JSON pra dict — quem
    usa essa classe não precisa lidar com string JSON crua.
    """

    nome: str
    argumentos: dict[str, Any]


@dataclass
class RespostaChat:
    """Resposta de uma chamada ao modelo. Os dois campos não são mutuamente
    exclusivos por acaso: o modelo pode devolver só texto, só chamadas de
    ferramenta, ou os dois juntos (dependendo do provedor). `texto` é
    opcional (None) porque um turno que só pede pra chamar uma ferramenta
    normalmente não vem com texto nenhum ainda.
    """

    texto: str | None
    # default_factory=list, não "= []" — armadilha clássica do Python:
    # usar uma lista mutável como valor padrão faria TODAS as instâncias de
    # RespostaChat compartilharem a MESMA lista por baixo dos panos.
    # default_factory garante uma lista nova a cada instância.
    chamadas_ferramentas: list[ChamadaFerramenta] = field(default_factory=list)


class ChatService(Protocol):
    async def gerar_resposta(
        self, mensagem: str, ferramentas_disponiveis: list[dict[str, Any]]
    ) -> RespostaChat: ...
    # `ferramentas_disponiveis` é uma lista de dicts no formato "tools" da
    # OpenAI (que o Groq também usa, por ser API-compatível):
    # [{"type": "function", "function": {"name": ..., "parameters": {...}}}]
    # Escolhi dict cru em vez de um tipo próprio pra não acoplar essa
    # interface a nenhuma biblioteca de SDK específica.


# IMPORTANTE pra quem for ler o resto do projeto: essa interface e o
# GroqAdapter que a implementa (adapters/groq_adapter.py) já existem e
# funcionam isoladamente, mas NENHUM use case chama gerar_resposta() ainda.
# A triagem de mensagem hoje (domain/mensagem.py) é só palavra-chave — isso
# aqui é a peça que falta pra virar conversa de verdade com IA.
