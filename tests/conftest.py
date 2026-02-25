from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.session import get_db
from app.main import app
from apps.accounts.models import User


@pytest.fixture(autouse=True)
def mock_redis(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_ping_redis() -> bool:
        return True

    monkeypatch.setattr("app.api.health.ping_redis", fake_ping_redis)


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    test_session_factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)

    async def override_get_db():
        async with test_session_factory() as session:
            yield session

    async def setup_db() -> None:
        async with test_engine.begin() as conn:
            await conn.run_sync(User.metadata.create_all, tables=[User.__table__])

    async def teardown_db() -> None:
        async with test_engine.begin() as conn:
            await conn.run_sync(User.metadata.drop_all, tables=[User.__table__])
        await test_engine.dispose()

    import asyncio

    asyncio.run(setup_db())
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    asyncio.run(teardown_db())
