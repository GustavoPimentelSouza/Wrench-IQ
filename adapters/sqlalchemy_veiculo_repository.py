from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.orm_models import VeiculoORM
from domain.veiculo import Veiculo


def _to_domain(orm: VeiculoORM) -> Veiculo:
    return Veiculo(
        id=orm.id,
        cliente_id=orm.cliente_id,
        marca=orm.marca,
        modelo=orm.modelo,
        ano=orm.ano,
        placa=orm.placa,
        criado_em=orm.criado_em,
    )


class SqlAlchemyVeiculoRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def criar(self, veiculo: Veiculo) -> Veiculo:
        orm = VeiculoORM(
            id=veiculo.id,
            cliente_id=veiculo.cliente_id,
            marca=veiculo.marca,
            modelo=veiculo.modelo,
            ano=veiculo.ano,
            placa=veiculo.placa,
            criado_em=veiculo.criado_em,
        )
        self._session.add(orm)
        await self._session.commit()
        await self._session.refresh(orm)
        return _to_domain(orm)

    async def listar_por_cliente(self, cliente_id: UUID) -> list[Veiculo]:
        result = await self._session.execute(
            select(VeiculoORM).where(VeiculoORM.cliente_id == cliente_id)
        )
        return [_to_domain(orm) for orm in result.scalars().all()]

    async def buscar_por_id(self, veiculo_id: UUID) -> Veiculo | None:
        orm = await self._session.get(VeiculoORM, veiculo_id)
        return _to_domain(orm) if orm else None

    async def atualizar(self, veiculo: Veiculo) -> Veiculo | None:
        orm = await self._session.get(VeiculoORM, veiculo.id)
        if orm is None:
            return None
        orm.marca = veiculo.marca
        orm.modelo = veiculo.modelo
        orm.ano = veiculo.ano
        orm.placa = veiculo.placa
        await self._session.commit()
        await self._session.refresh(orm)
        return _to_domain(orm)

    async def excluir(self, veiculo_id: UUID) -> bool:
        orm = await self._session.get(VeiculoORM, veiculo_id)
        if orm is None:
            return False
        await self._session.delete(orm)
        await self._session.commit()
        return True
