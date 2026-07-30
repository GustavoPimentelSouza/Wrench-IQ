from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.sqlalchemy_mensagem_repository import SqlAlchemyMensagemRepository
from application.classificacao_mensagem_service import ClassificadorDeMensagem
from application.mensagem_use_cases import MensagemUseCases
from infrastructure.db import get_db
from infrastructure.ia import get_classificador

router = APIRouter(prefix="/mensagens", tags=["mensagens"])


class MensagemIn(BaseModel):
    cliente_id: UUID
    texto: str


class MensagemOut(BaseModel):
    id: UUID
    categoria: str


def get_use_cases(
    session: AsyncSession = Depends(get_db),
    classificador: ClassificadorDeMensagem = Depends(get_classificador),
) -> MensagemUseCases:
    return MensagemUseCases(SqlAlchemyMensagemRepository(session), classificador)


@router.post("", response_model=MensagemOut, status_code=201)
async def receber_mensagem(
    payload: MensagemIn, use_cases: MensagemUseCases = Depends(get_use_cases)
) -> MensagemOut:
    mensagem = await use_cases.receber(payload.cliente_id, payload.texto)
    return MensagemOut(id=mensagem.id, categoria=mensagem.categoria.value)
