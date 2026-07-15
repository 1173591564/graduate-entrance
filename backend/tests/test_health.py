from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from graduate_entrance.db.session import is_database_ready
from graduate_entrance.main import app


async def database_is_ready() -> bool:
    return True


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    app.dependency_overrides[is_database_ready] = database_is_ready
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ping(client: AsyncClient) -> None:
    response = await client.get("/api/ping")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "Graduate Entrance API",
        "environment": "local",
    }


@pytest.mark.asyncio
async def test_liveness(client: AsyncClient) -> None:
    response = await client.get("/api/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_readiness(client: AsyncClient) -> None:
    response = await client.get("/api/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
