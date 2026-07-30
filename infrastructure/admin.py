import os

from fastapi import FastAPI
from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request

from adapters.orm_models import PecaORM, UsuarioORM
from infrastructure.db import engine

ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")
ADMIN_SECRET_KEY = os.getenv("ADMIN_SECRET_KEY", "wrenchiq-dev-secret")


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        if form.get("username") == ADMIN_USER and form.get("password") == ADMIN_PASSWORD:
            request.session.update({"autenticado": True})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        return bool(request.session.get("autenticado"))


class PecaAdmin(ModelView, model=PecaORM):
    column_list = [
        "id",
        "nome",
        "marca_modelo_compativel",
        "ano_compativel",
        "preco",
        "quantidade_estoque",
        "criado_em",
    ]
    name = "Peça"
    name_plural = "Peças"
    icon = "fa-solid fa-gear"


class UsuarioAdmin(ModelView, model=UsuarioORM):
    column_list = ["id", "nome", "email", "papel", "ativo", "criado_em"]
    form_excluded_columns = ["criado_em"]
    name = "Usuário"
    name_plural = "Usuários"
    icon = "fa-solid fa-user"


def registrar_admin(app: FastAPI) -> Admin:
    admin = Admin(app, engine, authentication_backend=AdminAuth(secret_key=ADMIN_SECRET_KEY))
    admin.add_view(PecaAdmin)
    admin.add_view(UsuarioAdmin)
    return admin
