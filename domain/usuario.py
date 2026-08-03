import enum
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


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
