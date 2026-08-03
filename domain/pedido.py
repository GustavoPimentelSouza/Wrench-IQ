import enum
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


class TipoEntrega(str, enum.Enum):
    RETIRADA_LOCAL = "retirada_local"
    ENVIO_REMOTO = "envio_remoto"


class StatusPedido(str, enum.Enum):
    # Ordem obrigatória (forçada em pedido_use_cases.py): não dá pra ir de
    # AGUARDANDO_PAGAMENTO direto pra DESPACHADO, tem que passar por
    # AGUARDANDO_CONFERENCIA — regra 2 do CLAUDE.md.
    AGUARDANDO_PAGAMENTO = "aguardando_pagamento"
    AGUARDANDO_RETIRADA = "aguardando_retirada"  # fluxo de retirada local, sem pagamento online
    AGUARDANDO_CONFERENCIA = "aguardando_conferencia"  # o "clique humano" antes de despachar
    DESPACHADO = "despachado"
    ENTREGUE = "entregue"
    CANCELADO = "cancelado"


@dataclass
class Pedido:
    id: UUID
    cliente_id: UUID
    peca_id: UUID
    quantidade: int
    # Sempre calculado a partir de peca.preco, nunca vindo de fora (regra 3, CLAUDE.md).
    valor_total: Decimal
    tipo_entrega: TipoEntrega
    status: StatusPedido
    criado_em: datetime
    numero: int | None = None  # gerado pelo banco, só existe após salvar
    endereco_entrega: str | None = None  # só preenchido quando tipo_entrega é ENVIO_REMOTO
    link_pagamento: str | None = None  # idem, só existe pra envio remoto
    entregue_em: datetime | None = None  # usado pra calcular o prazo de arrependimento (7 dias, CDC)
