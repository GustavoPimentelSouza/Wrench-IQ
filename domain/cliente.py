import re
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

# Formato com DDI que o WhatsApp usa, ex: 5511999999999.
_TELEFONE_REGEX = re.compile(r"^\d{10,15}$")


def telefone_valido(telefone: str) -> bool:
    """Só dígitos, entre 10 e 15 caracteres (padrão de número com DDI, ex: 5511999999999)."""
    return bool(_TELEFONE_REGEX.match(telefone))


@dataclass
class Cliente:
    id: UUID
    nome: str
    telefone: str
    criado_em: datetime
    # Nem sempre coletados (ex: cliente que só manda WhatsApp) — por isso
    # None em vez de string vazia.
    email: str | None = None
    endereco: str | None = None
    cpf_cnpj: str | None = None
