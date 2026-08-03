from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.sqlalchemy_agendamento_repository import SqlAlchemyAgendamentoRepository
from application.agendamento_use_cases import AgendamentoUseCases
from domain.agendamento import Agendamento, StatusAgendamento
from domain.usuario import Usuario
from infrastructure.db import get_db
from infrastructure.security_dependencies import get_current_user

router = APIRouter(prefix="/agendamentos", tags=["agendamentos"])


class AgendamentoCreate(BaseModel):
    cliente_id: UUID
    data_hora: datetime
    status: StatusAgendamento = StatusAgendamento.AGENDADO


class AgendamentoUpdate(BaseModel):
    data_hora: datetime
    status: StatusAgendamento


class AgendamentoOut(BaseModel):
    id: UUID
    cliente_id: UUID
    data_hora: datetime
    status: StatusAgendamento
    criado_em: datetime


def get_use_cases(session: AsyncSession = Depends(get_db)) -> AgendamentoUseCases:
    return AgendamentoUseCases(SqlAlchemyAgendamentoRepository(session))


@router.post("", response_model=AgendamentoOut, status_code=201)
async def criar_agendamento(
    payload: AgendamentoCreate,
    use_cases: AgendamentoUseCases = Depends(get_use_cases),
    _usuario: Usuario = Depends(get_current_user),
) -> Agendamento:
    agendamento = Agendamento(
        id=uuid4(),
        cliente_id=payload.cliente_id,
        data_hora=payload.data_hora,
        status=payload.status,
        criado_em=datetime.now(timezone.utc),
    )
    try:
        return await use_cases.criar(agendamento)
    except ValueError as erro:
        raise HTTPException(status_code=422, detail=str(erro))


@router.get("", response_model=list[AgendamentoOut])
async def listar_agendamentos(
    cliente_id: UUID | None = None,
    use_cases: AgendamentoUseCases = Depends(get_use_cases),
) -> list[Agendamento]:
    # Sem cliente_id: visão da oficina inteira (AgendaPage). Com
    # cliente_id: histórico de um cliente específico (ex: ClientesPage).
    if cliente_id is not None:
        return await use_cases.listar_por_cliente(cliente_id)
    return await use_cases.listar()


@router.get("/{agendamento_id}", response_model=AgendamentoOut)
async def buscar_agendamento(
    agendamento_id: UUID, use_cases: AgendamentoUseCases = Depends(get_use_cases)
) -> Agendamento:
    agendamento = await use_cases.buscar_por_id(agendamento_id)
    if agendamento is None:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    return agendamento


@router.put("/{agendamento_id}", response_model=AgendamentoOut)
async def atualizar_agendamento(
    agendamento_id: UUID,
    payload: AgendamentoUpdate,
    use_cases: AgendamentoUseCases = Depends(get_use_cases),
    _usuario: Usuario = Depends(get_current_user),
) -> Agendamento:
    existente = await use_cases.buscar_por_id(agendamento_id)
    if existente is None:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    agendamento = Agendamento(
        id=agendamento_id,
        cliente_id=existente.cliente_id,
        data_hora=payload.data_hora,
        status=payload.status,
        criado_em=existente.criado_em,
    )
    atualizado = await use_cases.atualizar(agendamento)
    if atualizado is None:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    return atualizado


@router.delete("/{agendamento_id}", status_code=204)
async def excluir_agendamento(
    agendamento_id: UUID,
    use_cases: AgendamentoUseCases = Depends(get_use_cases),
    _usuario: Usuario = Depends(get_current_user),
) -> None:
    excluido = await use_cases.excluir(agendamento_id)
    if not excluido:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
