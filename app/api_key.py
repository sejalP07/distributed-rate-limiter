import hashlib
import hmac
import secrets


API_KEY_PREFIX = "rl_"
API_KEY_BYTES = 32


def generate_api_key() -> str:
    """
    Generate a cryptographically secure API key.

    The plaintext key should only be shown to the
    client at creation time.
    """

    secret = secrets.token_urlsafe(API_KEY_BYTES)

    return f"{API_KEY_PREFIX}{secret}"


def hash_api_key(api_key: str) -> str:
    """
    Return the SHA-256 hexadecimal digest of an API key.
    """

    if not api_key:
        raise ValueError(
            "api_key must not be empty"
        )

    return hashlib.sha256(
        api_key.encode("utf-8")
    ).hexdigest()


def verify_api_key(
    api_key: str,
    expected_hash: str,
) -> bool:
    """
    Verify an API key against its stored digest.
    """

    if not api_key or not expected_hash:
        return False

    actual_hash = hash_api_key(api_key)

    return hmac.compare_digest(
        actual_hash,
        expected_hash,
    )