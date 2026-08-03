from uuid import UUID

from application.cliente_repository import ClienteRepository
from domain.cliente import Cliente


# Use case mais simples do projeto: praticamente só delega pro repository.
class ClienteUseCases:
    def __init__(self, repository: ClienteRepository):
        self._repository = repository

    async def criar(self, cliente: Cliente) -> Cliente:
        return await self._repository.criar(cliente)

    async def listar(self) -> list[Cliente]:
        return await self._repository.listar()

    async def buscar_por_id(self, cliente_id: UUID) -> Cliente | None:
        return await self._repository.buscar_por_id(cliente_id)

    async def buscar_por_telefone(self, telefone: str) -> Cliente | None:
        return await self._repository.buscar_por_telefone(telefone)

    async def atualizar(self, cliente: Cliente) -> Cliente | None:
        existente = await self._repository.buscar_por_id(cliente.id)
        if existente is None:
            return None
        return await self._repository.atualizar(cliente)

    async def excluir(self, cliente_id: UUID) -> bool:
        return await self._repository.excluir(cliente_id)
