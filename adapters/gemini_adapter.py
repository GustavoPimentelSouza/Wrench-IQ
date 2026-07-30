from google import genai

_MODELO_PADRAO = "gemini-2.0-flash"

_PROMPT_CLASSIFICACAO = (
    "Classifique o problema mostrado na imagem em uma categoria curta "
    "(ex: dano_estrutural, pintura, lanternagem, peca_desgastada, outro). "
    "Responda só com a categoria, em snake_case."
)


class GeminiAdapter:
    def __init__(self, api_key: str, modelo: str = _MODELO_PADRAO):
        self._client = genai.Client(api_key=api_key)
        self._modelo = modelo

    async def classificar_imagem(self, caminho_imagem: str) -> str:
        arquivo = await self._client.aio.files.upload(file=caminho_imagem)
        resposta = await self._client.aio.models.generate_content(
            model=self._modelo,
            contents=[arquivo, _PROMPT_CLASSIFICACAO],
        )
        return resposta.text.strip()
