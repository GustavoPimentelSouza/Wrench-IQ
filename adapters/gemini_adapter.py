from google import genai
from google.genai import types

_MODELO_PADRAO = "gemini-2.0-flash"
# text-embedding-004 foi descontinuado na API v1beta — gemini-embedding-001
# é o modelo de embedding atual do Gemini.
_MODELO_EMBEDDING_PADRAO = "gemini-embedding-001"
_DIMENSOES_EMBEDDING = 768

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


# Implementa EmbeddingService via duck typing (Protocol), sem herdar dele —
# mesmo padrão de GroqClassificador em groq_adapter.py.
class GeminiEmbeddingService:
    def __init__(self, api_key: str, modelo: str = _MODELO_EMBEDDING_PADRAO):
        self._client = genai.Client(api_key=api_key)
        self._modelo = modelo

    async def gerar_embedding(self, texto: str) -> list[float]:
        resposta = await self._client.aio.models.embed_content(
            model=self._modelo,
            contents=texto,
            # Fixa a dimensão em 768 pra bater com a coluna Vector(768) do
            # banco — gemini-embedding-001 varia de 128 a 3072 por padrão.
            config=types.EmbedContentConfig(output_dimensionality=_DIMENSOES_EMBEDDING),
        )
        return resposta.embeddings[0].values
