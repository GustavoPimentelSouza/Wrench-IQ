from typing import Protocol
from uuid import UUID

from domain.especialidade import Especialidade
from domain.lista_espera_agendamento import ListaEsperaAgendamento


class ListaEsperaRepository(Protocol):
    async def criar(self, entrada: ListaEsperaAgendamento) -> ListaEsperaAgendamento: ...

    # Primeiro pendente (atendido=False) por ordem de chegada — quem foi
    # notificado primeiro quando uma vaga daquela especialidade abrir.
    async def buscar_primeiro_pendente(
        self, especialidade: Especialidade
    ) -> ListaEsperaAgendamento | None: ...

    async def marcar_atendido(self, entrada_id: UUID) -> ListaEsperaAgendamento | None: ...
