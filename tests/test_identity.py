from fastapi import Request

from app.identity import get_client_identity


def make_request(headers=None, client_host="127.0.0.1"):
    headers = headers or {}

    scope = {
        "type": "http",
        "headers": [
            (key.lower().encode(), value.encode())
            for key, value in headers.items()
        ],
        "client": (client_host, 12345),
    }

    return Request(scope)


def test_api_key_has_priority():
    request = make_request(
        headers={
            "X-API-Key": "customer123",
            "X-User-ID": "user123",
        }
    )

    identity_type, identity_value = get_client_identity(request)

    assert identity_type == "api_key"
    assert identity_value == "customer123"


def test_user_id_used_when_api_key_missing():
    request = make_request(
        headers={
            "X-User-ID": "user123",
        }
    )

    identity_type, identity_value = get_client_identity(request)

    assert identity_type == "user_id"
    assert identity_value == "user123"


def test_ip_used_when_no_identity_header():
    request = make_request(
        client_host="192.168.1.50"
    )

    identity_type, identity_value = get_client_identity(request)

    assert identity_type == "ip"
    assert identity_value == "192.168.1.50"