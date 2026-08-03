from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.sqlalchemy_movimentacao_estoque_repository import (
    SqlAlchemyMovimentacaoEstoqueRepository,
)
from adapters.sqlalchemy_peca_repository import SqlAlchemyPecaRepository
from adapters.sqlalchemy_pedido_repository import SqlAlchemyPedidoRepository
from application.embedding_service import EmbeddingService
from application.pedido_use_cases import (
    EnderecoObrigatorioError,
    EstoqueInsuficienteError,
    PecaNaoEncontradaError,
    PedidoNaoEncontradoError,
    PedidoUseCases,
    TransicaoInvalidaError,
)
from domain.pedido import Pedido, StatusPedido, TipoEntrega
from domain.usuario import Usuario
from infrastructure.db import get_db
from infrastructure.ia import get_embedding_service
from infrastructure.security_dependencies import get_current_user

router = APIRouter(prefix="/pedidos", tags=["pedidos"])

_PRAZO_ARREPENDIMENTO = timedelta(days=7)


class PedidoCreate(BaseModel):
    cliente_id: UUID
    peca_id: UUID
    quantidade: int
    tipo_entrega: TipoEntrega
    endereco_entrega: str | None = None


class PedidoOut(BaseModel):
    id: UUID
    numero: int
    cliente_id: UUID
    peca_id: UUID
    quantidade: int
    valor_total: Decimal
    tipo_entrega: TipoEntrega
    status: StatusPedido
    endereco_entrega: str | None
    link_pagamento: str | None
    criado_em: datetime
    entregue_em: datetime | None
    dentro_do_prazo_arrependimento: bool


def _para_saida(pedido: Pedido) -> PedidoOut:
    dentro_do_prazo = (
        pedido.tipo_entrega == TipoEntrega.ENVIO_REMOTO
        and pedido.entregue_em is not None
        and datetime.now(timezone.utc) - pedido.entregue_em <= _PRAZO_ARREPENDIMENTO
    )
    return PedidoOut(
        id=pedido.id,
        numero=pedido.numero,
        cliente_id=pedido.cliente_id,
        peca_id=pedido.peca_id,
        quantidade=pedido.quantidade,
        valor_total=pedido.valor_total,
        tipo_entrega=pedido.tipo_entrega,
        status=pedido.status,
        endereco_entrega=pedido.endereco_entrega,
        link_pagamento=pedido.link_pagamento,
        criado_em=pedido.criado_em,
        entregue_em=pedido.entregue_em,
        dentro_do_prazo_arrependimento=dentro_do_prazo,
    )


def get_use_cases(
    session: AsyncSession = Depends(get_db),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
) -> PedidoUseCases:
    return PedidoUseCases(
        SqlAlchemyPedidoRepository(session),
        SqlAlchemyPecaRepository(session, embedding_service),
        SqlAlchemyMovimentacaoEstoqueRepository(session),
    )


@router.post("", response_model=PedidoOut, status_code=201)
async def criar_pedido(
    payload: PedidoCreate,
    use_cases: PedidoUseCases = Depends(get_use_cases),
    _usuario: Usuario = Depends(get_current_user),
) -> PedidoOut:
    try:
        pedido = await use_cases.criar(
            cliente_id=payload.cliente_id,
            peca_id=payload.peca_id,
            quantidade=payload.quantidade,
            tipo_entrega=payload.tipo_entrega,
            endereco_entrega=payload.endereco_entrega,
        )
    except PecaNaoEncontradaError:
        raise HTTPException(status_code=404, detail="Peça não encontrada")
    except EstoqueInsuficienteError:
        raise HTTPException(
            status_code=400, detail="Estoque insuficiente para essa quantidade"
        )
    except EnderecoObrigatorioError:
        raise HTTPException(
            status_code=400, detail="Endereço de entrega é obrigatório para envio remoto"
        )
    return _para_saida(pedido)


