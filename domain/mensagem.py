import enum
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

# A classificação por IA (I/O, depende de rede) mora em
# application/classificacao_mensagem_service.py + adapters/groq_adapter.py,
# não aqui — domain fica só com o conceito puro de negócio.


class CategoriaMensagem(str, enum.Enum):
    """Categorias possíveis pra uma mensagem recebida do cliente."""

    CONSULTA_PECA = "consulta_peca"
    DUVIDA_GERAL = "duvida_geral"
    NAO_IDENTIFICADO = "nao_identificado"
    # dano_estrutural e reclamacao_sensivel: regras 1 e 4 do CLAUDE.md
    # (nunca orçamento automático / sempre cai pro humano).
    DANO_ESTRUTURAL = "dano_estrutural"
    AGENDAMENTO = "agendamento"
    STATUS_PROTOCOLO = "status_protocolo"
    RECLAMACAO_SENSIVEL = "reclamacao_sensivel"


class MotivoAtendimento(str, enum.Enum):
    """Por que uma mensagem caiu pro atendente humano — sem isso, falha
    técnica (ex: IA fora do ar) e reclamação de verdade apareciam idênticas
    na fila, e o atendente não tinha como saber qual é qual sem ler tudo."""

    FALHA_TECNICA = "falha_tecnica"
    RECLAMACAO_SENSIVEL = "reclamacao_sensivel"
    # A própria IA, no meio da conversa, decidiu que precisa de um humano
    # (ex: pedido fora do que ela sabe resolver) — diferente de reclamação
    # sensível, que é decidido antes de chamar a IA, pela classificação.
    TRANSFERENCIA_IA = "transferencia_ia"


@dataclass
class Mensagem:
    id: UUID
    cliente_id: UUID
    texto: str
    categoria: CategoriaMensagem
    criado_em: datetime
    # Preenchida depois de criar a Mensagem, quando a IA gera a resposta
    # (ver ConversaUseCases) — é o que dá memória de conversa: sem isso, cada
    # mensagem do cliente é tratada como se fosse a primeira da conversa.
    resposta_ia: str | None = None
    # Regra 4 do CLAUDE.md: falha técnica ou reclamação sensível cai pro
    # atendente humano. Marcado automaticamente (ver webhook.py) quando a
    # categoria é reclamacao_sensivel, quando a IA falha tecnicamente, ou
    # quando a própria IA pede transferência (ver motivo_atendimento).
    precisa_atendimento_humano: bool = False
    motivo_atendimento: MotivoAtendimento | None = None
    atendimento_resolvido: bool = False
