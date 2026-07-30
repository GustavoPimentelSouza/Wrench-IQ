from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass
class Peca:
    id: UUID
    nome: str
    # Strings livres de compatibilidade (ex: "Honda CG 160", "2020-2024").
    # Hoje é texto simples, sem estrutura — é assim que o RAG mencionado no
    # CLAUDE.md vai entrar no futuro: usar esses campos (e o nome) pra buscar
    # por similaridade semântica, traduzindo "termo leigo" do cliente pra
    # peça certa no catálogo.
    marca_modelo_compativel: str
    ano_compativel: str
    # Decimal, não float — dinheiro nunca deve usar float (arredondamento
    # binário gera erro de centavos, tipo 0.1 + 0.2 != 0.3). SQLAlchemy mapeia
    # isso pra NUMERIC(10,2) no Postgres (ver adapters/orm_models.py).
    preco: Decimal
    quantidade_estoque: int
    criado_em: datetime
    imagem_url: str | None = None
    # Limite mínimo antes de soar alerta de estoque baixo. Tem valor padrão
    # 0 (equivalente a "sem alerta configurado") pra não quebrar peças
    # criadas antes desse campo existir.
    quantidade_minima: int = 0
