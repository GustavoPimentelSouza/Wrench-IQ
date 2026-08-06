import json
from typing import Any

from openai import AsyncOpenAI, BadRequestError

from application.chat_service import ChamadaFerramenta, RespostaChat
from domain.mensagem import CategoriaMensagem

_BASE_URL = "https://api.groq.com/openai/v1"

_MODELO_PADRAO = "openai/gpt-oss-120b"
# Classificação fixa em poucas categorias não precisa do modelo grande.
_MODELO_CLASSIFICACAO_PADRAO = "llama-3.1-8b-instant"

# Sem isso, a API roda no default (1.0) — alto pra decisão binária de tool
# calling (chamar ferramenta ou não, qual) e já causou inconsistência
# observada (mesma situação, ora agenda, ora transfere pro humano sem
# tentar). 0.2 mantém a conversa natural mas prioriza consistência na
# decisão, que aqui importa mais que variedade de texto.
_TEMPERATURE_CHAT = 0.2
# Classificação é categorização pura — não há ganho em variar a saída, só
# risco de a mesma mensagem cair em categoria diferente em dois turnos.
_TEMPERATURE_CLASSIFICACAO = 0

# O SDK da OpenAI (usado pela Groq) tem default de 600s de timeout — sem
# sobrescrever isso, um Groq lento/instável deixa o cliente sem resposta
# nenhuma no WhatsApp por até 10 minutos, sem cair no fallback nem no
# handoff pra humano (esses só disparam quando a chamada de fato falha).
# 20s é generoso pro tamanho das nossas respostas e ainda assim rápido o
# bastante pra não deixar o cliente esperando de verdade.
_TIMEOUT_SEGUNDOS = 20.0


class GroqAdapter:
    def __init__(self, api_key: str, modelo: str = _MODELO_PADRAO):
        self._client = AsyncOpenAI(api_key=api_key, base_url=_BASE_URL, timeout=_TIMEOUT_SEGUNDOS)
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
            temperature=_TEMPERATURE_CHAT,
        )


# Listar só os nomes das categorias não bastava — o modelo confundia
# "paralama" (peça de lataria) com dano_estrutural só pelo assunto "lataria"
# aparecer nos dois, mesmo o cliente só querendo comprar a peça. Cada
# categoria agora tem um exemplo, com a distinção explícita entre "quer
# comprar/saber preço da peça" (sempre consulta_peca, mesmo peça de lataria)
# e "relata um dano de verdade e quer orçamento de conserto" (dano_estrutural).
_PROMPT_CLASSIFICACAO = (
    "Você classifica mensagens de clientes de uma oficina mecânica em "
    "exatamente uma destas categorias:\n"
    "- consulta_peca: cliente quer comprar, saber preço ou disponibilidade "
    "de uma peça — inclui peças de lataria (paralama, para-choque, capô). "
    "Ex: 'quanto custa um paralama pra fan 160', 'tem farol pra CG 160?'\n"
    "- duvida_geral: pergunta geral sobre a oficina (horário, endereço, "
    "serviços), sem falar de peça específica.\n"
    "- dano_estrutural: cliente relata um acidente/dano DE VERDADE e quer "
    "orçamento ou avaliação do CONSERTO. Ex: 'bati o carro', 'amassei a "
    "lateral', 'preciso consertar depois de uma batida', 'caí de moto e o "
    "guidão entortou todo', 'capotei e quebrou tudo', 'derrubei a moto e "
    "quebrou o retrovisor na queda'. Vale pra carro E moto, qualquer "
    "relato de acidente/queda com dano físico. IMPORTANTE: só é essa "
    "categoria se o cliente estiver pedindo avaliação de um dano — só "
    "pedir a peça pra comprar (mesmo de lataria) é sempre consulta_peca.\n"
    "- agendamento: cliente quer marcar uma visita/horário.\n"
    "- status_protocolo: pergunta sobre andamento de um serviço já em execução.\n"
    "- reclamacao_sensivel: cliente insatisfeito, reclamando, ou assunto grave/sensível.\n"
    "- nao_identificado: não deu pra identificar.\n"
    'Responda APENAS um JSON no formato {"categoria": "<valor>"}, com um '
    "desses valores exatos, sem inventar nenhum outro."
)


# Implementa ClassificadorDeMensagem via duck typing (Protocol), sem herdar dele.
class GroqClassificador:
    def __init__(self, api_key: str, modelo: str = _MODELO_CLASSIFICACAO_PADRAO):
        self._client = AsyncOpenAI(api_key=api_key, base_url=_BASE_URL, timeout=_TIMEOUT_SEGUNDOS)
        self._modelo = modelo

    async def classificar(self, texto: str) -> CategoriaMensagem:
        mensagens = [
            {"role": "system", "content": _PROMPT_CLASSIFICACAO},
            {"role": "user", "content": texto},
        ]

        try:
            resposta = await self._chamar_classificacao(mensagens)
        except Exception:
            # Antes só pegava BadRequestError (o modelo não seguir o JSON
            # mode) — mas rate limit, timeout, conexão etc. são exceções
            # DIFERENTES e passavam direto, sem tratamento nenhum. Isso
            # acontecia ANTES da mensagem virar Mensagem (webhook.py não
            # tem try/except), então o cliente ficava sem resposta e a
            # conversa nem aparecia na fila de atendimento — a IA "sumia".
            # Uma segunda tentativa costuma resolver falha transitória.
            try:
                resposta = await self._chamar_classificacao(mensagens)
            except Exception:
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
            temperature=_TEMPERATURE_CLASSIFICACAO,
        )
