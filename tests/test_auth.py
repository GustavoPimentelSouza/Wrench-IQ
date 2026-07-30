import uuid

from adapters.orm_models import UsuarioORM
from adapters.seguranca import criar_hash_senha
from domain.usuario import PapelUsuario
from tests.conftest import TestSessionLocal


async def _criar_usuario(email: str, senha: str, papel: PapelUsuario) -> None:
    async with TestSessionLocal() as session:
        session.add(
            UsuarioORM(
                id=uuid.uuid4(),
                nome="Usuário de Teste",
                email=email,
                senha_hash=criar_hash_senha(senha),
                papel=papel,
                ativo=True,
            )
        )
        await session.commit()


_PAYLOAD_PECA = {
    "nome": "Peça de teste",
    "marca_modelo_compativel": "Honda CG 160",
    "ano_compativel": "2020-2024",
    "preco": "10.00",
    "quantidade_estoque": 1,
}


async def test_login_com_credenciais_corretas(client):
    email = f"login-ok-{uuid.uuid4()}@teste.com"
    await _criar_usuario(email, "senha-correta", PapelUsuario.ADMIN)

    resposta = await client.post(
        "/auth/login", json={"email": email, "senha": "senha-correta"}
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["token_type"] == "bearer"
    assert corpo["access_token"]


async def test_login_com_senha_errada_falha(client):
    email = f"login-errado-{uuid.uuid4()}@teste.com"
    await _criar_usuario(email, "senha-correta", PapelUsuario.ADMIN)

    resposta = await client.post(
        "/auth/login", json={"email": email, "senha": "senha-errada"}
    )

    assert resposta.status_code == 401


async def test_acesso_rota_protegida_sem_token(client):
    resposta = await client.post("/pecas", json=_PAYLOAD_PECA)

    assert resposta.status_code == 401


async def test_acesso_rota_protegida_com_token_valido(client):
    email = f"acesso-ok-{uuid.uuid4()}@teste.com"
    await _criar_usuario(email, "senha-correta", PapelUsuario.ATENDENTE)

    resposta_login = await client.post(
        "/auth/login", json={"email": email, "senha": "senha-correta"}
    )
    token = resposta_login.json()["access_token"]

    resposta = await client.post(
        "/pecas",
        json=_PAYLOAD_PECA,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resposta.status_code == 201


async def test_registrar_recusa_email_duplicado(client):
    email = f"duplicado-{uuid.uuid4()}@teste.com"
    await _criar_usuario(email, "senha-correta", PapelUsuario.ADMIN)

    resposta_login = await client.post(
        "/auth/login", json={"email": email, "senha": "senha-correta"}
    )
    token = resposta_login.json()["access_token"]

    resposta = await client.post(
        "/auth/registrar",
        json={
            "nome": "Outro Usuário",
            "email": email,
            "senha": "outra-senha",
            "papel": "atendente",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resposta.status_code == 409
