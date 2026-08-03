from typing import Protocol
from uuid import UUID

from domain.pedido import Pedido, StatusPedido


# Sem `excluir`: Pedido nunca é apagado, só muda de status (CANCELADO é
# estado, não remoção) — preserva histórico pra auditoria e arrependimento (CDC).
class PedidoRepository(Protocol):
    async def criar(self, pedido: Pedido) -> Pedido: ...

    async def listar(
        self, status: StatusPedido | None = None, limit: int = 50, offset: int = 0
    ) -> list[Pedido]: ...

    # Total no mesmo filtro de listar (sem limit/offset), pra paginação.
    async def contar(self, status: StatusPedido | None = None) -> int: ...

    async def listar_por_cliente(
        self,
        cliente_id: UUID,
        status: StatusPedido | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Pedido]: ...

    async def contar_por_cliente(
        self, cliente_id: UUID, status: StatusPedido | None = None
    ) -> int: ...

    async def buscar_por_id(self, pedido_id: UUID) -> Pedido | None: ...

    # Usado tanto pra avançar o status (confirmar pagamento, despachar,
    # etc.) quanto pra registrar a mudança de quantidade_estoque associada.
    async def atualizar(self, pedido: Pedido) -> Pedido | None: ...
