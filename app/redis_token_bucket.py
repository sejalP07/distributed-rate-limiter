from dataclasses import dataclass
from typing import Any

import redis.asyncio as redis


# Redis Lua script:
# The entire read -> refill -> check -> consume -> save operation
# happens atomically inside Redis.
TOKEN_BUCKET_SCRIPT = """
local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local requested = tonumber(ARGV[3])

-- Read the existing bucket state.
local bucket = redis.call(
    "HMGET",
    KEYS[1],
    "tokens",
    "last_refill_ms"
)

local tokens = tonumber(bucket[1])
local last_refill_ms = tonumber(bucket[2])

-- Use Redis server time so all gateway instances
-- use the same clock.
local server_time = redis.call("TIME")

local now_ms = (
    tonumber(server_time[1]) * 1000
) + math.floor(
    tonumber(server_time[2]) / 1000
)

-- First request for this client:
-- start with a full bucket.
if tokens == nil then
    tokens = capacity
end

if last_refill_ms == nil then
    last_refill_ms = now_ms
end

-- Calculate elapsed time.
local elapsed_ms = now_ms - last_refill_ms

-- Protect against unexpected negative time differences.
if elapsed_ms < 0 then
    elapsed_ms = 0
end

-- Refill tokens according to elapsed time.
local refill = (
    elapsed_ms / 1000
) * refill_rate

tokens = math.min(
    capacity,
    tokens + refill
)

-- Decide whether the request can be allowed.
local allowed = 0
local retry_after = 0

if tokens >= requested then

    -- Consume requested tokens.
    tokens = tokens - requested
    allowed = 1

else

    -- Calculate approximately how long the client
    -- needs to wait for enough tokens.
    local deficit = requested - tokens
    retry_after = deficit / refill_rate

end

-- Save the updated bucket state.
redis.call(
    "HSET",
    KEYS[1],
    "tokens",
    tokens,
    "last_refill_ms",
    now_ms
)

-- Automatically remove inactive buckets.
local ttl = math.max(
    1,
    math.ceil((capacity / refill_rate) * 2)
)

redis.call(
    "EXPIRE",
    KEYS[1],
    ttl
)

-- Return:
-- 1. allowed (1 or 0)
-- 2. remaining tokens
-- 3. retry-after seconds
return {
    allowed,
    tokens,
    retry_after
}
"""


@dataclass(frozen=True)
class RateLimitDecision:
    """
    Result of a Token Bucket decision.
    """

    allowed: bool
    remaining_tokens: float
    retry_after_seconds: float


class RedisTokenBucket:
    """
    Redis-backed Token Bucket rate limiter.

    Bucket state is stored in Redis so that multiple
    gateway instances can share the same rate-limit state.
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        *,
        capacity: float,
        refill_rate: float,
        key_prefix: str = "rate_limit:bucket",
    ) -> None:

        if capacity <= 0:
            raise ValueError(
                "capacity must be greater than 0"
            )

        if refill_rate <= 0:
            raise ValueError(
                "refill_rate must be greater than 0"
            )

        self.redis = redis_client
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.key_prefix = key_prefix

        # Register the Lua script with Redis.
        self._script = self.redis.register_script(
            TOKEN_BUCKET_SCRIPT
        )

    def key_for(self, identifier: str) -> str:
        """
        Create the Redis key for a client.
        """

        return f"{self.key_prefix}:{identifier}"

    async def try_consume(
        self,
        identifier: str,
        tokens: float = 1,
    ) -> RateLimitDecision:
        """
        Try to consume tokens for a client.

        Returns:
            RateLimitDecision containing:
            - whether the request is allowed
            - remaining tokens
            - retry-after time
        """

        if not identifier:
            raise ValueError(
                "identifier must not be empty"
            )

        if tokens <= 0:
            raise ValueError(
                "tokens must be greater than 0"
            )

        if tokens > self.capacity:
            raise ValueError(
                "tokens cannot exceed bucket capacity"
            )

        # Example:
        # rate_limit:bucket:user123
        key = self.key_for(identifier)

        # Execute the Lua script atomically.
        result: Any = await self._script(
            keys=[key],
            args=[
                str(self.capacity),
                str(self.refill_rate),
                str(tokens),
            ],
        )

        allowed = bool(int(result[0]))
        remaining_tokens = float(result[1])
        retry_after_seconds = float(result[2])

        return RateLimitDecision(
            allowed=allowed,
            remaining_tokens=remaining_tokens,
            retry_after_seconds=retry_after_seconds,
        )