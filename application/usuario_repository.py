from typing import Protocol
from uuid import UUID

from domain.usuario import Usuario


# Não tem `listar` nem `excluir` aqui — usuário só é criado (via
# /auth/registrar, só admin pode) e consultado. Desativar é feito mudando
# o campo `ativo` via `atualizar`, implementado direto no adapter
# (não exposto por rota própria hoje).
class UsuarioRepository(Protocol):
    async def criar(self, usuario: Usuario) -> Usuario: ...

    # Usado pelo get_current_user (infrastructure/security_dependencies.py)
    # pra recarregar o usuário do banco a cada requisição autenticada — o
    # JWT só guarda o ID, não os dados completos, então isso confirma que o
    # usuário ainda existe e ainda está ativo.
    async def buscar_por_id(self, usuario_id: UUID) -> Usuario | None: ...

    # Usado no login — email é como o usuário se identifica (diferente do
    # Cliente, que se identifica por telefone).
    async def buscar_por_email(self, email: str) -> Usuario | None: ...
