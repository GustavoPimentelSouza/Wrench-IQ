from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.orm_models import UsuarioORM
from domain.usuario import Usuario


def _to_domain(orm: UsuarioORM) -> Usuario:
    return Usuario(
        id=orm.id,
        nome=orm.nome,
        email=orm.email,
        senha_hash=orm.senha_hash,
        papel=orm.papel,
        ativo=orm.ativo,
        criado_em=orm.criado_em,
    )


class SqlAlchemyUsuarioRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def criar(self, usuario: Usuario) -> Usuario:
        orm = UsuarioORM(
            id=usuario.id,
            nome=usuario.nome,
            email=usuario.email,
            senha_hash=usuario.senha_hash,
            papel=usuario.papel,
            ativo=usuario.ativo,
            criado_em=usuario.criado_em,
        )
        self._session.add(orm)
        await self._session.commit()
        await self._session.refresh(orm)
        return _to_domain(orm)

    async def buscar_por_id(self, usuario_id: UUID) -> Usuario | None:
        orm = await self._session.get(UsuarioORM, usuario_id)
        return _to_domain(orm) if orm else None

    async def buscar_por_email(self, email: str) -> Usuario | None:
        result = await self._session.execute(
            select(UsuarioORM).where(UsuarioORM.email == email)
        )
        orm = result.scalar_one_or_none()
        return _to_domain(orm) if orm else None
