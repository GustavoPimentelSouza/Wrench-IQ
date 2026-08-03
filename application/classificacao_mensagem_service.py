from typing import Protocol

from domain.mensagem import CategoriaMensagem


# Implementada por adapters/groq_adapter.py (GroqClassificador). O use case
# só conhece esta interface, nunca importa Groq/OpenAI diretamente.
class ClassificadorDeMensagem(Protocol):
    async def classificar(self, texto: str) -> CategoriaMensagem: ...
