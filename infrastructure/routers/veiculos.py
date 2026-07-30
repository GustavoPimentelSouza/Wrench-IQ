from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.sqlalchemy_veiculo_repository import SqlAlchemyVeiculoRepository
from application.veiculo_use_cases import VeiculoUseCases
from domain.usuario import Usuario
from domain.veiculo import Veiculo
from infrastructure.db import get_db
from infrastructure.security_dependencies import get_current_user

router = APIRouter(prefix="/veiculos", tags=["veiculos"])


class _VeiculoFormulario(BaseModel):
    marca: str
    modelo: str
    ano: str
    placa: str


class VeiculoCreate(_VeiculoFormulario):
    cliente_id: UUID


class VeiculoUpdate(_VeiculoFormulario):
    pass


class VeiculoOut(BaseModel):
    id: UUID
    cliente_id: UUID
    marca: str
    modelo: str
    ano: str
    placa: str
    criado_em: datetime


def get_use_cases(session: AsyncSession = Depends(get_db)) -> VeiculoUseCases:
    return VeiculoUseCases(SqlAlchemyVeiculoRepository(session))


@router.post("", response_model=VeiculoOut, status_code=201)
async def criar_veiculo(
    payload: VeiculoCreate,
    use_cases: VeiculoUseCases = Depends(get_use_cases),
    _usuario: Usuario = Depends(get_current_user),
) -> Veiculo:
    veiculo = Veiculo(
        id=uuid4(),
        cliente_id=payload.cliente_id,
        marca=payload.marca,
        modelo=payload.modelo,
        ano=payload.ano,
        placa=payload.placa,
        criado_em=datetime.now(timezone.utc),
    )
    return await use_cases.criar(veiculo)


@router.get("", response_model=list[VeiculoOut])
async def listar_veiculos(
    cliente_id: UUID,
    use_cases: VeiculoUseCases = Depends(get_use_cases),
) -> list[Veiculo]:
    return await use_cases.listar_por_cliente(cliente_id)


@router.get("/{veiculo_id}", response_model=VeiculoOut)
async def buscar_veiculo(
    veiculo_id: UUID, use_cases: VeiculoUseCases = Depends(get_use_cases)
) -> Veiculo:
    veiculo = await use_cases.buscar_por_id(veiculo_id)
    if veiculo is None:
        raise HTTPException(status_code=404, detail="Veículo não encontrado")
    return veiculo


@router.put("/{veiculo_id}", response_model=VeiculoOut)
async def atualizar_veiculo(
    veiculo_id: UUID,
    payload: VeiculoUpdate,
    use_cases: VeiculoUseCases = Depends(get_use_cases),
    _usuario: Usuario = Depends(get_current_user),
) -> Veiculo:
    existente = await use_cases.buscar_por_id(veiculo_id)
    if existente is None:
        raise HTTPException(status_code=404, detail="Veículo não encontrado")
    veiculo = Veiculo(
        id=veiculo_id,
        cliente_id=existente.cliente_id,
        marca=payload.marca,
        modelo=payload.modelo,
        ano=payload.ano,
        placa=payload.placa,
        criado_em=existente.criado_em,
    )
    atualizado = await use_cases.atualizar(veiculo)
    if atualizado is None:
        raise HTTPException(status_code=404, detail="Veículo não encontrado")
    return atualizado


@router.delete("/{veiculo_id}", status_code=204)
async def excluir_veiculo(
    veiculo_id: UUID,
    use_cases: VeiculoUseCases = Depends(get_use_cases),
    _usuario: Usuario = Depends(get_current_user),
) -> None:
    excluido = await use_cases.excluir(veiculo_id)
    if not excluido:
        raise HTTPException(status_code=404, detail="Veículo não encontrado")
