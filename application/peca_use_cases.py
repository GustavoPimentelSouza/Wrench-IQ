from uuid import UUID

from application.peca_repository import PecaRepository
from domain.peca import Peca


# Mesmo padrão de ClienteUseCases — puro CRUD delegado, com o "buscar antes
# de atualizar" como única lógica própria. Repara que NÃO tem nenhuma regra
# de "não deixar quantidade_estoque negativa" aqui: essa validação mora em
# PedidoUseCases (quem de fato vende peça), não aqui. Isso é proposital —
# PecaUseCases é sobre cadastro/manutenção do catálogo, não sobre venda.
class PecaUseCases:
    def __init__(self, repository: PecaRepository):
        self._repository = repository

    async def criar(self, peca: Peca) -> Peca:
        return await self._repository.criar(peca)

    async def listar(self) -> list[Peca]:
        return await self._repository.listar()

    async def buscar_por_id(self, peca_id: UUID) -> Peca | None:
        return await self._repository.buscar_por_id(peca_id)

    async def atualizar(self, peca: Peca) -> Peca | None:
        existente = await self._repository.buscar_por_id(peca.id)
        if existente is None:
            return None
        return await self._repository.atualizar(peca)

    async def excluir(self, peca_id: UUID) -> bool:
        return await self._repository.excluir(peca_id)
