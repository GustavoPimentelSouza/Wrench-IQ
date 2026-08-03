from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.sqlalchemy_mensagem_repository import SqlAlchemyMensagemRepository
from application.classificacao_mensagem_service import ClassificadorDeMensagem
from application.mensagem_use_cases import MensagemUseCases
from domain.usuario import Usuario
from infrastructure.db import get_db
from infrastructure.ia import get_classificador
from infrastructure.security_dependencies import get_current_user

router = APIRouter(prefix="/mensagens", tags=["mensagens"])


class MensagemIn(BaseModel):
    cliente_id: UUID
    texto: str


class MensagemOut(BaseModel):
    id: UUID
    categoria: str


# Schema próprio (não reaproveita MensagemOut) porque a fila de atendimento
# precisa mostrar mais contexto pro staff decidir (texto, resposta que a IA
# já tentou dar, quando foi) — MensagemOut é só a confirmação mínima do POST.
class MensagemAtendimentoOut(BaseModel):
    id: UUID
    cliente_id: UUID
    texto: str
    categoria: str
    resposta_ia: str | None
    criado_em: datetime


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


# Regra 4 do CLAUDE.md: fila de conversas que precisam de atendente humano
# (reclamação sensível ou falha técnica da IA) — autenticado, é uso interno.
@router.get("/atendimento-pendente", response_model=list[MensagemAtendimentoOut])
async def listar_atendimento_pendente(
    use_cases: MensagemUseCases = Depends(get_use_cases),
    _usuario: Usuario = Depends(get_current_user),
) -> list[MensagemAtendimentoOut]:
    pendentes = await use_cases.listar_pendentes_atendimento()
    return [
        MensagemAtendimentoOut(
            id=m.id,
            cliente_id=m.cliente_id,
            texto=m.texto,
            categoria=m.categoria.value,
            resposta_ia=m.resposta_ia,
            criado_em=m.criado_em,
        )
        for m in pendentes
    ]


# Staff clica isso depois de atender o cliente por fora (telefone,
# WhatsApp manual) — só dá baixa na fila, não faz nada além disso.
@router.post("/{mensagem_id}/resolver-atendimento", status_code=204)
async def resolver_atendimento(
    mensagem_id: UUID,
    use_cases: MensagemUseCases = Depends(get_use_cases),
    _usuario: Usuario = Depends(get_current_user),
) -> None:
    await use_cases.marcar_atendimento_resolvido(mensagem_id)
