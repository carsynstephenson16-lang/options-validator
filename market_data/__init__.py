"""Read-only, provider-neutral market-data primitives.

The package is intentionally separate from the canonical H7/ThetaData cache
path.  It is suitable for development-time provider comparison and never
contains order-routing methods.
"""

from market_data.interface import DEFAULT_PROVIDER_ORDER, MarketDataProvider, provider_order
from market_data.models import (
    DataQualityStatus,
    DataTiming,
    OptionQuote,
    ProviderHealth,
    ProviderResponse,
    ValidationStatus,
    compute_midpoint,
    normalize_option_symbol,
    parse_option_symbol,
)
from market_data.validation import ValidationResult, validate_chain, validate_quote

__all__ = [
    "DataQualityStatus",
    "DataTiming",
    "OptionQuote",
    "ProviderHealth",
    "ProviderResponse",
    "ValidationStatus",
    "compute_midpoint",
    "normalize_option_symbol",
    "parse_option_symbol",
    "DEFAULT_PROVIDER_ORDER",
    "MarketDataProvider",
    "ValidationResult",
    "provider_order",
    "validate_chain",
    "validate_quote",
]
