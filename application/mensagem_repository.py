from datetime import datetime
from typing import Protocol
from uuid import UUID

from domain.mensagem import Mensagem, MotivoAtendimento


# Mensagem é append-only (log) — sem excluir de propósito. A única "edição"
# permitida é registrar_resposta, que preenche resposta_ia depois que a IA
# responde (a mensagem em si, uma vez criada, não muda).
class MensagemRepository(Protocol):
    async def criar(self, mensagem: Mensagem) -> Mensagem: ...

    async def buscar_por_id(self, mensagem_id: UUID) -> Mensagem | None: ...

    # Últimas mensagens do cliente, mais antiga primeiro — usado pra montar
    # o histórico de conversa antes de chamar a IA. `desde` (opcional) corta
    # mensagens mais antigas que essa data — ver MensagemUseCases.listar_recentes.
    async def listar_por_cliente(
        self, cliente_id: UUID, limit: int, desde: datetime | None = None
    ) -> list[Mensagem]: ...

    async def registrar_resposta(
        self,
        mensagem_id: UUID,
        resposta: str,
        acao_finalizadora: str | None = None,
        imagem_url: str | None = None,
        ferramentas_chamadas: list[str] | None = None,
    ) -> None: ...

    # Regra 4 do CLAUDE.md (reclamação sensível/falha técnica/pedido da IA →
    # humano). marcar_atendimento_resolvido é o staff dando baixa depois de
    # atender.
    async def marcar_precisa_atendimento(
        self, mensagem_id: UUID, motivo: MotivoAtendimento
    ) -> None: ...

    async def marcar_atendimento_resolvido(self, mensagem_id: UUID) -> None: ...

    # Fila do painel de atendimento humano — mais recente primeiro.
    async def listar_pendentes_atendimento(self) -> list[Mensagem]: ...
