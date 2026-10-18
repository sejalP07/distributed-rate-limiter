import app.main as main_module
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "gateway",
    }


def test_redis_health_healthy(monkeypatch):
    async def fake_ping():
        return True

    monkeypatch.setattr(
        main_module.redis_client,
        "ping",
        fake_ping,
    )

    response = client.get("/health/redis")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "redis": True,
    }


def test_redis_health_false_returns_503(monkeypatch):
    async def fake_ping():
        return False

    monkeypatch.setattr(
        main_module.redis_client,
        "ping",
        fake_ping,
    )

    response = client.get("/health/redis")

    assert response.status_code == 503
    assert response.json() == {
        "status": "unhealthy",
        "redis": "unavailable",
    }


def test_redis_health_exception_returns_503(monkeypatch):
    async def fake_ping():
        raise RuntimeError("internal connection details")

    monkeypatch.setattr(
        main_module.redis_client,
        "ping",
        fake_ping,
    )

    response = client.get("/health/redis")

    assert response.status_code == 503
    assert response.json()["status"] == "unhealthy"
    assert "internal connection details" not in response.text


def test_database_health_healthy(monkeypatch):
    async def fake_check_database_connection():
        return True

    monkeypatch.setattr(
        main_module,
        "check_database_connection",
        fake_check_database_connection,
    )

    response = client.get("/health/db")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "database": "postgresql",
        "connected": True,
    }


def test_database_health_false_returns_503(monkeypatch):
    async def fake_check_database_connection():
        return False

    monkeypatch.setattr(
        main_module,
        "check_database_connection",
        fake_check_database_connection,
    )

    response = client.get("/health/db")

    assert response.status_code == 503
    assert response.json() == {
        "status": "unhealthy",
        "database": "postgresql",
        "connected": False,
    }


def test_database_health_exception_returns_503(monkeypatch):
    async def fake_check_database_connection():
        raise RuntimeError("internal database connection details")

    monkeypatch.setattr(
        main_module,
        "check_database_connection",
        fake_check_database_connection,
    )

    response = client.get("/health/db")

    assert response.status_code == 503
    assert response.json() == {
        "status": "unhealthy",
        "database": "postgresql",
        "connected": False,
    }
    assert "internal database connection details" not in response.text