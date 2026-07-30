"""Teste de integração REAL com o Groq — chama a API de verdade.

Não roda no `pytest` padrão (marcado @pytest.mark.integracao_real, excluído
via `addopts` em pytest.ini). Pra rodar de propósito, com GROQ_API_KEY
configurada (no .env ou no ambiente):

    pytest -m integracao_real -o addopts="" tests/test_groq_integracao_real.py

Se GROQ_API_KEY não estiver configurada, o teste se auto-pula (não falha)
— então mesmo rodando esse arquivo direto, sem querer, não estoura erro.
"""
import pytest

from adapters.groq_adapter import GroqClassificador
from domain.mensagem import CategoriaMensagem
from infrastructure.config import settings


@pytest.mark.integracao_real
async def test_groq_classifica_consulta_peca_de_verdade():
    if not settings.groq_api_key:
        pytest.skip("GROQ_API_KEY não configurada — veja o docstring deste arquivo.")

    classificador = GroqClassificador(api_key=settings.groq_api_key)
    categoria = await classificador.classificar("Quanto custa uma pastilha de freio?")

    assert categoria == CategoriaMensagem.CONSULTA_PECA
