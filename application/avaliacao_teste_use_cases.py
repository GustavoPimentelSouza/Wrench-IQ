from datetime import datetime, timezone
from uuid import UUID, uuid4

from application.avaliacao_teste_repository import (
    AvaliacaoTesteRepository,
    ResumoConversaTeste,
)
from application.cliente_repository import ClienteRepository
from application.mensagem_repository import MensagemRepository
from domain.avaliacao_teste import AvaliacaoTeste, ResultadoAvaliacao
from domain.mensagem import Mensagem

# Teto só de segurança: conversa de teste real tem dezenas de mensagens, não milhares.
_LIMITE_MENSAGENS_CONVERSA = 500


class ConversaNaoEncontradaError(Exception):
    """Telefone sem cliente: a conversa ainda não teve nenhuma mensagem."""


class AvaliacaoTesteUseCases:
    def __init__(
        self,
        repository: AvaliacaoTesteRepository,
        cliente_repository: ClienteRepository,
        mensagem_repository: MensagemRepository,
    ):
        self._repository = repository
        self._cliente_repository = cliente_repository
        self._mensagem_repository = mensagem_repository

    async def listar_conversas(self) -> list[ResumoConversaTeste]:
        return await self._repository.listar_conversas()

    # Reaproveita a mesma busca que monta o histórico pra IA (mais antiga primeiro).
    async def listar_mensagens(self, cliente_id: UUID) -> list[Mensagem]:
        return await self._mensagem_repository.listar_por_cliente(
            cliente_id, limit=_LIMITE_MENSAGENS_CONVERSA
        )

    # O simulador só conhece o telefone da conversa, não o id do cliente.
    async def avaliar(
        self, telefone: str, resultado: ResultadoAvaliacao, comentario: str | None
    ) -> AvaliacaoTeste:
        cliente = await self._cliente_repository.buscar_por_telefone(telefone)
        if cliente is None:
            raise ConversaNaoEncontradaError(telefone)

        agora = datetime.now(timezone.utc)
        existente = await self._repository.buscar_por_cliente(cliente.id)
        if existente is not None:
            # Mudou de ideia: edita a mesma avaliação, mantém criado_em.
            existente.resultado = resultado
            existente.comentario = comentario
            existente.atualizado_em = agora
            return await self._repository.salvar(existente)

        return await self._repository.salvar(
            AvaliacaoTeste(
                id=uuid4(), cliente_id=cliente.id, resultado=resultado,
                comentario=comentario, criado_em=agora, atualizado_em=agora,
            )
        )
