from typing import Protocol
from uuid import UUID

from domain.veiculo import Veiculo


# Mesmo caso do AgendamentoRepository: só "listar_por_cliente", sem listar
# geral — não existe uma tela de "todos os veículos de todos os clientes"
# no projeto hoje.
class VeiculoRepository(Protocol):
    async def criar(self, veiculo: Veiculo) -> Veiculo: ...

    async def listar_por_cliente(self, cliente_id: UUID) -> list[Veiculo]: ...

    async def buscar_por_id(self, veiculo_id: UUID) -> Veiculo | None: ...

    async def atualizar(self, veiculo: Veiculo) -> Veiculo | None: ...

    async def excluir(self, veiculo_id: UUID) -> bool: ...
