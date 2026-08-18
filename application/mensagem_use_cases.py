from datetime import datetime, timezone
from uuid import UUID, uuid4

from application.classificacao_mensagem_service import ClassificadorDeMensagem
from application.mensagem_repository import MensagemRepository
from domain.mensagem import Mensagem, MotivoAtendimento


class MensagemUseCases:
    def __init__(
        self, repository: MensagemRepository, classificador: ClassificadorDeMensagem
    ):
        self._repository = repository
        self._classificador = classificador

    async def receber(self, cliente_id: UUID, texto: str) -> Mensagem:
        # Chamado por /webhook, /webhook/whatsapp e /mensagens. Classifica
        # antes de persistir; testes injetam um FakeClassificador (tests/fakes.py).
        # precisa_atendimento_humano nunca é decidido aqui: a categoria vem
        # de classificar só essa mensagem isolada, sem ver o histórico da
        # conversa — quem decide de verdade se precisa de humano é
        # ConversaUseCases, que tem o histórico completo (ver
        # marcar_precisa_atendimento, chamado por webhook.py depois).
        categoria = await self._classificador.classificar(texto)
        mensagem = Mensagem(
            id=uuid4(),
            cliente_id=cliente_id,
            texto=texto,
            categoria=categoria,
            criado_em=datetime.now(timezone.utc),
        )
        return await self._repository.criar(mensagem)

    async def listar_recentes(self, cliente_id: UUID, limit: int = 6) -> list[Mensagem]:
        return await self._repository.listar_por_cliente(cliente_id, limit)

    async def registrar_resposta(
        self,
        mensagem_id: UUID,
        resposta: str,
        acao_finalizadora: str | None = None,
        imagem_url: str | None = None,
        ferramentas_chamadas: list[str] | None = None,
    ) -> None:
        await self._repository.registrar_resposta(
            mensagem_id, resposta, acao_finalizadora, imagem_url, ferramentas_chamadas
        )

    # Chamado por ConversaUseCases quando a IA não consegue responder de
    # verdade, ou pede transferência ela mesma (regra 4) — separado de
    # receber() porque só se sabe se precisou de humano DEPOIS de tentar
    # responder, não na hora de classificar.
    async def marcar_precisa_atendimento(
        self, mensagem_id: UUID, motivo: MotivoAtendimento
    ) -> None:
        await self._repository.marcar_precisa_atendimento(mensagem_id, motivo)

    async def marcar_atendimento_resolvido(self, mensagem_id: UUID) -> None:
        await self._repository.marcar_atendimento_resolvido(mensagem_id)

    # Alimenta a tela de fila de atendimento humano no painel.
    async def listar_pendentes_atendimento(self) -> list[Mensagem]:
        return await self._repository.listar_pendentes_atendimento()
