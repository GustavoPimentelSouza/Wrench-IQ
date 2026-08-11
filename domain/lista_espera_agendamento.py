from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from domain.especialidade import Especialidade


@dataclass
class ListaEsperaAgendamento:
    """Cliente que preferiu esperar por uma vaga mais próxima em vez de
    aceitar a data alternativa que AgendamentoDisponibilidadeUseCases.
    consultar_disponibilidade sempre oferece. Fila simples, ordem de
    chegada (criado_em) — quando um agendamento da mesma especialidade é
    cancelado ou dá no-show, o primeiro pendente da lista é notificado (ver
    AgendamentoDisponibilidadeUseCases._notificar_proximo_da_espera).
    """

    id: UUID
    cliente_id: UUID
    especialidade: Especialidade
    criado_em: datetime
    atendido: bool = False
