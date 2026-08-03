from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.orm_models import ProtocoloORM
from domain.protocolo import Protocolo, StatusProtocolo


def _to_domain(orm: ProtocoloORM) -> Protocolo:
    return Protocolo(
        id=orm.id,
        numero=orm.numero,
        cliente_id=orm.cliente_id,
        veiculo=orm.veiculo,
        categoria=orm.categoria,
        status=StatusProtocolo(orm.status),
        descricao=orm.descricao,
        mecanico_id=orm.mecanico_id,
        criado_em=orm.criado_em,
        atualizado_em=orm.atualizado_em,
        valor_orcamento=orm.valor_orcamento,
        motivo_cancelamento=orm.motivo_cancelamento,
    )


class SqlAlchemyProtocoloRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def criar(self, protocolo: Protocolo) -> Protocolo:
        orm = ProtocoloORM(
            id=protocolo.id,
            cliente_id=protocolo.cliente_id,
            veiculo=protocolo.veiculo,
            categoria=protocolo.categoria,
            status=protocolo.status.value,
            descricao=protocolo.descricao,
            mecanico_id=protocolo.mecanico_id,
            criado_em=protocolo.criado_em,
            valor_orcamento=protocolo.valor_orcamento,
        )
        self._session.add(orm)
        await self._session.commit()
        await self._session.refresh(orm)
        return _to_domain(orm)

    async def listar(self) -> list[Protocolo]:
        result = await self._session.execute(
            select(ProtocoloORM).order_by(ProtocoloORM.numero.desc())
        )
        return [_to_domain(orm) for orm in result.scalars().all()]

    async def listar_por_cliente(self, cliente_id: UUID) -> list[Protocolo]:
        result = await self._session.execute(
            select(ProtocoloORM)
            .where(ProtocoloORM.cliente_id == cliente_id)
            .order_by(ProtocoloORM.numero.desc())
        )
        return [_to_domain(orm) for orm in result.scalars().all()]

    async def buscar_por_id(self, protocolo_id: UUID) -> Protocolo | None:
        orm = await self._session.get(ProtocoloORM, protocolo_id)
        return _to_domain(orm) if orm else None

    async def atualizar(self, protocolo: Protocolo) -> Protocolo | None:
        orm = await self._session.get(ProtocoloORM, protocolo.id)
        if orm is None:
            return None
        orm.veiculo = protocolo.veiculo
        orm.categoria = protocolo.categoria
        orm.status = protocolo.status.value
        orm.descricao = protocolo.descricao
        orm.mecanico_id = protocolo.mecanico_id
        orm.valor_orcamento = protocolo.valor_orcamento
        orm.motivo_cancelamento = protocolo.motivo_cancelamento
        await self._session.commit()
        await self._session.refresh(orm)
        return _to_domain(orm)
