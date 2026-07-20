"""Small, dependency-free HTTP, caching, and throttling primitives."""
from __future__ import annotations

import hashlib
import json
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen


class ProviderError(RuntimeError):
    """A provider request failed without exposing credentials."""


class UnsupportedFeatureError(ProviderError):
    """The account/provider does not support the requested read-only field."""


class JsonTransport(Protocol):
    def get_json(
        self,
        url: str,
        *,
        params: Mapping[str, object] | None = None,
        headers: Mapping[str, str] | None = None,
        cache_namespace: str | None = None,
    ) -> object: ...


@dataclass(frozen=True)
class CachedResponse:
    retrieved_at: datetime
    payload: object


class DiskResponseCache:
    """Content-addressed JSON cache that never stores sensitive parameters."""

    _SENSITIVE_PARAM_NAMES = frozenset(
        {"api_key", "apikey", "token", "access_token", "client_secret", "password"}
    )

    def __init__(self, root: Path | str = ".cache/market_data") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    @classmethod
    def _safe_key(
        cls, url: str, params: Mapping[str, object] | None, namespace: str | None
    ) -> str:
        safe_params = {
            str(key): str(value)
            for key, value in sorted((params or {}).items(), key=lambda item: str(item[0]))
            if str(key).lower() not in cls._SENSITIVE_PARAM_NAMES
        }
        material = json.dumps(
            {"namespace": namespace or "", "url": urlunsplit(urlsplit(url)._replace(query="")), "params": safe_params},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(material).hexdigest()

    def read(
        self, url: str, params: Mapping[str, object] | None, namespace: str | None
    ) -> CachedResponse | None:
        path = self.root / f"{self._safe_key(url, params, namespace)}.json"
        with self._lock:
            if not path.exists():
                return None
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                return CachedResponse(
                    retrieved_at=datetime.fromisoformat(raw["retrieved_at"]),
                    payload=raw["payload"],
                )
            except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                raise ProviderError(f"invalid cached response at {path}") from exc

    def write(
        self,
        url: str,
        params: Mapping[str, object] | None,
        namespace: str | None,
        payload: object,
        *,
        retrieved_at: datetime | None = None,
    ) -> None:
        path = self.root / f"{self._safe_key(url, params, namespace)}.json"
        temp = path.with_suffix(".tmp")
        record = {
            "retrieved_at": (retrieved_at or datetime.now(timezone.utc)).isoformat(),
            "payload": payload,
        }
        with self._lock:
            temp.write_text(json.dumps(record, sort_keys=True, default=str), encoding="utf-8")
            temp.replace(path)


class RateLimiter:
    """Sliding-window limiter suitable for a provider's free-tier quota."""

    def __init__(
        self,
        max_calls: int,
        window_seconds: float,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if max_calls <= 0 or window_seconds <= 0:
            raise ValueError("rate limiter requires positive limits")
        self.max_calls = max_calls
        self.window_seconds = float(window_seconds)
        self._clock = clock
        self._sleep = sleep
        self._calls: deque[float] = deque()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        while True:
            with self._lock:
                now = self._clock()
                while self._calls and now - self._calls[0] >= self.window_seconds:
                    self._calls.popleft()
                if len(self._calls) < self.max_calls:
                    self._calls.append(now)
                    return
                wait_for = self.window_seconds - (now - self._calls[0])
            self._sleep(max(wait_for, 0.0))


class HttpJsonTransport:
    """GET-only JSON transport with cache, throttling, and redacted errors."""

    def __init__(
        self,
        *,
        cache: DiskResponseCache | None = None,
        limiter: RateLimiter | None = None,
        timeout_seconds: float = 20.0,
    ) -> None:
        self.cache = cache
        self.limiter = limiter
        self.timeout_seconds = timeout_seconds
        self._request_lock = threading.RLock()

    @staticmethod
    def _display_url(url: str) -> str:
        parsed = urlsplit(url)
        return urlunsplit(parsed._replace(query=""))

    def get_json(
        self,
        url: str,
        *,
        params: Mapping[str, object] | None = None,
        headers: Mapping[str, str] | None = None,
        cache_namespace: str | None = None,
    ) -> object:
        params = dict(params or {})
        with self._request_lock:
            cached = self.cache.read(url, params, cache_namespace) if self.cache else None
            if cached is not None:
                return cached.payload
            if self.limiter is not None:
                self.limiter.acquire()
            query = urlencode({key: value for key, value in params.items() if value is not None})
            request_url = f"{url}{'&' if '?' in url else '?'}{query}" if query else url
            request = Request(request_url, headers=dict(headers or {}), method="GET")
            try:
                with urlopen(request, timeout=self.timeout_seconds) as response:
                    payload = json.loads(response.read().decode("utf-8"))
            except HTTPError as exc:
                raise ProviderError(
                    f"HTTP {exc.code} from {self._display_url(url)}"
                ) from exc
            except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
                raise ProviderError(
                    f"request failed for {self._display_url(url)}: {type(exc).__name__}"
                ) from exc
            if self.cache is not None:
                self.cache.write(url, params, cache_namespace, payload)
            return payload


class HttpFormTransport:
    """Minimal POST form transport for OAuth token exchange only."""

    def __init__(self, *, timeout_seconds: float = 20.0) -> None:
        self.timeout_seconds = timeout_seconds

    def post_form(
        self,
        url: str,
        *,
        form: Mapping[str, object],
        headers: Mapping[str, str] | None = None,
    ) -> object:
        body = urlencode({key: value for key, value in form.items()}).encode("utf-8")
        request_headers = {"Content-Type": "application/x-www-form-urlencoded"}
        request_headers.update(headers or {})
        request = Request(url, data=body, headers=request_headers, method="POST")
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise ProviderError(f"HTTP {exc.code} from {HttpJsonTransport._display_url(url)}") from exc
        except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise ProviderError(
                f"OAuth request failed for {HttpJsonTransport._display_url(url)}: {type(exc).__name__}"
            ) from exc


class RetryingJsonTransport:
    """Retry a bounded number of transport failures without retrying payload errors."""

    def __init__(
        self,
        transport: JsonTransport,
        *,
        attempts: int = 3,
        backoff_seconds: float = 0.25,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if attempts < 1:
            raise ValueError("attempts must be positive")
        self.transport = transport
        self.attempts = attempts
        self.backoff_seconds = backoff_seconds
        self.sleep = sleep

    def get_json(
        self,
        url: str,
        *,
        params: Mapping[str, object] | None = None,
        headers: Mapping[str, str] | None = None,
        cache_namespace: str | None = None,
    ) -> object:
        last_error: ProviderError | None = None
        for attempt in range(self.attempts):
            try:
                return self.transport.get_json(
                    url,
                    params=params,
                    headers=headers,
                    cache_namespace=cache_namespace,
                )
            except ProviderError as exc:
                last_error = exc
                if attempt + 1 < self.attempts:
                    self.sleep(self.backoff_seconds * (2**attempt))
        assert last_error is not None
        raise last_error
