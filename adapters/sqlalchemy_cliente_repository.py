from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.orm_models import ClienteORM
from application.cliente_repository import ClientePossuiProtocolosError
from domain.cliente import Cliente


def _to_domain(orm: ClienteORM) -> Cliente:
    return Cliente(
        id=orm.id,
        nome=orm.nome,
        telefone=orm.telefone,
        email=orm.email,
        endereco=orm.endereco,
        cpf_cnpj=orm.cpf_cnpj,
        criado_em=orm.criado_em,
    )


class SqlAlchemyClienteRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def criar(self, cliente: Cliente) -> Cliente:
        orm = ClienteORM(
            id=cliente.id,
            nome=cliente.nome,
            telefone=cliente.telefone,
            email=cliente.email,
            endereco=cliente.endereco,
            cpf_cnpj=cliente.cpf_cnpj,
            criado_em=cliente.criado_em,
        )
        self._session.add(orm)
        await self._session.commit()
        await self._session.refresh(orm)
        return _to_domain(orm)

    async def listar(self) -> list[Cliente]:
        result = await self._session.execute(select(ClienteORM))
        return [_to_domain(orm) for orm in result.scalars().all()]

    async def buscar_por_id(self, cliente_id: UUID) -> Cliente | None:
        orm = await self._session.get(ClienteORM, cliente_id)
        return _to_domain(orm) if orm else None

    async def buscar_por_telefone(self, telefone: str) -> Cliente | None:
        result = await self._session.execute(
            select(ClienteORM).where(ClienteORM.telefone == telefone)
        )
        orm = result.scalar_one_or_none()
        return _to_domain(orm) if orm else None

    async def atualizar(self, cliente: Cliente) -> Cliente | None:
        orm = await self._session.get(ClienteORM, cliente.id)
        if orm is None:
            return None
        orm.nome = cliente.nome
        orm.telefone = cliente.telefone
        orm.email = cliente.email
        orm.endereco = cliente.endereco
        orm.cpf_cnpj = cliente.cpf_cnpj
        await self._session.commit()
        await self._session.refresh(orm)
        return _to_domain(orm)

    async def excluir(self, cliente_id: UUID) -> bool:
        orm = await self._session.get(ClienteORM, cliente_id)
        if orm is None:
            return False
        await self._session.delete(orm)
        try:
            await self._session.commit()
        except IntegrityError as erro:
            await self._session.rollback()
            raise ClientePossuiProtocolosError() from erro
        return True
