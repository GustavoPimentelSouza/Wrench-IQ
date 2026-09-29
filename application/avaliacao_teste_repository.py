from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from domain.avaliacao_teste import AvaliacaoTeste, ResultadoAvaliacao


@dataclass
class ResumoConversaTeste:
    """Linha da página de histórico — dado de leitura (junta cliente,
    mensagens e avaliação), não entidade de domínio."""

    cliente_id: UUID
    telefone: str
    inicio: datetime
    fim: datetime
    total_mensagens: int
    resultado: ResultadoAvaliacao | None  # None = ainda não avaliada
    comentario: str | None


class AvaliacaoTesteRepository(Protocol):
    async def buscar_por_cliente(self, cliente_id: UUID) -> AvaliacaoTeste | None: ...

    # Cria ou sobrescreve — cada conversa tem no máximo uma avaliação.
    async def salvar(self, avaliacao: AvaliacaoTeste) -> AvaliacaoTeste: ...

    # Só conversas do simulador que tiveram ao menos uma mensagem, mais recente primeiro.
    async def listar_conversas(self) -> list[ResumoConversaTeste]: ...
