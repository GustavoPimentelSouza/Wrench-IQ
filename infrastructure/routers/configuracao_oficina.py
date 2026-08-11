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
    nome_empresa: str
    horario_semana_abertura: time
    horario_semana_fechamento: time
    horario_sabado_abertura: time | None = None
    horario_sabado_fechamento: time | None = None
    horario_domingo_abertura: time | None = None
    horario_domingo_fechamento: time | None = None
    endereco: str | None = None
    mensagem_encerramento: str | None = None
    tolerancia_no_show_minutos: int = 20
    limite_trocas_sem_resolucao: int = 3


# Idêntico ao In hoje, mas mantido como classe separada — mesmo padrão dos
# outros routers (In/Out desacoplados), pra não ter que mexer aqui se um dia
# o retorno precisar de um campo a mais que o formulário não deveria enviar.
class ConfiguracaoOficinaOut(ConfiguracaoOficinaIn):
    pass


def get_use_cases(session: AsyncSession = Depends(get_db)) -> ConfiguracaoOficinaUseCases:
    return ConfiguracaoOficinaUseCases(SqlAlchemyConfiguracaoOficinaRepository(session))


# Sem get_current_user de propósito: quem lê isso não é só a tela de
# configurações (que exige login), é também o próprio backend do chat
# (ConversaUseCases), montando o prompt da IA a cada mensagem — não faz
# sentido exigir um token de staff pra isso.
@router.get("", response_model=ConfiguracaoOficinaOut)
async def buscar_configuracao(
    use_cases: ConfiguracaoOficinaUseCases = Depends(get_use_cases),
) -> ConfiguracaoOficina:
    return await use_cases.buscar()


# PUT já exige login (get_current_user) — mudar o horário de funcionamento é
# uma decisão do dono/gerente, não algo que qualquer um deveria poder fazer.
@router.put("", response_model=ConfiguracaoOficinaOut)
async def atualizar_configuracao(
    payload: ConfiguracaoOficinaIn,
    use_cases: ConfiguracaoOficinaUseCases = Depends(get_use_cases),
    _usuario: Usuario = Depends(get_current_user),
) -> ConfiguracaoOficina:
    # id sempre 1 — é a mesma linha única que o repositório usa (ver
    # SqlAlchemyConfiguracaoOficinaRepository._ID_UNICO). O cliente HTTP
    # nunca escolhe o id, só o conteúdo.
    configuracao = ConfiguracaoOficina(id=1, **payload.model_dump())
    try:
        return await use_cases.atualizar(configuracao)
    except ValueError as erro:
        raise HTTPException(status_code=422, detail=str(erro))
