from typing import Protocol


# Interface pra "transformar áudio em texto". Implementada hoje por
# adapters/whisper_adapter.py (faster-whisper, rodando local — sem API
# externa, sem custo por chamada). Também ainda não é chamada por nenhum
# use case: no webhook do WhatsApp, uma mensagem de áudio hoje só é
# reconhecida como tal e devolvida sem processar (ver
# infrastructure/routers/webhook.py).
class TranscricaoService(Protocol):
    async def transcrever(self, caminho_audio: str) -> str: ...
