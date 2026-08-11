from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from adapters._especialidades import carregar, substituir
from adapters.orm_models import UsuarioORM, mecanico_especialidades
from domain.especialidade import Especialidade
from domain.usuario import PapelUsuario, Usuario


async def _to_domain(session: AsyncSession, orm: UsuarioORM) -> Usuario:
    especialidades = await carregar(session, mecanico_especialidades, "usuario_id", orm.id)
    return Usuario(
        id=orm.id,
        nome=orm.nome,
        email=orm.email,
        senha_hash=orm.senha_hash,
        papel=orm.papel,
        ativo=orm.ativo,
        criado_em=orm.criado_em,
        especialidades=especialidades,
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
        await substituir(
            self._session, mecanico_especialidades, "usuario_id", orm.id, usuario.especialidades
        )
        await self._session.commit()
        return await _to_domain(self._session, orm)

    async def buscar_por_id(self, usuario_id: UUID) -> Usuario | None:
        orm = await self._session.get(UsuarioORM, usuario_id)
        return await _to_domain(self._session, orm) if orm else None

    async def buscar_por_email(self, email: str) -> Usuario | None:
        result = await self._session.execute(
            select(UsuarioORM).where(UsuarioORM.email == email)
        )
        orm = result.scalar_one_or_none()
        return await _to_domain(self._session, orm) if orm else None

    async def listar_mecanicos_por_especialidade(
        self, especialidades: list[Especialidade]
    ) -> list[Usuario]:
        if not especialidades:
            return []
        valores = [e.value for e in especialidades]
        result = await self._session.execute(
            select(UsuarioORM)
            .join(
                mecanico_especialidades,
                mecanico_especialidades.c.usuario_id == UsuarioORM.id,
            )
            .where(UsuarioORM.papel == PapelUsuario.MECANICO)
            .where(UsuarioORM.ativo.is_(True))
            .where(mecanico_especialidades.c.especialidade.in_(valores))
            # .distinct() porque um mecânico com 2 especialidades que batem
            # a busca apareceria 2 vezes por causa do join.
            .distinct()
        )
        return [await _to_domain(self._session, orm) for orm in result.scalars().all()]
