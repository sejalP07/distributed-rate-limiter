import os
from dataclasses import dataclass


def _get_float(name: str, default: float) -> float:
    value = os.getenv(name, str(default))

    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(
            f"{name} must be a valid number"
        ) from exc


@dataclass(frozen=True)
class RateLimitSettings:
    capacity: float
    refill_rate: float


rate_limit_settings = RateLimitSettings(
    capacity=_get_float(
        "RATE_LIMIT_CAPACITY",
        5,
    ),
    refill_rate=_get_float(
        "RATE_LIMIT_REFILL_RATE",
        1.0,
    ),
)