from typing import Protocol
from uuid import UUID

from domain.mensagem import Mensagem


# Interface mais enxuta do projeto: Mensagem é registro histórico
# (append-only, tipo log) — não existe "atualizar" nem "excluir" porque não
# faz sentido editar uma mensagem que o cliente já mandou, só registrar e
# consultar depois.
class MensagemRepository(Protocol):
    async def criar(self, mensagem: Mensagem) -> Mensagem: ...

    async def buscar_por_id(self, mensagem_id: UUID) -> Mensagem | None: ...
