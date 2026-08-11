from typing import Protocol
from uuid import UUID

from domain.notificacao import Notificacao


class NotificacaoRepository(Protocol):
    async def criar(self, notificacao: Notificacao) -> Notificacao: ...

    # Usado pelo worker externo (cron) que de fato envia a mensagem —
    # mesma ideia de PedidoUseCases.cancelar_expirados: o caso de uso só
    # gera o registro, quem consome e envia é um processo à parte.
    async def listar_pendentes(self) -> list[Notificacao]: ...

    async def marcar_enviada(self, notificacao_id: UUID) -> Notificacao | None: ...
