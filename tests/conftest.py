from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from infrastructure.config import settings
from infrastructure.db import get_db
from infrastructure.ia import get_chat_service, get_classificador, get_embedding_service
from main import app
from tests.fakes import FakeChatService, FakeClassificador, FakeEmbeddingService

test_engine = create_async_engine(
    settings.database_url_test, echo=False, poolclass=NullPool
)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)


async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = _override_get_db
# Troca o classificador real (Groq) pelo FakeClassificador em TODOS os
# testes automatizados — sem isso, cada teste que passa por /mensagens ou
# /webhook faria uma chamada de API de verdade (custo, latência, e falharia
# sem GROQ_API_KEY configurada). Como get_classificador está definido uma
# única vez (infrastructure/ia.py) e usado por ambos os routers, essa linha
# cobre os dois de uma vez.
app.dependency_overrides[get_classificador] = lambda: FakeClassificador()
# Mesma ideia pro ChatService — sem isso, /webhook faria uma chamada de
# tool calling real (custo, latência, falha sem GROQ_API_KEY) em todo teste.
app.dependency_overrides[get_chat_service] = lambda: FakeChatService()
# Mesma ideia pro EmbeddingService — sem isso, qualquer criação/edição de
# peça (via /pecas, /pedidos, /webhook) chamaria a API real do Gemini.
app.dependency_overrides[get_embedding_service] = lambda: FakeEmbeddingService()


# Tabelas criadas por teste — não inclui "usuarios" aqui porque o admin
# semeado pela migração 0004 precisa sobreviver (é usado pelo login em
# quase todo teste). TRUNCATE ... CASCADE cobre FK entre elas sem precisar
# adivinhar a ordem certa de exclusão.
_TABELAS_DE_TESTE = (
    "movimentacoes_estoque", "pedidos", "mensagens",
    "reclassificacoes_especialidade",
    "notificacoes", "lista_espera_agendamento",
    "protocolos", "veiculos", "agendamentos", "clientes", "pecas",
)


async def _limpar_banco_de_teste() -> None:
    async with TestSessionLocal() as session:
        for tabela in _TABELAS_DE_TESTE:
            await session.execute(text(f"TRUNCATE TABLE {tabela} CASCADE"))
        await session.execute(text("DELETE FROM usuarios WHERE email != 'admin@wrenchiq.com'"))
        await session.commit()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _banco_de_teste_limpo() -> AsyncGenerator[None, None]:
    # Limpa antes (sobra de uma rodada anterior interrompida) e depois
    # (pra não deixar lixo acumulando) — o banco de teste começa e termina
    # vazio a cada `pytest`, nunca cresce indefinidamente.
    await _limpar_banco_de_teste()
    yield
    await _limpar_banco_de_teste()


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
