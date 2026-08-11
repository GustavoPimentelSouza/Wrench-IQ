import enum
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from domain.especialidade import Especialidade


class PapelUsuario(str, enum.Enum):
    """Não existe entidade "Mecânico" separada — é um Usuario com papel=MECANICO."""

    ADMIN = "admin"
    ATENDENTE = "atendente"
    MECANICO = "mecanico"


@dataclass
class Usuario:
    id: UUID
    nome: str
    email: str
    senha_hash: str  # hash bcrypt (adapters/seguranca.py), nunca texto puro
    papel: PapelUsuario
    # Soft delete: ativo=False corta acesso na hora, mesmo com JWT válido
    # (checado em get_current_user).
    ativo: bool
    criado_em: datetime
    # Só tem sentido pra papel=MECANICO. N:N — um mecânico pode cobrir mais
    # de uma área (ex: funilaria e elétrica). Usado por
    # AgendamentoUseCases.listar_mecanicos_qualificados pra filtrar quem
    # pode atender um caso.
    especialidades: list[Especialidade] = field(default_factory=list)
