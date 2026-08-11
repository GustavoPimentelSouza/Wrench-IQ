from types import SimpleNamespace

from adapters.groq_adapter import GroqAdapter

# Testa só a lógica pura de _malformada, sem chamar a API de verdade — a
# chave de API é fake porque o construtor de GroqAdapter só monta o client,
# não faz nenhuma chamada de rede.
_adapter = GroqAdapter(api_key="fake-key-sem-chamada-de-rede")


def _escolha(content: str | None, tool_calls: list | None = None):
    return SimpleNamespace(content=content, tool_calls=tool_calls)


def test_resposta_com_tool_call_nunca_e_malformada():
    assert _adapter._malformada(_escolha(None, tool_calls=[object()])) is False


def test_resposta_vazia_sem_tool_call_e_malformada():
    # Visto ao vivo: modelo não chama ferramenta E não devolve texto
    # nenhum — antes desse fix não disparava retry nenhum, só o fallback
    # genérico direto pro cliente, sem log de erro nenhum.
    assert _adapter._malformada(_escolha(None)) is True
    assert _adapter._malformada(_escolha("")) is True


def test_resposta_com_function_cru_e_malformada():
    assert _adapter._malformada(_escolha("<function=agendar_visita>...")) is True


def test_resposta_com_vazamento_de_raciocinio_e_malformada():
    assert _adapter._malformada(_escolha("Rascunho......... Resposta final")) is True


def test_resposta_normal_com_texto_nao_e_malformada():
    assert _adapter._malformada(_escolha("Olá! Como posso ajudar?")) is False
