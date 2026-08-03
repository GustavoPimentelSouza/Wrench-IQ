import uuid

from adapters.orm_models import ClienteORM, UsuarioORM
from adapters.seguranca import criar_hash_senha
from domain.usuario import PapelUsuario
from tests.conftest import TestSessionLocal


async def _obter_token_admin(client) -> str:
    resposta = await client.post(
        "/auth/login", json={"email": "admin@wrenchiq.com", "senha": "admin123"}
    )
    assert resposta.status_code == 200
    return resposta.json()["access_token"]


async def _criar_cliente(nome: str) -> str:
    cliente_id = uuid.uuid4()
    telefone = f"5599{uuid.uuid4().int % 100000000:08d}"
    async with TestSessionLocal() as session:
        session.add(ClienteORM(id=cliente_id, nome=nome, telefone=telefone))
        await session.commit()
    return str(cliente_id)


async def _criar_usuario(papel: PapelUsuario) -> str:
    usuario_id = uuid.uuid4()
    async with TestSessionLocal() as session:
        session.add(
            UsuarioORM(
                id=usuario_id,
                nome="Usuário de teste",
                email=f"{uuid.uuid4()}@teste.com",
                senha_hash=criar_hash_senha("senha123"),
                papel=papel,
                ativo=True,
            )
        )
        await session.commit()
    return str(usuario_id)


async def test_ciclo_completo_protocolo_aprovar_e_concluir(client):
    token = await _obter_token_admin(client)
    headers = {"Authorization": f"Bearer {token}"}
    cliente_id = await _criar_cliente("Cliente do protocolo")

    payload = {"cliente_id": cliente_id, "veiculo": "Onix 2022", "categoria": "farol"}

    resposta_criacao = await client.post("/protocolos", json=payload, headers=headers)
    assert resposta_criacao.status_code == 201
    protocolo = resposta_criacao.json()
    protocolo_id = protocolo["id"]
    assert protocolo["numero"] > 0
    # Todo protocolo nasce aguardando aprovação, sem exceção — não dá pra
    # escolher outro status inicial via payload.
    assert protocolo["status"] == "aguardando_aprovacao"

    resposta_listagem = await client.get("/protocolos")
    assert resposta_listagem.status_code == 200
    assert any(p["id"] == protocolo_id for p in resposta_listagem.json())

    resposta_busca = await client.get(f"/protocolos/{protocolo_id}")
    assert resposta_busca.status_code == 200
    assert resposta_busca.json()["veiculo"] == "Onix 2022"

    # Sem valor_orcamento definido, aprovar deve recusar.
    resposta_aprovar_sem_orcamento = await client.post(
        f"/protocolos/{protocolo_id}/aprovar", headers=headers
    )
    assert resposta_aprovar_sem_orcamento.status_code == 409

    resposta_orcamento = await client.put(
        f"/protocolos/{protocolo_id}",
        json={"veiculo": "Onix 2022", "categoria": "farol", "valor_orcamento": "350.00"},
        headers=headers,
    )
    assert resposta_orcamento.status_code == 200

    resposta_aprovar = await client.post(
        f"/protocolos/{protocolo_id}/aprovar", headers=headers
    )
    assert resposta_aprovar.status_code == 200
    assert resposta_aprovar.json()["status"] == "em_execucao"

    resposta_concluir = await client.post(
        f"/protocolos/{protocolo_id}/concluir", headers=headers
    )
    assert resposta_concluir.status_code == 200
    assert resposta_concluir.json()["status"] == "pronto"


async def test_nao_deixa_concluir_sem_aprovar_antes(client):
    token = await _obter_token_admin(client)
    headers = {"Authorization": f"Bearer {token}"}
    cliente_id = await _criar_cliente("Cliente")

    resposta_criacao = await client.post(
        "/protocolos",
        json={"cliente_id": cliente_id, "veiculo": "Onix 2022", "categoria": "farol"},
        headers=headers,
    )
    protocolo_id = resposta_criacao.json()["id"]

    # Ainda está aguardando_aprovacao — pular direto pra concluir tem que
    # falhar, é exatamente a máquina de estados fazendo o trabalho dela.
    resposta_concluir = await client.post(
        f"/protocolos/{protocolo_id}/concluir", headers=headers
    )
    assert resposta_concluir.status_code == 409


