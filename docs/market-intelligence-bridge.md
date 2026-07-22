# Equity-research market-intelligence bridge

`equity-research` owns the free-source ingestion service and its append-only
SQLite evidence store. `options-validator` only reads that store through
`options_researcher.market_context.get_recent_market_context`.

The reader never makes a network call and never changes a strategy, a position,
a watchlist, or an order. Callers must provide a timezone-aware `as_of` value;
the query filters on `published_at <= as_of`, never on retrieval time. This
keeps historical studies from seeing future news.

The default producer path is the sibling checkout:

```text
../equity-research/.local/market_updates/market_updates.sqlite3
```

Set `EQUITY_RESEARCH_MARKET_UPDATES_DB` to use another location, especially in
CI or when the repositories are not siblings.

```python
from datetime import datetime, timedelta, timezone

from options_researcher.market_context import get_recent_market_context

context = get_recent_market_context(
    {"VST", "CEG"},
    as_of=datetime(2026, 7, 20, 20, 0, tzinfo=timezone.utc),
    lookback=timedelta(days=7),
)
```

The returned evidence is descriptive context only. It cannot authorize an H5,
H6, H7, or H8 action and is not a substitute for their existing frozen,
receipt-bearing data sources.
