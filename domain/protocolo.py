import enum
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from domain.especialidade import Especialidade


class StatusProtocolo(str, enum.Enum):
    # AGUARDANDO_APROVACAO -> EM_EXECUCAO -> PRONTO; CANCELADO a partir dos
    # dois primeiros. PRONTO/CANCELADO são finais (protocolo_use_cases.py).
    AGUARDANDO_APROVACAO = "aguardando_aprovacao"
    EM_EXECUCAO = "em_execucao"
    PRONTO = "pronto"
    CANCELADO = "cancelado"


@dataclass
class Protocolo:
    """Ordem de serviço (veículo em avaliação/conserto). Diferente de Pedido
    (venda de peça): por regra de negócio (CLAUDE.md, regra 1) a IA nunca
    fecha orçamento de serviço sozinha, só classifica e agenda visita.
    """

    id: UUID
    cliente_id: UUID
    veiculo: str  # texto livre; não é FK pra domain/veiculo.py ainda
    categoria: str  # ex: "farol", "dano_estrutural" — decide se a IA age ou só agenda
    status: StatusProtocolo
    criado_em: datetime
    numero: int | None = None  # sequencial, gerado pelo banco
    descricao: str | None = None
    # Validado em protocolo_use_cases.py: precisa ser Usuario com papel=MECANICO.
    mecanico_id: UUID | None = None
    atualizado_em: datetime | None = None  # onupdate no banco
    # Exigido pelo use case antes de aprovar() (ver protocolo_use_cases.py).
    valor_orcamento: Decimal | None = None
    motivo_cancelamento: str | None = None
    # N:N (não um valor único) — um caso pode precisar de mais de uma área
    # ao mesmo tempo (ex: batida com dano elétrico junto). Reclassificável
    # pelo mecânico após avaliação presencial (ver
    # ProtocoloUseCases.reclassificar_especialidade).
    especialidades: list[Especialidade] = field(default_factory=list)
