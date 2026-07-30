from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.orm_models import PedidoORM
from domain.pedido import Pedido, StatusPedido, TipoEntrega


def _to_domain(orm: PedidoORM) -> Pedido:
    return Pedido(
        id=orm.id,
        numero=orm.numero,
        cliente_id=orm.cliente_id,
        peca_id=orm.peca_id,
        quantidade=orm.quantidade,
        valor_total=orm.valor_total,
        tipo_entrega=TipoEntrega(orm.tipo_entrega),
        status=StatusPedido(orm.status),
        endereco_entrega=orm.endereco_entrega,
        link_pagamento=orm.link_pagamento,
        entregue_em=orm.entregue_em,
        criado_em=orm.criado_em,
    )


class SqlAlchemyPedidoRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def criar(self, pedido: Pedido) -> Pedido:
        orm = PedidoORM(
            id=pedido.id,
            cliente_id=pedido.cliente_id,
            peca_id=pedido.peca_id,
            quantidade=pedido.quantidade,
            valor_total=pedido.valor_total,
            tipo_entrega=pedido.tipo_entrega.value,
            status=pedido.status.value,
            endereco_entrega=pedido.endereco_entrega,
            link_pagamento=pedido.link_pagamento,
            entregue_em=pedido.entregue_em,
            criado_em=pedido.criado_em,
        )
        self._session.add(orm)
        await self._session.commit()
        await self._session.refresh(orm)
        return _to_domain(orm)

    async def listar(
        self, status: StatusPedido | None = None, limit: int = 50, offset: int = 0
    ) -> list[Pedido]:
        query = select(PedidoORM)
        if status is not None:
            query = query.where(PedidoORM.status == status.value)
        query = query.order_by(PedidoORM.numero.desc()).limit(limit).offset(offset)
        result = await self._session.execute(query)
        return [_to_domain(orm) for orm in result.scalars().all()]

    async def contar(self, status: StatusPedido | None = None) -> int:
        query = select(func.count()).select_from(PedidoORM)
        if status is not None:
            query = query.where(PedidoORM.status == status.value)
        result = await self._session.execute(query)
        return result.scalar_one()

    async def listar_por_cliente(
        self,
        cliente_id: UUID,
        status: StatusPedido | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Pedido]:
        query = select(PedidoORM).where(PedidoORM.cliente_id == cliente_id)
        if status is not None:
            query = query.where(PedidoORM.status == status.value)
        query = query.order_by(PedidoORM.numero.desc()).limit(limit).offset(offset)
        result = await self._session.execute(query)
        return [_to_domain(orm) for orm in result.scalars().all()]

    async def contar_por_cliente(
        self, cliente_id: UUID, status: StatusPedido | None = None
    ) -> int:
        query = (
            select(func.count())
            .select_from(PedidoORM)
            .where(PedidoORM.cliente_id == cliente_id)
        )
        if status is not None:
            query = query.where(PedidoORM.status == status.value)
        result = await self._session.execute(query)
        return result.scalar_one()

    async def buscar_por_id(self, pedido_id: UUID) -> Pedido | None:
        orm = await self._session.get(PedidoORM, pedido_id)
        return _to_domain(orm) if orm else None

    async def atualizar(self, pedido: Pedido) -> Pedido | None:
        orm = await self._session.get(PedidoORM, pedido.id)
        if orm is None:
            return None
        orm.status = pedido.status.value
        orm.entregue_em = pedido.entregue_em
        await self._session.commit()
        await self._session.refresh(orm)
        return _to_domain(orm)
