from typing import Protocol


# Interface pra "olhar uma imagem e devolver uma categoria" — ex: foto de um
# farol quebrado deveria virar algo como "peca_desgastada" ou
# "dano_estrutural". Implementada por adapters/gemini_adapter.py (Gemini
# Vision). O retorno ser só `str` (não um objeto mais rico) é proposital:
# espelha o mesmo formato que `Mensagem.categoria` já usa em
# domain/mensagem.py, então dá pra reaproveitar o mesmo tipo de fluxo de
# decisão (ex: dano_estrutural -> nunca orça, só agenda — regra 1 do
# CLAUDE.md). Assim como as outras duas interfaces de IA, ainda não está
# conectada a nenhum use case.
class VisaoService(Protocol):
    async def classificar_imagem(self, caminho_imagem: str) -> str: ...
