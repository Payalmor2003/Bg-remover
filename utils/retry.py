"""Async retry decorator. """
from __future__ import annotations

import asyncio
import functools
from typing import Callable, TypeVar, Awaitable
from openai import RateLimitError, APIStatusError, APIConnectionError
from utils.logger import get_logger

log = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Awaitable])

# Errors worth retrying: transient network issues, rate limits, and 5xx.
_RETRYABLE = (RateLimitError, APIConnectionError)


def async_retry(max_retries: int = 5, backoff_base: float = 2.0):

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            last_exc: Exception | None = None
            for attempt in range(max_retries + 1):
                try:
                    return await fn(*args, **kwargs)
                except _RETRYABLE as exc:
                    last_exc = exc
                    if attempt == max_retries:
                        break
                    delay = backoff_base * (2 ** attempt)
                    log.warning(
                        "[%s] attempt %d/%d failed (%s) — retrying in %.1fs",
                        fn.__name__, attempt + 1, max_retries,
                        type(exc).__name__, delay,
                    )
                    await asyncio.sleep(delay)
                except APIStatusError as exc:
                    # 5xx → retry; 4xx (other than 429, handled above) → fail fast
                    if exc.status_code >= 500 and attempt < max_retries:
                        last_exc = exc
                        delay = backoff_base * (2 ** attempt)
                        log.warning(
                            "[%s] server error %d — retrying in %.1fs",
                            fn.__name__, exc.status_code, delay,
                        )
                        await asyncio.sleep(delay)
                        continue
                    raise
            raise RuntimeError(
                f"{fn.__name__} failed after {max_retries + 1} attempts"
            ) from last_exc
        return wrapper  # type: ignore[return-value]
    return decorator
