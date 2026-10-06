from http.client import responses

from fastapi.testclient import TestClient

import app.rate_limit_middleware as rate_limit_module
from app.config import rate_limit_settings
from app.main import app
from app.redis_token_bucket import RateLimitDecision
import app.rate_limit_middleware as rate_limit_module

class FakeRateLimiter:
    def __init__(
        self,
        capacity: int | None = None,
    ):
        if capacity is None:
            capacity = int(
                rate_limit_settings.capacity
            )

        self.remaining = capacity

    async def try_consume(
        self,
        identifier: str,
    ) -> RateLimitDecision:
        if self.remaining > 0:
            self.remaining -= 1

            return RateLimitDecision(
                allowed=True,
                remaining_tokens=float(
                    self.remaining
                ),
                retry_after_seconds=0,
            )

        return RateLimitDecision(
            allowed=False,
            remaining_tokens=0,
            retry_after_seconds=1,
        )


class FakeRateLimiterManager:
    def __init__(self, fake_limiter):
        self.fake_limiter = fake_limiter

    def get_limiter(self, policy):
        return self.fake_limiter


def test_api_request_is_allowed(
    monkeypatch,
):
    fake_limiter = FakeRateLimiter()

    fake_manager = FakeRateLimiterManager(
        fake_limiter
    )

    monkeypatch.setattr(
        rate_limit_module,
        "rate_limiter_manager",
        fake_manager,
    )

    with TestClient(app) as client:
        response = client.get("/api/demo")

    assert response.status_code == 200

    assert (
        response.headers["X-RateLimit-Limit"]
        == str(
            int(
                rate_limit_settings.capacity
            )
        )
    )

    assert (
        response.headers["X-RateLimit-Remaining"]
        == "9"
    )


def test_api_request_is_rejected_after_limit(
    monkeypatch,
):
    fake_limiter = FakeRateLimiter()

    fake_manager = FakeRateLimiterManager(
        fake_limiter
    )

    monkeypatch.setattr(
        rate_limit_module,
        "rate_limiter_manager",
        fake_manager,
    )

    with TestClient(app) as client:
        responses = [
            client.get("/api/demo")
            for _ in range(11)
        ]

    assert [
        response.status_code
        for response in responses[:-1]
    ] == [200] * 10

    assert responses[-1].status_code == 429

    rejected = responses[-1]

    assert (
        rejected.json()["detail"]
        == "Rate limit exceeded"
    )

    assert (
        rejected.headers["X-RateLimit-Limit"]
        == str(
            int(
                rate_limit_settings.capacity
            )
        )
    )

    assert (
        rejected.headers["X-RateLimit-Remaining"]
        == "0"
    )

    assert (
        rejected.headers["Retry-After"]
        == "1"
    )


def test_health_endpoint_is_not_rate_limited(
    monkeypatch,
):
    fake_limiter = FakeRateLimiter()

    fake_manager = FakeRateLimiterManager(
        fake_limiter
    )

    monkeypatch.setattr(
        rate_limit_module,
        "rate_limiter_manager",
        fake_manager,
    )

    with TestClient(app) as client:
        responses = [
            client.get("/health")
            for _ in range(10)
        ]

    assert all(
        response.status_code == 200
        for response in responses
    )


def test_api_request_rejection_is_logged(
    monkeypatch,
):
    fake_limiter = FakeRateLimiter(
        capacity=1
    )

    fake_manager = FakeRateLimiterManager(
        fake_limiter
    )

    monkeypatch.setattr(
        rate_limit_module,
        "rate_limiter_manager",
        fake_manager,
    )

    logged = []

    def fake_log_rate_limit_rejection(
        **kwargs,
    ):
        logged.append(kwargs)

    monkeypatch.setattr(
        rate_limit_module,
        "log_rate_limit_rejection",
        fake_log_rate_limit_rejection,
    )

    with TestClient(app) as client:
        first = client.get("/api/demo")
        second = client.get("/api/demo")

    assert first.status_code == 200
    assert second.status_code == 429

    assert len(logged) == 1

    assert logged[0]["endpoint"] == "/api/demo"
    assert logged[0]["method"] == "GET"
    assert logged[0]["remaining"] == 0