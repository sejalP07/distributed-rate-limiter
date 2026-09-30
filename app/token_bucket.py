from dataclasses import dataclass
from time import monotonic
from typing import Callable


@dataclass
class TokenBucket:
    capacity: float
    refill_rate: float
    clock: Callable[[], float] = monotonic

    def __post_init__(self) -> None:
        if self.capacity <= 0:
            raise ValueError("capacity must be greater than 0")

        if self.refill_rate <= 0:
            raise ValueError("refill_rate must be greater than 0")

        self.tokens = self.capacity
        self.last_refill_time = self.clock()

    def _refill(self) -> None:
        now = self.clock()
        elapsed = now - self.last_refill_time

        if elapsed <= 0:
            return

        new_tokens = elapsed * self.refill_rate

        self.tokens = min(
            self.capacity,
            self.tokens + new_tokens,
        )

        self.last_refill_time = now

    def try_consume(self, tokens: float = 1) -> bool:
        if tokens <= 0:
            raise ValueError("tokens must be greater than 0")

        self._refill()

        if self.tokens < tokens:
            return False

        self.tokens -= tokens
        return True

    def available_tokens(self) -> float:
        self._refill()
        return self.tokens