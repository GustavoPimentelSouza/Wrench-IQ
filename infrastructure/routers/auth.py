from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.sqlalchemy_usuario_repository import SqlAlchemyUsuarioRepository
from application.auth_use_cases import (
    AuthUseCases,
    CredenciaisInvalidasError,
    EmailJaCadastradoError,
)
from domain.especialidade import Especialidade
from domain.usuario import PapelUsuario, Usuario
from infrastructure.db import get_db
from infrastructure.security_dependencies import exigir_admin

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginIn(BaseModel):
    email: str
    senha: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RegistrarIn(BaseModel):
    nome: str
    email: str
    senha: str
    papel: PapelUsuario
    # Só usado quando papel=MECANICO — ignorado (fica vazio) pros outros papéis.
    especialidades: list[Especialidade] = []


class UsuarioOut(BaseModel):
    id: UUID
    nome: str
    email: str
    papel: PapelUsuario
    ativo: bool
    especialidades: list[Especialidade]


def get_auth_use_cases(session: AsyncSession = Depends(get_db)) -> AuthUseCases:
    return AuthUseCases(SqlAlchemyUsuarioRepository(session))


@router.post("/login", response_model=TokenOut)
async def login(
    payload: LoginIn, use_cases: AuthUseCases = Depends(get_auth_use_cases)
) -> TokenOut:
    try:
        token, _ = await use_cases.login(payload.email, payload.senha)
    except CredenciaisInvalidasError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha inválidos",
        )
    return TokenOut(access_token=token)


@router.post(
    "/registrar", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED
)
async def registrar(
    payload: RegistrarIn,
    use_cases: AuthUseCases = Depends(get_auth_use_cases),
    _admin: Usuario = Depends(exigir_admin),
) -> UsuarioOut:
    try:
        usuario = await use_cases.registrar(
            payload.nome, payload.email, payload.senha, payload.papel, payload.especialidades
        )
    except EmailJaCadastradoError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="E-mail já cadastrado"
        )
    return UsuarioOut(
        id=usuario.id,
        nome=usuario.nome,
        email=usuario.email,
        papel=usuario.papel,
        ativo=usuario.ativo,
        especialidades=usuario.especialidades,
    )
