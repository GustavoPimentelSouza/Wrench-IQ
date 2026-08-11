from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.sqlalchemy_agendamento_repository import SqlAlchemyAgendamentoRepository
from adapters.sqlalchemy_configuracao_oficina_repository import (
    SqlAlchemyConfiguracaoOficinaRepository,
)
from adapters.sqlalchemy_lista_espera_repository import SqlAlchemyListaEsperaRepository
from adapters.sqlalchemy_notificacao_repository import SqlAlchemyNotificacaoRepository
from adapters.sqlalchemy_usuario_repository import SqlAlchemyUsuarioRepository
from application.agendamento_disponibilidade_use_cases import (
    AgendamentoDisponibilidadeUseCases,
    DisponibilidadeResultado,
)
from application.agendamento_use_cases import AgendamentoUseCases
from application.configuracao_oficina_use_cases import ConfiguracaoOficinaUseCases
from application.notificacao_use_cases import NotificacaoUseCases
from domain.agendamento import Agendamento, StatusAgendamento
from domain.especialidade import Especialidade
from domain.lista_espera_agendamento import ListaEsperaAgendamento
from domain.usuario import Usuario
from infrastructure.db import get_db
from infrastructure.security_dependencies import get_current_user

router = APIRouter(prefix="/agendamentos", tags=["agendamentos"])


class AgendamentoCreate(BaseModel):
    cliente_id: UUID
    data_hora: datetime
    status: StatusAgendamento = StatusAgendamento.AGENDADO
    descricao: str | None = None
    especialidades: list[Especialidade] = []


class AgendamentoUpdate(BaseModel):
    data_hora: datetime
    status: StatusAgendamento
    descricao: str | None = None
    especialidades: list[Especialidade] | None = None


class AgendamentoOut(BaseModel):
    id: UUID
    cliente_id: UUID
    data_hora: datetime
    status: StatusAgendamento
    criado_em: datetime
    descricao: str | None
    especialidades: list[Especialidade]


class DisponibilidadeOut(BaseModel):
    disponivel_na_data: bool
    horarios_disponiveis: list[datetime]
    proxima_data_disponivel: date | None
    proximos_horarios: list[datetime]


class ListaEsperaIn(BaseModel):
    cliente_id: UUID
    especialidade: Especialidade


class ListaEsperaOut(BaseModel):
    id: UUID
    cliente_id: UUID
    especialidade: Especialidade
    criado_em: datetime
    atendido: bool


def get_use_cases(session: AsyncSession = Depends(get_db)) -> AgendamentoUseCases:
    return AgendamentoUseCases(
        SqlAlchemyAgendamentoRepository(session), SqlAlchemyUsuarioRepository(session)
    )


def get_disponibilidade_use_cases(
    session: AsyncSession = Depends(get_db),
) -> AgendamentoDisponibilidadeUseCases:
    return AgendamentoDisponibilidadeUseCases(
        SqlAlchemyAgendamentoRepository(session),
        SqlAlchemyUsuarioRepository(session),
        SqlAlchemyListaEsperaRepository(session),
        NotificacaoUseCases(SqlAlchemyNotificacaoRepository(session)),
    )


def get_configuracao_use_cases(
    session: AsyncSession = Depends(get_db),
) -> ConfiguracaoOficinaUseCases:
    return ConfiguracaoOficinaUseCases(SqlAlchemyConfiguracaoOficinaRepository(session))


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
        descricao=payload.descricao,
        especialidades=payload.especialidades,
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


# Vem antes de /{agendamento_id} de propósito — senão o FastAPI tentaria
# fazer o parse de "disponibilidade" como UUID e devolveria 422.
@router.get("/disponibilidade", response_model=DisponibilidadeOut)
async def consultar_disponibilidade(
    especialidades: list[Especialidade],
    data: date,
    use_cases: AgendamentoDisponibilidadeUseCases = Depends(get_disponibilidade_use_cases),
    configuracao_use_cases: ConfiguracaoOficinaUseCases = Depends(get_configuracao_use_cases),
) -> DisponibilidadeResultado:
    configuracao = await configuracao_use_cases.buscar()
    return await use_cases.consultar_disponibilidade(especialidades, data, configuracao)


@router.post("/lista-espera", response_model=ListaEsperaOut, status_code=201)
async def entrar_na_lista_de_espera(
    payload: ListaEsperaIn,
    use_cases: AgendamentoDisponibilidadeUseCases = Depends(get_disponibilidade_use_cases),
    _usuario: Usuario = Depends(get_current_user),
) -> ListaEsperaAgendamento:
    return await use_cases.entrar_na_lista_de_espera(payload.cliente_id, payload.especialidade)


# Mesmo padrão de POST /pedidos/expirar-retiradas: sem worker/agendador de
# verdade no projeto ainda, o frontend bate nessa rota ao carregar a
# AgendaPage, funcionando como limpeza "preguiçosa" em vez de job em
# segundo plano.
@router.post("/liberar-no-shows", response_model=list[AgendamentoOut])
async def liberar_no_shows(
    use_cases: AgendamentoDisponibilidadeUseCases = Depends(get_disponibilidade_use_cases),
    configuracao_use_cases: ConfiguracaoOficinaUseCases = Depends(get_configuracao_use_cases),
    _usuario: Usuario = Depends(get_current_user),
) -> list[Agendamento]:
    configuracao = await configuracao_use_cases.buscar()
    return await use_cases.liberar_no_shows(configuracao)


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
    disponibilidade_use_cases: AgendamentoDisponibilidadeUseCases = Depends(
        get_disponibilidade_use_cases
    ),
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
        descricao=payload.descricao if payload.descricao is not None else existente.descricao,
        especialidades=(
            payload.especialidades
            if payload.especialidades is not None
            else existente.especialidades
        ),
    )
    atualizado = await use_cases.atualizar(agendamento)
    if atualizado is None:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")

    # Item 6: cancelamento (detectado aqui, na transição de status) libera a
    # vaga pro primeiro da lista de espera daquela(s) especialidade(s). Só
    # dispara na transição DE fora-de-cancelado PARA cancelado — reenviar o
    # mesmo PUT duas vezes não notifica duas vezes.
    if (
        atualizado.status == StatusAgendamento.CANCELADO
        and existente.status != StatusAgendamento.CANCELADO
    ):
        await disponibilidade_use_cases.notificar_cancelamento(atualizado)

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
