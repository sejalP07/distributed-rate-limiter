from fastapi import FastAPI, Request

from app.proxy import proxy_request
from app.rate_limit_middleware import rate_limit_middleware
from app.redis import redis_client


app = FastAPI(
    title="Distributed Rate Limiter & API Gateway",
    version="0.4.0",
)


app.middleware("http")(
    rate_limit_middleware
)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "gateway",
    }


@app.get("/health/redis")
async def redis_health_check():
    try:
        response = await redis_client.ping()

        return {
            "status": "healthy",
            "redis": response,
        }

    except Exception as exc:
        return {
            "status": "unhealthy",
            "redis": str(exc),
        }


@app.get("/redis/test")
async def redis_test():
    test_key = "rate_limiter:test"

    try:
        await redis_client.set(
            test_key,
            "hello",
            ex=60,
        )

        value = await redis_client.get(
            test_key
        )

        return {
            "status": "success",
            "redis_key": test_key,
            "redis_value": value,
        }

    except Exception as exc:
        return {
            "status": "failed",
            "error": str(exc),
        }


@app.api_route(
    "/api/{path:path}",
    methods=[
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
        "OPTIONS",
    ],
)
async def gateway_proxy(
    request: Request,
    path: str,
):
    return await proxy_request(
        request,
        path,
    )