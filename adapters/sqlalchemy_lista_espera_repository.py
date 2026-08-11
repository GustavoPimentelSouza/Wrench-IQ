from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.orm_models import ListaEsperaAgendamentoORM
from domain.especialidade import Especialidade
from domain.lista_espera_agendamento import ListaEsperaAgendamento


def _to_domain(orm: ListaEsperaAgendamentoORM) -> ListaEsperaAgendamento:
    return ListaEsperaAgendamento(
        id=orm.id,
        cliente_id=orm.cliente_id,
        especialidade=Especialidade(orm.especialidade),
        criado_em=orm.criado_em,
        atendido=orm.atendido,
    )


class SqlAlchemyListaEsperaRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def criar(self, entrada: ListaEsperaAgendamento) -> ListaEsperaAgendamento:
        orm = ListaEsperaAgendamentoORM(
            id=entrada.id,
            cliente_id=entrada.cliente_id,
            especialidade=entrada.especialidade.value,
            criado_em=entrada.criado_em,
            atendido=entrada.atendido,
        )
        self._session.add(orm)
        await self._session.commit()
        await self._session.refresh(orm)
        return _to_domain(orm)

    async def buscar_primeiro_pendente(
        self, especialidade: Especialidade
    ) -> ListaEsperaAgendamento | None:
        result = await self._session.execute(
            select(ListaEsperaAgendamentoORM)
            .where(ListaEsperaAgendamentoORM.especialidade == especialidade.value)
            .where(ListaEsperaAgendamentoORM.atendido.is_(False))
            .order_by(ListaEsperaAgendamentoORM.criado_em)
            .limit(1)
        )
        orm = result.scalar_one_or_none()
        return _to_domain(orm) if orm else None

    async def marcar_atendido(self, entrada_id: UUID) -> ListaEsperaAgendamento | None:
        orm = await self._session.get(ListaEsperaAgendamentoORM, entrada_id)
        if orm is None:
            return None
        orm.atendido = True
        await self._session.commit()
        await self._session.refresh(orm)
        return _to_domain(orm)
