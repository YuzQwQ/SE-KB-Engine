from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from random import random
from typing import Callable


@dataclass(frozen=True)
class BackoffPolicy:
    base_seconds: float = 0.25
    maximum_seconds: float = 10.0
    jitter_ratio: float = 0.2

    def delay(
        self,
        attempt: int,
        *,
        retry_after: str | None = None,
        now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        jitter: Callable[[], float] = random,
    ) -> float:
        server_delay = _retry_after_seconds(retry_after, now())
        if server_delay is not None:
            return max(server_delay, 0.0)
        exponential = min(self.base_seconds * (2 ** max(attempt - 1, 0)), self.maximum_seconds)
        factor = 1 + ((jitter() * 2) - 1) * self.jitter_ratio
        return max(0.0, min(exponential * factor, self.maximum_seconds))


def _retry_after_seconds(value: str | None, current: datetime) -> float | None:
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        try:
            target = parsedate_to_datetime(value)
        except (TypeError, ValueError, OverflowError):
            return None
        if target.tzinfo is None:
            target = target.replace(tzinfo=timezone.utc)
        return (target - current).total_seconds()
