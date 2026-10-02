import os

import httpx
from fastapi import Request
from starlette.responses import JSONResponse, Response


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
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
    "date",
    "server",
}

def _forward_headers(request: Request) -> dict[str, str]:
    """
    Copy request headers to the backend while removing
    hop-by-hop headers that should not be forwarded.
    """

    return {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS
    }


def _response_headers(
    response: httpx.Response,
) -> dict[str, str]:
    """
    Copy useful backend response headers while removing
    headers managed by the gateway/HTTP server.
    """

    return {
        key: value
        for key, value in response.headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS
    }


async def proxy_request(
    request: Request,
    path: str,
) -> Response:
    """
    Forward the gateway request to the backend service.
    """

    body = await request.body()

    headers = _forward_headers(request)

    # /api/demo -> /demo
    # /api/search -> /search
    # /api/upload -> /upload
    backend_path = f"/{path}"

    try:
        async with httpx.AsyncClient(
            base_url=BACKEND_URL,
            timeout=10.0,
        ) as client:
            upstream_response = await client.request(
                method=request.method,
                url=backend_path,
                params=request.query_params,
                headers=headers,
                content=body,
            )

    except httpx.RequestError:
        return JSONResponse(
            status_code=502,
            content={
                "detail": "Backend service unavailable",
            },
        )

    return Response(
        content=upstream_response.content,
        status_code=upstream_response.status_code,
        headers=_response_headers(
            upstream_response
        ),
        media_type=upstream_response.headers.get(
            "content-type"
        ),
    )