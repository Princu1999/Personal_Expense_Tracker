import asyncio
import time
from collections import defaultdict
from typing import Dict, List, Tuple

from app.guardrails.base import GuardrailAction, GuardrailResult
from app.guardrails.config import guardrail_settings


class RateLimiter:
    """
    Sliding window in-memory rate limiter with automatic stale key eviction.
    Thread-safe and async-friendly.
    """

    def __init__(
        self,
        default_requests: int = guardrail_settings.RATE_LIMIT_REQUESTS_PER_MINUTE,
        default_window: int = guardrail_settings.RATE_LIMIT_WINDOW_SECONDS,
    ):
        self.default_requests = default_requests
        self.default_window = default_window
        self._history: Dict[str, List[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def check(
        self,
        key: str,
        max_requests: int = None,
        window_seconds: int = None,
    ) -> GuardrailResult:
        if not guardrail_settings.ENABLE_RATE_LIMITING or not guardrail_settings.ENABLED:
            return GuardrailResult(action=GuardrailAction.ALLOW, passed=True)

        limit = max_requests if max_requests is not None else self.default_requests
        window = window_seconds if window_seconds is not None else self.default_window

        now = time.time()
        cutoff = now - window

        async with self._lock:
            timestamps = self._history[key]
            # Prune expired timestamps
            valid_timestamps = [t for t in timestamps if t > cutoff]
            self._history[key] = valid_timestamps

            if len(valid_timestamps) >= limit:
                oldest_in_window = valid_timestamps[0]
                retry_after = max(1, int(window - (now - oldest_in_window)))
                return GuardrailResult(
                    action=GuardrailAction.BLOCK,
                    passed=False,
                    violation_type="rate_limit_exceeded",
                    reason=f"Rate limit exceeded: {len(valid_timestamps)}/{limit} requests in {window}s.",
                    metadata={
                        "retry_after": retry_after,
                        "limit": limit,
                        "window": window,
                        "current_count": len(valid_timestamps),
                    },
                    safe_response=(
                        f"You have reached the maximum rate of {limit} requests per minute. "
                        f"Please wait {retry_after} seconds before trying again."
                    ),
                )

            # Record this request
            self._history[key].append(now)
            remaining = max(0, limit - len(self._history[key]))

            return GuardrailResult(
                action=GuardrailAction.ALLOW,
                passed=True,
                metadata={
                    "remaining": remaining,
                    "limit": limit,
                    "window": window,
                },
            )

    async def reset(self, key: str = None):
        """Reset rate limit history for a specific key or all keys (useful for testing)."""
        async with self._lock:
            if key:
                self._history.pop(key, None)
            else:
                self._history.clear()


rate_limiter = RateLimiter()
