from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.orm_models import PecaORM
from application.embedding_service import EmbeddingService
from application.peca_repository import PecaPossuiPedidosError
from domain.peca import Peca

# Acima disso, cosine_distance indica "não é a mesma coisa" — calibrado
# testando uma busca sem correspondência real no catálogo (~0.43-0.46)
# contra uma busca com correspondência boa (~0.22-0.26). Sem esse corte, a
# busca sempre devolvia o item "menos distante" mesmo quando nada no
# catálogo tinha a ver com o que o cliente pediu.
_LIMITE_DISTANCIA_SEMANTICA = 0.35


# Traduz PecaORM (SQLAlchemy) <-> Peca (domínio puro). Só esse arquivo
# conhece PecaORM.
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


def _texto_busca(peca: Peca) -> str:
    return f"{peca.nome} {peca.marca_modelo_compativel} {peca.ano_compativel}"


class SqlAlchemyPecaRepository:
    def __init__(self, session: AsyncSession, embedding_service: EmbeddingService):
        self._session = session
        self._embeddings = embedding_service

    async def criar(self, peca: Peca) -> Peca:
        embedding = await self._embeddings.gerar_embedding(_texto_busca(peca))
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
            embedding=embedding,
        )
        self._session.add(orm)
        await self._session.commit()
        await self._session.refresh(orm)  # recarrega valores gerados pelo banco
        return _to_domain(orm)

    async def listar(self) -> list[Peca]:
        result = await self._session.execute(select(PecaORM))
        return [_to_domain(orm) for orm in result.scalars().all()]

    async def buscar_por_id(self, peca_id: UUID) -> Peca | None:
        orm = await self._session.get(PecaORM, peca_id)
        return _to_domain(orm) if orm else None

    async def buscar_por_nome_aproximado(self, texto: str) -> list[Peca]:
        # Busca semântica (pgvector): compara o SIGNIFICADO da descrição do
        # cliente com o das peças cadastradas, em vez de bater substring
        # literal — "paralama pra fan 160" e "para-lama de uma honda 160
        # fan" viram vetores parecidos mesmo sem nenhuma palavra em comum, e
        # "vela" nunca fica próximo de "paralama". Substituiu a busca por
        # palavra-chave (ILIKE), que não generalizava pras várias formas
        # diferentes que um cliente pergunta a mesma coisa.
        vetor_busca = await self._embeddings.gerar_embedding(texto)
        distancia = PecaORM.embedding.cosine_distance(vetor_busca)
        result = await self._session.execute(
            select(PecaORM)
            .where(PecaORM.embedding.isnot(None))
            .where(distancia < _LIMITE_DISTANCIA_SEMANTICA)
            .order_by(distancia)
            .limit(5)
        )
        return [_to_domain(orm) for orm in result.scalars().all()]

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
        orm.embedding = await self._embeddings.gerar_embedding(_texto_busca(peca))
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
            # FK Pedido->Peca com ondelete=RESTRICT; traduz pro router virar 409.
            await self._session.rollback()
            raise PecaPossuiPedidosError() from erro
        return True
