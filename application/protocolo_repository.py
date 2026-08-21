from typing import Protocol
from uuid import UUID

from domain.protocolo import Protocolo


class ProtocoloRepository(Protocol):
    async def criar(self, protocolo: Protocolo) -> Protocolo: ...

    async def listar(self) -> list[Protocolo]: ...

    # Usado na tela "histórico do cliente" — todos os serviços que um
    # cliente específico já trouxe pra oficina.
    async def listar_por_cliente(self, cliente_id: UUID) -> list[Protocolo]: ...

    async def buscar_por_id(self, protocolo_id: UUID) -> Protocolo | None: ...

    async def atualizar(self, protocolo: Protocolo) -> Protocolo | None: ...
