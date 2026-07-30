from datetime import datetime, timezone
from uuid import UUID, uuid4

from adapters.pagamento import gerar_link_pagamento
from application.movimentacao_estoque_repository import MovimentacaoEstoqueRepository
from application.peca_repository import PecaRepository
from application.pedido_repository import PedidoRepository
from domain.movimentacao_estoque import MovimentacaoEstoque, TipoMovimentacao
from domain.pedido import Pedido, StatusPedido, TipoEntrega


class PecaNaoEncontradaError(Exception):
    pass


class EstoqueInsuficienteError(Exception):
    pass


class EnderecoObrigatorioError(Exception):
    pass


class PedidoNaoEncontradoError(Exception):
    pass


class TransicaoInvalidaError(Exception):
    pass


class PedidoUseCases:
    def __init__(
        self,
        pedido_repository: PedidoRepository,
        peca_repository: PecaRepository,
        movimentacao_estoque_repository: MovimentacaoEstoqueRepository,
    ):
        self._pedidos = pedido_repository
        self._pecas = peca_repository
        self._movimentacoes = movimentacao_estoque_repository

    async def criar(
        self,
        cliente_id: UUID,
        peca_id: UUID,
        quantidade: int,
        tipo_entrega: TipoEntrega,
        endereco_entrega: str | None,
    ) -> Pedido:
        peca = await self._pecas.buscar_por_id(peca_id)
        if peca is None:
            raise PecaNaoEncontradaError()
        if peca.quantidade_estoque < quantidade:
            raise EstoqueInsuficienteError()
        if tipo_entrega == TipoEntrega.ENVIO_REMOTO and not endereco_entrega:
            raise EnderecoObrigatorioError()

        # Preço nunca vem do cliente — sempre calculado a partir do valor
        # real cadastrado na peça (defesa contra manipulação via conversa/API).
        valor_total = peca.preco * quantidade

        status_inicial = (
            StatusPedido.AGUARDANDO_PAGAMENTO
            if tipo_entrega == TipoEntrega.ENVIO_REMOTO
            else StatusPedido.AGUARDANDO_RETIRADA
        )

        pedido = Pedido(
            id=uuid4(),
            cliente_id=cliente_id,
            peca_id=peca_id,
            quantidade=quantidade,
            valor_total=valor_total,
            tipo_entrega=tipo_entrega,
            status=status_inicial,
            endereco_entrega=endereco_entrega,
            criado_em=datetime.now(timezone.utc),
        )
        if tipo_entrega == TipoEntrega.ENVIO_REMOTO:
            pedido.link_pagamento = gerar_link_pagamento(pedido.id, valor_total)

        pedido_criado = await self._pedidos.criar(pedido)

        peca.quantidade_estoque -= quantidade
        await self._pecas.atualizar(peca)
        await self._registrar_movimentacao(peca_id, TipoMovimentacao.SAIDA, quantidade)

        return pedido_criado

    async def listar(
        self, status: StatusPedido | None = None, limit: int = 50, offset: int = 0
    ) -> list[Pedido]:
        return await self._pedidos.listar(status=status, limit=limit, offset=offset)

    async def contar(self, status: StatusPedido | None = None) -> int:
        return await self._pedidos.contar(status=status)

    async def listar_por_cliente(
        self,
        cliente_id: UUID,
        status: StatusPedido | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Pedido]:
        return await self._pedidos.listar_por_cliente(
            cliente_id, status=status, limit=limit, offset=offset
        )

    async def contar_por_cliente(
        self, cliente_id: UUID, status: StatusPedido | None = None
    ) -> int:
        return await self._pedidos.contar_por_cliente(cliente_id, status=status)

    async def buscar_por_id(self, pedido_id: UUID) -> Pedido | None:
        return await self._pedidos.buscar_por_id(pedido_id)

    async def confirmar_pagamento(self, pedido_id: UUID) -> Pedido:
        pedido = await self._exigir_pedido(pedido_id)
        if pedido.status != StatusPedido.AGUARDANDO_PAGAMENTO:
            raise TransicaoInvalidaError()
        pedido.status = StatusPedido.AGUARDANDO_CONFERENCIA
        return await self._salvar(pedido)

    async def confirmar_conferencia(self, pedido_id: UUID) -> Pedido:
        # "Fila de conferência simples (um clique)" — nunca despacha sem
        # essa checagem humana, mesmo com o pagamento já confirmado.
        pedido = await self._exigir_pedido(pedido_id)
        if pedido.status != StatusPedido.AGUARDANDO_CONFERENCIA:
            raise TransicaoInvalidaError()
        pedido.status = StatusPedido.DESPACHADO
        return await self._salvar(pedido)

    async def marcar_entregue(self, pedido_id: UUID) -> Pedido:
        pedido = await self._exigir_pedido(pedido_id)
        if pedido.status not in (StatusPedido.DESPACHADO, StatusPedido.AGUARDANDO_RETIRADA):
            raise TransicaoInvalidaError()
        pedido.status = StatusPedido.ENTREGUE
        pedido.entregue_em = datetime.now(timezone.utc)
        return await self._salvar(pedido)

    async def cancelar(self, pedido_id: UUID) -> Pedido:
        pedido = await self._exigir_pedido(pedido_id)
        if pedido.status in (StatusPedido.ENTREGUE, StatusPedido.CANCELADO):
            raise TransicaoInvalidaError()
        pedido.status = StatusPedido.CANCELADO
        pedido_atualizado = await self._salvar(pedido)

        peca = await self._pecas.buscar_por_id(pedido.peca_id)
        if peca is not None:
            peca.quantidade_estoque += pedido.quantidade
            await self._pecas.atualizar(peca)
            await self._registrar_movimentacao(
                pedido.peca_id, TipoMovimentacao.ENTRADA, pedido.quantidade
            )

        return pedido_atualizado

    async def _exigir_pedido(self, pedido_id: UUID) -> Pedido:
        pedido = await self._pedidos.buscar_por_id(pedido_id)
        if pedido is None:
            raise PedidoNaoEncontradoError()
        return pedido

    async def _salvar(self, pedido: Pedido) -> Pedido:
        atualizado = await self._pedidos.atualizar(pedido)
        assert atualizado is not None
        return atualizado

    async def _registrar_movimentacao(
        self, peca_id: UUID, tipo: TipoMovimentacao, quantidade: int
    ) -> None:
        movimentacao = MovimentacaoEstoque(
            id=uuid4(),
            peca_id=peca_id,
            tipo=tipo,
            quantidade=quantidade,
            criado_em=datetime.now(timezone.utc),
        )
        await self._movimentacoes.criar(movimentacao)
