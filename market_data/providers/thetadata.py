"""Bridge to the repository's existing official ThetaData cache/client path."""
from __future__ import annotations

import os
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

import pandas as pd

from market_data.models import (
    DataTiming,
    OptionQuote,
    ProviderHealth,
    normalize_option_symbol,
    parse_option_symbol,
)
from market_data.providers.base import ProviderBase, quote_from_fields, utc_now
from market_data.transport import JsonTransport, ProviderError


class ThetaDataProvider(ProviderBase):
    """ThetaData adapter with cache-only reads by default.

    ``fetch_on_miss`` is opt-in because the canonical H7 path deliberately
    separates data acquisition from offline analysis and enforces its OOS gate.
    """

    name = "thetadata"
    _NY = ZoneInfo("America/New_York")

    def __init__(self, *, transport: JsonTransport | None = None) -> None:
        # transport is accepted for interface symmetry; the official client is
        # already owned by data.thetadata_adapter and is not HTTP-based.
        self.transport = transport

    @staticmethod
    def _has_credentials() -> bool:
        return bool(
            os.environ.get("THETADATA_API_KEY")
            or os.environ.get("THETA_DATA_API_KEY")
            or (
                os.environ.get("THETADATA_USERNAME")
                and os.environ.get("THETADATA_PASSWORD")
            )
        )

    def health_check(self) -> ProviderHealth:
        if not self._has_credentials():
            return self.missing_credentials(
                detail="set THETADATA_API_KEY or the configured username/password pair"
            )
        if not (os.environ.get("THETADATA_API_KEY") or os.environ.get("THETA_DATA_API_KEY")):
            return ProviderHealth(
                provider=self.name,
                connection_status="not_checked",
                authentication_status="configured-but-unsupported",
                subscription_status="unknown",
                detail="this repository's official client path uses THETADATA_API_KEY; username/password are retained for account setup notes",
            )
        try:
            from data.thetadata_adapter import _client

            client = _client()
        except Exception as exc:  # client library exposes multiple transport exception classes
            return ProviderHealth(
                provider=self.name,
                connection_status="failed",
                authentication_status="rejected-or-unreachable",
                subscription_status="unknown",
                detail=f"official client health check failed: {type(exc).__name__}",
            )
        return ProviderHealth(
            provider=self.name,
            connection_status="connected",
            authentication_status="accepted",
            subscription_status=(
                "options-enabled"
                if getattr(client, "options_subscription", True)
                else "options-disabled"
            ),
            detail="official repository ThetaData client authenticated",
        )

    @classmethod
    def _quote_timestamp(cls, as_of: date) -> datetime:
        return datetime.combine(as_of, time(17, 15), tzinfo=cls._NY).astimezone(timezone.utc)

    def get_option_chain(
        self,
        underlying_symbol: str,
        *,
        as_of: date,
        allow_oos: bool = False,
        fetch_on_miss: bool = False,
    ) -> list[OptionQuote]:
        from data import thetadata_adapter

        symbol = underlying_symbol.strip().upper()
        try:
            if fetch_on_miss:
                frame = thetadata_adapter.get_eod_chain(symbol, as_of.isoformat(), allow_oos=allow_oos)
            else:
                frame = thetadata_adapter.load_cached_chain(
                    symbol, as_of.isoformat(), allow_oos=allow_oos
                )
        except (FileNotFoundError, ValueError, RuntimeError) as exc:
            raise ProviderError(f"ThetaData chain unavailable for {symbol} @ {as_of}: {exc}") from exc
        if not isinstance(frame, pd.DataFrame):
            raise ProviderError("ThetaData adapter returned a non-DataFrame chain")
        quotes: list[OptionQuote] = []
        for row in frame.to_dict(orient="records"):
            try:
                expiration = date.fromisoformat(str(row["expiration"])[:10])
            except ValueError as exc:
                raise ProviderError("ThetaData returned an invalid expiration") from exc
            right = str(row["right"]).upper()
            contract_symbol = normalize_option_symbol(
                symbol, expiration, right, float(row["strike"])
            )
            quotes.append(
                quote_from_fields(
                    provider=self.name,
                    symbol=contract_symbol,
                    underlying_symbol=symbol,
                    option_type="call" if right == "C" else "put",
                    strike=row["strike"],
                    expiration=expiration,
                    bid=row.get("bid"),
                    ask=row.get("ask"),
                    open_interest=row.get("open_interest"),
                    implied_volatility=row.get("iv"),
                    delta=row.get("delta"),
                    gamma=row.get("gamma"),
                    theta=row.get("theta"),
                    vega=row.get("vega"),
                    quote_timestamp=self._quote_timestamp(as_of),
                    timing=DataTiming.DELAYED,
                    retrieved_at=utc_now(),
                    unavailable_reasons={
                        "last_price": "canonical ThetaData EOD chain stores NBBO and Greeks, not a last trade field",
                        "underlying_price": "canonical chain schema does not contain a synchronized underlying spot",
                    },
                )
            )
        return quotes

    def get_option_quote(
        self, symbol: str, *, as_of: date, allow_oos: bool = False
    ) -> OptionQuote:
        contract = parse_option_symbol(symbol)
        matches = [
            quote
            for quote in self.get_option_chain(
                contract.underlying_symbol, as_of=as_of, allow_oos=allow_oos
            )
            if quote.expiration == contract.expiration
            and quote.option_type == contract.option_type
            and quote.strike == contract.strike
        ]
        if len(matches) != 1:
            raise ProviderError(f"ThetaData contract not uniquely found: {contract.symbol}")
        return matches[0]
