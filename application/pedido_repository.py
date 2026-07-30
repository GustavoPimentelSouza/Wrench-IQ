from typing import Protocol
from uuid import UUID

from domain.pedido import Pedido, StatusPedido


# Repara que não existe `excluir` aqui. Pedido nunca é apagado do banco —
# só muda de status (ver StatusPedido em domain/pedido.py: CANCELADO é um
# estado, não uma remoção). Isso preserva histórico de venda mesmo quando
# algo é cancelado, que é importante pra auditoria e pro direito de
# arrependimento (CDC, 7 dias).
class PedidoRepository(Protocol):
    async def criar(self, pedido: Pedido) -> Pedido: ...

    # `status` filtra a "fila de ação" (ex: só aguardando_conferencia).
    # `limit`/`offset` existem desde já — mesmo com poucas dezenas de
    # pedidos hoje, é o tipo de coisa que fica muito mais cara de adicionar
    # depois (muda contrato de API) do que de já nascer certo.
    async def listar(
        self, status: StatusPedido | None = None, limit: int = 50, offset: int = 0
    ) -> list[Pedido]: ...

    # Total de registros que batem no MESMO filtro de `listar` (sem
    # limit/offset) — usado pra montar paginação no cliente da API (ex:
    # "mostrando 50 de 230").
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
