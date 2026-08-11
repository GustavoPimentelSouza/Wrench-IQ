from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from domain.especialidade import Especialidade


@dataclass
class ReclassificacaoEspecialidade:
    """Registro histórico de toda vez que um mecânico corrige a
    especialidade que a IA classificou sozinha, depois de avaliar o
    veículo presencialmente (ver ProtocoloUseCases.reclassificar_
    especialidade). Nenhum classificador acerta 100% do volume e da
    variedade real de mensagens de produção — esse histórico é o dado bruto
    pra medir isso na prática (ver GET /relatorios/taxa-reclassificacao) e,
    com o tempo, virar eval set de verdade e apontar padrões que merecem
    virar atalho determinístico na camada de palavra-chave/prompt (ver
    conversa_prompts.py) em vez de depender só do modelo.
    """

    id: UUID
    protocolo_id: UUID
    especialidades_originais: list[Especialidade]
    especialidades_finais: list[Especialidade]
    criado_em: datetime
