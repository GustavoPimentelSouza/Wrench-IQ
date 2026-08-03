import json
from typing import Any

from openai import AsyncOpenAI, BadRequestError

from application.chat_service import ChamadaFerramenta, RespostaChat
from domain.mensagem import CategoriaMensagem

_BASE_URL = "https://api.groq.com/openai/v1"
_MODELO_PADRAO = "llama-3.3-70b-versatile"
# Classificação fixa em poucas categorias não precisa do modelo grande.
_MODELO_CLASSIFICACAO_PADRAO = "llama-3.1-8b-instant"


class GroqAdapter:
    def __init__(self, api_key: str, modelo: str = _MODELO_PADRAO):
        self._client = AsyncOpenAI(api_key=api_key, base_url=_BASE_URL)
        self._modelo = modelo

    async def gerar_resposta(
        self, mensagens: list[dict[str, Any]], ferramentas_disponiveis: list[dict[str, Any]]
    ) -> RespostaChat:
        escolha = await self._gerar_escolha(mensagens, ferramentas_disponiveis)
        if self._malformada(escolha):
            # Mesma falha de sempre (o modelo erra a chamada de função), só
            # que dessa vez sem levantar erro — ele escreve o
            # "<function=...>" cru como se fosse texto de resposta. Uma
            # segunda tentativa costuma resolver, igual o caso do BadRequestError.
            escolha = await self._gerar_escolha(mensagens, ferramentas_disponiveis)

        chamadas = [
            ChamadaFerramenta(
                id=chamada.id,
                nome=chamada.function.name,
                argumentos=json.loads(chamada.function.arguments),
            )
            for chamada in (escolha.tool_calls or [])
        ]
        return RespostaChat(texto=escolha.content, chamadas_ferramentas=chamadas)

    async def _gerar_escolha(
        self, mensagens: list[dict[str, Any]], ferramentas_disponiveis: list[dict[str, Any]]
    ):
        try:
            resposta = await self._chamar(mensagens, ferramentas_disponiveis)
        except BadRequestError:
            resposta = await self._chamar(mensagens, ferramentas_disponiveis)
        return resposta.choices[0].message

    def _malformada(self, escolha) -> bool:
        return not escolha.tool_calls and "<function" in (escolha.content or "")

    async def _chamar(
        self, mensagens: list[dict[str, Any]], ferramentas_disponiveis: list[dict[str, Any]]
    ):
        return await self._client.chat.completions.create(
            model=self._modelo,
            messages=mensagens,
            tools=ferramentas_disponiveis or None,
        )


# Implementa ClassificadorDeMensagem via duck typing (Protocol), sem herdar dele.
class GroqClassificador:
    def __init__(self, api_key: str, modelo: str = _MODELO_CLASSIFICACAO_PADRAO):
        self._client = AsyncOpenAI(api_key=api_key, base_url=_BASE_URL)
        self._modelo = modelo

    async def classificar(self, texto: str) -> CategoriaMensagem:
        # Categorias listadas a partir do enum, não duplicadas como texto solto.
        categorias = ", ".join(categoria.value for categoria in CategoriaMensagem)
        mensagens = [
            {
                "role": "system",
                "content": (
                    "Você classifica mensagens de clientes de uma "
                    "oficina mecânica. Responda APENAS um JSON no "
                    'formato {"categoria": "<valor>"}, onde <valor> é '
                    "exatamente uma destas opções, sem inventar "
                    f"nenhuma outra: {categorias}."
                ),
            },
            {"role": "user", "content": texto},
        ]

        try:
            resposta = await self._chamar_classificacao(mensagens)
        except BadRequestError:
            # Mesma falha de sempre (o modelo às vezes não segue o JSON
            # mode) — uma segunda tentativa costuma resolver.
            try:
                resposta = await self._chamar_classificacao(mensagens)
            except BadRequestError:
                return CategoriaMensagem.NAO_IDENTIFICADO

        conteudo = resposta.choices[0].message.content or "{}"
        try:
            categoria_bruta = json.loads(conteudo)["categoria"]
            return CategoriaMensagem(categoria_bruta)
        except (json.JSONDecodeError, KeyError, ValueError):
            # Modelo não seguiu o formato ou inventou categoria inexistente.
            return CategoriaMensagem.NAO_IDENTIFICADO

    async def _chamar_classificacao(self, mensagens: list[dict[str, Any]]):
        return await self._client.chat.completions.create(
            model=self._modelo,
            response_format={"type": "json_object"},  # força JSON válido na saída
            messages=mensagens,
        )
