from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from application.item_adicional_repository import ItemAdicionalRepository
from application.notificacao_use_cases import NotificacaoUseCases
from application.protocolo_repository import ProtocoloRepository
from application.protocolo_use_cases import ProtocoloNaoEncontradoError
from domain.item_adicional_protocolo import ItemAdicionalProtocolo, StatusItemAdicional
from domain.notificacao import Notificacao, TipoNotificacao
from domain.protocolo import StatusProtocolo


class ProtocoloNaoEstaEmExecucaoError(Exception):
    """Só faz sentido registrar item adicional em cima de um serviço que já
    está sendo feito — não antes de aprovar o orçamento original, nem
    depois de pronto/cancelado."""


class ItemAdicionalNaoEncontradoError(Exception):
    pass


class ItemAdicionalJaProcessadoError(Exception):
    """Já foi aprovado ou recusado antes — não dá pra decidir de novo."""


# Um serviço pode revelar problema novo no meio da execução (regra 1 do
# CLAUDE.md continua valendo: nem a IA nem o mecânico sozinho fecham esse
# valor a mais — o cliente decide). Separado de ProtocoloUseCases (que já
# tem sua própria máquina de estados) porque aqui a transição de status do
# Protocolo é só um EFEITO colateral de decidir sobre o item, não o
# propósito do caso de uso.
class ItemAdicionalUseCases:
    def __init__(
        self,
        repository: ItemAdicionalRepository,
        protocolo_repository: ProtocoloRepository,
        notificacoes: NotificacaoUseCases,
    ):
        self._repository = repository
        self._protocolos = protocolo_repository
        self._notificacoes = notificacoes

    async def registrar(
        self,
        protocolo_id: UUID,
        descricao: str,
        valor: Decimal,
        peca_id: UUID | None = None,
    ) -> ItemAdicionalProtocolo:
        protocolo = await self._protocolos.buscar_por_id(protocolo_id)
        if protocolo is None:
            raise ProtocoloNaoEncontradoError()
        if protocolo.status != StatusProtocolo.EM_EXECUCAO:
            raise ProtocoloNaoEstaEmExecucaoError()

        item = await self._repository.criar(
            ItemAdicionalProtocolo(
                id=uuid4(),
                protocolo_id=protocolo_id,
                descricao=descricao,
                valor=valor,
                peca_id=peca_id,
                status=StatusItemAdicional.PENDENTE,
                criado_em=datetime.now(timezone.utc),
            )
        )

        # O protocolo trava aqui até o cliente decidir — nunca segue "como
        # se nada tivesse acontecido" escondendo o problema novo dele.
        protocolo.status = StatusProtocolo.AGUARDANDO_APROVACAO_ADICIONAL
        await self._protocolos.atualizar(protocolo)

        await self._notificacoes.criar(
            Notificacao(
                id=uuid4(),
                cliente_id=protocolo.cliente_id,
                tipo=TipoNotificacao.ITEM_ADICIONAL_PROTOCOLO,
                mensagem=(
                    f"Encontramos um item adicional no seu veículo (protocolo "
                    f"#{protocolo.numero}): {descricao} — R$ {valor}. Podemos "
                    "incluir no serviço?"
                ),
                criado_em=datetime.now(timezone.utc),
            )
        )
        return item

    async def aprovar(self, item_id: UUID) -> ItemAdicionalProtocolo:
        item = await self._buscar_pendente(item_id)
        item.status = StatusItemAdicional.APROVADO
        item_atualizado = await self._repository.atualizar(item)
        assert item_atualizado is not None

        protocolo = await self._protocolos.buscar_por_id(item.protocolo_id)
        assert protocolo is not None
        # Retoma a execução — e o valor a mais entra no orçamento agora,
        # nunca antes do cliente aprovar (regra 1 do CLAUDE.md).
        protocolo.status = StatusProtocolo.EM_EXECUCAO
        protocolo.valor_orcamento = (protocolo.valor_orcamento or Decimal("0")) + item.valor
        await self._protocolos.atualizar(protocolo)
        return item_atualizado

    async def recusar(self, item_id: UUID) -> ItemAdicionalProtocolo:
        item = await self._buscar_pendente(item_id)
        item.status = StatusItemAdicional.RECUSADO
        item_atualizado = await self._repository.atualizar(item)
        assert item_atualizado is not None

        protocolo = await self._protocolos.buscar_por_id(item.protocolo_id)
        assert protocolo is not None
        # Sem o item recusado, não sobra nada mais a decidir — conclui com
        # o escopo original (valor_orcamento intacto, nunca inclui o item
        # que o cliente recusou).
        protocolo.status = StatusProtocolo.PRONTO
        await self._protocolos.atualizar(protocolo)
        return item_atualizado

    async def _buscar_pendente(self, item_id: UUID) -> ItemAdicionalProtocolo:
        item = await self._repository.buscar_por_id(item_id)
        if item is None:
            raise ItemAdicionalNaoEncontradoError()
        if item.status != StatusItemAdicional.PENDENTE:
            raise ItemAdicionalJaProcessadoError()
        return item
