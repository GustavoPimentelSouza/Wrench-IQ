from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.sqlalchemy_item_adicional_repository import SqlAlchemyItemAdicionalRepository
from adapters.sqlalchemy_notificacao_repository import SqlAlchemyNotificacaoRepository
from adapters.sqlalchemy_protocolo_repository import SqlAlchemyProtocoloRepository
from application.item_adicional_use_cases import (
    ItemAdicionalJaProcessadoError,
    ItemAdicionalNaoEncontradoError,
    ItemAdicionalUseCases,
    ProtocoloNaoEncontradoError,
    ProtocoloNaoEstaEmExecucaoError,
)
from application.notificacao_use_cases import NotificacaoUseCases
from domain.item_adicional_protocolo import ItemAdicionalProtocolo, StatusItemAdicional
from domain.usuario import Usuario
from infrastructure.db import get_db
from infrastructure.security_dependencies import get_current_user

# Rota vive fora de /protocolos por ter uma máquina de estados própria (ver
# ItemAdicionalUseCases) — o registro em si é aninhado (nasce sempre a
# partir de um protocolo_id), mas aprovar/recusar operam direto sobre o
# item_id, sem precisar saber o protocolo dono.
router = APIRouter(tags=["itens-adicionais"])


class ItemAdicionalCreate(BaseModel):
    descricao: str
    valor: Decimal
    peca_id: UUID | None = None


class ItemAdicionalOut(BaseModel):
    id: UUID
    protocolo_id: UUID
    descricao: str
    valor: Decimal
    status: StatusItemAdicional
    peca_id: UUID | None
    criado_em: datetime


def get_use_cases(session: AsyncSession = Depends(get_db)) -> ItemAdicionalUseCases:
    return ItemAdicionalUseCases(
        SqlAlchemyItemAdicionalRepository(session),
        SqlAlchemyProtocoloRepository(session),
        NotificacaoUseCases(SqlAlchemyNotificacaoRepository(session)),
    )


@router.post(
    "/protocolos/{protocolo_id}/itens-adicionais",
    response_model=ItemAdicionalOut,
    status_code=201,
)
async def registrar_item_adicional(
    protocolo_id: UUID,
    payload: ItemAdicionalCreate,
    use_cases: ItemAdicionalUseCases = Depends(get_use_cases),
    _usuario: Usuario = Depends(get_current_user),
) -> ItemAdicionalProtocolo:
    try:
        return await use_cases.registrar(
            protocolo_id, payload.descricao, payload.valor, payload.peca_id
        )
    except ProtocoloNaoEncontradoError:
        raise HTTPException(status_code=404, detail="Protocolo não encontrado")
    except ProtocoloNaoEstaEmExecucaoError:
        raise HTTPException(
            status_code=409, detail="Protocolo precisa estar em execução pra ter item adicional"
        )


@router.post("/itens-adicionais/{item_id}/aprovar", response_model=ItemAdicionalOut)
async def aprovar_item_adicional(
    item_id: UUID,
    use_cases: ItemAdicionalUseCases = Depends(get_use_cases),
    _usuario: Usuario = Depends(get_current_user),
) -> ItemAdicionalProtocolo:
    try:
        return await use_cases.aprovar(item_id)
    except ItemAdicionalNaoEncontradoError:
        raise HTTPException(status_code=404, detail="Item adicional não encontrado")
    except ItemAdicionalJaProcessadoError:
        raise HTTPException(status_code=409, detail="Item adicional já foi decidido antes")


@router.post("/itens-adicionais/{item_id}/recusar", response_model=ItemAdicionalOut)
async def recusar_item_adicional(
    item_id: UUID,
    use_cases: ItemAdicionalUseCases = Depends(get_use_cases),
    _usuario: Usuario = Depends(get_current_user),
) -> ItemAdicionalProtocolo:
    try:
        return await use_cases.recusar(item_id)
    except ItemAdicionalNaoEncontradoError:
        raise HTTPException(status_code=404, detail="Item adicional não encontrado")
    except ItemAdicionalJaProcessadoError:
        raise HTTPException(status_code=409, detail="Item adicional já foi decidido antes")
