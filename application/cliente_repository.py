from typing import Protocol
from uuid import UUID

from domain.cliente import Cliente


class ClientePossuiProtocolosError(Exception):
    """Levantado ao tentar excluir um cliente que ainda tem protocolos vinculados."""


# Padrão seguido por todos os outros *_repository.py do projeto.
class ClienteRepository(Protocol):
    async def criar(self, cliente: Cliente) -> Cliente: ...

    async def listar(self) -> list[Cliente]: ...

    async def buscar_por_id(self, cliente_id: UUID) -> Cliente | None: ...

    # Usado no webhook do WhatsApp — telefone é o identificador de quem manda mensagem.
    async def buscar_por_telefone(self, telefone: str) -> Cliente | None: ...

    async def atualizar(self, cliente: Cliente) -> Cliente | None: ...

    # Pode levantar ClientePossuiProtocolosError (FK ondelete=RESTRICT).
    async def excluir(self, cliente_id: UUID) -> bool: ...
