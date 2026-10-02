from fastapi import Request


def get_client_identity(request: Request) -> tuple[str, str]:
    # For an already-authenticated API key, use the database
    # client ID instead of the secret API key itself.
    authenticated_client_id = getattr(
        request.state,
        "authenticated_client_id",
        None,
    )

    if authenticated_client_id is not None:
        return "api_key", str(authenticated_client_id)

    api_key = request.headers.get("X-API-Key")

    if api_key:
        return "api_key", api_key

    user_id = request.headers.get("X-User-ID")

    if user_id:
        return "user_id", user_id

    if request.client is not None:
        return "ip", request.client.host

    return "ip", "unknown"