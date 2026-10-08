from urllib import response

from fastapi import Request
from starlette.responses import JSONResponse

from app.auth import authenticate_api_key
from app.database import AsyncSessionLocal
from app.identity import get_client_identity
from app.observability import log_rate_limit_rejection
from app.policies import RateLimitPolicy, get_policy
from app.redis import redis_client
from app.redis_token_bucket import RedisTokenBucket

from time import perf_counter

from app.metrics import (
    AUTH_FAILURES,
    DEPENDENCY_ERRORS,
    GATEWAY_REQUESTS,
    RATE_LIMIT_REJECTIONS,
    REQUEST_LATENCY,
)

class RateLimiterManager:
    """
    Creates and caches one RedisTokenBucket per policy.

    Each policy has its own configuration and Redis key prefix.
    """

    def __init__(self) -> None:
        self.redis = redis_client
        self._limiters: dict[str, RedisTokenBucket] = {}

    def get_limiter(
        self,
        policy: RateLimitPolicy,
    ) -> RedisTokenBucket:
        if policy.name not in self._limiters:
            self._limiters[policy.name] = RedisTokenBucket(
                self.redis,
                capacity=policy.capacity,
                refill_rate=policy.refill_rate,
                key_prefix=f"rate_limit:{policy.name}",
            )

        return self._limiters[policy.name]


rate_limiter_manager = RateLimiterManager()


async def rate_limit_middleware(
    request: Request,
    call_next,
):
    """
    Apply a rate-limit policy to /api/* requests.
    """

    # Health and internal endpoints are not rate limited.
    if not request.url.path.startswith("/api/"):
        return await call_next(request)
    start_time = perf_counter()
    def record_request(
        status_code: int,
    ) -> None:
        status_class = f"{status_code // 100}xx"

        GATEWAY_REQUESTS.labels(
            status_class=status_class,
        ).inc()

        REQUEST_LATENCY.observe(
            perf_counter() - start_time,
        )
    # Authenticate API-key clients before rate limiting.
    api_key = request.headers.get("X-API-Key")

    if api_key:
        try:
            async with AsyncSessionLocal() as session:
                client = await authenticate_api_key(
                    session,
                    api_key,
                )

        except Exception:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Authentication service unavailable",
                },
            )

        if client is None:
            AUTH_FAILURES.inc()

            record_request(401)

            return JSONResponse(
                status_code=401,
                content={
                    "detail": "Invalid or inactive API key",
                },
            )

        # Store only the safe database client ID.
        request.state.authenticated_client_id = client.id

    # Determine client identity.
    identity_type, identity_value = get_client_identity(request)

    # Select policy based on identity and endpoint.
    policy = get_policy(
        identity_type,
        request.url.path,
    )

    # Get the Redis-backed limiter for this policy.
    limiter = rate_limiter_manager.get_limiter(policy)

    # The identifier should NOT include the identity type again.
    # The policy name is already part of the Redis key prefix.
    identifier = identity_value

    try:
        decision = await limiter.try_consume(
            identifier
        )

    except Exception:
        DEPENDENCY_ERRORS.labels(
            dependency="postgres",
        ).inc()

        record_request(503)

        return JSONResponse(
            status_code=503,
            content={
                "detail": "Authentication service unavailable",
            },
        )

    remaining = max(
        0,
        int(decision.remaining_tokens),
    )

    # Headers returned for allowed requests.
    rate_limit_headers = {
        "X-RateLimit-Limit": str(
            int(policy.capacity)
        ),
        "X-RateLimit-Remaining": str(
            remaining
        ),
    }

    # Reject request when rate limit is exceeded.
    if not decision.allowed:
        RATE_LIMIT_REJECTIONS.labels(
            policy=policy.name,
        ).inc()

        record_request(429)
        log_rate_limit_rejection(
            identity_type=identity_type,
            identity=identifier,
            method=request.method,
            endpoint=request.url.path,
            policy_name=policy.name,
            limit=policy.capacity,
            remaining=decision.remaining_tokens,
            retry_after_seconds=decision.retry_after_seconds,
        )

        response = JSONResponse(
            status_code=429,
            content={
                "detail": "Rate limit exceeded",
                "retry_after_seconds": int(
                    max(
                        1,
                        decision.retry_after_seconds,
                    )
                ),
            },
        )

        response.headers["X-RateLimit-Limit"] = str(
            int(policy.capacity)
        )

        response.headers["X-RateLimit-Remaining"] = str(
            int(
                max(
                    0,
                    decision.remaining_tokens,
                )
            )
        )

        response.headers["Retry-After"] = str(
            int(
                max(
                    1,
                    decision.retry_after_seconds,
                )
            )
        )

        return response

    # Allowed request: forward to backend.
    response = await call_next(request)

    for key, value in rate_limit_headers.items():
        response.headers[key] = value

    record_request(response.status_code)

    return response
