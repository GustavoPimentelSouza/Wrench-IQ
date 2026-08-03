from typing import Protocol
from uuid import UUID

from domain.agendamento import Agendamento


class AgendamentoRepository(Protocol):
    async def criar(self, agendamento: Agendamento) -> Agendamento: ...

    # Todos os agendamentos, de todos os clientes — usado pela AgendaPage
    # (visão da oficina inteira). Sem isso, um agendamento criado pela IA
    # via chat ficava invisível pro time, só consultável por cliente.
    async def listar(self) -> list[Agendamento]: ...

    async def listar_por_cliente(self, cliente_id: UUID) -> list[Agendamento]: ...

    async def buscar_por_id(self, agendamento_id: UUID) -> Agendamento | None: ...

    async def atualizar(self, agendamento: Agendamento) -> Agendamento | None: ...

    async def excluir(self, agendamento_id: UUID) -> bool: ...
