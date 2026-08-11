from datetime import date, datetime, time, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.orm_models import ReclassificacaoEspecialidadeORM
from domain.especialidade import Especialidade
from domain.reclassificacao_especialidade import ReclassificacaoEspecialidade


def _codificar(especialidades: list[Especialidade]) -> str:
    return ",".join(e.value for e in especialidades)


def _decodificar(bruto: str) -> list[Especialidade]:
    return [Especialidade(valor) for valor in bruto.split(",") if valor]


def _to_domain(orm: ReclassificacaoEspecialidadeORM) -> ReclassificacaoEspecialidade:
    return ReclassificacaoEspecialidade(
        id=orm.id,
        protocolo_id=orm.protocolo_id,
        especialidades_originais=_decodificar(orm.especialidades_originais),
        especialidades_finais=_decodificar(orm.especialidades_finais),
        criado_em=orm.criado_em,
    )


class SqlAlchemyReclassificacaoRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def criar(
        self, reclassificacao: ReclassificacaoEspecialidade
    ) -> ReclassificacaoEspecialidade:
        orm = ReclassificacaoEspecialidadeORM(
            id=reclassificacao.id,
            protocolo_id=reclassificacao.protocolo_id,
            especialidades_originais=_codificar(reclassificacao.especialidades_originais),
            especialidades_finais=_codificar(reclassificacao.especialidades_finais),
            criado_em=reclassificacao.criado_em,
        )
        self._session.add(orm)
        await self._session.commit()
        await self._session.refresh(orm)
        return _to_domain(orm)

    async def listar_por_periodo(
        self, inicio: date, fim: date
    ) -> list[ReclassificacaoEspecialidade]:
        # fim é inclusivo (dia inteiro) — por isso vai até meia-noite do dia
        # seguinte, não até 00:00 do próprio "fim".
        inicio_dt = datetime.combine(inicio, time.min, tzinfo=timezone.utc)
        fim_dt = datetime.combine(fim, time.max, tzinfo=timezone.utc)
        result = await self._session.execute(
            select(ReclassificacaoEspecialidadeORM)
            .where(ReclassificacaoEspecialidadeORM.criado_em >= inicio_dt)
            .where(ReclassificacaoEspecialidadeORM.criado_em <= fim_dt)
        )
        return [_to_domain(orm) for orm in result.scalars().all()]
