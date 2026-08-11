from uuid import UUID

from application.notificacao_repository import NotificacaoRepository
from domain.notificacao import Notificacao


# Fino de propósito: só embrulha o repository, sem regra de negócio própria
# — existe pra ter um único ponto de acesso reaproveitado tanto por
# ItemAdicionalUseCases quanto por AgendamentoDisponibilidadeUseCases (ver
# domain/notificacao.py), em vez de cada um falar direto com o repository.
class NotificacaoUseCases:
    def __init__(self, repository: NotificacaoRepository):
        self._repository = repository

    async def criar(self, notificacao: Notificacao) -> Notificacao:
        return await self._repository.criar(notificacao)

    async def listar_pendentes(self) -> list[Notificacao]:
        return await self._repository.listar_pendentes()

    async def marcar_enviada(self, notificacao_id: UUID) -> Notificacao | None:
        return await self._repository.marcar_enviada(notificacao_id)
