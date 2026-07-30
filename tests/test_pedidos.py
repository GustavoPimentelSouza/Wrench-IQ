import uuid

from adapters.orm_models import ClienteORM, PecaORM
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


async def _criar_peca(quantidade_estoque: int, preco: str = "50.00") -> str:
    peca_id = uuid.uuid4()
    async with TestSessionLocal() as session:
        session.add(
            PecaORM(
                id=peca_id,
                nome="Peça teste",
                marca_modelo_compativel="Honda CG 160",
                ano_compativel="2020-2024",
                preco=preco,
                quantidade_estoque=quantidade_estoque,
            )
        )
        await session.commit()
    return str(peca_id)


async def test_criar_pedido_retirada_local_nao_gera_link(client):
    token = await _obter_token_admin(client)
    headers = {"Authorization": f"Bearer {token}"}
    cliente_id = await _criar_cliente()
    peca_id = await _criar_peca(quantidade_estoque=10)

    resposta = await client.post(
        "/pedidos",
        json={
            "cliente_id": cliente_id,
            "peca_id": peca_id,
            "quantidade": 2,
            "tipo_entrega": "retirada_local",
        },
        headers=headers,
    )

    assert resposta.status_code == 201
    pedido = resposta.json()
    assert pedido["status"] == "aguardando_retirada"
    assert pedido["link_pagamento"] is None
    assert pedido["valor_total"] == "100.00"


async def test_criar_pedido_envio_remoto_gera_link_e_exige_endereco(client):
    token = await _obter_token_admin(client)
    headers = {"Authorization": f"Bearer {token}"}
    cliente_id = await _criar_cliente()
    peca_id = await _criar_peca(quantidade_estoque=10)

    resposta_sem_endereco = await client.post(
        "/pedidos",
        json={
            "cliente_id": cliente_id,
            "peca_id": peca_id,
            "quantidade": 1,
            "tipo_entrega": "envio_remoto",
        },
        headers=headers,
    )
    assert resposta_sem_endereco.status_code == 400

    resposta = await client.post(
        "/pedidos",
        json={
            "cliente_id": cliente_id,
            "peca_id": peca_id,
            "quantidade": 1,
            "tipo_entrega": "envio_remoto",
            "endereco_entrega": "Rua Exemplo, 123",
        },
        headers=headers,
    )
    assert resposta.status_code == 201
    pedido = resposta.json()
    assert pedido["status"] == "aguardando_pagamento"
    assert pedido["link_pagamento"] is not None


async def test_criar_pedido_sem_estoque_falha(client):
    token = await _obter_token_admin(client)
    headers = {"Authorization": f"Bearer {token}"}
    cliente_id = await _criar_cliente()
    peca_id = await _criar_peca(quantidade_estoque=1)

    resposta = await client.post(
        "/pedidos",
        json={
            "cliente_id": cliente_id,
            "peca_id": peca_id,
            "quantidade": 5,
            "tipo_entrega": "retirada_local",
        },
        headers=headers,
    )

    assert resposta.status_code == 400


async def test_fluxo_completo_envio_remoto_ate_arrependimento(client):
    token = await _obter_token_admin(client)
    headers = {"Authorization": f"Bearer {token}"}
    cliente_id = await _criar_cliente()
    peca_id = await _criar_peca(quantidade_estoque=5)

    resposta_criacao = await client.post(
        "/pedidos",
        json={
            "cliente_id": cliente_id,
            "peca_id": peca_id,
            "quantidade": 2,
            "tipo_entrega": "envio_remoto",
            "endereco_entrega": "Rua Exemplo, 123",
        },
        headers=headers,
    )
    pedido_id = resposta_criacao.json()["id"]

    resposta_pagamento = await client.post(
        f"/pedidos/{pedido_id}/confirmar-pagamento", headers=headers
    )
    assert resposta_pagamento.status_code == 200
    assert resposta_pagamento.json()["status"] == "aguardando_conferencia"

    resposta_conferencia = await client.post(
        f"/pedidos/{pedido_id}/confirmar-conferencia", headers=headers
    )
    assert resposta_conferencia.status_code == 200
    assert resposta_conferencia.json()["status"] == "despachado"

    resposta_entrega = await client.post(
        f"/pedidos/{pedido_id}/marcar-entregue", headers=headers
    )
    assert resposta_entrega.status_code == 200
    corpo_entrega = resposta_entrega.json()
    assert corpo_entrega["status"] == "entregue"
    assert corpo_entrega["dentro_do_prazo_arrependimento"] is True


