"""Read-only Massive (formerly Polygon) options adapter."""
from __future__ import annotations

import os
from datetime import date
from urllib.parse import quote

from market_data.models import DataTiming, OptionQuote, ProviderHealth, parse_option_symbol
from market_data.providers.base import (
    ProviderBase,
    as_float,
    payload_dict,
    quote_from_fields,
)
from market_data.transport import (
    DiskResponseCache,
    HttpJsonTransport,
    JsonTransport,
    ProviderError,
    RateLimiter,
)


class MassiveProvider(ProviderBase):
    """Massive REST adapter restricted to market-data GET endpoints."""

    name = "massive"
    base_url = "https://api.massive.com"

    def __init__(
        self,
        api_key: str | None = None,
        *,
        transport: JsonTransport | None = None,
    ) -> None:
        if transport is None:
            transport = HttpJsonTransport(
                cache=DiskResponseCache(".cache/market_data/massive"),
                limiter=RateLimiter(5, 60.0),
            )
        super().__init__(transport)
        self._api_key = api_key

    def _key(self) -> str | None:
        return self._api_key or os.environ.get("MASSIVE_API_KEY") or os.environ.get("POLYGON_API_KEY")

    def _get(self, path: str, params: dict[str, object] | None = None) -> object:
        key = self._key()
        if not key:
            raise ProviderError("MASSIVE_API_KEY or POLYGON_API_KEY is not configured")
        request_params = dict(params or {})
        # Massive documents apiKey query authentication. The cache removes
        # this sensitive parameter from its content-addressed key and files.
        request_params["apiKey"] = key
        return self.transport.get_json(
            f"{self.base_url}{path}", params=request_params, cache_namespace=self.name
        )

    def health_check(self) -> ProviderHealth:
        if not self._key():
            return self.missing_credentials(detail="set MASSIVE_API_KEY (POLYGON_API_KEY is a fallback)")
        try:
            payload = payload_dict(self._get("/v1/marketstatus/now"), provider=self.name)
        except ProviderError as exc:
            return ProviderHealth(
                provider=self.name,
                connection_status="failed",
                authentication_status="unknown",
                subscription_status="unknown",
                detail=str(exc),
            )
        status = str(payload.get("status", "")).lower()
        if status in {"error", "unauthorized", "forbidden"} or "error" in payload:
            return ProviderHealth(
                provider=self.name,
                connection_status="connected",
                authentication_status="rejected",
                subscription_status="unknown",
                detail="provider rejected the configured credential",
            )
        return ProviderHealth(
            provider=self.name,
            connection_status="connected",
            authentication_status="accepted",
            subscription_status="unknown",
            detail="read-only market-status endpoint responded",
        )

    def get_contracts(
        self,
        underlying_symbol: str,
        *,
        expiration: date | None = None,
        limit: int = 1000,
    ) -> list[dict[str, object]]:
        if not 1 <= limit <= 1000:
            raise ValueError("Massive contract limit must be between 1 and 1000")
        params: dict[str, object] = {
            "underlying_ticker": underlying_symbol.strip().upper(),
            "limit": limit,
            "order": "asc",
            "sort": "expiration_date",
        }
        if expiration is not None:
            params["expiration_date"] = expiration.isoformat()
        payload = payload_dict(self._get("/v3/reference/options/contracts", params), provider=self.name)
        results = payload.get("results", [])
        if not isinstance(results, list):
            raise ProviderError("Massive contracts response has a non-list results field")
        return [row for row in results if isinstance(row, dict)]

    def get_option_chain(
        self, underlying_symbol: str, *, expiration: date | None = None
    ) -> list[OptionQuote]:
        """Return contract identities; Basic does not promise live chain fields."""

        quotes: list[OptionQuote] = []
        for row in self.get_contracts(underlying_symbol, expiration=expiration):
            symbol = str(row.get("ticker", ""))
            contract = parse_option_symbol(symbol)
            quotes.append(
                quote_from_fields(
                    provider=self.name,
                    symbol=contract.symbol,
                    underlying_symbol=contract.underlying_symbol,
                    option_type=contract.option_type,
                    strike=contract.strike,
                    expiration=contract.expiration,
                    timing=DataTiming.DELAYED,
                    unavailable_reasons={
                        "quote": "Massive Options Basic contract reference does not include a current quote",
                        "greeks": "Massive Options Basic does not promise Greeks or IV",
                        "open_interest": "Massive Options Basic does not promise open interest",
                    },
                )
            )
        return quotes

    def get_option_quote(self, symbol: str) -> OptionQuote:
        contract = parse_option_symbol(symbol)
        encoded_symbol = quote(contract.symbol, safe="")
        payload = payload_dict(
            self._get(f"/v2/aggs/ticker/{encoded_symbol}/prev"), provider=self.name
        )
        result = payload.get("results")
        if not isinstance(result, dict):
            raise ProviderError(f"Massive returned no previous-day bar for {contract.symbol}")
        return quote_from_fields(
            provider=self.name,
            symbol=contract.symbol,
            underlying_symbol=contract.underlying_symbol,
            option_type=contract.option_type,
            strike=contract.strike,
            expiration=contract.expiration,
            last_price=result.get("c"),
            volume=result.get("v"),
            quote_timestamp=result.get("t"),
            timing=DataTiming.DELAYED,
            unavailable_reasons={
                "bid": "Massive Options Basic previous-day bar has no NBBO bid",
                "ask": "Massive Options Basic previous-day bar has no NBBO ask",
                "open_interest": "Massive Options Basic does not promise daily open interest",
                "implied_volatility": "Massive Options Basic does not promise IV",
                "greeks": "Massive Options Basic does not promise Greeks",
                "underlying_price": "previous-day option bar does not include the underlying close",
            },
        )

    def get_underlying_previous_day(self, symbol: str) -> float | None:
        payload = payload_dict(
            self._get(f"/v2/aggs/ticker/{quote(symbol.strip().upper(), safe='')}/prev"),
            provider=self.name,
        )
        result = payload.get("results")
        return as_float(result.get("c")) if isinstance(result, dict) else None
