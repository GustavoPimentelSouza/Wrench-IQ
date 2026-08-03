from datetime import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.sqlalchemy_configuracao_oficina_repository import (
    SqlAlchemyConfiguracaoOficinaRepository,
)
from application.configuracao_oficina_use_cases import ConfiguracaoOficinaUseCases
from domain.configuracao_oficina import ConfiguracaoOficina
from domain.usuario import Usuario
from infrastructure.db import get_db
from infrastructure.security_dependencies import get_current_user

router = APIRouter(prefix="/configuracao-oficina", tags=["configuracao-oficina"])


class ConfiguracaoOficinaIn(BaseModel):
    horario_semana_abertura: time
    horario_semana_fechamento: time
    horario_sabado_abertura: time | None = None
    horario_sabado_fechamento: time | None = None
    horario_domingo_abertura: time | None = None
    horario_domingo_fechamento: time | None = None


class ConfiguracaoOficinaOut(ConfiguracaoOficinaIn):
    pass


def get_use_cases(session: AsyncSession = Depends(get_db)) -> ConfiguracaoOficinaUseCases:
    return ConfiguracaoOficinaUseCases(SqlAlchemyConfiguracaoOficinaRepository(session))


@router.get("", response_model=ConfiguracaoOficinaOut)
async def buscar_configuracao(
    use_cases: ConfiguracaoOficinaUseCases = Depends(get_use_cases),
) -> ConfiguracaoOficina:
    return await use_cases.buscar()


@router.put("", response_model=ConfiguracaoOficinaOut)
async def atualizar_configuracao(
    payload: ConfiguracaoOficinaIn,
    use_cases: ConfiguracaoOficinaUseCases = Depends(get_use_cases),
    _usuario: Usuario = Depends(get_current_user),
) -> ConfiguracaoOficina:
    configuracao = ConfiguracaoOficina(id=1, **payload.model_dump())
    try:
        return await use_cases.atualizar(configuracao)
    except ValueError as erro:
        raise HTTPException(status_code=422, detail=str(erro))
