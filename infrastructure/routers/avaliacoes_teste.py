from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.sqlalchemy_avaliacao_teste_repository import SqlAlchemyAvaliacaoTesteRepository
from adapters.sqlalchemy_cliente_repository import SqlAlchemyClienteRepository
from adapters.sqlalchemy_mensagem_repository import SqlAlchemyMensagemRepository
from application.avaliacao_teste_use_cases import (
    AvaliacaoTesteUseCases,
    ConversaNaoEncontradaError,
)
from domain.avaliacao_teste import ResultadoAvaliacao
from domain.usuario import Usuario
from infrastructure.db import get_db
from infrastructure.security_dependencies import exigir_admin

# TEMPORÁRIO (ferramenta de dev, ver domain/avaliacao_teste.py). Só admin:
# é avaliação da IA, não recurso de atendimento da oficina.
router = APIRouter(prefix="/avaliacoes-teste", tags=["avaliacoes-teste"])


class AvaliacaoIn(BaseModel):
    telefone: str
    resultado: ResultadoAvaliacao
    comentario: str | None = None


class AvaliacaoOut(BaseModel):
    id: UUID
    cliente_id: UUID
    resultado: ResultadoAvaliacao
    comentario: str | None
    criado_em: datetime
    atualizado_em: datetime


class ConversaTesteOut(BaseModel):
    cliente_id: UUID
    telefone: str
    inicio: datetime
    fim: datetime
    total_mensagens: int
    resultado: ResultadoAvaliacao | None
    comentario: str | None


class MensagemTesteOut(BaseModel):
    texto: str
    resposta_ia: str | None
    ferramentas_chamadas: list[str]
    criado_em: datetime


def get_use_cases(session: AsyncSession = Depends(get_db)) -> AvaliacaoTesteUseCases:
    return AvaliacaoTesteUseCases(
        SqlAlchemyAvaliacaoTesteRepository(session),
        SqlAlchemyClienteRepository(session),
        SqlAlchemyMensagemRepository(session),
    )


# PUT porque é idempotente: avaliar de novo a mesma conversa sobrescreve.
@router.put("", response_model=AvaliacaoOut)
async def avaliar_conversa(
    payload: AvaliacaoIn,
    use_cases: AvaliacaoTesteUseCases = Depends(get_use_cases),
    _admin: Usuario = Depends(exigir_admin),
) -> AvaliacaoOut:
    comentario = (payload.comentario or "").strip() or None
    try:
        avaliacao = await use_cases.avaliar(payload.telefone, payload.resultado, comentario)
    except ConversaNaoEncontradaError:
        raise HTTPException(
            status_code=404, detail="Conversa sem mensagens ainda — nada pra avaliar"
        )
    return AvaliacaoOut(**avaliacao.__dict__)


@router.get("/conversas", response_model=list[ConversaTesteOut])
async def listar_conversas(
    use_cases: AvaliacaoTesteUseCases = Depends(get_use_cases),
    _admin: Usuario = Depends(exigir_admin),
) -> list[ConversaTesteOut]:
    conversas = await use_cases.listar_conversas()
    return [ConversaTesteOut(**conversa.__dict__) for conversa in conversas]


@router.get("/conversas/{cliente_id}/mensagens", response_model=list[MensagemTesteOut])
async def listar_mensagens_da_conversa(
    cliente_id: UUID,
    use_cases: AvaliacaoTesteUseCases = Depends(get_use_cases),
    _admin: Usuario = Depends(exigir_admin),
) -> list[MensagemTesteOut]:
    mensagens = await use_cases.listar_mensagens(cliente_id)
    return [
        MensagemTesteOut(
            texto=m.texto, resposta_ia=m.resposta_ia,
            ferramentas_chamadas=m.ferramentas_chamadas, criado_em=m.criado_em,
        )
        for m in mensagens
    ]
