from dataclasses import dataclass
from datetime import time


@dataclass
class ConfiguracaoOficina:
    """Horário de funcionamento da oficina. Sempre uma linha só no banco —
    não é por cliente nem por peça, é uma configuração global do negócio.
    Sábado e domingo podem ficar fechados (abertura/fechamento = None).
    """

    id: int
    horario_semana_abertura: time
    horario_semana_fechamento: time
    horario_sabado_abertura: time | None
    horario_sabado_fechamento: time | None
    horario_domingo_abertura: time | None
    horario_domingo_fechamento: time | None
