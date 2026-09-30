from fastapi import Request


def get_client_identity(request: Request) -> tuple[str, str]:
    """
    Determine how this request should be rate-limited.

    Priority:
    1. API key
    2. User ID
    3. IP address
    """

    api_key = request.headers.get("X-API-Key")

    if api_key:
        return "api_key", api_key

    user_id = request.headers.get("X-User-ID")

    if user_id:
        return "user_id", user_id

    if request.client is not None:
        return "ip", request.client.host

    return "ip", "unknown"