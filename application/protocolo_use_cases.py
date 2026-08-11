from datetime import datetime, timezone
from uuid import UUID, uuid4

from application.protocolo_repository import ProtocoloRepository
from application.reclassificacao_repository import ReclassificacaoRepository
from application.usuario_repository import UsuarioRepository
from domain.especialidade import Especialidade
from domain.protocolo import Protocolo, StatusProtocolo
from domain.reclassificacao_especialidade import ReclassificacaoEspecialidade
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
    # Entra/sai desse estado só via ItemAdicionalUseCases (registrar leva
    # aqui; aprovar/recusar tiram daqui) — por isso o único destino válido
    # pelas transições genéricas abaixo (aprovar/concluir/cancelar) é
    # cancelar o serviço inteiro enquanto o item ainda está pendente.
    StatusProtocolo.AGUARDANDO_APROVACAO_ADICIONAL: {StatusProtocolo.CANCELADO},
    StatusProtocolo.PRONTO: set(),
    StatusProtocolo.CANCELADO: set(),
}


class ProtocoloUseCases:
    def __init__(
        self,
        repository: ProtocoloRepository,
        usuario_repository: UsuarioRepository,
        reclassificacao_repository: ReclassificacaoRepository,
    ):
        self._repository = repository
        self._usuarios = usuario_repository
        self._reclassificacoes = reclassificacao_repository

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

    # A IA classifica pelo relato do cliente ANTES de qualquer mecânico
    # olhar o veículo de verdade — é só uma estimativa. Esse método existe
    # pra corrigir isso depois da avaliação presencial, sem precisar passar
    # pelo formulário genérico de atualizar() (que exige reenviar todos os
    # outros campos do protocolo só pra mudar isso).
    async def reclassificar_especialidade(
        self, protocolo_id: UUID, especialidades: list[Especialidade]
    ) -> Protocolo:
        protocolo = await self._repository.buscar_por_id(protocolo_id)
        if protocolo is None:
            raise ProtocoloNaoEncontradoError()
        especialidades_originais = protocolo.especialidades
        protocolo.especialidades = especialidades
        atualizado = await self._repository.atualizar(protocolo)
        assert atualizado is not None
        # Nenhum classificador acerta 100% do volume real de mensagens — esse
        # registro é o dado bruto de onde a IA está errando (ver GET
        # /relatorios/taxa-reclassificacao e domain/reclassificacao_especialidade.py).
        # Grava sempre, mesmo se o mecânico "reclassificar" pro mesmo valor
        # (não filtra por "mudou de verdade?") — simplicidade > otimizar um
        # caso raro que não atrapalha a métrica de qualquer jeito.
        await self._reclassificacoes.criar(
            ReclassificacaoEspecialidade(
                id=uuid4(),
                protocolo_id=protocolo_id,
                especialidades_originais=especialidades_originais,
                especialidades_finais=especialidades,
                criado_em=datetime.now(timezone.utc),
            )
        )
        return atualizado

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
