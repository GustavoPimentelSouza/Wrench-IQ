import enum
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


class TipoNotificacao(str, enum.Enum):
    ITEM_ADICIONAL_PROTOCOLO = "item_adicional_protocolo"
    LISTA_ESPERA_VAGA_DISPONIVEL = "lista_espera_vaga_disponivel"


@dataclass
class Notificacao:
    """Aviso pendente de envio pro cliente (WhatsApp). O projeto ainda não
    tem um worker de fila de verdade rodando em background — mesmo padrão
    já usado pra expirar reserva de pedido (ver
    PedidoUseCases.cancelar_expirados/POST /pedidos/expirar-retiradas): um
    caso de uso gera o registro, e um processo externo (cron batendo num
    endpoint) consome e envia depois. Reaproveitado tanto por item
    adicional de protocolo quanto por lista de espera de agendamento, pra
    não duplicar esse mecanismo duas vezes.
    """

    id: UUID
    cliente_id: UUID
    tipo: TipoNotificacao
    mensagem: str
    criado_em: datetime
    enviada: bool = False
    enviada_em: datetime | None = None
