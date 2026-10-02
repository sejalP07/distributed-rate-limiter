from dataclasses import dataclass

from app.config import _get_float, rate_limit_settings


@dataclass(frozen=True)
class RateLimitPolicy:
    name: str
    capacity: float
    refill_rate: float


def _policy(
    name: str,
    capacity_env: str,
    refill_env: str,
    default_capacity: float,
    default_refill_rate: float,
) -> RateLimitPolicy:
    return RateLimitPolicy(
        name=name,
        capacity=_get_float(
            capacity_env,
            default_capacity,
        ),
        refill_rate=_get_float(
            refill_env,
            default_refill_rate,
        ),
    )


POLICIES = {
    "ip": _policy(
        name="ip",
        capacity_env="IP_RATE_LIMIT_CAPACITY",
        refill_env="IP_RATE_LIMIT_REFILL_RATE",
        default_capacity=rate_limit_settings.capacity,
        default_refill_rate=rate_limit_settings.refill_rate,
    ),
    "user_id": _policy(
        name="user_id",
        capacity_env="USER_RATE_LIMIT_CAPACITY",
        refill_env="USER_RATE_LIMIT_REFILL_RATE",
        default_capacity=20,
        default_refill_rate=2,
    ),
    "api_key": _policy(
        name="api_key",
        capacity_env="API_KEY_RATE_LIMIT_CAPACITY",
        refill_env="API_KEY_RATE_LIMIT_REFILL_RATE",
        default_capacity=50,
        default_refill_rate=5,
    ),
}


def get_policy(identity_type: str) -> RateLimitPolicy:
    return POLICIES.get(
        identity_type,
        RateLimitPolicy(
            name="default",
            capacity=rate_limit_settings.capacity,
            refill_rate=rate_limit_settings.refill_rate,
        ),
    )