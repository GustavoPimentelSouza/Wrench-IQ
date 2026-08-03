from uuid import UUID

from application.protocolo_repository import ProtocoloRepository
from application.usuario_repository import UsuarioRepository
from domain.protocolo import Protocolo, StatusProtocolo
from domain.usuario import PapelUsuario


class ProtocoloNaoEncontradoError(Exception):
    pass

class TransicaoInvalidaError(Exception):
    pass


class MecanicoInvalidoError(Exception):
    """Levantado quando mecanico_id não existe ou não é um usuário com papel=MECANICO."""


class OrcamentoNaoDefinidoError(Exception):
    """Levantado ao tentar aprovar um protocolo sem valor_orcamento definido."""


# status atual -> destinos permitidos. PRONTO/CANCELADO são finais.
_TRANSICOES_VALIDAS: dict[StatusProtocolo, set[StatusProtocolo]] = {
    StatusProtocolo.AGUARDANDO_APROVACAO: {
        StatusProtocolo.EM_EXECUCAO,
        StatusProtocolo.CANCELADO,
    },
    StatusProtocolo.EM_EXECUCAO: {StatusProtocolo.PRONTO, StatusProtocolo.CANCELADO},
    StatusProtocolo.PRONTO: set(),
    StatusProtocolo.CANCELADO: set(),
}


class ProtocoloUseCases:
    def __init__(self, repository: ProtocoloRepository, usuario_repository: UsuarioRepository):
        self._repository = repository
        self._usuarios = usuario_repository

    async def criar(self, protocolo: Protocolo) -> Protocolo:
        await self._validar_mecanico(protocolo.mecanico_id)
        return await self._repository.criar(protocolo)

    async def listar(self) -> list[Protocolo]:
        return await self._repository.listar()

    async def listar_por_cliente(self, cliente_id: UUID) -> list[Protocolo]:
        return await self._repository.listar_por_cliente(cliente_id)

    async def buscar_por_id(self, protocolo_id: UUID) -> Protocolo | None:
        return await self._repository.buscar_por_id(protocolo_id)

    async def atualizar(self, protocolo: Protocolo) -> Protocolo | None:
        # Status sempre vem do registro existente — só aprovar/concluir/cancelar mudam estado.
        existente = await self._repository.buscar_por_id(protocolo.id)
        if existente is None:
            return None
        await self._validar_mecanico(protocolo.mecanico_id)
        protocolo.status = existente.status
        return await self._repository.atualizar(protocolo)

    async def aprovar(self, protocolo_id: UUID) -> Protocolo:
        protocolo = await self._buscar_para_transicao(protocolo_id, StatusProtocolo.EM_EXECUCAO)
        if protocolo.valor_orcamento is None:
            raise OrcamentoNaoDefinidoError()
        return await self._transicionar(protocolo, StatusProtocolo.EM_EXECUCAO)

    async def concluir(self, protocolo_id: UUID) -> Protocolo:
        protocolo = await self._buscar_para_transicao(protocolo_id, StatusProtocolo.PRONTO)
        return await self._transicionar(protocolo, StatusProtocolo.PRONTO)

    async def cancelar(self, protocolo_id: UUID, motivo: str | None = None) -> Protocolo:
        protocolo = await self._buscar_para_transicao(protocolo_id, StatusProtocolo.CANCELADO)
        protocolo.motivo_cancelamento = motivo
        return await self._transicionar(protocolo, StatusProtocolo.CANCELADO)

    async def _buscar_para_transicao(
        self, protocolo_id: UUID, destino: StatusProtocolo
    ) -> Protocolo:
        protocolo = await self._repository.buscar_por_id(protocolo_id)
        if protocolo is None:
            raise ProtocoloNaoEncontradoError()
        if destino not in _TRANSICOES_VALIDAS[protocolo.status]:
            raise TransicaoInvalidaError()
        return protocolo

    async def _transicionar(self, protocolo: Protocolo, destino: StatusProtocolo) -> Protocolo:
        protocolo.status = destino
        atualizado = await self._repository.atualizar(protocolo)
        assert atualizado is not None
        return atualizado

    async def _validar_mecanico(self, mecanico_id: UUID | None) -> None:
        if mecanico_id is None:
            return
        usuario = await self._usuarios.buscar_por_id(mecanico_id)
        if usuario is None or usuario.papel != PapelUsuario.MECANICO:
            raise MecanicoInvalidoError()
