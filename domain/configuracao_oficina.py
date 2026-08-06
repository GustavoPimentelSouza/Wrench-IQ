from dataclasses import dataclass
from datetime import time


@dataclass
class ConfiguracaoOficina:
    """Dados institucionais da oficina, usados pelo prompt da IA (pra ela
    parar de inventar coisa que não sabe — nome, endereço, horário, mensagem
    de encerramento). Sempre uma linha só no banco — não é por cliente nem
    por peça, é uma configuração global do negócio. Sábado e domingo podem
    ficar fechados (abertura/fechamento = None).
    """

    id: int
    nome_empresa: str
    horario_semana_abertura: time
    horario_semana_fechamento: time
    horario_sabado_abertura: time | None
    horario_sabado_fechamento: time | None
    horario_domingo_abertura: time | None
    horario_domingo_fechamento: time | None
    endereco: str | None = None
    mensagem_encerramento: str | None = None
