from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from adapters.estado_ia import ultima_falha_classificacao
from domain.usuario import Usuario
from infrastructure.security_dependencies import get_current_user

router = APIRouter(prefix="/sistema", tags=["sistema"])


class StatusIAOut(BaseModel):
    falha_classificacao_em: datetime | None


# Diagnóstico de dev (ver adapters/estado_ia.py): dá visibilidade na tela
# quando o classificador da IA cai no fallback silencioso, em vez de sumir
# sem deixar rastro (foi o que aconteceu com o llama-3.1-8b-instant).
@router.get("/status-ia", response_model=StatusIAOut)
async def status_ia(_usuario: Usuario = Depends(get_current_user)) -> StatusIAOut:
    return StatusIAOut(falha_classificacao_em=ultima_falha_classificacao())
