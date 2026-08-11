from typing import Protocol
from uuid import UUID

from domain.item_adicional_protocolo import ItemAdicionalProtocolo


class ItemAdicionalRepository(Protocol):
    async def criar(self, item: ItemAdicionalProtocolo) -> ItemAdicionalProtocolo: ...

    async def buscar_por_id(self, item_id: UUID) -> ItemAdicionalProtocolo | None: ...

    async def atualizar(
        self, item: ItemAdicionalProtocolo
    ) -> ItemAdicionalProtocolo | None: ...
