import asyncio

from faster_whisper import WhisperModel

_MODELO_PADRAO = "base"


class WhisperAdapter:
    def __init__(
        self, modelo: str = _MODELO_PADRAO, device: str = "cpu", compute_type: str = "int8"
    ):
        self._modelo = WhisperModel(modelo, device=device, compute_type=compute_type)

    async def transcrever(self, caminho_audio: str) -> str:
        def _executar() -> str:
            segmentos, _ = self._modelo.transcribe(caminho_audio, language="pt")
            return " ".join(segmento.text.strip() for segmento in segmentos)

        return await asyncio.to_thread(_executar)
