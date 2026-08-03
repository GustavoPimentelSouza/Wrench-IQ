from typing import Protocol
from uuid import UUID

from domain.peca import Peca


class PecaPossuiPedidosError(Exception):
    """Levantado ao tentar excluir uma peça que ainda tem pedidos vinculados."""


# Mesmo padrão de application/cliente_repository.py — Protocol descrevendo
# só "o que dá pra fazer com uma Peça", sem falar de banco.
class PecaRepository(Protocol):
    async def criar(self, peca: Peca) -> Peca: ...

    async def listar(self) -> list[Peca]: ...

    async def buscar_por_id(self, peca_id: UUID) -> Peca | None: ...

    # Usado pela ferramenta de tool calling "consultar_preco_peca" — busca
    # livre por nome, sem RAG/pgvector ainda (isso é etapa futura do CLAUDE.md).
    async def buscar_por_nome_aproximado(self, texto: str) -> list[Peca]: ...

    async def atualizar(self, peca: Peca) -> Peca | None: ...

    # Levanta PecaPossuiPedidosError se a peça ainda tem pedido vinculado
    # (FK RESTRICT no banco) — mesma ideia do Cliente.
    async def excluir(self, peca_id: UUID) -> bool: ...
