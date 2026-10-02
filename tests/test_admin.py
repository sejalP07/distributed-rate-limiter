import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.database import AsyncSessionLocal
from app.main import app
from app.models import Client


@pytest.fixture
def admin_client(monkeypatch):
    monkeypatch.setenv(
        "ADMIN_API_KEY",
        "test-admin-key",
    )

    with TestClient(app) as client:
        yield client


def test_create_client_requires_admin_key(
    monkeypatch,
):
    monkeypatch.setenv(
        "ADMIN_API_KEY",
        "test-admin-key",
    )

    with TestClient(app) as client:
        response = client.post(
            "/admin/clients",
            json={"name": "unauthorized-client"},
        )

    assert response.status_code == 401


def test_create_client_with_invalid_admin_key(
    monkeypatch,
):
    monkeypatch.setenv(
        "ADMIN_API_KEY",
        "test-admin-key",
    )

    with TestClient(app) as client:
        response = client.post(
            "/admin/clients",
            headers={
                "X-Admin-Key": "wrong-key",
            },
            json={"name": "invalid-admin-client"},
        )

    assert response.status_code == 403


@pytest.mark.anyio
async def test_create_client_success(
    admin_client,
):
    response = admin_client.post(
        "/admin/clients",
        headers={
            "X-Admin-Key": "test-admin-key",
        },
        json={
            "name": "step10-client",
        },
    )

    assert response.status_code == 201

    body = response.json()

    assert body["name"] == "step10-client"
    assert body["id"] > 0
    assert body["api_key"].startswith("rl_")

    api_key = body["api_key"]

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            Client.__table__.select().where(
                Client.name == "step10-client"
            )
        )

        row = result.first()

        assert row is not None

        stored_hash = row.api_key_hash

        assert stored_hash != api_key
        assert len(stored_hash) == 64

        await session.execute(
            delete(Client).where(
                Client.id == row.id
            )
        )

        await session.commit()