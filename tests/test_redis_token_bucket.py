import asyncio
from uuid import uuid4

import redis.asyncio as redis

from app.redis_token_bucket import RedisTokenBucket


REDIS_URL = "redis://redis:6379"


def test_redis_bucket_allows_and_rejects():
    async def run_test():
        redis_client = redis.from_url(
            REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )

        identifier = f"test:{uuid4().hex}"

        bucket = RedisTokenBucket(
            redis_client,
            capacity=5,
            refill_rate=1,
        )

        key = bucket.key_for(identifier)

        try:
            decisions = [
                await bucket.try_consume(identifier)
                for _ in range(5)
            ]

            assert all(
                decision.allowed
                for decision in decisions
            )

            rejected = await bucket.try_consume(identifier)

            assert rejected.allowed is False

        finally:
            await redis_client.delete(key)
            await redis_client.aclose()

    asyncio.run(run_test())


def test_redis_bucket_state_is_shared():
    async def run_test():
        redis_client = redis.from_url(
            REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )

        identifier = f"test:{uuid4().hex}"

        bucket_a = RedisTokenBucket(
            redis_client,
            capacity=2,
            refill_rate=0.1,
        )

        bucket_b = RedisTokenBucket(
            redis_client,
            capacity=2,
            refill_rate=0.1,
        )

        key = bucket_a.key_for(identifier)

        try:
            first = await bucket_a.try_consume(identifier)
            second = await bucket_b.try_consume(identifier)
            third = await bucket_a.try_consume(identifier)

            assert first.allowed is True
            assert second.allowed is True
            assert third.allowed is False

        finally:
            await redis_client.delete(key)
            await redis_client.aclose()

    asyncio.run(run_test())


def test_redis_bucket_concurrent_requests():
    async def run_test():
        redis_client = redis.from_url(
            REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )

        identifier = f"test:{uuid4().hex}"

        bucket = RedisTokenBucket(
            redis_client,
            capacity=10,
            refill_rate=0.01,
        )

        key = bucket.key_for(identifier)

        try:
            tasks = [
                bucket.try_consume(identifier)
                for _ in range(50)
            ]

            decisions = await asyncio.gather(*tasks)

            allowed_count = sum(
                decision.allowed
                for decision in decisions
            )

            assert allowed_count == 10

        finally:
            await redis_client.delete(key)
            await redis_client.aclose()

    asyncio.run(run_test())