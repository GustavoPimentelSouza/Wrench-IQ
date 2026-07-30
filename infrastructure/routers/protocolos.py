from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.sqlalchemy_protocolo_repository import SqlAlchemyProtocoloRepository
from adapters.sqlalchemy_usuario_repository import SqlAlchemyUsuarioRepository
from application.protocolo_use_cases import (
    MecanicoInvalidoError,
    ProtocoloNaoEncontradoError,
    ProtocoloUseCases,
    TransicaoInvalidaError,
)
from domain.protocolo import Protocolo, StatusProtocolo
from domain.usuario import Usuario
from infrastructure.db import get_db
from infrastructure.security_dependencies import get_current_user

router = APIRouter(prefix="/protocolos", tags=["protocolos"])


class ProtocoloCreate(BaseModel):
    cliente_id: UUID
    veiculo: str
    categoria: str
    descricao: str | None = None
    mecanico_id: UUID | None = None
    # Sem campo `status` aqui — todo protocolo nasce em AGUARDANDO_APROVACAO,
    # sem exceção. Deixar o cliente da API escolher o status inicial
    # permitiria pular a máquina de estados na criação (ex: já nascer
    # "pronto").


class ProtocoloUpdate(BaseModel):
    veiculo: str
    categoria: str
    descricao: str | None = None
    mecanico_id: UUID | None = None
    # Também sem `status` — mudar de estado só é possível pelos endpoints
    # /aprovar, /concluir, /cancelar abaixo.


class ProtocoloOut(BaseModel):
    id: UUID
    numero: int
    cliente_id: UUID
    veiculo: str
    categoria: str
    status: StatusProtocolo
    descricao: str | None
    mecanico_id: UUID | None
    criado_em: datetime
    atualizado_em: datetime


def get_use_cases(session: AsyncSession = Depends(get_db)) -> ProtocoloUseCases:
    return ProtocoloUseCases(
        SqlAlchemyProtocoloRepository(session), SqlAlchemyUsuarioRepository(session)
    )


@router.post("", response_model=ProtocoloOut, status_code=201)
async def criar_protocolo(
    payload: ProtocoloCreate,
    use_cases: ProtocoloUseCases = Depends(get_use_cases),
    _usuario: Usuario = Depends(get_current_user),
) -> Protocolo:
    protocolo = Protocolo(
        id=uuid4(),
        cliente_id=payload.cliente_id,
        veiculo=payload.veiculo,
        categoria=payload.categoria,
        status=StatusProtocolo.AGUARDANDO_APROVACAO,
        descricao=payload.descricao,
        mecanico_id=payload.mecanico_id,
        criado_em=datetime.now(timezone.utc),
    )
    try:
        return await use_cases.criar(protocolo)
    except MecanicoInvalidoError:
        raise HTTPException(
            status_code=400,
            detail="mecanico_id precisa ser de um usuário existente com papel mecânico",
        )


@router.get("", response_model=list[ProtocoloOut])
async def listar_protocolos(
    cliente_id: UUID | None = None,
    use_cases: ProtocoloUseCases = Depends(get_use_cases),
) -> list[Protocolo]:
    if cliente_id is not None:
        return await use_cases.listar_por_cliente(cliente_id)
    return await use_cases.listar()


@router.get("/{protocolo_id}", response_model=ProtocoloOut)
async def buscar_protocolo(
    protocolo_id: UUID, use_cases: ProtocoloUseCases = Depends(get_use_cases)
) -> Protocolo:
    protocolo = await use_cases.buscar_por_id(protocolo_id)
    if protocolo is None:
        raise HTTPException(status_code=404, detail="Protocolo não encontrado")
    return protocolo


@router.put("/{protocolo_id}", response_model=ProtocoloOut)
async def atualizar_protocolo(
    protocolo_id: UUID,
    payload: ProtocoloUpdate,
    use_cases: ProtocoloUseCases = Depends(get_use_cases),
    _usuario: Usuario = Depends(get_current_user),
) -> Protocolo:
    existente = await use_cases.buscar_por_id(protocolo_id)
    if existente is None:
        raise HTTPException(status_code=404, detail="Protocolo não encontrado")
    protocolo = Protocolo(
        id=protocolo_id,
        numero=existente.numero,
        cliente_id=existente.cliente_id,
        veiculo=payload.veiculo,
        categoria=payload.categoria,
        status=existente.status,
        descricao=payload.descricao,
        mecanico_id=payload.mecanico_id,
        criado_em=existente.criado_em,
    )
    try:
        atualizada = await use_cases.atualizar(protocolo)
    except MecanicoInvalidoError:
        raise HTTPException(
            status_code=400,
            detail="mecanico_id precisa ser de um usuário existente com papel mecânico",
        )
    if atualizada is None:
        raise HTTPException(status_code=404, detail="Protocolo não encontrado")
    return atualizada


@router.post("/{protocolo_id}/aprovar", response_model=ProtocoloOut)
async def aprovar_protocolo(
    protocolo_id: UUID,
    use_cases: ProtocoloUseCases = Depends(get_use_cases),
    _usuario: Usuario = Depends(get_current_user),
) -> Protocolo:
    try:
        return await use_cases.aprovar(protocolo_id)
    except ProtocoloNaoEncontradoError:
        raise HTTPException(status_code=404, detail="Protocolo não encontrado")
    except TransicaoInvalidaError:
        raise HTTPException(
            status_code=409, detail="Protocolo não está aguardando aprovação"
        )


@router.post("/{protocolo_id}/concluir", response_model=ProtocoloOut)
async def concluir_protocolo(
    protocolo_id: UUID,
    use_cases: ProtocoloUseCases = Depends(get_use_cases),
    _usuario: Usuario = Depends(get_current_user),
) -> Protocolo:
    try:
        return await use_cases.concluir(protocolo_id)
    except ProtocoloNaoEncontradoError:
        raise HTTPException(status_code=404, detail="Protocolo não encontrado")
    except TransicaoInvalidaError:
        raise HTTPException(status_code=409, detail="Protocolo não está em execução")


@router.post("/{protocolo_id}/cancelar", response_model=ProtocoloOut)
async def cancelar_protocolo(
    protocolo_id: UUID,
    use_cases: ProtocoloUseCases = Depends(get_use_cases),
    _usuario: Usuario = Depends(get_current_user),
) -> Protocolo:
    try:
        return await use_cases.cancelar(protocolo_id)
    except ProtocoloNaoEncontradoError:
        raise HTTPException(status_code=404, detail="Protocolo não encontrado")
    except TransicaoInvalidaError:
        raise HTTPException(
            status_code=409, detail="Protocolo já está concluído ou cancelado"
        )
