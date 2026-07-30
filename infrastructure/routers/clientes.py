from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.sqlalchemy_cliente_repository import SqlAlchemyClienteRepository
from application.cliente_repository import ClientePossuiProtocolosError
from application.cliente_use_cases import ClienteUseCases
from domain.cliente import Cliente, telefone_valido
from domain.usuario import Usuario
from infrastructure.db import get_db
from infrastructure.security_dependencies import get_current_user

router = APIRouter(prefix="/clientes", tags=["clientes"])


class _ClienteFormulario(BaseModel):
    nome: str
    telefone: str
    email: str | None = None
    endereco: str | None = None
    cpf_cnpj: str | None = None

    @field_validator("telefone")
    @classmethod
    def validar_telefone(cls, valor: str) -> str:
        if not telefone_valido(valor):
            raise ValueError(
                "Telefone deve conter só dígitos, entre 10 e 15 caracteres (ex: 5511999999999)"
            )
        return valor


class ClienteCreate(_ClienteFormulario):
    pass


class ClienteUpdate(_ClienteFormulario):
    pass


class ClienteOut(BaseModel):
    id: UUID
    nome: str
    telefone: str
    email: str | None
    endereco: str | None
    cpf_cnpj: str | None
    criado_em: datetime


def get_use_cases(session: AsyncSession = Depends(get_db)) -> ClienteUseCases:
    return ClienteUseCases(SqlAlchemyClienteRepository(session))


@router.post("", response_model=ClienteOut, status_code=201)
async def criar_cliente(
    payload: ClienteCreate,
    use_cases: ClienteUseCases = Depends(get_use_cases),
    _usuario: Usuario = Depends(get_current_user),
) -> Cliente:
    cliente = Cliente(
        id=uuid4(),
        nome=payload.nome,
        telefone=payload.telefone,
        email=payload.email,
        endereco=payload.endereco,
        cpf_cnpj=payload.cpf_cnpj,
        criado_em=datetime.now(timezone.utc),
    )
    return await use_cases.criar(cliente)


@router.get("", response_model=list[ClienteOut])
async def listar_clientes(use_cases: ClienteUseCases = Depends(get_use_cases)) -> list[Cliente]:
    return await use_cases.listar()


@router.get("/{cliente_id}", response_model=ClienteOut)
async def buscar_cliente(
    cliente_id: UUID, use_cases: ClienteUseCases = Depends(get_use_cases)
) -> Cliente:
    cliente = await use_cases.buscar_por_id(cliente_id)
    if cliente is None:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return cliente


@router.put("/{cliente_id}", response_model=ClienteOut)
async def atualizar_cliente(
    cliente_id: UUID,
    payload: ClienteUpdate,
    use_cases: ClienteUseCases = Depends(get_use_cases),
    _usuario: Usuario = Depends(get_current_user),
) -> Cliente:
    existente = await use_cases.buscar_por_id(cliente_id)
    if existente is None:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    cliente = Cliente(
        id=cliente_id,
        nome=payload.nome,
        telefone=payload.telefone,
        email=payload.email,
        endereco=payload.endereco,
        cpf_cnpj=payload.cpf_cnpj,
        criado_em=existente.criado_em,
    )
    atualizado = await use_cases.atualizar(cliente)
    if atualizado is None:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return atualizado


@router.delete("/{cliente_id}", status_code=204)
async def excluir_cliente(
    cliente_id: UUID,
    use_cases: ClienteUseCases = Depends(get_use_cases),
    _usuario: Usuario = Depends(get_current_user),
) -> None:
    try:
        excluido = await use_cases.excluir(cliente_id)
    except ClientePossuiProtocolosError:
        raise HTTPException(
            status_code=409,
            detail=(
                "Não é possível excluir: cliente possui registros vinculados "
                "(protocolos, veículos, mensagens ou agendamentos)"
            ),
        )
    if not excluido:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
