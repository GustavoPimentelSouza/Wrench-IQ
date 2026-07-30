from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.orm_models import PecaORM
from application.peca_repository import PecaPossuiPedidosError
from domain.peca import Peca


# Isso aqui é o que faz esse arquivo ser um "adapter": traduz entre o mundo
# do SQLAlchemy (PecaORM, ligado ao banco) e o mundo puro do domínio (Peca,
# um dataclass sem dependência nenhuma). O resto do app (use cases, routers)
# só enxerga `Peca` — nunca importa PecaORM diretamente. Se um dia trocar
# Postgres por outro banco, só esse arquivo muda.
def _to_domain(orm: PecaORM) -> Peca:
    return Peca(
        id=orm.id,
        nome=orm.nome,
        marca_modelo_compativel=orm.marca_modelo_compativel,
        ano_compativel=orm.ano_compativel,
        preco=orm.preco,
        quantidade_estoque=orm.quantidade_estoque,
        imagem_url=orm.imagem_url,
        quantidade_minima=orm.quantidade_minima,
        criado_em=orm.criado_em,
    )


class SqlAlchemyPecaRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def criar(self, peca: Peca) -> Peca:
        orm = PecaORM(
            id=peca.id,
            nome=peca.nome,
            marca_modelo_compativel=peca.marca_modelo_compativel,
            ano_compativel=peca.ano_compativel,
            preco=peca.preco,
            quantidade_estoque=peca.quantidade_estoque,
            imagem_url=peca.imagem_url,
            quantidade_minima=peca.quantidade_minima,
            criado_em=peca.criado_em,
        )
        self._session.add(orm)
        await self._session.commit()
        # refresh() recarrega o objeto a partir do banco depois do commit —
        # necessário pra pegar valores que o Postgres gera sozinho (aqui é
        # só o default de criado_em, mas em Protocolo/Pedido é assim que o
        # `numero` sequencial, gerado por Identity(), volta pro Python).
        await self._session.refresh(orm)
        return _to_domain(orm)

    async def listar(self) -> list[Peca]:
        result = await self._session.execute(select(PecaORM))
        return [_to_domain(orm) for orm in result.scalars().all()]

    async def buscar_por_id(self, peca_id: UUID) -> Peca | None:
        orm = await self._session.get(PecaORM, peca_id)
        return _to_domain(orm) if orm else None

    async def atualizar(self, peca: Peca) -> Peca | None:
        orm = await self._session.get(PecaORM, peca.id)
        if orm is None:
            return None
        orm.nome = peca.nome
        orm.marca_modelo_compativel = peca.marca_modelo_compativel
        orm.ano_compativel = peca.ano_compativel
        orm.preco = peca.preco
        orm.quantidade_estoque = peca.quantidade_estoque
        orm.imagem_url = peca.imagem_url
        orm.quantidade_minima = peca.quantidade_minima
        await self._session.commit()
        await self._session.refresh(orm)
        return _to_domain(orm)

    async def excluir(self, peca_id: UUID) -> bool:
        orm = await self._session.get(PecaORM, peca_id)
        if orm is None:
            return False
        await self._session.delete(orm)
        try:
            await self._session.commit()
        except IntegrityError as erro:
            # O banco (não o Python) é quem realmente impede a exclusão —
            # a FK de Pedido pra Peca foi criada com ondelete="RESTRICT"
            # (ver adapters/orm_models.py). Aqui só traduzimos o erro cru do
            # Postgres pra uma exceção com significado de negócio, que o
            # router sabe transformar num 409 (ver infrastructure/routers/
            # pecas.py). Sem isso, o cliente da API veria um 500 genérico.
            await self._session.rollback()
            raise PecaPossuiPedidosError() from erro
        return True
