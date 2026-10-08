import os

import httpx
from fastapi import HTTPException, Request
from fastapi.responses import Response
from time import perf_counter
from app.metrics import BACKEND_LATENCY

BACKEND_URL = os.getenv(
    "BACKEND_URL",
    "http://backend:9000",
)

HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
    "date",
    "server",
}


def create_backend_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(
            connect=2.0,
            read=10.0,
            write=10.0,
            pool=2.0,
        ),
        limits=httpx.Limits(
            max_connections=200,
            max_keepalive_connections=50,
        ),
    )


async def proxy_request(
    request: Request,
    backend_path: str,
) -> Response:
    backend_client = getattr(
        request.app.state,
        "backend_client",
        None,
    )

    if backend_client is None:
        raise HTTPException(
            status_code=503,
            detail="Backend HTTP client is not initialized",
        )

    url = (
        f"{BACKEND_URL.rstrip('/')}/"
        f"{backend_path.lstrip('/')}"
    )

    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS
    }

    body = await request.body()

    backend_start = perf_counter()

    try:
        response = await backend_client.request(
            method=request.method,
            url=url,
            headers=headers,
            content=body,
            params=request.query_params,
        )
    except httpx.RequestError as exc:
        BACKEND_LATENCY.observe(
            perf_counter() - backend_start
        )

        raise HTTPException(
            status_code=502,
            detail=f"Backend unavailable: {type(exc).__name__}",
        ) from exc

    BACKEND_LATENCY.observe(
        perf_counter() - backend_start
    )

    response_headers = {
        key: value
        for key, value in response.headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS
    }

    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=response_headers,
        media_type=response.headers.get("content-type"),
    )