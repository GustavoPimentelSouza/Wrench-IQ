"""Popula o catálogo com peças fictícias pra ter mais variedade no
Simulador/testes manuais (mais cores, mais itens, todas com imagem).

NUNCA rodar contra produção — isso é dado de demonstração, não catálogo
real (nomes, preços e fotos são inventados). As imagens são placeholders
reais de https://placehold.co (resolvem de verdade, só não são fotos das
peças de verdade).

Passa pela API (não SQL direto) de propósito: criar_peca gera o embedding
da peça via EmbeddingService (ver SqlAlchemyPecaRepository) — inserir
direto no banco deixaria essas peças invisíveis pra busca semântica
(consultar_preco_peca).

Uso:
    python scripts/seed_pecas_teste.py
Variáveis de ambiente opcionais:
    API_BASE_URL (default http://localhost:8010)
    ADMIN_EMAIL, ADMIN_SENHA (default admin@wrenchiq.com / admin123)
"""
import os

import httpx

_API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8010")
_ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@wrenchiq.com")
_ADMIN_SENHA = os.getenv("ADMIN_SENHA", "admin123")


def _imagem(texto: str) -> str:
    # placehold.co gera uma imagem de verdade (cor de fundo + texto), só
    # pra ter uma URL que resolve — não é foto real da peça.
    return f"https://placehold.co/400x300?text={texto.replace(' ', '+')}"


# Cada cor é uma peça (linha) separada no catálogo — é assim que o projeto
# já modela variação de cor (ver domain/peca.py), não um campo de lista
# dentro de uma peça só.
_PECAS = [
    # Paralama Fan 160 — mais cores além da já usada nos testes.
    {"nome": "Paralama dianteiro", "marca_modelo_compativel": "Honda Fan 160", "ano_compativel": "2020-2024", "preco": "120.00", "quantidade_estoque": 8, "cor": "Preto"},
    {"nome": "Paralama dianteiro", "marca_modelo_compativel": "Honda Fan 160", "ano_compativel": "2020-2024", "preco": "125.00", "quantidade_estoque": 5, "cor": "Prata"},
    {"nome": "Paralama dianteiro", "marca_modelo_compativel": "Honda Fan 160", "ano_compativel": "2020-2024", "preco": "130.00", "quantidade_estoque": 3, "cor": "Vermelho"},
    {"nome": "Paralama dianteiro", "marca_modelo_compativel": "Honda Fan 160", "ano_compativel": "2020-2024", "preco": "135.00", "quantidade_estoque": 2, "cor": "Rosa"},
    # Retrovisor Fan 160 — usado no exemplo de acidente/venda avulsa.
    {"nome": "Retrovisor esquerdo", "marca_modelo_compativel": "Honda Fan 160", "ano_compativel": "2020-2024", "preco": "45.00", "quantidade_estoque": 10, "cor": "Preto"},
    {"nome": "Retrovisor direito", "marca_modelo_compativel": "Honda Fan 160", "ano_compativel": "2020-2024", "preco": "45.00", "quantidade_estoque": 10, "cor": "Preto"},
    {"nome": "Retrovisor esquerdo", "marca_modelo_compativel": "Honda Fan 160", "ano_compativel": "2020-2024", "preco": "52.00", "quantidade_estoque": 4, "cor": "Cromado"},
    # Farol CG 160.
    {"nome": "Farol dianteiro", "marca_modelo_compativel": "Honda CG 160", "ano_compativel": "2018-2023", "preco": "180.00", "quantidade_estoque": 6, "cor": None},
    # Pastilha de freio — sem variação de cor (peça funcional, não estética).
    {"nome": "Pastilha de freio", "marca_modelo_compativel": "Honda CG 160", "ano_compativel": "2020-2023", "preco": "45.00", "quantidade_estoque": 15, "cor": None},
    {"nome": "Pastilha de freio", "marca_modelo_compativel": "Honda Fan 160", "ano_compativel": "2020-2024", "preco": "42.00", "quantidade_estoque": 12, "cor": None},
    # Para-choque de carro — mais cores, pra testar fora do universo moto.
    {"nome": "Para-choque dianteiro", "marca_modelo_compativel": "Fiat Uno", "ano_compativel": "2015-2021", "preco": "310.00", "quantidade_estoque": 4, "cor": "Branco"},
    {"nome": "Para-choque dianteiro", "marca_modelo_compativel": "Fiat Uno", "ano_compativel": "2015-2021", "preco": "310.00", "quantidade_estoque": 2, "cor": "Prata"},
    # Capacete/itens de venda direta simples.
    {"nome": "Vela de ignição", "marca_modelo_compativel": "Honda CG 160", "ano_compativel": "2018-2023", "preco": "22.50", "quantidade_estoque": 30, "cor": None},
    {"nome": "Amortecedor traseiro", "marca_modelo_compativel": "Honda Fan 160", "ano_compativel": "2020-2024", "preco": "165.00", "quantidade_estoque": 5, "cor": "Preto"},
]


def main() -> None:
    with httpx.Client(base_url=_API_BASE_URL, timeout=20.0) as client:
        login = client.post("/auth/login", json={"email": _ADMIN_EMAIL, "senha": _ADMIN_SENHA})
        login.raise_for_status()
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        criadas, falhas = 0, 0
        for peca in _PECAS:
            payload = {**peca, "imagem_url": _imagem(f"{peca['nome']} {peca['cor'] or ''}".strip())}
            resposta = client.post("/pecas", json=payload, headers=headers)
            if resposta.status_code == 201:
                criadas += 1
                print(f"criada: {payload['nome']} ({payload['marca_modelo_compativel']}, cor={payload['cor']})")
            else:
                falhas += 1
                print(f"falhou: {payload['nome']} — {resposta.status_code} {resposta.text}")

        print(f"\n{criadas} peças criadas, {falhas} falharam.")


if __name__ == "__main__":
    main()
