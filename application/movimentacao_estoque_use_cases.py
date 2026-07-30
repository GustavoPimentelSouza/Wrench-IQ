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
    # Repara que esse construtor recebe DOIS repositories, não um — porque
    # "registrar uma movimentação" mexe em duas entidades ao mesmo tempo:
    # a Peça (muda quantidade_estoque) e a própria MovimentacaoEstoque (o
    # registro histórico). Esse é o padrão pra reconhecer "regra de negócio
    # de verdade" nesse projeto: quando um __init__ recebe mais de um
    # repository, é sinal de que o use case está coordenando várias
    # entidades juntas, não só fazendo CRUD de uma.
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
        # Usado pra ajuste manual de estoque (ex: admin repondo peça física
        # que chegou, ou corrigindo uma contagem errada) — diferente da
        # movimentação automática que acontece dentro de PedidoUseCases
        # quando um pedido é criado/cancelado.
        peca = await self._pecas.buscar_por_id(peca_id)
        if peca is None:
            raise PecaNaoEncontradaError()
        if tipo == TipoMovimentacao.SAIDA and peca.quantidade_estoque < quantidade:
            # Só bloqueia saída maior que o estoque disponível — entrada
            # nunca tem esse problema (sempre pode repor).
            raise EstoqueInsuficienteError()

        # O sinal do ajuste depende do tipo: entrada soma, saída subtrai.
        # `quantidade` em si é sempre um número positivo (ver domain/
        # movimentacao_estoque.py) — é esse `delta` que carrega o sinal.
        delta = quantidade if tipo == TipoMovimentacao.ENTRADA else -quantidade
        peca.quantidade_estoque += delta
        await self._pecas.atualizar(peca)

        # Só depois de garantir que o ajuste de estoque deu certo é que o
        # registro histórico é criado — se algo desse errado antes disso
        # (peça não existe, estoque insuficiente), a exceção já teria
        # interrompido a execução e nenhum registro fantasma seria criado.
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
