from typing import Protocol


# Classifica imagem (ex: foto de farol quebrado) numa categoria — mesmo
# formato de Mensagem.categoria. Implementada por adapters/gemini_adapter.py,
# ainda sem use case consumindo.
class VisaoService(Protocol):
    async def classificar_imagem(self, caminho_imagem: str) -> str: ...
