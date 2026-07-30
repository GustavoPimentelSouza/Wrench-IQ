import re
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

# Regex compilada uma única vez no import do módulo (não a cada chamada da
# função) — padrão: só dígitos, entre 10 e 15 caracteres. É o formato de
# telefone com DDI que o WhatsApp usa, ex: 5511999999999 (55 = Brasil,
# 11 = DDD, resto é o número).
_TELEFONE_REGEX = re.compile(r"^\d{10,15}$")


def telefone_valido(telefone: str) -> bool:
    """Só dígitos, entre 10 e 15 caracteres (padrão de número com DDI, ex: 5511999999999)."""
    return bool(_TELEFONE_REGEX.match(telefone))


@dataclass
class Cliente:
    # Campos sem valor padrão vêm primeiro (obrigatórios ao criar um Cliente).
    id: UUID
    nome: str
    telefone: str
    criado_em: datetime
    # Campos com "= None" são opcionais — Python exige que fiquem depois dos
    # obrigatórios num dataclass, senão dá erro de sintaxe. email/endereco/
    # cpf_cnpj nem sempre são coletados (ex: cliente que só manda WhatsApp
    # sem nunca ter dado o endereço) — por isso são None por padrão, e não
    # string vazia.
    email: str | None = None
    endereco: str | None = None
    cpf_cnpj: str | None = None
