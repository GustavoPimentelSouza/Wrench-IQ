from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.sqlalchemy_protocolo_repository import SqlAlchemyProtocoloRepository
from adapters.sqlalchemy_reclassificacao_repository import SqlAlchemyReclassificacaoRepository
from adapters.sqlalchemy_usuario_repository import SqlAlchemyUsuarioRepository
from application.protocolo_use_cases import (
    MecanicoInvalidoError,
    OrcamentoNaoDefinidoError,
    ProtocoloNaoEncontradoError,
    ProtocoloUseCases,
    TransicaoInvalidaError,
)
from domain.especialidade import Especialidade
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
    especialidades: list[Especialidade] = []
    # Sem `status`: todo protocolo nasce em AGUARDANDO_APROVACAO.


class ProtocoloUpdate(BaseModel):
    veiculo: str
    categoria: str
    descricao: str | None = None
    mecanico_id: UUID | None = None
    valor_orcamento: Decimal | None = None
    # Também sem `status` — mudar de estado só é possível pelos endpoints
    # /aprovar, /concluir, /cancelar abaixo. Especialidade também não muda
    # por aqui — é o endpoint /reclassificar-especialidade dedicado, pra
    # não obrigar reenviar todo o resto do protocolo só pra corrigir isso.


class ProtocoloCancelamento(BaseModel):
    motivo: str | None = None


class ProtocoloReclassificacao(BaseModel):
    especialidades: list[Especialidade]


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
    valor_orcamento: Decimal | None
    motivo_cancelamento: str | None
    especialidades: list[Especialidade]


def get_use_cases(session: AsyncSession = Depends(get_db)) -> ProtocoloUseCases:
    return ProtocoloUseCases(
        SqlAlchemyProtocoloRepository(session),
        SqlAlchemyUsuarioRepository(session),
        SqlAlchemyReclassificacaoRepository(session),
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
        especialidades=payload.especialidades,
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
        valor_orcamento=payload.valor_orcamento,
        especialidades=existente.especialidades,
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
    except OrcamentoNaoDefinidoError:
        raise HTTPException(
            status_code=409, detail="Protocolo não tem valor_orcamento definido"
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
    payload: ProtocoloCancelamento = ProtocoloCancelamento(),
    use_cases: ProtocoloUseCases = Depends(get_use_cases),
    _usuario: Usuario = Depends(get_current_user),
) -> Protocolo:
    try:
        return await use_cases.cancelar(protocolo_id, payload.motivo)
    except ProtocoloNaoEncontradoError:
        raise HTTPException(status_code=404, detail="Protocolo não encontrado")
    except TransicaoInvalidaError:
        raise HTTPException(
            status_code=409, detail="Protocolo já está concluído ou cancelado"
        )


# A IA classifica especialidade só pelo relato do cliente, antes de
# qualquer avaliação de verdade — esse endpoint é pro mecânico corrigir
# isso depois de olhar o veículo presencialmente, sem precisar passar pelo
# formulário genérico de PUT (que exige reenviar todos os outros campos).
@router.post("/{protocolo_id}/reclassificar-especialidade", response_model=ProtocoloOut)
async def reclassificar_especialidade_protocolo(
    protocolo_id: UUID,
    payload: ProtocoloReclassificacao,
    use_cases: ProtocoloUseCases = Depends(get_use_cases),
    _usuario: Usuario = Depends(get_current_user),
) -> Protocolo:
    try:
        return await use_cases.reclassificar_especialidade(protocolo_id, payload.especialidades)
    except ProtocoloNaoEncontradoError:
        raise HTTPException(status_code=404, detail="Protocolo não encontrado")
