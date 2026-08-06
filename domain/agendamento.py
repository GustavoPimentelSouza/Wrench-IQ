import enum
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


class StatusAgendamento(str, enum.Enum):
    AGENDADO = "agendado"  # estado inicial, ao criar
    CONFIRMADO = "confirmado"
    CANCELADO = "cancelado"
    CONCLUIDO = "concluido"


@dataclass
class Agendamento:
    """Uma visita marcada por um Cliente (ex: pra avaliação de dano
    estrutural, que a IA nunca orça sozinha — só agenda). Ainda sem vínculo
    direto com Protocolo (isso continua manual, criado pelo mecânico depois
    da visita) — `descricao` existe pra não perder o que a IA já apurou na
    conversa (o quê, em qual veículo) até esse momento manual acontecer.
    """

    id: UUID
    cliente_id: UUID
    data_hora: datetime
    status: StatusAgendamento
    criado_em: datetime
    descricao: str | None = None
