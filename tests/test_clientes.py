import uuid


async def _obter_token_admin(client) -> str:
    resposta = await client.post(
        "/auth/login", json={"email": "admin@wrenchiq.com", "senha": "admin123"}
    )
    assert resposta.status_code == 200
    return resposta.json()["access_token"]


async def test_ciclo_completo_crud_cliente(client):
    token = await _obter_token_admin(client)
    headers = {"Authorization": f"Bearer {token}"}
    telefone = f"5599{uuid.uuid4().int % 100000000:08d}"

    payload = {"nome": "Fulano da Silva", "telefone": telefone, "email": "fulano@teste.com"}

    resposta_criacao = await client.post("/clientes", json=payload, headers=headers)
    assert resposta_criacao.status_code == 201
    cliente_id = resposta_criacao.json()["id"]

    resposta_listagem = await client.get("/clientes")
    assert resposta_listagem.status_code == 200
    assert any(c["id"] == cliente_id for c in resposta_listagem.json())

    resposta_busca = await client.get(f"/clientes/{cliente_id}")
    assert resposta_busca.status_code == 200
    assert resposta_busca.json()["nome"] == "Fulano da Silva"

    payload_atualizado = {**payload, "nome": "Fulano da Silva Junior"}
    resposta_atualizacao = await client.put(
        f"/clientes/{cliente_id}", json=payload_atualizado, headers=headers
    )
    assert resposta_atualizacao.status_code == 200
    assert resposta_atualizacao.json()["nome"] == "Fulano da Silva Junior"

    resposta_exclusao = await client.delete(f"/clientes/{cliente_id}", headers=headers)
    assert resposta_exclusao.status_code == 204

    resposta_busca_apos_exclusao = await client.get(f"/clientes/{cliente_id}")
    assert resposta_busca_apos_exclusao.status_code == 404


async def test_criar_cliente_sem_token_retorna_401(client):
    resposta = await client.post(
        "/clientes", json={"nome": "Sem Token", "telefone": "5599999999999"}
    )

    assert resposta.status_code == 401


async def test_excluir_cliente_com_protocolo_retorna_409(client):
    token = await _obter_token_admin(client)
    headers = {"Authorization": f"Bearer {token}"}
    telefone = f"5599{uuid.uuid4().int % 100000000:08d}"

    resposta_cliente = await client.post(
        "/clientes",
        json={"nome": "Cliente com protocolo", "telefone": telefone},
        headers=headers,
    )
    assert resposta_cliente.status_code == 201
    cliente_id = resposta_cliente.json()["id"]

    resposta_protocolo = await client.post(
        "/protocolos",
        json={"cliente_id": cliente_id, "veiculo": "Onix 2022", "categoria": "farol"},
        headers=headers,
    )
    assert resposta_protocolo.status_code == 201

    resposta_exclusao = await client.delete(f"/clientes/{cliente_id}", headers=headers)
    assert resposta_exclusao.status_code == 409
