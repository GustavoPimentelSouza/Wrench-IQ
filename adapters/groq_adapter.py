import json
from typing import Any

from openai import AsyncOpenAI

from application.chat_service import ChamadaFerramenta, RespostaChat
from domain.mensagem import CategoriaMensagem

_BASE_URL = "https://api.groq.com/openai/v1"
_MODELO_PADRAO = "llama-3.3-70b-versatile"
# Classificação em 7 categorias fixas é uma tarefa simples — não precisa do
# modelo grande usado pra conversa/tool calling acima. Um modelo menor é
# mais rápido e mais barato por chamada, e dá conta perfeitamente de um
# JSON de uma linha.
_MODELO_CLASSIFICACAO_PADRAO = "llama-3.1-8b-instant"


class GroqAdapter:
    def __init__(self, api_key: str, modelo: str = _MODELO_PADRAO):
        self._client = AsyncOpenAI(api_key=api_key, base_url=_BASE_URL)
        self._modelo = modelo

    async def gerar_resposta(
        self, mensagem: str, ferramentas_disponiveis: list[dict[str, Any]]
    ) -> RespostaChat:
        resposta = await self._client.chat.completions.create(
            model=self._modelo,
            messages=[{"role": "user", "content": mensagem}],
            tools=ferramentas_disponiveis or None,
        )
        escolha = resposta.choices[0].message
        chamadas = [
            ChamadaFerramenta(
                nome=chamada.function.name,
                argumentos=json.loads(chamada.function.arguments),
            )
            for chamada in (escolha.tool_calls or [])
        ]
        return RespostaChat(texto=escolha.content, chamadas_ferramentas=chamadas)


# Implementa application.classificacao_mensagem_service.ClassificadorDeMensagem
# — mas repara que essa classe não importa (nem depende de) essa interface
# em lugar nenhum. Isso é "duck typing" estrutural: em Python, um Protocol é
# satisfeito só por ter o método com a assinatura certa, sem herança
# explícita. Quem exige o contrato é quem RECEBE o objeto (o use case), não
# quem o implementa.
class GroqClassificador:
    def __init__(self, api_key: str, modelo: str = _MODELO_CLASSIFICACAO_PADRAO):
        self._client = AsyncOpenAI(api_key=api_key, base_url=_BASE_URL)
        self._modelo = modelo

    async def classificar(self, texto: str) -> CategoriaMensagem:
        # Lista as categorias válidas dinamicamente a partir do próprio enum
        # (não como texto solto duplicado aqui) — se alguém adicionar uma
        # categoria nova em domain/mensagem.py, o prompt já reflete isso
        # sozinho, sem precisar lembrar de atualizar dois lugares.
        categorias = ", ".join(categoria.value for categoria in CategoriaMensagem)

        resposta = await self._client.chat.completions.create(
            model=self._modelo,
            # "JSON mode": força o modelo a devolver só JSON válido, em vez
            # de texto livre que a gente teria que tentar interpretar na
            # unha. Ainda assim não há garantia de que o VALOR dentro do
            # JSON seja uma das categorias certas — por isso o try/except
            # mais abaixo.
            response_format={"type": "json_object"},
            messages=[
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
            ],
        )

        conteudo = resposta.choices[0].message.content or "{}"
        try:
            categoria_bruta = json.loads(conteudo)["categoria"]
            return CategoriaMensagem(categoria_bruta)
        except (json.JSONDecodeError, KeyError, ValueError):
            # O modelo não seguiu o formato pedido, ou "inventou" uma
            # categoria que não existe no enum — em vez de deixar o erro de
            # parsing estourar até o endpoint (virando um 500 sem
            # explicação), cai no mesmo "não sei classificar" que a versão
            # por palavra-chave já usava como catch-all.
            return CategoriaMensagem.NAO_IDENTIFICADO
