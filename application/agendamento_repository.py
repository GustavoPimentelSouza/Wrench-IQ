from typing import Protocol
from uuid import UUID

from domain.agendamento import Agendamento


class AgendamentoRepository(Protocol):
    async def criar(self, agendamento: Agendamento) -> Agendamento: ...

    # Não existe "listar" geral (todos os agendamentos de todos os
    # clientes) — só por cliente. Reflete o único caso de uso que existe
    # hoje (ver a rota GET /agendamentos, que exige ?cliente_id= sempre).
    async def listar_por_cliente(self, cliente_id: UUID) -> list[Agendamento]: ...

    async def buscar_por_id(self, agendamento_id: UUID) -> Agendamento | None: ...

    async def atualizar(self, agendamento: Agendamento) -> Agendamento | None: ...

    async def excluir(self, agendamento_id: UUID) -> bool: ...
