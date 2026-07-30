from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.orm_models import MovimentacaoEstoqueORM
from domain.movimentacao_estoque import MovimentacaoEstoque, TipoMovimentacao


def _to_domain(orm: MovimentacaoEstoqueORM) -> MovimentacaoEstoque:
    return MovimentacaoEstoque(
        id=orm.id,
        peca_id=orm.peca_id,
        tipo=TipoMovimentacao(orm.tipo),
        quantidade=orm.quantidade,
        criado_em=orm.criado_em,
    )


class SqlAlchemyMovimentacaoEstoqueRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def criar(self, movimentacao: MovimentacaoEstoque) -> MovimentacaoEstoque:
        orm = MovimentacaoEstoqueORM(
            id=movimentacao.id,
            peca_id=movimentacao.peca_id,
            tipo=movimentacao.tipo.value,
            quantidade=movimentacao.quantidade,
            criado_em=movimentacao.criado_em,
        )
        self._session.add(orm)
        await self._session.commit()
        await self._session.refresh(orm)
        return _to_domain(orm)

    async def listar_por_peca(self, peca_id: UUID) -> list[MovimentacaoEstoque]:
        result = await self._session.execute(
            select(MovimentacaoEstoqueORM)
            .where(MovimentacaoEstoqueORM.peca_id == peca_id)
            .order_by(MovimentacaoEstoqueORM.criado_em.desc())
        )
        return [_to_domain(orm) for orm in result.scalars().all()]
