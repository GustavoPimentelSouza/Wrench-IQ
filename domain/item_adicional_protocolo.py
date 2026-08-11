import enum
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


class StatusItemAdicional(str, enum.Enum):
    PENDENTE = "pendente"
    APROVADO = "aprovado"
    RECUSADO = "recusado"


@dataclass
class ItemAdicionalProtocolo:
    """Problema novo encontrado pelo mecânico DURANTE a execução de um
    Protocolo (ex: abriu o motor pra trocar a correia e achou a bomba
    d'água furada). Mesma regra 1 do CLAUDE.md que já vale pro Protocolo
    inteiro: a IA (e nem o próprio mecânico sozinho) não fecha esse valor
    a mais sem o cliente decidir — fica PENDENTE até ele aprovar ou
    recusar (ver ItemAdicionalUseCases).
    """

    id: UUID
    protocolo_id: UUID
    descricao: str
    valor: Decimal
    status: StatusItemAdicional
    criado_em: datetime
    peca_id: UUID | None = None
