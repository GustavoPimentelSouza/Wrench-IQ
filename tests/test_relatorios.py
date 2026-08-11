import uuid
from datetime import date, datetime, timezone

from adapters.orm_models import ClienteORM, UsuarioORM
from adapters.seguranca import criar_hash_senha
from adapters.sqlalchemy_protocolo_repository import SqlAlchemyProtocoloRepository
from adapters.sqlalchemy_reclassificacao_repository import SqlAlchemyReclassificacaoRepository
from adapters.sqlalchemy_usuario_repository import SqlAlchemyUsuarioRepository
from application.protocolo_use_cases import ProtocoloUseCases
from domain.especialidade import Especialidade
from domain.protocolo import Protocolo, StatusProtocolo
from domain.usuario import PapelUsuario
from tests.conftest import TestSessionLocal


async def _obter_token_admin(client) -> str:
    resposta = await client.post(
        "/auth/login", json={"email": "admin@wrenchiq.com", "senha": "admin123"}
    )
    assert resposta.status_code == 200
    return resposta.json()["access_token"]


async def _obter_token_atendente(client) -> str:
    email = f"{uuid.uuid4()}@teste.com"
    async with TestSessionLocal() as session:
        session.add(
            UsuarioORM(
                id=uuid.uuid4(),
                nome="Atendente",
                email=email,
                senha_hash=criar_hash_senha("senha123"),
                papel=PapelUsuario.ATENDENTE,
                ativo=True,
            )
        )
        await session.commit()
    resposta = await client.post("/auth/login", json={"email": email, "senha": "senha123"})
    assert resposta.status_code == 200
    return resposta.json()["access_token"]


async def _criar_protocolo_reclassificado(cliente_id: uuid.UUID) -> uuid.UUID:
    async with TestSessionLocal() as session:
        protocolo_use_cases = ProtocoloUseCases(
            SqlAlchemyProtocoloRepository(session),
            SqlAlchemyUsuarioRepository(session),
            SqlAlchemyReclassificacaoRepository(session),
        )
        protocolo = await protocolo_use_cases.criar(
            Protocolo(
                id=uuid.uuid4(),
                cliente_id=cliente_id,
                veiculo="Onix 2022",
                categoria="dano_estrutural",
                status=StatusProtocolo.AGUARDANDO_APROVACAO,
                criado_em=datetime.now(timezone.utc),
                especialidades=[Especialidade.FUNILARIA_PINTURA],
            )
        )
        await protocolo_use_cases.reclassificar_especialidade(
            protocolo.id, [Especialidade.ELETRICA]
        )
        return protocolo.id


async def test_taxa_reclassificacao_exige_admin(client):
    token = await _obter_token_atendente(client)
    headers = {"Authorization": f"Bearer {token}"}
    hoje = date.today().isoformat()

    resposta = await client.get(
        f"/relatorios/taxa-reclassificacao?inicio={hoje}&fim={hoje}", headers=headers
    )

    assert resposta.status_code == 403


async def test_taxa_reclassificacao_agrega_por_especialidade(client):
    cliente_id = uuid.uuid4()
    async with TestSessionLocal() as session:
        session.add(
            ClienteORM(
                id=cliente_id,
                nome="Cliente teste",
                telefone=f"5599{uuid.uuid4().int % 100000000:08d}",
            )
        )
        await session.commit()

    await _criar_protocolo_reclassificado(cliente_id)

    token = await _obter_token_admin(client)
    headers = {"Authorization": f"Bearer {token}"}
    hoje = date.today().isoformat()

    resposta = await client.get(
        f"/relatorios/taxa-reclassificacao?inicio={hoje}&fim={hoje}", headers=headers
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["total_reclassificados"] >= 1
    assert corpo["total_protocolos"] >= corpo["total_reclassificados"]
    assert any(
        item["especialidade"] == "eletrica" and item["total_reclassificacoes"] >= 1
        for item in corpo["por_especialidade"]
    )