@router.get("", response_model=list[PedidoOut])
async def listar_pedidos(
    response: Response,
    cliente_id: UUID | None = None,
    # Filtro de status — o uso real do dia a dia é "só o que precisa da
    # minha ação agora" (ex: ?status=aguardando_conferencia), em vez de
    # rolar a lista inteira procurando.
    status: StatusPedido | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    use_cases: PedidoUseCases = Depends(get_use_cases),
    _usuario: Usuario = Depends(get_current_user),
) -> list[PedidoOut]:
    if cliente_id is not None:
        pedidos = await use_cases.listar_por_cliente(
            cliente_id, status=status, limit=limit, offset=offset
        )
        total = await use_cases.contar_por_cliente(cliente_id, status=status)
    else:
        pedidos = await use_cases.listar(status=status, limit=limit, offset=offset)
        total = await use_cases.contar(status=status)
    # Total via header (não no corpo) pra não quebrar quem já espera uma
    # lista simples de PedidoOut no JSON — é o mesmo contrato de sempre,
    # só com metadado extra de paginação por fora.
    response.headers["X-Total-Count"] = str(total)
    return [_para_saida(pedido) for pedido in pedidos]


@router.get("/{pedido_id}", response_model=PedidoOut)
async def buscar_pedido(
    pedido_id: UUID,
    use_cases: PedidoUseCases = Depends(get_use_cases),
    _usuario: Usuario = Depends(get_current_user),
) -> PedidoOut:
    pedido = await use_cases.buscar_por_id(pedido_id)
    if pedido is None:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    return _para_saida(pedido)


@router.post("/{pedido_id}/confirmar-pagamento", response_model=PedidoOut)
async def confirmar_pagamento(
    pedido_id: UUID,
    use_cases: PedidoUseCases = Depends(get_use_cases),
    _usuario: Usuario = Depends(get_current_user),
) -> PedidoOut:
    try:
        pedido = await use_cases.confirmar_pagamento(pedido_id)
    except PedidoNaoEncontradoError:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    except TransicaoInvalidaError:
        raise HTTPException(
            status_code=409, detail="Pedido não está aguardando pagamento"
        )
    return _para_saida(pedido)


@router.post("/{pedido_id}/confirmar-conferencia", response_model=PedidoOut)
async def confirmar_conferencia(
    pedido_id: UUID,
    use_cases: PedidoUseCases = Depends(get_use_cases),
    _usuario: Usuario = Depends(get_current_user),
) -> PedidoOut:
    try:
        pedido = await use_cases.confirmar_conferencia(pedido_id)
    except PedidoNaoEncontradoError:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    except TransicaoInvalidaError:
        raise HTTPException(
            status_code=409, detail="Pedido não está aguardando conferência"
        )
    return _para_saida(pedido)


@router.post("/{pedido_id}/marcar-entregue", response_model=PedidoOut)
async def marcar_entregue(
    pedido_id: UUID,
    use_cases: PedidoUseCases = Depends(get_use_cases),
    _usuario: Usuario = Depends(get_current_user),
) -> PedidoOut:
    try:
        pedido = await use_cases.marcar_entregue(pedido_id)
    except PedidoNaoEncontradoError:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    except TransicaoInvalidaError:
        raise HTTPException(
            status_code=409,
            detail="Pedido não está pronto para ser marcado como entregue",
        )
    return _para_saida(pedido)


@router.post("/{pedido_id}/cancelar", response_model=PedidoOut)
async def cancelar_pedido(
    pedido_id: UUID,
    use_cases: PedidoUseCases = Depends(get_use_cases),
    _usuario: Usuario = Depends(get_current_user),
) -> PedidoOut:
    try:
        pedido = await use_cases.cancelar(pedido_id)
    except PedidoNaoEncontradoError:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    except TransicaoInvalidaError:
        raise HTTPException(status_code=409, detail="Pedido não pode mais ser cancelado")
    return _para_saida(pedido)


# Sem agendador/fila no projeto ainda — o frontend chama essa rota toda vez
# que a tela de Pedidos carrega (ver PedidosPage.tsx), funcionando como uma
# limpeza "preguiçosa" em vez de um job rodando sozinho em segundo plano.
@router.post("/expirar-retiradas", response_model=list[PedidoOut])
async def expirar_retiradas(
    use_cases: PedidoUseCases = Depends(get_use_cases),
    _usuario: Usuario = Depends(get_current_user),
) -> list[PedidoOut]:
    cancelados = await use_cases.cancelar_expirados()
    return [_para_saida(pedido) for pedido in cancelados]
