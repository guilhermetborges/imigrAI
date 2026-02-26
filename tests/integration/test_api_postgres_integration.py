from __future__ import annotations

import asyncio
import os
from collections.abc import Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.session import get_db
from app.main import app
from apps.accounts.models import User

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")


pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="TEST_DATABASE_URL is required for postgres integration tests",
)


@pytest.fixture
def postgres_client() -> Generator[TestClient, None, None]:
    assert TEST_DATABASE_URL
    test_engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
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

    asyncio.run(setup_db())
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    asyncio.run(teardown_db())


def test_auth_flow_with_postgres(postgres_client: TestClient) -> None:
    email = f"postgres-int-{uuid4()}@example.com"
    password = "supersecret123"

    register_response = postgres_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert register_response.status_code == 200
    tokens = register_response.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens

    login_response = postgres_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200
    login_tokens = login_response.json()
    assert login_tokens["access_token"]
    assert login_tokens["refresh_token"]

    me_response = postgres_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {login_tokens['access_token']}"},
    )
    assert me_response.status_code == 200
    me_payload = me_response.json()
    assert me_payload["email"] == email
