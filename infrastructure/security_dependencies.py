from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.seguranca import decodificar_token_acesso
from adapters.sqlalchemy_usuario_repository import SqlAlchemyUsuarioRepository
from domain.usuario import PapelUsuario, Usuario
from infrastructure.db import get_db

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credenciais: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    session: AsyncSession = Depends(get_db),
) -> Usuario:
    erro_credenciais = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas ou expiradas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credenciais is None:
        raise erro_credenciais

    try:
        payload = decodificar_token_acesso(credenciais.credentials)
        usuario_id = UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise erro_credenciais

    repository = SqlAlchemyUsuarioRepository(session)
    usuario = await repository.buscar_por_id(usuario_id)
    if usuario is None or not usuario.ativo:
        raise erro_credenciais
    return usuario


def exigir_admin(usuario: Usuario = Depends(get_current_user)) -> Usuario:
    if usuario.papel != PapelUsuario.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem realizar esta ação",
        )
    return usuario
