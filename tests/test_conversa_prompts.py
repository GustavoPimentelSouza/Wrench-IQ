from datetime import time

from application.conversa_prompts import construir_prompt_sistema
from domain.configuracao_oficina import ConfiguracaoOficina
from domain.mensagem import CategoriaMensagem

_CONFIG = ConfiguracaoOficina(
    id=1,
    nome_empresa="Oficina Dugrau",
    horario_semana_abertura=time(8, 0),
    horario_semana_fechamento=time(19, 0),
    horario_sabado_abertura=time(8, 0),
    horario_sabado_fechamento=time(18, 0),
    horario_domingo_abertura=None,
    horario_domingo_fechamento=None,
    endereco="Rua das Oficinas, 123",
    mensagem_encerramento="Agradecemos seu contato!",
)


def test_prompt_inclui_trava_de_escopo():
    # Bug real: a IA respondeu "quanto é 1+1?" antes dessa trava existir.
    prompt = construir_prompt_sistema(_CONFIG, CategoriaMensagem.CONSULTA_PECA)
    assert "SÓ ajuda com assuntos" in prompt


def test_prompt_inclui_dados_reais_da_oficina_em_vez_de_inventar():
    prompt = construir_prompt_sistema(_CONFIG, CategoriaMensagem.CONSULTA_PECA)
    assert "Oficina Dugrau" in prompt
    assert "Rua das Oficinas, 123" in prompt
    assert "08:00 às 19:00" in prompt


def test_prompt_domingo_fechado_aparece_como_fechado():
    prompt = construir_prompt_sistema(_CONFIG, CategoriaMensagem.CONSULTA_PECA)
    assert "domingo fechado" in prompt


def test_prompt_mensagem_encerramento_incluida():
    prompt = construir_prompt_sistema(_CONFIG, CategoriaMensagem.CONSULTA_PECA)
    assert "Agradecemos seu contato!" in prompt


def test_prompt_dano_estrutural_nunca_estima_valor():
    prompt = construir_prompt_sistema(_CONFIG, CategoriaMensagem.DANO_ESTRUTURAL)
    assert "NUNCA estima valor" in prompt
