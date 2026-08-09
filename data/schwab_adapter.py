"""Read-only Schwab Market Data adapter for the intraday preview lane.

This module deliberately exposes quotes and option chains only. It does not
import or wrap Schwab account, order, transaction, or position endpoints.
Returned frames match the small ThetaData-shaped interface consumed by
``options_researcher.live_quotes``; they never enter the historical chain
cache, backtests, scoring, positions, receipts, or official verdict paths.
"""

from __future__ import annotations

import os
import stat
import threading
import time as monotonic_time
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from data.schwab_credentials import (
    PRIVATE_TOKEN_DIR,
    SHARED_TOKEN_PATH,
    LockedReadOnlySchwabClient,
    load_client_secret,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
EXPECTED_CALLBACK_URL = "https://127.0.0.1:8182"
DEFAULT_TOKEN_PATH = SHARED_TOKEN_PATH
PROVIDER_NAME = "schwab"
CHAIN_CACHE_TTL_SECONDS = 25.0

_client_singleton = None
_client_lock = threading.Lock()


@dataclass(frozen=True)
class SchwabConfig:
    api_key: str
    app_secret: str
    callback_url: str
    token_path: Path
    entitlement: str


def _is_truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def load_config(*, require_token: bool = True) -> SchwabConfig:
    """Load and validate local Schwab settings without ever echoing values."""
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")
    if _is_truthy(os.environ.get("SCHWAB_TRADING_ENABLED")):
        raise RuntimeError(
            "SCHWAB_TRADING_ENABLED must remain false: this integration is market-data-only."
        )

    api_key = os.environ.get("SCHWAB_API_KEY", "").strip()
    callback_url = os.environ.get("SCHWAB_CALLBACK_URL", EXPECTED_CALLBACK_URL).strip()
    token_path = Path(os.environ.get("SCHWAB_TOKEN_PATH", str(DEFAULT_TOKEN_PATH))).expanduser()
    if not token_path.is_absolute():
        token_path = REPO_ROOT / token_path
    token_path = token_path.resolve()
    private_token_root = PRIVATE_TOKEN_DIR.resolve()

    if not api_key:
        raise RuntimeError("Schwab setup is incomplete; run `uv run python tools/setup_schwab.py`.")
    if callback_url != EXPECTED_CALLBACK_URL:
        raise RuntimeError(f"SCHWAB_CALLBACK_URL must exactly match {EXPECTED_CALLBACK_URL}.")
    if token_path.parent != private_token_root:
        raise RuntimeError(
            "SCHWAB_TOKEN_PATH must be directly inside the private Schwab "
            "directory in ~/Library/Application Support."
        )
    if token_path.is_symlink():
        raise RuntimeError("SCHWAB_TOKEN_PATH must not be a symbolic link.")
    if require_token and not token_path.is_file():
        raise RuntimeError(
            "Schwab OAuth token is missing; run `uv run python tools/setup_schwab.py`."
        )
    if require_token:
        directory_mode = stat.S_IMODE(token_path.parent.stat().st_mode)
        token_mode = stat.S_IMODE(token_path.stat().st_mode)
        if directory_mode != 0o700 or token_mode != 0o600:
            raise RuntimeError(
                "Schwab credential permissions are unsafe; rerun "
                "`uv run python tools/setup_schwab.py --configure-only`."
            )

    entitlement = os.environ.get("SCHWAB_ENTITLEMENT", "NP").strip().upper()
    if entitlement not in {"NP", "PP", "PN"}:
        raise RuntimeError("SCHWAB_ENTITLEMENT must be NP, PP, or PN.")
    app_secret = load_client_secret()
    return SchwabConfig(
        api_key=api_key,
        app_secret=app_secret,
        callback_url=callback_url,
        token_path=token_path,
        entitlement=entitlement,
    )


def _client():
    """Return one token-aware client per process, created lazily."""
    global _client_singleton
    if _client_singleton is None:
        with _client_lock:
            if _client_singleton is None:
                cfg = load_config()
                _client_singleton = SchwabMarketData(
                    LockedReadOnlySchwabClient(
                        cfg.api_key, cfg.app_secret, cfg.token_path
                    ),
                    entitlement=cfg.entitlement,
                )
    return _client_singleton


def _reset_client() -> None:
    global _client_singleton
    _client_singleton = None


def _response_json(response) -> dict:
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise RuntimeError("Schwab returned a non-object JSON response.")
    return payload


def _timestamp(value: Any):
    if value in (None, ""):
        return pd.NaT
    try:
        number = float(value)
    except (TypeError, ValueError):
        return pd.to_datetime(value, utc=True, errors="coerce")
    unit = "ms" if abs(number) > 10_000_000_000 else "s"
    return pd.to_datetime(number, unit=unit, utc=True, errors="coerce")


def _iv_decimal(value: Any):
    """Schwab reports IV in percentage points; normalize to decimal IV."""
    try:
        iv = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return iv / 100.0


class SchwabMarketData:
    """Small, intentionally read-only facade matching the live-preview API."""

    provider_name = PROVIDER_NAME

    def __init__(
        self,
        api_client,
        *,
        entitlement: str = "NP",
        chain_cache_ttl_seconds: float = CHAIN_CACHE_TTL_SECONDS,
        clock=monotonic_time.monotonic,
    ):
        self.api = api_client
        self.entitlement = entitlement
        self.provider_version = self._version()
        self.chain_cache_ttl_seconds = max(0.0, float(chain_cache_ttl_seconds))
        self._clock = clock
        self._chain_cache: dict[tuple[str, str], tuple[float, pd.DataFrame]] = {}
        self._market_hours_cache: dict[str, dict] = {}

    @staticmethod
    def _version() -> str:
        try:
            from importlib.metadata import version

            return version("schwab-py")
        except Exception:
            return "unknown"

    def _entitlement_enum(self):
        from schwab.client import Client

        return {
            "NP": Client.Options.Entitlement.NON_PRO,
            "PP": Client.Options.Entitlement.PAYING_PRO,
            "PN": Client.Options.Entitlement.NON_PAYING_PRO,
        }[self.entitlement]

    def _parse_chain_payload(
        self,
        symbol: str,
        payload: dict,
        *,
        expected_expiration: date | None = None,
    ) -> pd.DataFrame:
        chain_is_delayed = payload.get("isDelayed")
        chain_is_truncated = payload.get("isChainTruncated")
        chain_status = payload.get("status")
        provider_contract_count = payload.get("numberOfContracts")
        if chain_is_delayed is True:
            raise RuntimeError("Schwab marked the requested option chain delayed.")
        if chain_is_truncated is True:
            raise RuntimeError("Schwab marked the requested option chain truncated.")
        if str(chain_status or "").strip().upper() != "SUCCESS":
            raise RuntimeError("Schwab option-chain status was not SUCCESS.")

        expected_iso = (
            expected_expiration.isoformat() if expected_expiration is not None else None
        )
        rows = []
        for map_name, right in (("callExpDateMap", "C"), ("putExpDateMap", "P")):
            for exp_key, strikes in (payload.get(map_name) or {}).items():
                exp_iso = str(exp_key).split(":", 1)[0]
                if expected_iso is not None and exp_iso != expected_iso:
                    raise RuntimeError(
                        "Schwab option chain contained an unexpected expiration."
                    )
                for strike_key, contracts in (strikes or {}).items():
                    for contract in contracts or []:
                        if not isinstance(contract, dict):
                            raise RuntimeError(
                                "Schwab option chain contained a malformed contract."
                            )
                        rows.append(
                            {
                                "symbol": symbol,
                                "expiration": exp_iso,
                                "strike": contract.get("strikePrice", strike_key),
                                "right": right,
                                "contract_symbol": contract.get("symbol"),
                                "bid": contract.get("bid"),
                                "ask": contract.get("ask"),
                                "last": contract.get("last"),
                                "mark": contract.get("mark"),
                                "volume": contract.get("totalVolume"),
                                "delta": contract.get("delta"),
                                "gamma": contract.get("gamma"),
                                "theta": contract.get("theta"),
                                "vega": contract.get("vega"),
                                "rho": contract.get("rho"),
                                "implied_vol": _iv_decimal(contract.get("volatility")),
                                "open_interest": contract.get("openInterest"),
                                "intrinsic_value": contract.get("intrinsicValue"),
                                "extrinsic_value": contract.get("extrinsicValue"),
                                "time_value": contract.get("timeValue"),
                                "days_to_expiration": contract.get("daysToExpiration"),
                                "multiplier": contract.get("multiplier"),
                                "non_standard": contract.get("nonStandard"),
                                "mini": contract.get("mini"),
                                "in_the_money": contract.get("inTheMoney"),
                                "expiration_type": contract.get("expirationType"),
                                "settlement_type": contract.get("settlementType"),
                                "deliverable_note": contract.get("deliverableNote"),
                                "timestamp": _timestamp(
                                    contract.get("quoteTimeInLong")
                                    or contract.get("quoteTime")
                                ),
                                "trade_timestamp": _timestamp(
                                    contract.get("tradeTimeInLong")
                                    or contract.get("tradeTime")
                                ),
                                "chain_is_delayed": chain_is_delayed,
                                "chain_is_truncated": chain_is_truncated,
                                "chain_status": chain_status,
                                "provider_contract_count": provider_contract_count,
                            }
                        )
        try:
            expected_count = int(str(provider_contract_count))
        except (TypeError, ValueError):
            raise RuntimeError("Schwab option chain omitted a valid contract count.")
        if expected_count != len(rows):
            raise RuntimeError(
                "Schwab option chain contract count did not match parsed rows."
            )
        native_symbols = [row["contract_symbol"] for row in rows]
        if any(not native_symbol for native_symbol in native_symbols):
            raise RuntimeError("Schwab option chain omitted a native contract symbol.")
        if len(set(native_symbols)) != len(native_symbols):
            raise RuntimeError("Schwab option chain contained duplicate contract symbols.")
        return pd.DataFrame(rows)

    def stock_snapshot_quote(self, symbols) -> pd.DataFrame:
        normalized = [str(symbol).strip().upper() for symbol in symbols]
        payload = _response_json(self.api.get_quotes(normalized))
        rows = []
        for symbol in normalized:
            item = payload.get(symbol) or payload.get(symbol.lower()) or {}
            quote = item.get("quote") or {}
            extended = item.get("extended") or {}
            regular = item.get("regular") or {}
            rows.append(
                {
                    "symbol": symbol,
                    "bid": quote.get("bidPrice"),
                    "ask": quote.get("askPrice"),
                    "last": quote.get("lastPrice"),
                    "mark": quote.get("mark"),
                    "open": quote.get("openPrice"),
                    "high": quote.get("highPrice"),
                    "low": quote.get("lowPrice"),
                    "previous_close": quote.get("closePrice"),
                    "volume": quote.get("totalVolume"),
                    "security_status": quote.get("securityStatus"),
                    "realtime": item.get("realtime"),
                    "timestamp": _timestamp(
                        quote.get("quoteTime")
                        or quote.get("quoteTimeInLong")
                        or item.get("quoteTimeInLong")
                    ),
                    "trade_timestamp": _timestamp(quote.get("tradeTime")),
                    "regular_last": regular.get("regularMarketLastPrice"),
                    "regular_timestamp": _timestamp(
                        regular.get("regularMarketTradeTime")
                    ),
                    "extended_bid": extended.get("bidPrice"),
                    "extended_ask": extended.get("askPrice"),
                    "extended_last": extended.get("lastPrice"),
                    "extended_mark": extended.get("mark"),
                    "extended_timestamp": _timestamp(extended.get("quoteTime")),
                }
            )
        return pd.DataFrame(rows)

    def _fetch_chain(self, symbol: str, expiration: date) -> pd.DataFrame:
        symbol = symbol.strip().upper()
        exp = expiration if isinstance(expiration, date) else date.fromisoformat(str(expiration))
        key = (symbol, exp.isoformat())
        cached = self._chain_cache.get(key)
        now = self._clock()
        if cached is not None:
            fetched_at, frame = cached
            if now - fetched_at < self.chain_cache_ttl_seconds:
                return frame.copy()

        from schwab.client import Client

        response = self.api.get_option_chain(
            symbol,
            contract_type=Client.Options.ContractType.ALL,
            from_date=exp,
            to_date=exp,
            include_underlying_quote=False,
            entitlement=self._entitlement_enum(),
        )
        payload = _response_json(response)
        frame = self._parse_chain_payload(
            symbol, payload, expected_expiration=exp
        )
        self._chain_cache[key] = (now, frame)
        return frame.copy()

    def option_full_chain(self, symbol: str) -> pd.DataFrame:
        """Return every expiration from one read-only Schwab chain response."""
        symbol = symbol.strip().upper()
        from schwab.client import Client

        response = self.api.get_option_chain(
            symbol,
            contract_type=Client.Options.ContractType.ALL,
            include_underlying_quote=False,
            entitlement=self._entitlement_enum(),
        )
        return self._parse_chain_payload(symbol, _response_json(response))

    def option_list_expirations(self, symbol: str) -> pd.DataFrame:
        payload = _response_json(
            self.api.get_option_expiration_chain(symbol.strip().upper())
        )
        rows = []
        for item in payload.get("expirationList") or []:
            if not isinstance(item, dict):
                continue
            rows.append(
                {
                    "expiration": item.get("expirationDate"),
                    "days_to_expiration": item.get("daysToExpiration"),
                    "expiration_type": item.get("expirationType"),
                    "settlement_type": item.get("settlementType"),
                    "standard": item.get("standard"),
                    "option_roots": item.get("optionRoots"),
                }
            )
        return pd.DataFrame(rows)

    def option_snapshot_quote(self, symbol: str, *, expiration: date) -> pd.DataFrame:
        cols = [
            "symbol", "expiration", "strike", "right", "contract_symbol",
            "bid", "ask", "last", "mark", "volume", "timestamp",
            "trade_timestamp", "multiplier", "non_standard", "mini",
            "chain_is_delayed", "chain_is_truncated", "chain_status",
        ]
        return self._fetch_chain(symbol, expiration).reindex(columns=cols)

    def option_snapshot_greeks_all(self, symbol: str, *, expiration: date) -> pd.DataFrame:
        cols = [
            "symbol",
            "expiration",
            "strike",
            "right",
            "bid",
            "ask",
            "last",
            "mark",
            "volume",
            "delta",
            "gamma",
            "theta",
            "vega",
            "rho",
            "implied_vol",
            "intrinsic_value",
            "extrinsic_value",
            "days_to_expiration",
            "contract_symbol",
            "multiplier",
            "non_standard",
            "mini",
            "timestamp",
            "trade_timestamp",
            "chain_is_delayed",
            "chain_is_truncated",
            "chain_status",
        ]
        return self._fetch_chain(symbol, expiration).reindex(columns=cols)

    def option_snapshot_open_interest(self, symbol: str, *, expiration: date) -> pd.DataFrame:
        cols = [
            "symbol", "expiration", "strike", "right", "contract_symbol",
            "open_interest", "timestamp", "multiplier", "non_standard",
            "chain_is_delayed", "chain_is_truncated", "chain_status",
        ]
        return self._fetch_chain(symbol, expiration).reindex(columns=cols)

    def regular_session_state(self, now_ny: datetime) -> dict[str, Any]:
        """Return provider-scheduled equity/option regular-session state."""
        ny_date = now_ny.date().isoformat()
        payload = self._market_hours_cache.get(ny_date)
        if payload is None:
            from schwab.client import Client

            payload = _response_json(
                self.api.get_market_hours(
                    [
                        Client.MarketHours.Market.EQUITY,
                        Client.MarketHours.Market.OPTION,
                    ],
                    date=now_ny.date(),
                )
            )
            self._market_hours_cache[ny_date] = payload

        def in_window(market: str, product: str) -> bool:
            item = ((payload.get(market) or {}).get(product) or {})
            windows = ((item.get("sessionHours") or {}).get("regularMarket") or [])
            for window in windows:
                try:
                    start = pd.Timestamp(window["start"])
                    end = pd.Timestamp(window["end"])
                except (KeyError, TypeError, ValueError):
                    continue
                if start.tzinfo is None or end.tzinfo is None:
                    continue
                current = pd.Timestamp(now_ny).tz_convert(start.tz)
                if start <= current < end:
                    return True
            return False

        equity_open = in_window("equity", "EQ")
        option_open = in_window("option", "EQO")
        return {
            "open": equity_open and option_open,
            "equity_regular_open": equity_open,
            "option_regular_open": option_open,
            "source": "schwab_market_hours",
        }
