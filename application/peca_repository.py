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
    # semântica (pgvector) com corte de confiança alto: só devolve algo
    # quando a distância indica que é praticamente a mesma peça.
    async def buscar_por_nome_aproximado(self, texto: str) -> list[Peca]: ...

    # Fallback de buscar_por_nome_aproximado quando ela não acha nada — corte
    # mais largo, pra cobrir erro de digitação/nome incompleto sem confirmar
    # a peça sozinho (vira lista de sugestão pro cliente escolher, ver
    # ExecutorFerramentasConversa._consultar_preco_peca).
    async def sugerir_por_nome_aproximado(self, texto: str) -> list[Peca]: ...

    async def atualizar(self, peca: Peca) -> Peca | None: ...

    # Levanta PecaPossuiPedidosError se a peça ainda tem pedido vinculado
    # (FK RESTRICT no banco) — mesma ideia do Cliente.
    async def excluir(self, peca_id: UUID) -> bool: ...
