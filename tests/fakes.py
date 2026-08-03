from typing import Any

from application.chat_service import RespostaChat
from domain.mensagem import CategoriaMensagem


class FakeClassificador:
    """Test double de application.classificacao_mensagem_service.
    ClassificadorDeMensagem — decide a categoria por palavra-chave, sem
    chamar nenhuma API. Usado em todos os testes automatizados (via
    app.dependency_overrides em tests/conftest.py) pra rodar sem custo,
    sem chave de API e sem depender de rede. A integração de verdade com o
    Groq é validada à parte, em tests/test_groq_integracao_real.py.
    """

    _MAPA_PALAVRA_CATEGORIA = {
        "preco": CategoriaMensagem.CONSULTA_PECA,
        "preço": CategoriaMensagem.CONSULTA_PECA,
        "peça": CategoriaMensagem.CONSULTA_PECA,
        "peca": CategoriaMensagem.CONSULTA_PECA,
        "pastilha": CategoriaMensagem.CONSULTA_PECA,
        "farol": CategoriaMensagem.CONSULTA_PECA,
        "horario": CategoriaMensagem.DUVIDA_GERAL,
        "horário": CategoriaMensagem.DUVIDA_GERAL,
        "estrutural": CategoriaMensagem.DANO_ESTRUTURAL,
        "batida": CategoriaMensagem.DANO_ESTRUTURAL,
        "agendar": CategoriaMensagem.AGENDAMENTO,
        "protocolo": CategoriaMensagem.STATUS_PROTOCOLO,
        "reclamacao": CategoriaMensagem.RECLAMACAO_SENSIVEL,
        "reclamação": CategoriaMensagem.RECLAMACAO_SENSIVEL,
    }

    async def classificar(self, texto: str) -> CategoriaMensagem:
        texto_normalizado = texto.lower()
        for palavra, categoria in self._MAPA_PALAVRA_CATEGORIA.items():
            if palavra in texto_normalizado:
                return categoria
        return CategoriaMensagem.NAO_IDENTIFICADO


class FakeChatService:
    """Test double de application.chat_service.ChatService — nunca chama
    ferramenta, só devolve um texto fixo e determinístico a partir da última
    mensagem. Cobre o /webhook sem custo, sem chave de API e sem rede.
    """

    async def gerar_resposta(
        self, mensagens: list[dict[str, Any]], ferramentas_disponiveis: list[dict[str, Any]]
    ) -> RespostaChat:
        ultima = mensagens[-1]["content"]
        return RespostaChat(texto=f"[fake-ia] resposta para: {ultima}")


class FakeEmbeddingService:
    """Test double de application.embedding_service.EmbeddingService —
    devolve um vetor determinístico (hash do texto), sem chamar o Gemini.
    Cobre /pecas, /pedidos, /movimentacoes-estoque e /webhook sem custo.
    """

    async def gerar_embedding(self, texto: str) -> list[float]:
        semente = sum(ord(c) for c in texto)
        return [((semente + i) % 1000) / 1000 for i in range(768)]