async def test_cancelar_protocolo_preserva_registro(client):
    token = await _obter_token_admin(client)
    headers = {"Authorization": f"Bearer {token}"}
    cliente_id = await _criar_cliente("Cliente")

    resposta_criacao = await client.post(
        "/protocolos",
        json={"cliente_id": cliente_id, "veiculo": "HB20 2021", "categoria": "retirar"},
        headers=headers,
    )
    protocolo_id = resposta_criacao.json()["id"]

    resposta_cancelar = await client.post(
        f"/protocolos/{protocolo_id}/cancelar", headers=headers
    )
    assert resposta_cancelar.status_code == 200
    assert resposta_cancelar.json()["status"] == "cancelado"

    # Diferente do DELETE físico de antes: o registro continua existindo e
    # consultável — cancelado é um estado, não um sumiço.
    resposta_busca = await client.get(f"/protocolos/{protocolo_id}")
    assert resposta_busca.status_code == 200
    assert resposta_busca.json()["status"] == "cancelado"

    # Estado final — não dá pra sair de cancelado pra lugar nenhum.
    resposta_aprovar = await client.post(
        f"/protocolos/{protocolo_id}/aprovar", headers=headers
    )
    assert resposta_aprovar.status_code == 409


async def test_cancelar_protocolo_com_motivo(client):
    token = await _obter_token_admin(client)
    headers = {"Authorization": f"Bearer {token}"}
    cliente_id = await _criar_cliente("Cliente")

    resposta_criacao = await client.post(
        "/protocolos",
        json={"cliente_id": cliente_id, "veiculo": "HB20 2021", "categoria": "retirar"},
        headers=headers,
    )
    protocolo_id = resposta_criacao.json()["id"]

    resposta_cancelar = await client.post(
        f"/protocolos/{protocolo_id}/cancelar",
        json={"motivo": "cliente desistiu"},
        headers=headers,
    )
    assert resposta_cancelar.status_code == 200
    assert resposta_cancelar.json()["motivo_cancelamento"] == "cliente desistiu"


async def test_criar_protocolo_sem_token_retorna_401(client):
    resposta = await client.post(
        "/protocolos",
        json={
            "cliente_id": str(uuid.uuid4()),
            "veiculo": "HB20 2021",
            "categoria": "retirar",
        },
    )

    assert resposta.status_code == 401


async def test_listar_protocolos_filtra_por_cliente(client):
    token = await _obter_token_admin(client)
    headers = {"Authorization": f"Bearer {token}"}
    cliente_a = await _criar_cliente("Cliente A")
    cliente_b = await _criar_cliente("Cliente B")

    resposta_a = await client.post(
        "/protocolos",
        json={"cliente_id": cliente_a, "veiculo": "Onix 2022", "categoria": "farol"},
        headers=headers,
    )
    assert resposta_a.status_code == 201

    resposta_b = await client.post(
        "/protocolos",
        json={"cliente_id": cliente_b, "veiculo": "HB20 2021", "categoria": "retirar"},
        headers=headers,
    )
    assert resposta_b.status_code == 201

    resposta_filtrada = await client.get(f"/protocolos?cliente_id={cliente_a}")
    assert resposta_filtrada.status_code == 200
    protocolos = resposta_filtrada.json()
    assert len(protocolos) == 1
    assert protocolos[0]["cliente_id"] == cliente_a


async def test_criar_protocolo_com_mecanico_valido(client):
    token = await _obter_token_admin(client)
    headers = {"Authorization": f"Bearer {token}"}
    cliente_id = await _criar_cliente("Cliente")
    mecanico_id = await _criar_usuario(PapelUsuario.MECANICO)

    resposta = await client.post(
        "/protocolos",
        json={
            "cliente_id": cliente_id,
            "veiculo": "Onix 2022",
            "categoria": "farol",
            "mecanico_id": mecanico_id,
        },
        headers=headers,
    )

    assert resposta.status_code == 201
    assert resposta.json()["mecanico_id"] == mecanico_id


async def test_criar_protocolo_com_mecanico_de_papel_errado_falha(client):
    token = await _obter_token_admin(client)
    headers = {"Authorization": f"Bearer {token}"}
    cliente_id = await _criar_cliente("Cliente")
    atendente_id = await _criar_usuario(PapelUsuario.ATENDENTE)

    resposta = await client.post(
        "/protocolos",
        json={
            "cliente_id": cliente_id,
            "veiculo": "Onix 2022",
            "categoria": "farol",
            "mecanico_id": atendente_id,
        },
        headers=headers,
    )

    assert resposta.status_code == 400


async def test_criar_protocolo_com_mecanico_inexistente_falha(client):
    token = await _obter_token_admin(client)
    headers = {"Authorization": f"Bearer {token}"}
    cliente_id = await _criar_cliente("Cliente")

    resposta = await client.post(
        "/protocolos",
        json={
            "cliente_id": cliente_id,
            "veiculo": "Onix 2022",
            "categoria": "farol",
            "mecanico_id": str(uuid.uuid4()),
        },
        headers=headers,
    )

    assert resposta.status_code == 400
