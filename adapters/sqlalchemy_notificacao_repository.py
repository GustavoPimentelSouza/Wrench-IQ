from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.orm_models import NotificacaoORM
from domain.notificacao import Notificacao, TipoNotificacao


def _to_domain(orm: NotificacaoORM) -> Notificacao:
    return Notificacao(
        id=orm.id,
        cliente_id=orm.cliente_id,
        tipo=TipoNotificacao(orm.tipo),
        mensagem=orm.mensagem,
        criado_em=orm.criado_em,
        enviada=orm.enviada,
        enviada_em=orm.enviada_em,
    )


class SqlAlchemyNotificacaoRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def criar(self, notificacao: Notificacao) -> Notificacao:
        orm = NotificacaoORM(
            id=notificacao.id,
            cliente_id=notificacao.cliente_id,
            tipo=notificacao.tipo.value,
            mensagem=notificacao.mensagem,
            criado_em=notificacao.criado_em,
            enviada=notificacao.enviada,
            enviada_em=notificacao.enviada_em,
        )
        self._session.add(orm)
        await self._session.commit()
        await self._session.refresh(orm)
        return _to_domain(orm)

    async def listar_pendentes(self) -> list[Notificacao]:
        result = await self._session.execute(
            select(NotificacaoORM)
            .where(NotificacaoORM.enviada.is_(False))
            .order_by(NotificacaoORM.criado_em)
        )
        return [_to_domain(orm) for orm in result.scalars().all()]

    async def marcar_enviada(self, notificacao_id: UUID) -> Notificacao | None:
        orm = await self._session.get(NotificacaoORM, notificacao_id)
        if orm is None:
            return None
        orm.enviada = True
        orm.enviada_em = datetime.now(timezone.utc)
        await self._session.commit()
        await self._session.refresh(orm)
        return _to_domain(orm)
