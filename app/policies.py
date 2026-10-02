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


# Policies used when an endpoint does not have
# a custom policy.
DEFAULT_POLICIES = {
    "ip": _policy(
        name="default:ip",
        capacity_env="IP_RATE_LIMIT_CAPACITY",
        refill_env="IP_RATE_LIMIT_REFILL_RATE",
        default_capacity=rate_limit_settings.capacity,
        default_refill_rate=rate_limit_settings.refill_rate,
    ),
    "user_id": _policy(
        name="default:user_id",
        capacity_env="USER_RATE_LIMIT_CAPACITY",
        refill_env="USER_RATE_LIMIT_REFILL_RATE",
        default_capacity=20,
        default_refill_rate=2,
    ),
    "api_key": _policy(
        name="default:api_key",
        capacity_env="API_KEY_RATE_LIMIT_CAPACITY",
        refill_env="API_KEY_RATE_LIMIT_REFILL_RATE",
        default_capacity=50,
        default_refill_rate=5,
    ),
}


# Custom policies for specific endpoints.
ENDPOINT_POLICIES = {
    "/api/search": {
        "ip": _policy(
            name="search:ip",
            capacity_env="SEARCH_IP_RATE_LIMIT_CAPACITY",
            refill_env="SEARCH_IP_RATE_LIMIT_REFILL_RATE",
            default_capacity=5,
            default_refill_rate=1,
        ),
        "user_id": _policy(
            name="search:user_id",
            capacity_env="SEARCH_USER_RATE_LIMIT_CAPACITY",
            refill_env="SEARCH_USER_RATE_LIMIT_REFILL_RATE",
            default_capacity=10,
            default_refill_rate=2,
        ),
        "api_key": _policy(
            name="search:api_key",
            capacity_env="SEARCH_API_KEY_RATE_LIMIT_CAPACITY",
            refill_env="SEARCH_API_KEY_RATE_LIMIT_REFILL_RATE",
            default_capacity=25,
            default_refill_rate=5,
        ),
    },
    "/api/upload": {
        "ip": _policy(
            name="upload:ip",
            capacity_env="UPLOAD_IP_RATE_LIMIT_CAPACITY",
            refill_env="UPLOAD_IP_RATE_LIMIT_REFILL_RATE",
            default_capacity=2,
            default_refill_rate=0.5,
        ),
        "user_id": _policy(
            name="upload:user_id",
            capacity_env="UPLOAD_USER_RATE_LIMIT_CAPACITY",
            refill_env="UPLOAD_USER_RATE_LIMIT_REFILL_RATE",
            default_capacity=5,
            default_refill_rate=1,
        ),
        "api_key": _policy(
            name="upload:api_key",
            capacity_env="UPLOAD_API_KEY_RATE_LIMIT_CAPACITY",
            refill_env="UPLOAD_API_KEY_RATE_LIMIT_REFILL_RATE",
            default_capacity=10,
            default_refill_rate=2,
        ),
    },
}


def get_policy(
    identity_type: str,
    endpoint: str | None = None,
) -> RateLimitPolicy:
    """
    Select a policy using both identity type and endpoint.

    Endpoint-specific policy has priority.
    Otherwise the default identity policy is used.
    """

    if endpoint is not None:
        endpoint_policies = ENDPOINT_POLICIES.get(
            endpoint
        )

        if endpoint_policies is not None:
            policy = endpoint_policies.get(
                identity_type
            )

            if policy is not None:
                return policy

    return DEFAULT_POLICIES.get(
        identity_type,
        DEFAULT_POLICIES["ip"],
    )