from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from adapters.orm_models import ItemAdicionalProtocoloORM
from domain.item_adicional_protocolo import ItemAdicionalProtocolo, StatusItemAdicional


def _to_domain(orm: ItemAdicionalProtocoloORM) -> ItemAdicionalProtocolo:
    return ItemAdicionalProtocolo(
        id=orm.id,
        protocolo_id=orm.protocolo_id,
        descricao=orm.descricao,
        peca_id=orm.peca_id,
        valor=orm.valor,
        status=StatusItemAdicional(orm.status),
        criado_em=orm.criado_em,
    )


class SqlAlchemyItemAdicionalRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def criar(self, item: ItemAdicionalProtocolo) -> ItemAdicionalProtocolo:
        orm = ItemAdicionalProtocoloORM(
            id=item.id,
            protocolo_id=item.protocolo_id,
            descricao=item.descricao,
            peca_id=item.peca_id,
            valor=item.valor,
            status=item.status.value,
            criado_em=item.criado_em,
        )
        self._session.add(orm)
        await self._session.commit()
        await self._session.refresh(orm)
        return _to_domain(orm)

    async def buscar_por_id(self, item_id: UUID) -> ItemAdicionalProtocolo | None:
        orm = await self._session.get(ItemAdicionalProtocoloORM, item_id)
        return _to_domain(orm) if orm else None

    async def atualizar(self, item: ItemAdicionalProtocolo) -> ItemAdicionalProtocolo | None:
        orm = await self._session.get(ItemAdicionalProtocoloORM, item.id)
        if orm is None:
            return None
        orm.status = item.status.value
        await self._session.commit()
        await self._session.refresh(orm)
        return _to_domain(orm)
