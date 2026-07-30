import uuid

from adapters.orm_models import ClienteORM, MensagemORM
from tests.conftest import TestSessionLocal


async def _criar_cliente() -> str:
    cliente_id = uuid.uuid4()
    telefone = f"5599{uuid.uuid4().int % 100000000:08d}"
    async with TestSessionLocal() as session:
        session.add(ClienteORM(id=cliente_id, nome="Cliente teste", telefone=telefone))
        await session.commit()
    return str(cliente_id)


async def _classificar(client, texto: str) -> str:
    cliente_id = await _criar_cliente()
    resposta = await client.post(
        "/mensagens", json={"cliente_id": cliente_id, "texto": texto}
    )
    assert resposta.status_code == 201
    return resposta.json()["categoria"]


# Um caso pra cada uma das 7 categorias — o classificador de verdade (Groq)
# está trocado pelo FakeClassificador nesses testes (ver
# app.dependency_overrides em tests/conftest.py), então isso testa o
# roteamento (endpoint -> caso de uso -> persistência), não a qualidade da
# IA em si. Validar a IA de verdade é o papel de
# tests/test_groq_integracao_real.py.


async def test_classifica_consulta_peca(client):
    assert await _classificar(client, "Qual o preço da pastilha de freio?") == "consulta_peca"


async def test_classifica_duvida_geral(client):
    categoria = await _classificar(client, "Qual o horário de funcionamento de vocês?")
    assert categoria == "duvida_geral"


async def test_classifica_nao_identificado(client):
    assert await _classificar(client, "blablabla xyz 123") == "nao_identificado"


async def test_classifica_dano_estrutural(client):
    categoria = await _classificar(client, "Bati o carro, acho que ficou um dano estrutural")
    assert categoria == "dano_estrutural"


async def test_classifica_agendamento(client):
    categoria = await _classificar(client, "Quero agendar uma visita pra semana que vem")
    assert categoria == "agendamento"


async def test_classifica_status_protocolo(client):
    categoria = await _classificar(client, "Qual o status do meu protocolo #0123?")
    assert categoria == "status_protocolo"


async def test_classifica_reclamacao_sensivel(client):
    categoria = await _classificar(client, "Quero fazer uma reclamação sobre o atendimento")
    assert categoria == "reclamacao_sensivel"


async def test_mensagem_persistida_no_banco(client):
    cliente_id = await _criar_cliente()

    resposta = await client.post(
        "/mensagens",
        json={"cliente_id": cliente_id, "texto": "Vocês têm farol para Honda CG 160?"},
    )

    assert resposta.status_code == 201
    mensagem_id = resposta.json()["id"]

    async with TestSessionLocal() as session:
        orm = await session.get(MensagemORM, uuid.UUID(mensagem_id))

    assert orm is not None
    assert str(orm.cliente_id) == cliente_id
    assert orm.texto == "Vocês têm farol para Honda CG 160?"
    assert orm.categoria == "consulta_peca"
