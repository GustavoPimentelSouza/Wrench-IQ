from datetime import date, datetime, time, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from adapters._especialidades import carregar, substituir
from adapters.orm_models import AgendamentoORM, agendamento_especialidades
from domain.agendamento import Agendamento, StatusAgendamento

# Único, ainda AGENDADO/CONFIRMADO — quem já foi cancelado/concluído/deu
# no-show não conta pra ocupar vaga nem pra ser varrido de novo pelo
# worker de no-show.
_STATUS_OCUPA_VAGA = (StatusAgendamento.AGENDADO.value, StatusAgendamento.CONFIRMADO.value)


async def _to_domain(session: AsyncSession, orm: AgendamentoORM) -> Agendamento:
    especialidades = await carregar(
        session, agendamento_especialidades, "agendamento_id", orm.id
    )
    return Agendamento(
        id=orm.id,
        cliente_id=orm.cliente_id,
        data_hora=orm.data_hora,
        status=StatusAgendamento(orm.status),
        criado_em=orm.criado_em,
        descricao=orm.descricao,
        especialidades=especialidades,
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
        await substituir(
            self._session,
            agendamento_especialidades,
            "agendamento_id",
            orm.id,
            agendamento.especialidades,
        )
        await self._session.commit()
        return await _to_domain(self._session, orm)

    async def listar(self) -> list[Agendamento]:
        result = await self._session.execute(
            select(AgendamentoORM).order_by(AgendamentoORM.data_hora)
        )
        return [await _to_domain(self._session, orm) for orm in result.scalars().all()]

    async def listar_por_cliente(self, cliente_id: UUID) -> list[Agendamento]:
        result = await self._session.execute(
            select(AgendamentoORM)
            .where(AgendamentoORM.cliente_id == cliente_id)
            .order_by(AgendamentoORM.data_hora)
        )
        return [await _to_domain(self._session, orm) for orm in result.scalars().all()]

    async def listar_por_data(self, data: date) -> list[Agendamento]:
        inicio = datetime.combine(data, time.min, tzinfo=timezone.utc)
        fim = datetime.combine(data, time.max, tzinfo=timezone.utc)
        result = await self._session.execute(
            select(AgendamentoORM)
            .where(AgendamentoORM.data_hora >= inicio)
            .where(AgendamentoORM.data_hora <= fim)
            .where(AgendamentoORM.status.in_(_STATUS_OCUPA_VAGA))
        )
        return [await _to_domain(self._session, orm) for orm in result.scalars().all()]

    async def listar_pendentes_antes_de(self, limite: datetime) -> list[Agendamento]:
        result = await self._session.execute(
            select(AgendamentoORM)
            .where(AgendamentoORM.data_hora < limite)
            .where(AgendamentoORM.status.in_(_STATUS_OCUPA_VAGA))
        )
        return [await _to_domain(self._session, orm) for orm in result.scalars().all()]

    async def buscar_por_id(self, agendamento_id: UUID) -> Agendamento | None:
        orm = await self._session.get(AgendamentoORM, agendamento_id)
        return await _to_domain(self._session, orm) if orm else None

    async def atualizar(self, agendamento: Agendamento) -> Agendamento | None:
        orm = await self._session.get(AgendamentoORM, agendamento.id)
        if orm is None:
            return None
        orm.data_hora = agendamento.data_hora
        orm.status = agendamento.status.value
        orm.descricao = agendamento.descricao
        await self._session.commit()
        await self._session.refresh(orm)
        await substituir(
            self._session,
            agendamento_especialidades,
            "agendamento_id",
            orm.id,
            agendamento.especialidades,
        )
        await self._session.commit()
        return await _to_domain(self._session, orm)

    async def excluir(self, agendamento_id: UUID) -> bool:
        orm = await self._session.get(AgendamentoORM, agendamento_id)
        if orm is None:
            return False
        await self._session.delete(orm)
        await self._session.commit()
        return True
