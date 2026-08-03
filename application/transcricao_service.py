from typing import Protocol


# Implementada por adapters/whisper_adapter.py. Ainda sem use case consumindo.
class TranscricaoService(Protocol):
    async def transcrever(self, caminho_audio: str) -> str: ...
