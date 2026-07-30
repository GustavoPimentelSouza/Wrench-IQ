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


# Mapa de transição: status atual -> conjunto de status destino permitidos.
# PRONTO e CANCELADO são estados finais (conjunto vazio, nenhuma saída).
# Mesma ideia de máquina de estados que StatusPedido já usava em
# application/pedido_use_cases.py — aqui replicada pra Protocolo.
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
        # Edição de campos "de cadastro" (veiculo, categoria, descricao,
        # mecanico_id) — NÃO muda status. O status vem sempre do registro já
        # existente, ignorando o que tiver em `protocolo.status`, pra
        # garantir que só aprovar()/concluir()/cancelar() consigam mudar o
        # estado, mesmo que algum chamador futuro tente passar outra coisa
        # aqui por engano.
        existente = await self._repository.buscar_por_id(protocolo.id)
        if existente is None:
            return None
        await self._validar_mecanico(protocolo.mecanico_id)
        protocolo.status = existente.status
        return await self._repository.atualizar(protocolo)

    async def aprovar(self, protocolo_id: UUID) -> Protocolo:
        return await self._transicionar(protocolo_id, StatusProtocolo.EM_EXECUCAO)

    async def concluir(self, protocolo_id: UUID) -> Protocolo:
        return await self._transicionar(protocolo_id, StatusProtocolo.PRONTO)

    async def cancelar(self, protocolo_id: UUID) -> Protocolo:
        return await self._transicionar(protocolo_id, StatusProtocolo.CANCELADO)

    async def _transicionar(self, protocolo_id: UUID, destino: StatusProtocolo) -> Protocolo:
        protocolo = await self._repository.buscar_por_id(protocolo_id)
        if protocolo is None:
            raise ProtocoloNaoEncontradoError()
        if destino not in _TRANSICOES_VALIDAS[protocolo.status]:
            raise TransicaoInvalidaError()
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
