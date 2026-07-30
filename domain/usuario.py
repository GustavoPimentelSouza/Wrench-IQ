import enum
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


class PapelUsuario(str, enum.Enum):
    """Os 3 papéis possíveis pra quem tem login no sistema. Não existe uma
    entidade "Mecânico" separada — mecânico é só um Usuario com
    papel=MECANICO. Mesma tabela, mesmo login, diferenciados só por esse
    campo (ver infrastructure/security_dependencies.py, exigir_admin, pra
    ver como esse papel vira controle de acesso de verdade).
    """

    ADMIN = "admin"
    ATENDENTE = "atendente"
    MECANICO = "mecanico"


@dataclass
class Usuario:
    id: UUID
    nome: str
    email: str
    # Nunca a senha em texto puro — só o hash (bcrypt, gerado em
    # adapters/seguranca.py). Ninguém no sistema, nem o próprio código,
    # consegue "ver" a senha original a partir daqui.
    senha_hash: str
    papel: PapelUsuario
    # "Soft delete" — desativar um usuário não apaga a linha, só marca
    # ativo=False. Isso é checado em todo login E em toda requisição
    # autenticada (get_current_user), então desativar alguém corta o acesso
    # na hora, mesmo com um token JWT ainda válido.
    ativo: bool
    criado_em: datetime
