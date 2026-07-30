from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from infrastructure.config import settings
from infrastructure.db import get_db
from infrastructure.ia import get_classificador
from main import app
from tests.fakes import FakeClassificador

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


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
