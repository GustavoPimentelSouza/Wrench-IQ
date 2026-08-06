from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.orm_models import AgendamentoORM
from domain.agendamento import Agendamento, StatusAgendamento


def _to_domain(orm: AgendamentoORM) -> Agendamento:
    return Agendamento(
        id=orm.id,
        cliente_id=orm.cliente_id,
        data_hora=orm.data_hora,
        status=StatusAgendamento(orm.status),
        criado_em=orm.criado_em,
        descricao=orm.descricao,
    )


class SqlAlchemyAgendamentoRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def criar(self, agendamento: Agendamento) -> Agendamento:
        orm = AgendamentoORM(
            id=agendamento.id,
            cliente_id=agendamento.cliente_id,
            data_hora=agendamento.data_hora,
            status=agendamento.status.value,
            criado_em=agendamento.criado_em,
            descricao=agendamento.descricao,
        )
        self._session.add(orm)
        await self._session.commit()
        await self._session.refresh(orm)
        return _to_domain(orm)

    async def listar(self) -> list[Agendamento]:
        result = await self._session.execute(
            select(AgendamentoORM).order_by(AgendamentoORM.data_hora)
        )
        return [_to_domain(orm) for orm in result.scalars().all()]

    async def listar_por_cliente(self, cliente_id: UUID) -> list[Agendamento]:
        result = await self._session.execute(
            select(AgendamentoORM)
            .where(AgendamentoORM.cliente_id == cliente_id)
            .order_by(AgendamentoORM.data_hora)
        )
        return [_to_domain(orm) for orm in result.scalars().all()]

    async def buscar_por_id(self, agendamento_id: UUID) -> Agendamento | None:
        orm = await self._session.get(AgendamentoORM, agendamento_id)
        return _to_domain(orm) if orm else None

    async def atualizar(self, agendamento: Agendamento) -> Agendamento | None:
        orm = await self._session.get(AgendamentoORM, agendamento.id)
        if orm is None:
            return None
        orm.data_hora = agendamento.data_hora
        orm.status = agendamento.status.value
        orm.descricao = agendamento.descricao
        await self._session.commit()
        await self._session.refresh(orm)
        return _to_domain(orm)

    async def excluir(self, agendamento_id: UUID) -> bool:
        orm = await self._session.get(AgendamentoORM, agendamento_id)
        if orm is None:
            return False
        await self._session.delete(orm)
        await self._session.commit()
        return True
