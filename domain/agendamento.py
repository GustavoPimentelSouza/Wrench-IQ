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
    estrutural, que a IA nunca orça sozinha — só agenda). Modelo bem
    simples de propósito: só data/hora + status, sem vínculo direto com
    Protocolo ou Veículo ainda — nenhum caso de uso pedia mais que isso até
    agora, então não foi construído (evitar over-engineering).
    """

    id: UUID
    cliente_id: UUID
    data_hora: datetime
    status: StatusAgendamento
    criado_em: datetime
