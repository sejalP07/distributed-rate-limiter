from math import ceil

from fastapi import Request
from starlette.responses import JSONResponse

from app.redis import redis_client
from app.redis_token_bucket import RedisTokenBucket


# Simple policy for Step 4
RATE_LIMIT_CAPACITY = 5
RATE_LIMIT_REFILL_RATE = 1.0


# One shared rate limiter instance for this gateway process.
# The actual bucket state is stored in Redis.
rate_limiter = RedisTokenBucket(
    redis_client,
    capacity=RATE_LIMIT_CAPACITY,
    refill_rate=RATE_LIMIT_REFILL_RATE,
    key_prefix="rate_limit:ip",
)


async def rate_limit_middleware(request: Request, call_next):
    """
    Runs before the requested FastAPI endpoint.

    For /api/*:
    1. Identify the client by IP.
    2. Ask Redis token bucket whether one token is available.
    3. Reject with 429 if no token is available.
    4. Otherwise continue to the endpoint.
    """

    # Do not rate-limit health or internal endpoints yet.
    if not request.url.path.startswith("/api/"):
        return await call_next(request)

    # Identify client IP.
    if request.client is not None:
        client_ip = request.client.host
    else:
        client_ip = "unknown"

    identifier = f"ip:{client_ip}"

    try:
        decision = await rate_limiter.try_consume(identifier)

    except Exception:
        # For now, fail closed so API traffic is not allowed
        # to bypass the rate limiter when Redis is unavailable.
        return JSONResponse(
            status_code=503,
            content={
                "detail": "Rate limiter unavailable",
            },
        )

    remaining = max(0, int(decision.remaining_tokens))

    headers = {
        "X-RateLimit-Limit": str(int(RATE_LIMIT_CAPACITY)),
        "X-RateLimit-Remaining": str(remaining),
    }

    # No token available.
    if not decision.allowed:
        retry_after = max(
            1,
            ceil(decision.retry_after_seconds),
        )

        headers["Retry-After"] = str(retry_after)

        return JSONResponse(
            status_code=429,
            content={
                "detail": "Rate limit exceeded",
                "retry_after_seconds": retry_after,
            },
            headers=headers,
        )

    # Token was consumed.
    response = await call_next(request)

    # Add rate-limit information to successful responses too.
    response.headers.update(headers)

    return response