async def test_cancelar_pedido_restaura_estoque(client):
    token = await _obter_token_admin(client)
    headers = {"Authorization": f"Bearer {token}"}
    cliente_id = await _criar_cliente()
    peca_id = await _criar_peca(quantidade_estoque=5)

    resposta_criacao = await client.post(
        "/pedidos",
        json={
            "cliente_id": cliente_id,
            "peca_id": peca_id,
            "quantidade": 3,
            "tipo_entrega": "retirada_local",
        },
        headers=headers,
    )
    pedido_id = resposta_criacao.json()["id"]

    resposta_peca_apos_pedido = await client.get(f"/pecas/{peca_id}")
    assert resposta_peca_apos_pedido.json()["quantidade_estoque"] == 2

    resposta_cancelamento = await client.post(
        f"/pedidos/{pedido_id}/cancelar", headers=headers
    )
    assert resposta_cancelamento.status_code == 200
    assert resposta_cancelamento.json()["status"] == "cancelado"

    resposta_peca_apos_cancelamento = await client.get(f"/pecas/{peca_id}")
    assert resposta_peca_apos_cancelamento.json()["quantidade_estoque"] == 5


async def test_criar_e_cancelar_pedido_registra_movimentacao_estoque(client):
    token = await _obter_token_admin(client)
    headers = {"Authorization": f"Bearer {token}"}
    cliente_id = await _criar_cliente()
    peca_id = await _criar_peca(quantidade_estoque=5)

    resposta_criacao = await client.post(
        "/pedidos",
        json={
            "cliente_id": cliente_id,
            "peca_id": peca_id,
            "quantidade": 3,
            "tipo_entrega": "retirada_local",
        },
        headers=headers,
    )
    pedido_id = resposta_criacao.json()["id"]

    resposta_movimentacoes = await client.get(
        f"/movimentacoes-estoque?peca_id={peca_id}", headers=headers
    )
    movimentacoes = resposta_movimentacoes.json()
    assert len(movimentacoes) == 1
    assert movimentacoes[0]["tipo"] == "saida"
    assert movimentacoes[0]["quantidade"] == 3

    await client.post(f"/pedidos/{pedido_id}/cancelar", headers=headers)

    resposta_movimentacoes_apos_cancelamento = await client.get(
        f"/movimentacoes-estoque?peca_id={peca_id}", headers=headers
    )
    movimentacoes_apos_cancelamento = resposta_movimentacoes_apos_cancelamento.json()
    tipos = [m["tipo"] for m in movimentacoes_apos_cancelamento]
    assert sorted(tipos) == ["entrada", "saida"]


async def test_listar_pedidos_filtra_por_status(client):
    token = await _obter_token_admin(client)
    headers = {"Authorization": f"Bearer {token}"}
    cliente_id = await _criar_cliente()
    peca_id = await _criar_peca(quantidade_estoque=10)

    resposta_retirada = await client.post(
        "/pedidos",
        json={
            "cliente_id": cliente_id,
            "peca_id": peca_id,
            "quantidade": 1,
            "tipo_entrega": "retirada_local",
        },
        headers=headers,
    )
    pedido_retirada_id = resposta_retirada.json()["id"]

    await client.post(
        "/pedidos",
        json={
            "cliente_id": cliente_id,
            "peca_id": peca_id,
            "quantidade": 1,
            "tipo_entrega": "envio_remoto",
            "endereco_entrega": "Rua Exemplo, 123",
        },
        headers=headers,
    )

    resposta_filtrada = await client.get(
        "/pedidos?status=aguardando_retirada", headers=headers
    )
    assert resposta_filtrada.status_code == 200
    pedidos = resposta_filtrada.json()
    assert all(p["status"] == "aguardando_retirada" for p in pedidos)
    assert any(p["id"] == pedido_retirada_id for p in pedidos)
    assert not any(p["status"] == "aguardando_pagamento" for p in pedidos)


async def test_listar_pedidos_retorna_total_no_header_e_respeita_limit(client):
    token = await _obter_token_admin(client)
    headers = {"Authorization": f"Bearer {token}"}
    cliente_id = await _criar_cliente()
    peca_id = await _criar_peca(quantidade_estoque=10)

    for _ in range(3):
        await client.post(
            "/pedidos",
            json={
                "cliente_id": cliente_id,
                "peca_id": peca_id,
                "quantidade": 1,
                "tipo_entrega": "retirada_local",
            },
            headers=headers,
        )

    resposta = await client.get(
        f"/pedidos?cliente_id={cliente_id}&limit=2", headers=headers
    )
    assert resposta.status_code == 200
    assert len(resposta.json()) == 2
    assert int(resposta.headers["X-Total-Count"]) == 3
