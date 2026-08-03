from typing import Protocol
from uuid import UUID

from domain.usuario import Usuario


# Sem listar/excluir: usuário só é criado (via /auth/registrar) e consultado.
class UsuarioRepository(Protocol):
    async def criar(self, usuario: Usuario) -> Usuario: ...

    # Usado por get_current_user a cada requisição (JWT só guarda o ID).
    async def buscar_por_id(self, usuario_id: UUID) -> Usuario | None: ...

    async def buscar_por_email(self, email: str) -> Usuario | None: ...
