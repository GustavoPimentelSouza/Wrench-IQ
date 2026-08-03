from datetime import datetime, timezone
from uuid import UUID

from application.agendamento_repository import AgendamentoRepository
from domain.agendamento import Agendamento


# Ainda não existe regra impedindo dois agendamentos no mesmo horário —
# validação desse tipo simplesmente não existe ainda no projeto (não foi
# pedido, não foi construído).
class AgendamentoUseCases:
    def __init__(self, repository: AgendamentoRepository):
        self._repository = repository

    async def criar(self, agendamento: Agendamento) -> Agendamento:
        if agendamento.data_hora < datetime.now(timezone.utc):
            raise ValueError("data_hora não pode ser no passado")
        return await self._repository.criar(agendamento)

    async def listar(self) -> list[Agendamento]:
        return await self._repository.listar()

    async def listar_por_cliente(self, cliente_id: UUID) -> list[Agendamento]:
        return await self._repository.listar_por_cliente(cliente_id)

    async def buscar_por_id(self, agendamento_id: UUID) -> Agendamento | None:
        return await self._repository.buscar_por_id(agendamento_id)

    async def atualizar(self, agendamento: Agendamento) -> Agendamento | None:
        existente = await self._repository.buscar_por_id(agendamento.id)
        if existente is None:
            return None
        return await self._repository.atualizar(agendamento)

    async def excluir(self, agendamento_id: UUID) -> bool:
        return await self._repository.excluir(agendamento_id)
