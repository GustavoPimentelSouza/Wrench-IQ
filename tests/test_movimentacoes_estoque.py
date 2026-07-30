import uuid

from adapters.orm_models import PecaORM
from tests.conftest import TestSessionLocal


async def _obter_token_admin(client) -> str:
    resposta = await client.post(
        "/auth/login", json={"email": "admin@wrenchiq.com", "senha": "admin123"}
    )
    assert resposta.status_code == 200
    return resposta.json()["access_token"]


async def _criar_peca(quantidade_estoque: int) -> str:
    peca_id = uuid.uuid4()
    async with TestSessionLocal() as session:
        session.add(
            PecaORM(
                id=peca_id,
                nome="Peça teste",
                marca_modelo_compativel="Honda CG 160",
                ano_compativel="2020-2024",
                preco="50.00",
                quantidade_estoque=quantidade_estoque,
            )
        )
        await session.commit()
    return str(peca_id)


async def test_registrar_entrada_aumenta_estoque(client):
    token = await _obter_token_admin(client)
    headers = {"Authorization": f"Bearer {token}"}
    peca_id = await _criar_peca(quantidade_estoque=5)

    resposta = await client.post(
        "/movimentacoes-estoque",
        json={"peca_id": peca_id, "tipo": "entrada", "quantidade": 10},
        headers=headers,
    )
    assert resposta.status_code == 201
    assert resposta.json()["tipo"] == "entrada"

    resposta_peca = await client.get(f"/pecas/{peca_id}")
    assert resposta_peca.json()["quantidade_estoque"] == 15


async def test_registrar_saida_maior_que_estoque_falha(client):
    token = await _obter_token_admin(client)
    headers = {"Authorization": f"Bearer {token}"}
    peca_id = await _criar_peca(quantidade_estoque=2)

    resposta = await client.post(
        "/movimentacoes-estoque",
        json={"peca_id": peca_id, "tipo": "saida", "quantidade": 5},
        headers=headers,
    )
    assert resposta.status_code == 400


async def test_listar_movimentacoes_por_peca(client):
    token = await _obter_token_admin(client)
    headers = {"Authorization": f"Bearer {token}"}
    peca_id = await _criar_peca(quantidade_estoque=20)

    await client.post(
        "/movimentacoes-estoque",
        json={"peca_id": peca_id, "tipo": "saida", "quantidade": 3},
        headers=headers,
    )
    await client.post(
        "/movimentacoes-estoque",
        json={"peca_id": peca_id, "tipo": "entrada", "quantidade": 8},
        headers=headers,
    )

    resposta = await client.get(
        f"/movimentacoes-estoque?peca_id={peca_id}", headers=headers
    )
    assert resposta.status_code == 200
    tipos = {m["tipo"] for m in resposta.json()}
    assert tipos == {"saida", "entrada"}
