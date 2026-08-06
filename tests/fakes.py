from typing import Any

from application.chat_service import RespostaChat
from domain.mensagem import CategoriaMensagem
from domain.peca import Peca


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
    """Test double de application.chat_service.ChatService. Por padrão nunca
    chama ferramenta, só devolve um texto fixo e determinístico a partir da
    última mensagem — cobre o /webhook sem custo, sem chave de API e sem rede.

    Pra testar o loop de tool calling (ConversaUseCases), passe `respostas`:
    uma fila de RespostaChat consumida em ordem, uma por chamada — simula
    "o modelo decidiu chamar criar_pedido" sem depender do Groq de verdade.
    `ferramentas_recebidas` grava o que cada chamada recebeu, pra testes
    conferirem ex: "na categoria dano_estrutural, criar_pedido nunca pode
    estar na lista de ferramentas oferecidas".
    """

    def __init__(self, respostas: list[RespostaChat] | None = None):
        self._fila = list(respostas) if respostas else None
        self.ferramentas_recebidas: list[list[dict[str, Any]]] = []

    async def gerar_resposta(
        self, mensagens: list[dict[str, Any]], ferramentas_disponiveis: list[dict[str, Any]]
    ) -> RespostaChat:
        self.ferramentas_recebidas.append(ferramentas_disponiveis)
        if self._fila:
            return self._fila.pop(0)
        ultima = mensagens[-1]["content"]
        return RespostaChat(texto=f"[fake-ia] resposta para: {ultima}")


class FakeChatServiceComErro:
    """Simula falha técnica na chamada à IA (rede, API fora do ar etc.) —
    usado pra testar a rede de segurança de ConversaUseCases.responder()
    (regra 4 do CLAUDE.md: falha técnica cai pro atendente humano)."""

    async def gerar_resposta(
        self, mensagens: list[dict[str, Any]], ferramentas_disponiveis: list[dict[str, Any]]
    ) -> RespostaChat:
        raise ConnectionError("falha simulada de rede")


class FakePecaRepository:
    """Test double de application.peca_repository.PecaRepository — só os
    dois métodos que ConversaUseCases usa de verdade."""

    def __init__(self, pecas: list[Peca] | None = None):
        self._pecas = pecas or []

    async def buscar_por_nome_aproximado(self, texto: str) -> list[Peca]:
        return self._pecas

    async def buscar_por_id(self, peca_id: Any) -> Peca | None:
        return next((p for p in self._pecas if p.id == peca_id), None)


class FakePedidoUseCases:
    """Test double de application.pedido_use_cases.PedidoUseCases — só os
    métodos que ConversaUseCases chama (criar, listar_por_cliente, cancelar).
    `ultima_chamada` grava os argumentos recebidos, pra confirmar que um
    pedido NÃO foi criado quando o teste espera um bloqueio (ex: endereço
    inválido)."""

    def __init__(
        self,
        pedido: Any = None,
        erro: Exception | None = None,
        pedidos_do_cliente: list[Any] | None = None,
        erro_cancelar: Exception | None = None,
    ):
        self._pedido = pedido
        self._erro = erro
        self._pedidos_do_cliente = pedidos_do_cliente or []
        self._erro_cancelar = erro_cancelar
        self.ultima_chamada: dict[str, Any] | None = None
        self.cancelado_id: Any = None

    async def criar(self, **kwargs: Any) -> Any:
        self.ultima_chamada = kwargs
        if self._erro:
            raise self._erro
        return self._pedido

    async def listar_por_cliente(self, cliente_id: Any, **kwargs: Any) -> list[Any]:
        return self._pedidos_do_cliente

    async def cancelar(self, pedido_id: Any) -> Any:
        if self._erro_cancelar:
            raise self._erro_cancelar
        self.cancelado_id = pedido_id
        return next(p for p in self._pedidos_do_cliente if p.id == pedido_id)


class FakeAgendamentoUseCases:
    """Test double de application.agendamento_use_cases.AgendamentoUseCases
    — só `criar`, único método que ConversaUseCases chama."""

    def __init__(self, erro: Exception | None = None):
        self._erro = erro
        self.ultimo_agendamento: Any = None

    async def criar(self, agendamento: Any) -> Any:
        if self._erro:
            raise self._erro
        self.ultimo_agendamento = agendamento
        return agendamento


class FakeConfiguracaoOficinaUseCases:
    """Test double de
    application.configuracao_oficina_use_cases.ConfiguracaoOficinaUseCases —
    só `buscar`, único método que ConversaUseCases chama."""

    def __init__(self, configuracao: Any):
        self._configuracao = configuracao

    async def buscar(self) -> Any:
        return self._configuracao


class FakeProtocoloUseCases:
    """Test double de application.protocolo_use_cases.ProtocoloUseCases — só
    `listar_por_cliente`, único método que ConversaUseCases chama."""

    def __init__(self, protocolos_do_cliente: list[Any] | None = None):
        self._protocolos_do_cliente = protocolos_do_cliente or []

    async def listar_por_cliente(self, cliente_id: Any) -> list[Any]:
        return self._protocolos_do_cliente


class FakeEmbeddingService:
    """Test double de application.embedding_service.EmbeddingService —
    devolve um vetor determinístico (hash do texto), sem chamar o Gemini.
    Cobre /pecas, /pedidos, /movimentacoes-estoque e /webhook sem custo.
    """

    async def gerar_embedding(self, texto: str) -> list[float]:
        semente = sum(ord(c) for c in texto)
        return [((semente + i) % 1000) / 1000 for i in range(768)]
