async def _obter_token_admin(client) -> str:
    resposta = await client.post(
        "/auth/login", json={"email": "admin@wrenchiq.com", "senha": "admin123"}
    )
    assert resposta.status_code == 200
    return resposta.json()["access_token"]


async def test_ciclo_completo_crud_peca(client):
    token = await _obter_token_admin(client)
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "nome": "Pastilha de freio",
        "marca_modelo_compativel": "Honda CG 160",
        "ano_compativel": "2020-2024",
        "preco": "89.90",
        "quantidade_estoque": 10,
    }

    resposta_criacao = await client.post("/pecas", json=payload, headers=headers)
    assert resposta_criacao.status_code == 201
    peca_id = resposta_criacao.json()["id"]

    resposta_listagem = await client.get("/pecas")
    assert resposta_listagem.status_code == 200
    assert any(p["id"] == peca_id for p in resposta_listagem.json())

    resposta_busca = await client.get(f"/pecas/{peca_id}")
    assert resposta_busca.status_code == 200
    assert resposta_busca.json()["nome"] == payload["nome"]

    payload_atualizado = {**payload, "quantidade_estoque": 5}
    resposta_atualizacao = await client.put(
        f"/pecas/{peca_id}", json=payload_atualizado, headers=headers
    )
    assert resposta_atualizacao.status_code == 200
    assert resposta_atualizacao.json()["quantidade_estoque"] == 5

    resposta_exclusao = await client.delete(f"/pecas/{peca_id}", headers=headers)
    assert resposta_exclusao.status_code == 204

    resposta_busca_apos_exclusao = await client.get(f"/pecas/{peca_id}")
    assert resposta_busca_apos_exclusao.status_code == 404


async def test_criar_peca_sem_token_retorna_401(client):
    resposta = await client.post(
        "/pecas",
        json={
            "nome": "Pastilha de freio",
            "marca_modelo_compativel": "Honda CG 160",
            "ano_compativel": "2020-2024",
            "preco": "89.90",
            "quantidade_estoque": 10,
        },
    )

    assert resposta.status_code == 401
