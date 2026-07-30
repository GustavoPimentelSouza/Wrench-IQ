from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class Veiculo:
    """Cadastro estruturado de veículo (marca/modelo/ano/placa) vinculado a
    um Cliente. Existe como entidade própria, mas hoje NÃO é referenciada
    por Protocolo (que ainda usa um campo `veiculo: str` livre) — são dois
    caminhos paralelos que ainda não foram unificados, de propósito, pra não
    quebrar o que já funcionava.
    """

    id: UUID
    cliente_id: UUID  # dono do veículo — um cliente pode ter vários
    marca: str
    modelo: str
    ano: str
    placa: str
    criado_em: datetime
