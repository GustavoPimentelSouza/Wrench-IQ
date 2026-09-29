import uuid


async def _obter_token_admin(client) -> str:
    resposta = await client.post(
        "/auth/login", json={"email": "admin@wrenchiq.com", "senha": "admin123"}
    )
    assert resposta.status_code == 200
    return resposta.json()["access_token"]


async def _criar_conversa(client, headers) -> str:
    telefone = f"5599{uuid.uuid4().int % 100000000:08d}"
    resposta = await client.post(
        "/clientes", json={"nome": "Teste", "telefone": telefone}, headers=headers
    )
    assert resposta.status_code == 201
    return telefone


async def test_avaliar_e_reavaliar_mesma_conversa(client):
    headers = {"Authorization": f"Bearer {await _obter_token_admin(client)}"}
    telefone = await _criar_conversa(client, headers)

    primeira = await client.put(
        "/avaliacoes-teste",
        json={"telefone": telefone, "resultado": "alucinou", "comentario": "inventou preço"},
        headers=headers,
    )
    assert primeira.status_code == 200
    assert primeira.json()["resultado"] == "alucinou"

    # Mudou de ideia: mesma avaliação (mesmo id), resultado novo.
    segunda = await client.put(
        "/avaliacoes-teste",
        json={"telefone": telefone, "resultado": "correto", "comentario": "   "},
        headers=headers,
    )
    assert segunda.status_code == 200
    assert segunda.json()["id"] == primeira.json()["id"]
    assert segunda.json()["resultado"] == "correto"
    assert segunda.json()["comentario"] is None


async def test_avaliar_telefone_sem_conversa_retorna_404(client):
    headers = {"Authorization": f"Bearer {await _obter_token_admin(client)}"}
    resposta = await client.put(
        "/avaliacoes-teste",
        json={"telefone": "559900000000", "resultado": "correto"},
        headers=headers,
    )
    assert resposta.status_code == 404


async def test_avaliar_resultado_invalido_retorna_422(client):
    headers = {"Authorization": f"Bearer {await _obter_token_admin(client)}"}
    telefone = await _criar_conversa(client, headers)
    resposta = await client.put(
        "/avaliacoes-teste",
        json={"telefone": telefone, "resultado": "mais_ou_menos"},
        headers=headers,
    )
    assert resposta.status_code == 422


async def test_avaliar_sem_token_retorna_401(client):
    resposta = await client.put(
        "/avaliacoes-teste", json={"telefone": "559900000000", "resultado": "correto"}
    )
    assert resposta.status_code == 401


async def test_listar_conversas_e_mensagens_com_avaliacao(client):
    headers = {"Authorization": f"Bearer {await _obter_token_admin(client)}"}
    telefone = f"5599{uuid.uuid4().int % 100000000:08d}"
    await client.post("/webhook", json={"telefone": telefone, "mensagem": "oi"})
    await client.post("/webhook", json={"telefone": telefone, "mensagem": "de novo"})
    await client.put(
        "/avaliacoes-teste",
        json={"telefone": telefone, "resultado": "errou_fluxo"},
        headers=headers,
    )

    conversas = (await client.get("/avaliacoes-teste/conversas", headers=headers)).json()
    conversa = next(c for c in conversas if c["telefone"] == telefone)
    assert conversa["total_mensagens"] == 2
    assert conversa["resultado"] == "errou_fluxo"

    mensagens = await client.get(
        f"/avaliacoes-teste/conversas/{conversa['cliente_id']}/mensagens", headers=headers
    )
    assert [m["texto"] for m in mensagens.json()] == ["oi", "de novo"]


async def test_listar_conversas_ignora_telefone_fora_do_padrao_do_simulador(client):
    headers = {"Authorization": f"Bearer {await _obter_token_admin(client)}"}
    telefone_real = f"5511{uuid.uuid4().int % 1000000000:09d}"
    await client.post("/webhook", json={"telefone": telefone_real, "mensagem": "oi"})

    conversas = (await client.get("/avaliacoes-teste/conversas", headers=headers)).json()
    assert all(c["telefone"] != telefone_real for c in conversas)
