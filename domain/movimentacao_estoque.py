import enum
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


class TipoMovimentacao(str, enum.Enum):
    ENTRADA = "entrada"  # estoque aumentando (reposição, cancelamento de pedido)
    SAIDA = "saida"  # estoque diminuindo (venda confirmada)


@dataclass
class MovimentacaoEstoque:
    """Registro append-only (só se cria, nunca se edita/apaga) de toda vez
    que o estoque de uma peça muda. É o "extrato bancário" do estoque — serve
    pra auditoria: dá pra reconstruir o histórico de quantidade_estoque de
    uma peça somando/subtraindo essas movimentações, em vez de confiar só no
    valor atual guardado em Peca.quantidade_estoque.

    Quem cria isso hoje: application/pedido_use_cases.py (uma saída ao criar
    pedido, uma entrada ao cancelar) e
    application/movimentacao_estoque_use_cases.py (ajuste manual, ex:
    reposição de estoque pelo admin).
    """

    id: UUID
    peca_id: UUID
    tipo: TipoMovimentacao
    quantidade: int  # sempre positivo — o sinal (+/-) é dado pelo campo `tipo`, não por um número negativo
    criado_em: datetime
