from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass
class Peca:
    id: UUID
    nome: str
    # Texto livre (ex: "Honda CG 160", "2020-2024") — futuro campo de busca
    # do RAG mencionado no CLAUDE.md.
    marca_modelo_compativel: str
    ano_compativel: str
    preco: Decimal  # nunca float — dinheiro não pode ter erro de arredondamento
    quantidade_estoque: int
    criado_em: datetime
    imagem_url: str | None = None
    quantidade_minima: int = 0  # 0 = sem alerta de estoque baixo configurado
    # None = peça não tem variação de cor (ex: vela, cabo) — nem toda peça
    # tem, por isso opcional, não um valor tipo "sem cor" fixo.
    cor: str | None = None
