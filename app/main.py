from fastapi import FastAPI

from app.redis import redis_client


app = FastAPI(
    title="Distributed Rate Limiter & API Gateway",
    version="0.2.0",
)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy"
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
        await redis_client.set(test_key, "hello", ex=60)

        value = await redis_client.get(test_key)

        return {
            "status": "success",
            "key": test_key,
            "value": value,
        }

    except Exception as exc:
        return {
            "status": "failed",
            "error": str(exc),
        }