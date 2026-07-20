"""Common provider boundary and explicit fallback order."""
from __future__ import annotations

from datetime import date
from typing import Protocol, runtime_checkable

from market_data.models import OptionQuote, ProviderHealth


@runtime_checkable
class MarketDataProvider(Protocol):
    name: str

    def health_check(self) -> ProviderHealth: ...

    def get_option_chain(
        self, underlying_symbol: str, *, expiration: date | None = None
    ) -> list[OptionQuote]: ...


DEFAULT_PROVIDER_ORDER = (
    "schwab",
    "thetadata",
    "massive",
    "alpha_vantage",
)


def provider_order() -> tuple[str, ...]:
    """Return the frozen default order; callers still must inspect freshness."""

    return DEFAULT_PROVIDER_ORDER
