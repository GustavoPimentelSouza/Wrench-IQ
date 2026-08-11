import uuid
from datetime import datetime, timedelta, timezone

from adapters.orm_models import ClienteORM
from adapters.seguranca import criar_hash_senha
from adapters.sqlalchemy_agendamento_repository import SqlAlchemyAgendamentoRepository
from adapters.sqlalchemy_usuario_repository import SqlAlchemyUsuarioRepository
from application.agendamento_use_cases import AgendamentoUseCases
from domain.especialidade import Especialidade
from domain.usuario import PapelUsuario, Usuario
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


async def test_ciclo_completo_crud_agendamento(client):
    token = await _obter_token_admin(client)
    headers = {"Authorization": f"Bearer {token}"}
    cliente_id = await _criar_cliente()
    data_hora = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()

    payload = {"cliente_id": cliente_id, "data_hora": data_hora}

    resposta_criacao = await client.post("/agendamentos", json=payload, headers=headers)
    assert resposta_criacao.status_code == 201
    agendamento = resposta_criacao.json()
    agendamento_id = agendamento["id"]
    assert agendamento["status"] == "agendado"

    resposta_listagem = await client.get(f"/agendamentos?cliente_id={cliente_id}")
    assert resposta_listagem.status_code == 200
    assert any(a["id"] == agendamento_id for a in resposta_listagem.json())

    resposta_busca = await client.get(f"/agendamentos/{agendamento_id}")
    assert resposta_busca.status_code == 200

    payload_confirmado = {"data_hora": data_hora, "status": "confirmado"}
    resposta_atualizacao = await client.put(
        f"/agendamentos/{agendamento_id}", json=payload_confirmado, headers=headers
    )
    assert resposta_atualizacao.status_code == 200
    assert resposta_atualizacao.json()["status"] == "confirmado"

    resposta_exclusao = await client.delete(
        f"/agendamentos/{agendamento_id}", headers=headers
    )
    assert resposta_exclusao.status_code == 204

    resposta_busca_apos_exclusao = await client.get(f"/agendamentos/{agendamento_id}")
    assert resposta_busca_apos_exclusao.status_code == 404


async def test_criar_agendamento_sem_token_retorna_401(client):
    resposta = await client.post(
        "/agendamentos",
        json={
            "cliente_id": str(uuid.uuid4()),
            "data_hora": datetime.now(timezone.utc).isoformat(),
        },
    )

    assert resposta.status_code == 401


async def test_criar_agendamento_com_multiplas_especialidades_persiste_lista(client):
    token = await _obter_token_admin(client)
    headers = {"Authorization": f"Bearer {token}"}
    cliente_id = await _criar_cliente()
    data_hora = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()

    resposta = await client.post(
        "/agendamentos",
        json={
            "cliente_id": cliente_id,
            "data_hora": data_hora,
            "especialidades": ["funilaria_pintura", "eletrica"],
        },
        headers=headers,
    )

    assert resposta.status_code == 201
    especialidades = set(resposta.json()["especialidades"])
    assert especialidades == {"funilaria_pintura", "eletrica"}

    resposta_busca = await client.get(f"/agendamentos/{resposta.json()['id']}")
    assert set(resposta_busca.json()["especialidades"]) == {"funilaria_pintura", "eletrica"}


async def _criar_mecanico(especialidades: list[Especialidade]) -> str:
    usuario = Usuario(
        id=uuid.uuid4(),
        nome="Mecânico teste",
        email=f"{uuid.uuid4()}@teste.com",
        senha_hash=criar_hash_senha("senha123"),
        papel=PapelUsuario.MECANICO,
        ativo=True,
        criado_em=datetime.now(timezone.utc),
        especialidades=especialidades,
    )
    async with TestSessionLocal() as session:
        criado = await SqlAlchemyUsuarioRepository(session).criar(usuario)
    return str(criado.id)


async def test_listar_mecanicos_qualificados_filtra_por_especialidade(client):
    mecanico_eletrica = await _criar_mecanico([Especialidade.ELETRICA])
    mecanico_funilaria = await _criar_mecanico([Especialidade.FUNILARIA_PINTURA])
    mecanico_ambos = await _criar_mecanico(
        [Especialidade.ELETRICA, Especialidade.MECANICA_GERAL]
    )

    async with TestSessionLocal() as session:
        use_cases = AgendamentoUseCases(
            SqlAlchemyAgendamentoRepository(session), SqlAlchemyUsuarioRepository(session)
        )
        qualificados = await use_cases.listar_mecanicos_qualificados([Especialidade.ELETRICA])

    # >= (não ==): o banco de teste é compartilhado por todos os testes da
    # sessão (sem truncar "usuarios" entre um teste e outro — ver
    # tests/conftest.py), então outro teste pode ter criado mais mecânicos
    # de elétrica antes deste rodar. O que importa é que ESSES dois
    # apareçam e o de funilaria não.
    ids_qualificados = {str(m.id) for m in qualificados}
    assert {mecanico_eletrica, mecanico_ambos} <= ids_qualificados
    assert mecanico_funilaria not in ids_qualificados
