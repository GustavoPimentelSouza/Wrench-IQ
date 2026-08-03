from typing import Protocol


# Implementada por adapters/gemini_adapter.py (GeminiEmbeddingService).
# Usada por SqlAlchemyPecaRepository pra gerar o vetor de busca semântica —
# domain/application nunca veem o vetor em si, só o texto e o resultado.
class EmbeddingService(Protocol):
    async def gerar_embedding(self, texto: str) -> list[float]: ...
