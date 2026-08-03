from datetime import datetime, timezone
from uuid import UUID, uuid4

from application.movimentacao_estoque_repository import MovimentacaoEstoqueRepository
from application.peca_repository import PecaRepository
from domain.movimentacao_estoque import MovimentacaoEstoque, TipoMovimentacao


class PecaNaoEncontradaError(Exception):
    pass


class EstoqueInsuficienteError(Exception):
    pass


class MovimentacaoEstoqueUseCases:
    # Dois repositories porque registrar movimentação mexe em Peca
    # (quantidade_estoque) e no histórico (MovimentacaoEstoque) juntos.
    def __init__(
        self,
        movimentacao_repository: MovimentacaoEstoqueRepository,
        peca_repository: PecaRepository,
    ):
        self._movimentacoes = movimentacao_repository
        self._pecas = peca_repository

    async def registrar(
        self, peca_id: UUID, tipo: TipoMovimentacao, quantidade: int
    ) -> MovimentacaoEstoque:
        # Ajuste manual (ex: reposição física, correção de contagem) —
        # diferente da movimentação automática de PedidoUseCases.
        peca = await self._pecas.buscar_por_id(peca_id)
        if peca is None:
            raise PecaNaoEncontradaError()
        if tipo == TipoMovimentacao.SAIDA and peca.quantidade_estoque < quantidade:
            raise EstoqueInsuficienteError()

        delta = quantidade if tipo == TipoMovimentacao.ENTRADA else -quantidade
        peca.quantidade_estoque += delta
        await self._pecas.atualizar(peca)

        movimentacao = MovimentacaoEstoque(
            id=uuid4(),
            peca_id=peca_id,
            tipo=tipo,
            quantidade=quantidade,
            criado_em=datetime.now(timezone.utc),
        )
        return await self._movimentacoes.criar(movimentacao)

    async def listar_por_peca(self, peca_id: UUID) -> list[MovimentacaoEstoque]:
        return await self._movimentacoes.listar_por_peca(peca_id)
