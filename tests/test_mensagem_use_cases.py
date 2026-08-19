import uuid
from datetime import datetime, timedelta, timezone

from adapters.orm_models import ClienteORM
from adapters.sqlalchemy_mensagem_repository import SqlAlchemyMensagemRepository
from application.mensagem_use_cases import MensagemUseCases
from domain.mensagem import CategoriaMensagem, Mensagem
from tests.conftest import TestSessionLocal
from tests.fakes import FakeClassificador

# Testes de application/mensagem_use_cases.py — cobrem especificamente o
# limite de histórico mandado pro LLM (5 mensagens, janela de 3h), que não
# tinha teste próprio antes (só era exercitado indiretamente pelo default
# de listar_recentes()).


async def _criar_cliente() -> uuid.UUID:
    cliente_id = uuid.uuid4()
    telefone = f"5599{uuid.uuid4().int % 100000000:08d}"
    async with TestSessionLocal() as session:
        session.add(ClienteORM(id=cliente_id, nome="Cliente teste", telefone=telefone))
        await session.commit()
    return cliente_id


async def _inserir_mensagem(cliente_id: uuid.UUID, texto: str, criado_em: datetime) -> None:
    # Insere direto via repository (não via receber()), porque receber()
    # sempre carimba "agora" — pra testar a janela de 3h precisamos
    # controlar criado_em manualmente, simulando mensagem antiga.
    async with TestSessionLocal() as session:
        await SqlAlchemyMensagemRepository(session).criar(
            Mensagem(
                id=uuid.uuid4(),
                cliente_id=cliente_id,
                texto=texto,
                categoria=CategoriaMensagem.CONSULTA_PECA,
                criado_em=criado_em,
            )
        )


def _use_cases(session) -> MensagemUseCases:
    return MensagemUseCases(SqlAlchemyMensagemRepository(session), FakeClassificador())


async def test_listar_recentes_limita_a_5_mensagens():
    cliente_id = await _criar_cliente()
    agora = datetime.now(timezone.utc)
    for i in range(7):
        await _inserir_mensagem(cliente_id, f"mensagem {i}", agora - timedelta(minutes=7 - i))

    async with TestSessionLocal() as session:
        recentes = await _use_cases(session).listar_recentes(cliente_id)

    assert len(recentes) == 5
    # As 5 mais recentes, mais antiga primeiro (pra virar histórico).
    assert [m.texto for m in recentes] == ["mensagem 2", "mensagem 3", "mensagem 4", "mensagem 5", "mensagem 6"]


async def test_listar_recentes_ignora_mensagem_fora_da_janela_de_3h():
    cliente_id = await _criar_cliente()
    agora = datetime.now(timezone.utc)
    await _inserir_mensagem(cliente_id, "mensagem de ontem", agora - timedelta(hours=5))
    await _inserir_mensagem(cliente_id, "mensagem recente", agora - timedelta(minutes=10))

    async with TestSessionLocal() as session:
        recentes = await _use_cases(session).listar_recentes(cliente_id)

    textos = [m.texto for m in recentes]
    assert "mensagem recente" in textos
    assert "mensagem de ontem" not in textos
