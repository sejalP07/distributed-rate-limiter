from fastapi.testclient import TestClient
from starlette.responses import JSONResponse

import app.main as main_module
import app.rate_limit_middleware as rate_limit_module
from app.main import app
from app.redis_token_bucket import RateLimitDecision


class FakeRateLimiter:
    async def try_consume(
        self,
        identifier: str,
    ) -> RateLimitDecision:
        return RateLimitDecision(
            allowed=True,
            remaining_tokens=49,
            retry_after_seconds=0,
        )


class FakeRateLimiterManager:
    def __init__(self):
        self.limiter = FakeRateLimiter()

    def get_limiter(self, policy):
        return self.limiter


def test_gateway_forwards_request(
    monkeypatch,
):
    called = {}

    monkeypatch.setattr(
        rate_limit_module,
        "rate_limiter_manager",
        FakeRateLimiterManager(),
    )

    async def fake_proxy_request(
        request,
        path,
    ):
        called["path"] = path
        called["method"] = request.method

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
        response = client.get("/api/demo")

    assert response.status_code == 200

    assert response.json() == {
        "service": "backend",
        "path": "demo",
    }

    assert called["path"] == "demo"
    assert called["method"] == "GET"


def test_search_is_forwarded(
    monkeypatch,
):
    called = {}

    monkeypatch.setattr(
        rate_limit_module,
        "rate_limiter_manager",
        FakeRateLimiterManager(),
    )

    async def fake_proxy_request(
        request,
        path,
    ):
        called["path"] = path

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
            "/api/search"
        )

    assert response.status_code == 200

    assert response.json() == {
        "service": "backend",
        "path": "search",
    }

    assert called["path"] == "search"


def test_health_does_not_use_proxy(
    monkeypatch,
):
    called = False

    monkeypatch.setattr(
        rate_limit_module,
        "rate_limiter_manager",
        FakeRateLimiterManager(),
    )

    async def fake_proxy_request(
        request,
        path,
    ):
        nonlocal called
        called = True

        return JSONResponse(
            status_code=200,
            content={
                "unexpected": True,
            },
        )

    monkeypatch.setattr(
        main_module,
        "proxy_request",
        fake_proxy_request,
    )

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200

    assert response.json() == {
        "status": "healthy",
        "service": "gateway",
    }

    assert called is False