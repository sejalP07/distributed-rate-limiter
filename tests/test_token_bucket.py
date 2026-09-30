import pytest

from app.token_bucket import TokenBucket


class FakeClock:
    def __init__(self, start: float = 0.0):
        self.current = start

    def now(self) -> float:
        return self.current

    def advance(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("seconds cannot be negative")

        self.current += seconds


def test_bucket_starts_full():
    clock = FakeClock()

    bucket = TokenBucket(
        capacity=10,
        refill_rate=2,
        clock=clock.now,
    )

    assert bucket.available_tokens() == 10


def test_consume_one_token():
    clock = FakeClock()

    bucket = TokenBucket(
        capacity=10,
        refill_rate=2,
        clock=clock.now,
    )

    assert bucket.try_consume() is True
    assert bucket.available_tokens() == 9


def test_consume_multiple_tokens():
    clock = FakeClock()

    bucket = TokenBucket(
        capacity=10,
        refill_rate=2,
        clock=clock.now,
    )

    assert bucket.try_consume(4) is True
    assert bucket.available_tokens() == 6


def test_reject_when_not_enough_tokens():
    clock = FakeClock()

    bucket = TokenBucket(
        capacity=2,
        refill_rate=1,
        clock=clock.now,
    )

    assert bucket.try_consume() is True
    assert bucket.try_consume() is True
    assert bucket.try_consume() is False


def test_tokens_refill_over_time():
    clock = FakeClock()

    bucket = TokenBucket(
        capacity=10,
        refill_rate=2,
        clock=clock.now,
    )

    assert bucket.try_consume(10) is True
    assert bucket.available_tokens() == 0

    clock.advance(2)

    assert bucket.available_tokens() == 4


def test_bucket_never_exceeds_capacity():
    clock = FakeClock()

    bucket = TokenBucket(
        capacity=10,
        refill_rate=2,
        clock=clock.now,
    )

    assert bucket.try_consume(10) is True

    clock.advance(100)

    assert bucket.available_tokens() == 10


def test_fractional_refill():
    clock = FakeClock()

    bucket = TokenBucket(
        capacity=10,
        refill_rate=2,
        clock=clock.now,
    )

    assert bucket.try_consume(10) is True

    clock.advance(0.5)

    assert bucket.available_tokens() == 1


def test_no_time_means_no_refill():
    clock = FakeClock()

    bucket = TokenBucket(
        capacity=10,
        refill_rate=2,
        clock=clock.now,
    )

    bucket.try_consume(5)

    assert bucket.available_tokens() == 5


def test_invalid_capacity():
    clock = FakeClock()

    with pytest.raises(ValueError):
        TokenBucket(
            capacity=0,
            refill_rate=2,
            clock=clock.now,
        )


def test_invalid_refill_rate():
    clock = FakeClock()

    with pytest.raises(ValueError):
        TokenBucket(
            capacity=10,
            refill_rate=0,
            clock=clock.now,
        )


def test_invalid_token_amount():
    clock = FakeClock()

    bucket = TokenBucket(
        capacity=10,
        refill_rate=2,
        clock=clock.now,
    )

    with pytest.raises(ValueError):
        bucket.try_consume(0)