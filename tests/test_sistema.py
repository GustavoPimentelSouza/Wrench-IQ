from adapters.estado_ia import registrar_falha_classificacao, ultima_falha_classificacao


async def _obter_token_admin(client) -> str:
    resposta = await client.post(
        "/auth/login", json={"email": "admin@wrenchiq.com", "senha": "admin123"}
    )
    assert resposta.status_code == 200
    return resposta.json()["access_token"]


# Não testa o estado "sem falha ainda" isoladamente — é uma variável global
# em memória (ver adapters/estado_ia.py), então o valor inicial depende da
# ordem de execução dos testes no processo inteiro, não só deste arquivo.
async def test_status_ia_apos_falha_retorna_timestamp(client):
    token = await _obter_token_admin(client)
    registrar_falha_classificacao()

    resposta = await client.get(
        "/sistema/status-ia", headers={"Authorization": f"Bearer {token}"}
    )

    assert resposta.status_code == 200
    assert resposta.json()["falha_classificacao_em"] is not None
    assert ultima_falha_classificacao() is not None


async def test_status_ia_sem_token_retorna_401(client):
    resposta = await client.get("/sistema/status-ia")
    assert resposta.status_code == 401
