import enum
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


class TipoEntrega(str, enum.Enum):
    RETIRADA_LOCAL = "retirada_local"
    ENVIO_REMOTO = "envio_remoto"


class StatusPedido(str, enum.Enum):
    # Este enum É a regra de negócio "venda remota tem fila de conferência
    # humana antes de despachar" (CLAUDE.md, regra 2) virando um caminho
    # obrigatório de estados. Repara a ordem: não dá pra ir direto de
    # AGUARDANDO_PAGAMENTO pra DESPACHADO — tem que passar por
    # AGUARDANDO_CONFERENCIA no meio (essa transição é forçada em
    # application/pedido_use_cases.py, não aqui — aqui é só a lista de
    # estados possíveis).
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
    # valor_total é sempre calculado no use case a partir de peca.preco —
    # nunca deve ser um valor que "vem de fora" (nem do cliente, nem da
    # conversa com a IA). Ver o comentário em
    # application/pedido_use_cases.py sobre isso, é a regra 3 do CLAUDE.md.
    valor_total: Decimal
    tipo_entrega: TipoEntrega
    status: StatusPedido
    criado_em: datetime
    # numero é o número sequencial "amigável" (tipo #42) gerado pelo banco
    # via Identity() — por isso é None aqui (o dataclass é criado ANTES de
    # existir no banco) e só fica preenchido depois que o repository salva
    # e devolve o registro completo.
    numero: int | None = None
    endereco_entrega: str | None = None  # só preenchido quando tipo_entrega é ENVIO_REMOTO
    link_pagamento: str | None = None  # idem, só existe pra envio remoto
    entregue_em: datetime | None = None  # usado pra calcular o prazo de arrependimento (7 dias, CDC)
