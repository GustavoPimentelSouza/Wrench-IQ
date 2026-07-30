from uuid import UUID

from application.veiculo_repository import VeiculoRepository
from domain.veiculo import Veiculo


# Mesmo padrão de sempre. Sem "listar" geral, só "listar_por_cliente" —
# reflexo direto de VeiculoRepository (ver o comentário lá pra entender o
# porquê).
class VeiculoUseCases:
    def __init__(self, repository: VeiculoRepository):
        self._repository = repository

    async def criar(self, veiculo: Veiculo) -> Veiculo:
        return await self._repository.criar(veiculo)

    async def listar_por_cliente(self, cliente_id: UUID) -> list[Veiculo]:
        return await self._repository.listar_por_cliente(cliente_id)

    async def buscar_por_id(self, veiculo_id: UUID) -> Veiculo | None:
        return await self._repository.buscar_por_id(veiculo_id)

    async def atualizar(self, veiculo: Veiculo) -> Veiculo | None:
        existente = await self._repository.buscar_por_id(veiculo.id)
        if existente is None:
            return None
        return await self._repository.atualizar(veiculo)

    async def excluir(self, veiculo_id: UUID) -> bool:
        return await self._repository.excluir(veiculo_id)
