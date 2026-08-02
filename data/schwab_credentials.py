"""Local credential storage for the read-only Schwab integration."""

from __future__ import annotations

import fcntl
import json
import os
import random
import subprocess
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

KEYCHAIN_SERVICE = "com.carsynstephenson.schwab-market-data"
KEYCHAIN_ACCOUNT = "readonly-market-data"
PRIVATE_TOKEN_DIR = Path.home() / "Library" / "Application Support" / "Carsyn Research" / "Schwab"
SHARED_TOKEN_PATH = PRIVATE_TOKEN_DIR / "shared-market-data-tokens.json"
SECURITY_TOOL = Path("/usr/bin/security")
SCHWAB_HTTP_TIMEOUT_SECONDS = 15.0
SCHWAB_MAX_ATTEMPTS = 3
SCHWAB_BACKOFF_BASE_SECONDS = 0.25
SCHWAB_MAX_RETRY_AFTER_SECONDS = 5.0

READ_ONLY_METHODS = frozenset(
    {
        "get_quote",
        "get_quotes",
        "get_option_chain",
        "get_option_expiration_chain",
        "get_price_history",
        "get_price_history_every_minute",
        "get_price_history_every_five_minutes",
        "get_price_history_every_ten_minutes",
        "get_price_history_every_fifteen_minutes",
        "get_price_history_every_thirty_minutes",
        "get_price_history_every_day",
        "get_price_history_every_week",
        "get_market_hours",
        "get_instruments",
        "get_instrument_by_cusip",
        "get_movers",
    }
)


def load_client_secret() -> str:
    """Read the Client Secret from macOS Keychain without logging it."""
    if os.environ.get("SCHWAB_APP_SECRET", "").strip():
        raise RuntimeError(
            "Plaintext SCHWAB_APP_SECRET is not accepted. Remove it from the "
            "environment and run `uv run python tools/setup_schwab.py`."
        )
    result = subprocess.run(
        [
            str(SECURITY_TOOL),
            "find-generic-password",
            "-s",
            KEYCHAIN_SERVICE,
            "-a",
            KEYCHAIN_ACCOUNT,
            "-w",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    secret = result.stdout.rstrip("\r\n") if result.returncode == 0 else ""
    if not secret:
        raise RuntimeError(
            "The Schwab Client Secret is missing from macOS Keychain; run "
            "`uv run python tools/setup_schwab.py`."
        )
    return secret


def store_client_secret() -> None:
    """Prompt securely and store/update the Client Secret in macOS Keychain."""
    print("\nPaste the new Schwab Client Secret at the macOS Keychain prompt.")
    print("The input is hidden and is not written to either repository.")
    subprocess.run(
        [
            str(SECURITY_TOOL),
            "add-generic-password",
            "-U",
            "-s",
            KEYCHAIN_SERVICE,
            "-a",
            KEYCHAIN_ACCOUNT,
            "-l",
            "Schwab read-only market data",
            "-w",
        ],
        check=True,
    )


def _read_token(token_path: Path) -> dict[str, Any]:
    with token_path.open("r", encoding="utf-8") as handle:
        token = json.load(handle)
    if not isinstance(token, dict):
        raise RuntimeError("Schwab token file is malformed.")
    return token


def _atomic_write_token(token_path: Path, token: dict[str, Any], *_args, **_kwargs) -> None:
    """Persist a refreshed token without exposing it or leaving a partial file."""
    token_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    token_path.parent.chmod(0o700)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{token_path.name}.", suffix=".tmp", dir=token_path.parent
    )
    temporary_path = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(token, handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, token_path)
        token_path.chmod(0o600)
    except Exception:
        try:
            temporary_path.unlink()
        except FileNotFoundError:
            pass
        raise


@contextmanager
def _token_lock(token_path: Path) -> Iterator[None]:
    """Serialize token reads, refreshes, and writes across both repositories."""
    lock_path = token_path.with_name(f"{token_path.name}.lock")
    flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(lock_path, flags, 0o600)
    try:
        os.fchmod(descriptor, 0o600)
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


class LockedReadOnlySchwabClient:
    """Reload a shared token under a process lock for every market-data call.

    Recreating the SDK client inside the lock prevents a long-running process
    from refreshing with an in-memory token that another process already
    rotated. Only explicitly allowlisted GET market-data methods are exposed.
    """

    def __init__(self, api_key: str, app_secret: str, token_path: Path):
        self._api_key = api_key
        self._app_secret = app_secret
        self._token_path = token_path

    @contextmanager
    def _client(self):
        import schwab.auth

        with _token_lock(self._token_path):
            client = schwab.auth.client_from_access_functions(
                self._api_key,
                self._app_secret,
                lambda: _read_token(self._token_path),
                lambda token, *args, **kwargs: _atomic_write_token(
                    self._token_path, token, *args, **kwargs
                ),
            )
            client.set_timeout(SCHWAB_HTTP_TIMEOUT_SECONDS)
            yield client

    def token_age(self) -> int:
        with self._client() as client:
            return client.token_age()

    def __getattr__(self, name: str):
        if name not in READ_ONLY_METHODS:
            raise AttributeError(name)

        def call(*args, **kwargs):
            import httpx

            for attempt in range(SCHWAB_MAX_ATTEMPTS):
                try:
                    with self._client() as client:
                        response = getattr(client, name)(*args, **kwargs)
                except (httpx.TimeoutException, httpx.TransportError):
                    if attempt + 1 >= SCHWAB_MAX_ATTEMPTS:
                        raise
                    delay = SCHWAB_BACKOFF_BASE_SECONDS * (2**attempt)
                    time.sleep(delay + random.uniform(0.0, delay))
                    continue

                status = getattr(response, "status_code", None)
                if status not in {429, 500, 502, 503, 504}:
                    return response
                if attempt + 1 >= SCHWAB_MAX_ATTEMPTS:
                    return response

                retry_after = None
                if status == 429:
                    try:
                        retry_after = float(response.headers.get("retry-after"))
                    except (AttributeError, TypeError, ValueError):
                        retry_after = None
                    if (
                        retry_after is not None
                        and retry_after > SCHWAB_MAX_RETRY_AFTER_SECONDS
                    ):
                        return response
                delay = (
                    retry_after
                    if retry_after is not None and retry_after >= 0
                    else SCHWAB_BACKOFF_BASE_SECONDS * (2**attempt)
                    + random.uniform(
                        0.0, SCHWAB_BACKOFF_BASE_SECONDS * (2**attempt)
                    )
                )
                time.sleep(delay)
            raise AssertionError("unreachable")

        return call
