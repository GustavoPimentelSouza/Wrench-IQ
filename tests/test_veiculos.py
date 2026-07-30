import uuid

from adapters.orm_models import ClienteORM
from tests.conftest import TestSessionLocal


async def _obter_token_admin(client) -> str:
    resposta = await client.post(
        "/auth/login", json={"email": "admin@wrenchiq.com", "senha": "admin123"}
    )
    assert resposta.status_code == 200
    return resposta.json()["access_token"]


async def _criar_cliente() -> str:
    cliente_id = uuid.uuid4()
    telefone = f"5599{uuid.uuid4().int % 100000000:08d}"
    async with TestSessionLocal() as session:
        session.add(ClienteORM(id=cliente_id, nome="Cliente teste", telefone=telefone))
        await session.commit()
    return str(cliente_id)


async def test_ciclo_completo_crud_veiculo(client):
    token = await _obter_token_admin(client)
    headers = {"Authorization": f"Bearer {token}"}
    cliente_id = await _criar_cliente()

    payload = {
        "cliente_id": cliente_id,
        "marca": "Chevrolet",
        "modelo": "Onix",
        "ano": "2022",
        "placa": f"ABC{uuid.uuid4().int % 10000:04d}",
    }

    resposta_criacao = await client.post("/veiculos", json=payload, headers=headers)
    assert resposta_criacao.status_code == 201
    veiculo = resposta_criacao.json()
    veiculo_id = veiculo["id"]

    resposta_listagem = await client.get(f"/veiculos?cliente_id={cliente_id}")
    assert resposta_listagem.status_code == 200
    assert any(v["id"] == veiculo_id for v in resposta_listagem.json())

    resposta_busca = await client.get(f"/veiculos/{veiculo_id}")
    assert resposta_busca.status_code == 200
    assert resposta_busca.json()["modelo"] == "Onix"

    payload_atualizado = {**payload, "modelo": "Onix Plus"}
    del payload_atualizado["cliente_id"]
    resposta_atualizacao = await client.put(
        f"/veiculos/{veiculo_id}", json=payload_atualizado, headers=headers
    )
    assert resposta_atualizacao.status_code == 200
    assert resposta_atualizacao.json()["modelo"] == "Onix Plus"

    resposta_exclusao = await client.delete(f"/veiculos/{veiculo_id}", headers=headers)
    assert resposta_exclusao.status_code == 204

    resposta_busca_apos_exclusao = await client.get(f"/veiculos/{veiculo_id}")
    assert resposta_busca_apos_exclusao.status_code == 404


async def test_criar_veiculo_sem_token_retorna_401(client):
    resposta = await client.post(
        "/veiculos",
        json={
            "cliente_id": str(uuid.uuid4()),
            "marca": "Honda",
            "modelo": "CG 160",
            "ano": "2021",
            "placa": f"XYZ{uuid.uuid4().int % 10000:04d}",
        },
    )

    assert resposta.status_code == 401
