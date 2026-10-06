import json
import logging
from typing import Any


logger = logging.getLogger("rate_limiter")


def log_rate_limit_rejection(
    *,
    identity_type: str,
    identity: str,
    method: str,
    endpoint: str,
    policy_name: str,
    limit: float,
    remaining: float,
    retry_after_seconds: float,
) -> None:
    event = {
        "event": "rate_limit_rejected",
        "identity_type": identity_type,
        "identity": identity,
        "method": method,
        "endpoint": endpoint,
        "policy": policy_name,
        "limit": limit,
        "remaining": remaining,
        "retry_after_seconds": retry_after_seconds,
    }

    logger.warning(
        json.dumps(
            event,
            separators=(",", ":"),
        )
    )