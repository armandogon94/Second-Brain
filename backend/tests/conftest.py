import asyncio
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import JSON, Text, event, String
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import get_db
from app.main import app

# Register SQLite-compatible type compilers for PostgreSQL types
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.ext.compiler import compiles
from pgvector.sqlalchemy import Vector


@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


@compiles(TSVECTOR, "sqlite")
def compile_tsvector_sqlite(type_, compiler, **kw):
    return "TEXT"


@compiles(Vector, "sqlite")
def compile_vector_sqlite(type_, compiler, **kw):
    return "TEXT"


from app.models import Base

TEST_DATABASE_URL = "sqlite+aiosqlite://"  # In-memory


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client(db_session) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def mock_embed():
    """Mock the embedding service to avoid API calls in tests."""
    with (
        patch(
            "app.services.embedding_service.create_chunks_and_embeddings",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "app.api.notes.create_chunks_and_embeddings",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "app.api.bookmarks.create_chunks_and_embeddings",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "app.api.pdfs.create_chunks_and_embeddings",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        yield


@pytest.fixture
def mock_embed_single():
    """Mock single embedding."""
    fake_vector = [0.1] * 1536
    with patch(
        "app.services.embedding_service.embed_single",
        new_callable=AsyncMock,
        return_value=fake_vector,
    ) as mock:
        yield mock


@pytest.fixture
def mock_llm():
    """Mock the LLM service."""
    with patch(
        "app.services.llm_service.generate_answer",
        new_callable=AsyncMock,
        return_value={
            "answer": "Test answer from your notes.",
            "usage": {"input_tokens": 100, "output_tokens": 50, "model": "test"},
        },
    ) as mock:
        yield mock


@pytest.fixture
def mock_scrape():
    """Mock URL scraping (patched at the import location in the route module)."""
    mock_return = {
        "content": "This is the scraped article content about machine learning.",
        "title": "Test Article",
        "domain": "example.com",
    }
    with (
        patch(
            "app.api.bookmarks.scrape_url",
            new_callable=AsyncMock,
            return_value=mock_return,
        ) as mock,
        patch(
            "app.services.scraping_service.scrape_url",
            new_callable=AsyncMock,
            return_value=mock_return,
        ),
    ):
        yield mock
