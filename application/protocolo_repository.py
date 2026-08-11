from datetime import date
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

    # Denominador de GET /relatorios/taxa-reclassificacao (ver
    # RelatorioUseCases) — total de protocolos criados no período, pra
    # calcular a proporção que foi reclassificada depois.
    async def contar_por_periodo(self, inicio: date, fim: date) -> int: ...
