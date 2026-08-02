"""Research-only ThetaData option trade-flow primitives.

This package is deliberately separate from the canonical EOD chain cache and
is never imported by ranking, scoring, or order-routing paths.
"""

from .normalize import NORMALIZED_COLUMNS, RAW_TRADE_QUOTE_COLUMNS

__all__ = ["NORMALIZED_COLUMNS", "RAW_TRADE_QUOTE_COLUMNS"]
