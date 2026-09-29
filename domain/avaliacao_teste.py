import enum
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

# TEMPORÁRIO (ferramenta de dev): avaliação manual das conversas do
# simulador enquanto a IA amadurece. Tudo que é dessa feature leva
# "avaliacao_teste" no nome — um grep acha o que remover depois.


class ResultadoAvaliacao(str, enum.Enum):
    """Mesmos eixos do eval automático (tests/eval_conversa/), pra que as
    duas medições contem a mesma história no TCC."""

    CORRETO = "correto"
    # Inventou informação (preço, peça, horário) — falha de "decisão segura".
    ALUCINOU = "alucinou"
    # Não inventou nada, mas agiu errado — falha de "acerto de intenção".
    ERROU_FLUXO = "errou_fluxo"


@dataclass
class AvaliacaoTeste:
    """Uma avaliação por conversa (conversa = cliente do simulador)."""

    id: UUID
    cliente_id: UUID
    resultado: ResultadoAvaliacao
    comentario: str | None
    criado_em: datetime
    atualizado_em: datetime
