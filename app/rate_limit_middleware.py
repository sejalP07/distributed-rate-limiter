from math import ceil

from fastapi import Request
from starlette.responses import JSONResponse

from app.config import rate_limit_settings
from app.identity import get_client_identity
from app.policies import RateLimitPolicy, get_policy
from app.redis import redis_client
from app.redis_token_bucket import RedisTokenBucket


class RateLimiterManager:
    """
    Creates and caches one RedisTokenBucket per policy.

    Each policy has its own configuration and Redis key prefix.
    """

    def __init__(self):
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

    # Health/internal endpoints are not rate limited.
    if not request.url.path.startswith("/api/"):
        return await call_next(request)

    # Determine client identity.
    identity_type, identity_value = get_client_identity(
        request
    )

    # Select policy for this identity type.
    policy = get_policy(
        identity_type,
        request.url.path,
    )

    # Get the Redis-backed limiter for that policy.
    limiter = rate_limiter_manager.get_limiter(policy)

    # Identifier uniquely identifies this client.
    identifier = (
        f"{identity_type}:{identity_value}"
    )

    try:
        decision = await limiter.try_consume(
            identifier
        )

    except Exception:
        return JSONResponse(
            status_code=503,
            content={
                "detail": "Rate limiter unavailable",
            },
        )

    remaining = max(
        0,
        int(decision.remaining_tokens),
    )

    headers = {
        "X-RateLimit-Limit": str(
            int(policy.capacity)
        ),
        "X-RateLimit-Remaining": str(
            remaining
        ),
    }

    if not decision.allowed:
        retry_after = max(
            1,
            ceil(
                decision.retry_after_seconds
            ),
        )

        headers["Retry-After"] = str(
            retry_after
        )

        return JSONResponse(
            status_code=429,
            content={
                "detail": "Rate limit exceeded",
                "retry_after_seconds": retry_after,
            },
            headers=headers,
        )

    response = await call_next(request)

    response.headers.update(headers)

    return response