from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from app.database import (
    check_database_connection,
    close_database,
    init_database,
)
from app.proxy import proxy_request
from app.rate_limit_middleware import rate_limit_middleware
from app.redis import redis_client
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from prometheus_client import make_asgi_app
from app.admin_auth import require_admin
from app.database import get_db
from app.schemas import (
    CreateClientRequest,
    CreateClientResponse,
)
from app.services import ClientService
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initialize resources when the gateway starts
    and release them when it shuts down.
    """

    await init_database()

    try:
        yield
    finally:
        await close_database()


app = FastAPI(
    title="Distributed Rate Limiter & API Gateway",
    version="0.5.0",
    lifespan=lifespan,
)


app.middleware("http")(
    rate_limit_middleware
)

metrics_app = make_asgi_app()

app.mount(
    "/metrics",
    metrics_app,
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


@app.get("/health/db")
async def database_health_check():
    try:
        healthy = await check_database_connection()

        return {
            "status": "healthy",
            "database": "postgresql",
            "connected": healthy,
        }

    except Exception as exc:
        return {
            "status": "unhealthy",
            "database": "postgresql",
            "error": str(exc),
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
@app.post(
    "/admin/clients",
    response_model=CreateClientResponse,
    status_code=201,
)
async def create_client(
    payload: CreateClientRequest,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> CreateClientResponse:
    service = ClientService(db)

    created = await service.create_client(
        payload.name,
    )

    return CreateClientResponse(
        id=created.client.id,
        name=created.client.name,
        api_key=created.api_key,
    )