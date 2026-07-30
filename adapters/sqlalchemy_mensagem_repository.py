from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from adapters.orm_models import MensagemORM
from domain.mensagem import CategoriaMensagem, Mensagem


def _to_domain(orm: MensagemORM) -> Mensagem:
    return Mensagem(
        id=orm.id,
        cliente_id=orm.cliente_id,
        texto=orm.texto,
        categoria=CategoriaMensagem(orm.categoria),
        criado_em=orm.criado_em,
    )


class SqlAlchemyMensagemRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def criar(self, mensagem: Mensagem) -> Mensagem:
        orm = MensagemORM(
            id=mensagem.id,
            cliente_id=mensagem.cliente_id,
            texto=mensagem.texto,
            categoria=mensagem.categoria.value,
            criado_em=mensagem.criado_em,
        )
        self._session.add(orm)
        await self._session.commit()
        await self._session.refresh(orm)
        return _to_domain(orm)

    async def buscar_por_id(self, mensagem_id: UUID) -> Mensagem | None:
        orm = await self._session.get(MensagemORM, mensagem_id)
        return _to_domain(orm) if orm else None
