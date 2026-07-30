from typing import Protocol
from uuid import UUID

from domain.movimentacao_estoque import MovimentacaoEstoque


# Igual Mensagem: só "criar" e "listar", sem atualizar/excluir — é um
# registro append-only (o "extrato" de entradas/saídas de estoque, ver
# domain/movimentacao_estoque.py). Uma vez criado, não se edita.
class MovimentacaoEstoqueRepository(Protocol):
    async def criar(self, movimentacao: MovimentacaoEstoque) -> MovimentacaoEstoque: ...

    async def listar_por_peca(self, peca_id: UUID) -> list[MovimentacaoEstoque]: ...
