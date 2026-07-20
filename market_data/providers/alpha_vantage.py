"""Official Alpha Vantage supplemental data adapter.

The free tier is deliberately limited to compact daily/equity and
fundamental/news requests. Premium realtime/historical options endpoints are
not called by this adapter unless a future, explicit entitlement is added.
"""
from __future__ import annotations

import os

from market_data.models import DataTiming, ProviderHealth, ProviderResponse
from market_data.providers.base import ProviderBase, payload_dict, utc_now
from market_data.transport import (
    DiskResponseCache,
    HttpJsonTransport,
    JsonTransport,
    ProviderError,
    RateLimiter,
    RetryingJsonTransport,
    UnsupportedFeatureError,
)


class AlphaVantageProvider(ProviderBase):
    name = "alpha_vantage"
    base_url = "https://www.alphavantage.co/query"

    def __init__(
        self,
        api_key: str | None = None,
        *,
        transport: JsonTransport | None = None,
        max_attempts: int = 3,
    ) -> None:
        if transport is None:
            transport = RetryingJsonTransport(
                HttpJsonTransport(
                    cache=DiskResponseCache(".cache/market_data/alpha_vantage"),
                    limiter=RateLimiter(25, 86_400.0),
                ),
                attempts=max_attempts,
            )
        super().__init__(transport)
        self._api_key = api_key

    def _key(self) -> str | None:
        return self._api_key or os.environ.get("ALPHAVANTAGE_API_KEY")

    def _get(self, function: str, **params: object) -> ProviderResponse:
        key = self._key()
        if not key:
            raise ProviderError("ALPHAVANTAGE_API_KEY is not configured")
        request_params = {"function": function, **params, "apikey": key}
        payload = payload_dict(
            self.transport.get_json(
                self.base_url,
                params=request_params,
                cache_namespace=f"{self.name}:{function}",
            ),
            provider=self.name,
        )
        if "Error Message" in payload:
            raise ProviderError("Alpha Vantage rejected the request")
        if "Note" in payload:
            raise ProviderError("Alpha Vantage request limit response")
        return ProviderResponse(
            provider=self.name,
            endpoint=function,
            payload=payload,
            retrieved_at=utc_now(),
            timing=DataTiming.DELAYED,
        )

    def health_check(self) -> ProviderHealth:
        if not self._key():
            return self.missing_credentials(detail="set ALPHAVANTAGE_API_KEY")
        try:
            response = self._get("MARKET_STATUS")
        except ProviderError as exc:
            return ProviderHealth(
                provider=self.name,
                connection_status="failed",
                authentication_status="unknown",
                subscription_status="unknown",
                detail=str(exc),
            )
        return ProviderHealth(
            provider=self.name,
            connection_status="connected",
            authentication_status="accepted",
            subscription_status="free-or-configured",
            detail=f"{response.endpoint} responded; fields are supplemental and delayed-labeled",
        )

    def get_company_overview(self, symbol: str) -> ProviderResponse:
        return self._get("OVERVIEW", symbol=symbol.strip().upper())

    def get_earnings(self, symbol: str) -> ProviderResponse:
        return self._get("EARNINGS", symbol=symbol.strip().upper())

    def get_daily_prices(self, symbol: str, *, outputsize: str = "compact") -> ProviderResponse:
        if outputsize != "compact":
            raise UnsupportedFeatureError(
                "Alpha Vantage full daily history requires a premium key; use compact on free tier"
            )
        return self._get(
            "TIME_SERIES_DAILY", symbol=symbol.strip().upper(), outputsize=outputsize
        )

    def get_news_sentiment(self, symbol: str, *, limit: int = 50) -> ProviderResponse:
        if not 1 <= limit <= 50:
            raise ValueError("free-tier news limit must be between 1 and 50")
        return self._get("NEWS_SENTIMENT", tickers=symbol.strip().upper(), limit=limit)

    def get_option_chain(self, symbol: str) -> ProviderResponse:
        raise UnsupportedFeatureError(
            "Alpha Vantage realtime and historical options endpoints are premium-only; "
            "the supplemental adapter will not spend a free key on them"
        )
