from types import SimpleNamespace

from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse

import app.main as main_module
import app.rate_limit_middleware as rate_limit_module
from app.main import app


class FakeLimiter:
    def __init__(self, calls):
        self.calls = calls

    async def try_consume(
        self,
        identifier,
        tokens=1,
    ):
        self.calls.append(identifier)

        return SimpleNamespace(
            allowed=True,
            remaining_tokens=9,
            retry_after_seconds=0,
        )


class FakeRateLimiterManager:
    def __init__(self, calls):
        self.calls = calls

    def get_limiter(self, policy):
        return FakeLimiter(self.calls)


def test_invalid_api_key_is_rejected(monkeypatch):
    async def fake_authenticate(
        session,
        api_key,
    ):
        return None

    limiter_calls = []

    monkeypatch.setattr(
        rate_limit_module,
        "authenticate_api_key",
        fake_authenticate,
    )

    monkeypatch.setattr(
        rate_limit_module,
        "rate_limiter_manager",
        FakeRateLimiterManager(limiter_calls),
    )

    with TestClient(app) as client:
        response = client.get(
            "/api/demo",
            headers={
                "X-API-Key": "rl_invalid",
            },
        )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid or inactive API key"
    }

    assert limiter_calls == []


def test_valid_api_key_reaches_rate_limiter_and_backend(
    monkeypatch,
):
    async def fake_authenticate(
        session,
        api_key,
    ):
        return SimpleNamespace(
            id=29,
            is_active=True,
        )

    limiter_calls = []

    monkeypatch.setattr(
        rate_limit_module,
        "authenticate_api_key",
        fake_authenticate,
    )

    monkeypatch.setattr(
        rate_limit_module,
        "rate_limiter_manager",
        FakeRateLimiterManager(limiter_calls),
    )

    async def fake_proxy_request(
        request,
        path,
    ):
        return JSONResponse(
            status_code=200,
            content={
                "service": "backend",
                "path": path,
            },
        )

    monkeypatch.setattr(
        main_module,
        "proxy_request",
        fake_proxy_request,
    )

    with TestClient(app) as client:
        response = client.get(
            "/api/demo",
            headers={
                "X-API-Key": "rl_valid",
            },
        )

    assert response.status_code == 200

    assert response.json() == {
        "service": "backend",
        "path": "demo",
    }

    assert limiter_calls == [
        "29",
    ]


def test_authentication_failure_returns_503(
    monkeypatch,
):
    async def fake_authenticate(
        session,
        api_key,
    ):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(
        rate_limit_module,
        "authenticate_api_key",
        fake_authenticate,
    )

    with TestClient(app) as client:
        response = client.get(
            "/api/demo",
            headers={
                "X-API-Key": "rl_valid",
            },
        )

    assert response.status_code == 503

    assert response.json() == {
        "detail": "Authentication service unavailable"
    }