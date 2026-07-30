from decimal import Decimal
from uuid import UUID


def gerar_link_pagamento(pedido_id: UUID, valor_total: Decimal) -> str:
    """Placeholder de link de pagamento — sem integração real ainda.

    Troque esta função pela chamada ao gateway escolhido (ex: Mercado Pago)
    quando houver credenciais configuradas. Nenhum outro código depende de
    como o link é gerado, só desta função.
    """
    return f"https://pagamento.wrenchiq.com/mock/{pedido_id}"
