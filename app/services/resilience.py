import asyncio
import hashlib
import json
import logging
import random
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, Optional, List, Tuple, Callable
import httpx
from app.schemas import BookSearchQuery, BookCandidate

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "CLOSED"      # Normal operation
    OPEN = "OPEN"          # Failing, fast-reject requests
    HALF_OPEN = "HALF_OPEN"  # Testing if provider has recovered


class CircuitBreaker:
    """
    Circuit breaker pattern for unreliable external providers.
    Trips to OPEN after consecutive failures, auto-recovers after cooldown.
    """
    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        recovery_cooldown_seconds: float = 45.0
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_cooldown_seconds = recovery_cooldown_seconds
        self.state = CircuitState.CLOSED
        self.consecutive_failures = 0
        self.last_failure_time: float = 0.0
        self.last_state_change: float = time.time()
        self._lock = asyncio.Lock()

    async def allow_request(self) -> Tuple[bool, Optional[str]]:
        async with self._lock:
            now = time.time()
            if self.state == CircuitState.OPEN:
                if (now - self.last_failure_time) >= self.recovery_cooldown_seconds:
                    logger.info(f"CircuitBreaker [{self.name}]: Cooldown elapsed. Transitioning from OPEN to HALF_OPEN.")
                    self.state = CircuitState.HALF_OPEN
                    self.last_state_change = now
                    return True, None
                remaining = int(self.recovery_cooldown_seconds - (now - self.last_failure_time))
                return False, f"Provider circuit breaker is OPEN due to repeated failures. Cooldown: {remaining}s remaining."
            return True, None

    async def record_success(self):
        async with self._lock:
            if self.state != CircuitState.CLOSED:
                logger.info(f"CircuitBreaker [{self.name}]: Successful request. Transitioning to CLOSED.")
            self.state = CircuitState.CLOSED
            self.consecutive_failures = 0

    async def record_failure(self, reason: Optional[str] = None):
        async with self._lock:
            self.consecutive_failures += 1
            self.last_failure_time = time.time()
            if self.consecutive_failures >= self.failure_threshold and self.state != CircuitState.OPEN:
                self.state = CircuitState.OPEN
                logger.warning(
                    f"CircuitBreaker [{self.name}]: Tripped to OPEN after {self.consecutive_failures} failures. Reason: {reason}"
                )


class SearchCache:
    """
    In-memory asynchronous TTL cache for provider search responses.
    Caches bibliographic discovery results where provider terms permit.
    """
    def __init__(self, default_ttl_seconds: int = 600, max_entries: int = 500):
        self.default_ttl = default_ttl_seconds
        self.max_entries = max_entries
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    def _make_key(self, provider_name: str, query: BookSearchQuery, limit: int) -> str:
        raw = f"{provider_name.lower().strip()}|{query.title or ''}|{query.author or ''}|{query.isbn or ''}|{query.q or ''}|{query.subject or ''}|{limit}"
        return hashlib.sha256(raw.lower().encode("utf-8")).hexdigest()

    async def get(self, provider_name: str, query: BookSearchQuery, limit: int) -> Optional[List[BookCandidate]]:
        key = self._make_key(provider_name, query, limit)
        async with self._lock:
            entry = self._cache.get(key)
            if not entry:
                return None
            if time.time() > entry["expires_at"]:
                del self._cache[key]
                return None
            # Return fresh instances deserialized from stored JSON
            try:
                candidates_data = entry["data"]
                return [BookCandidate.model_validate(c) for c in candidates_data]
            except Exception as e:
                logger.warning(f"Cache deserialization failed for {provider_name}: {e}")
                return None

    async def set(
        self,
        provider_name: str,
        query: BookSearchQuery,
        limit: int,
        candidates: List[BookCandidate],
        ttl_seconds: Optional[int] = None
    ):
        key = self._make_key(provider_name, query, limit)
        ttl = ttl_seconds or self.default_ttl
        async with self._lock:
            # Evict oldest entries if capacity exceeded
            if len(self._cache) >= self.max_entries:
                oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k]["created_at"])
                del self._cache[oldest_key]

            self._cache[key] = {
                "created_at": time.time(),
                "expires_at": time.time() + ttl,
                "data": [c.model_dump() for c in candidates]
            }

    async def clear(self):
        async with self._lock:
            self._cache.clear()


# Global Registry of circuit breakers and provider cache
_CIRCUIT_BREAKERS: Dict[str, CircuitBreaker] = {}
search_cache = SearchCache(default_ttl_seconds=600, max_entries=1000)


def get_circuit_breaker(provider_name: str) -> CircuitBreaker:
    if provider_name not in _CIRCUIT_BREAKERS:
        _CIRCUIT_BREAKERS[provider_name] = CircuitBreaker(provider_name)
    return _CIRCUIT_BREAKERS[provider_name]


async def execute_with_backoff(
    provider_name: str,
    action: Callable[[], Any],
    max_retries: int = 2,
    base_backoff_seconds: float = 0.5
) -> Any:
    """
    Execute an asynchronous provider call with circuit breaker verification,
    Retry-After compliance, and bounded exponential backoff for transient failures.
    """
    breaker = get_circuit_breaker(provider_name)
    allowed, block_reason = await breaker.allow_request()
    if not allowed:
        raise RuntimeError(f"CIRCUIT_OPEN: {block_reason}")

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            result = await action()
            await breaker.record_success()
            return result
        except httpx.HTTPStatusError as hse:
            status = hse.response.status_code
            last_error = hse

            # Check Retry-After header on 429 or 503
            if status in (429, 503):
                retry_after_str = hse.response.headers.get("Retry-After")
                retry_delay = None
                if retry_after_str and retry_after_str.isdigit():
                    retry_delay = min(float(retry_after_str), 5.0)

                if attempt < max_retries:
                    wait_time = retry_delay if retry_delay is not None else (base_backoff_seconds * (2 ** attempt) + random.uniform(0.1, 0.3))
                    logger.info(f"Provider '{provider_name}' received HTTP {status}. Retrying in {wait_time:.2f}s (attempt {attempt + 1}/{max_retries})...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    await breaker.record_failure(f"HTTP {status}")
                    raise RuntimeError(f"RATE_LIMITED: {provider_name} rate limit reached (HTTP {status})")
            else:
                await breaker.record_failure(f"HTTP {status}")
                raise hse

        except (httpx.TimeoutException, httpx.NetworkError, asyncio.TimeoutError) as net_err:
            last_error = net_err
            if attempt < max_retries:
                wait_time = base_backoff_seconds * (2 ** attempt) + random.uniform(0.1, 0.3)
                logger.info(f"Provider '{provider_name}' network/timeout error: {net_err}. Retrying in {wait_time:.2f}s...")
                await asyncio.sleep(wait_time)
                continue
            else:
                await breaker.record_failure(str(net_err))
                raise RuntimeError(f"UNAVAILABLE: {provider_name} connection failed after {max_retries + 1} attempts ({str(net_err)})")

        except Exception as e:
            await breaker.record_failure(str(e))
            raise e

    raise last_error or RuntimeError(f"ERROR: {provider_name} query failed")
