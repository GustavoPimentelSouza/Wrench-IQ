import enum
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from domain.especialidade import Especialidade


class StatusAgendamento(str, enum.Enum):
    AGENDADO = "agendado"  # estado inicial, ao criar
    CONFIRMADO = "confirmado"
    CANCELADO = "cancelado"
    CONCLUIDO = "concluido"
    # Passou da tolerância de no-show (ConfiguracaoOficina.tolerancia_no_
    # show_minutos) sem o cliente aparecer — liberado automaticamente por
    # AgendamentoDisponibilidadeUseCases.liberar_no_shows. Diferente de
    # CANCELADO: aqui é a oficina que constatou a ausência, não o cliente
    # que desistiu — útil separar pra métricas de no-show no futuro.
    NAO_COMPARECEU = "nao_compareceu"


@dataclass
class Agendamento:
    """Uma visita marcada por um Cliente (ex: pra avaliação de dano
    estrutural, que a IA nunca orça sozinha — só agenda). Ainda sem vínculo
    direto com Protocolo (isso continua manual, criado pelo mecânico depois
    da visita) — `descricao` existe pra não perder o que a IA já apurou na
    conversa (o quê, em qual veículo) até esse momento manual acontecer.
    """

    id: UUID
    cliente_id: UUID
    data_hora: datetime
    status: StatusAgendamento
    criado_em: datetime
    descricao: str | None = None
    # N:N — a IA classifica pelo relato do cliente (ver conversa_prompts.py).
    # Pode conter Especialidade.INDEFINIDO de verdade (persistido como está,
    # nunca convertido na criação) — só a busca de disponibilidade trata
    # isso como MECANICA_GERAL (ver domain/especialidade.py).
    especialidades: list[Especialidade] = field(default_factory=list)
