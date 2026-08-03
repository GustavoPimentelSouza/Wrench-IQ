from uuid import UUID

from application.peca_repository import PecaRepository
from domain.peca import Peca


# CRUD de catálogo. Validação de estoque fica em PedidoUseCases, não aqui.
class PecaUseCases:
    def __init__(self, repository: PecaRepository):
        self._repository = repository

    async def criar(self, peca: Peca) -> Peca:
        return await self._repository.criar(peca)

    async def listar(self) -> list[Peca]:
        return await self._repository.listar()

    async def buscar_por_id(self, peca_id: UUID) -> Peca | None:
        return await self._repository.buscar_por_id(peca_id)

    async def buscar_por_nome_aproximado(self, texto: str) -> list[Peca]:
        return await self._repository.buscar_por_nome_aproximado(texto)

    async def atualizar(self, peca: Peca) -> Peca | None:
        existente = await self._repository.buscar_por_id(peca.id)
        if existente is None:
            return None
        return await self._repository.atualizar(peca)

    async def excluir(self, peca_id: UUID) -> bool:
        return await self._repository.excluir(peca_id)
