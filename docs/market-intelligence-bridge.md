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

## Relationship to the parked 2026-07-15 bridge proposal

These are two different bridges and only one of them is live.

| | direction | status |
|---|---|---|
| This reader (`market_context`) | equity-research → options-validator, read-only descriptive context | **BUILT and RETAINED** (owner decision 2026-07-22, commit `4082141`) |
| The 2026-07-15 proposal | options-validator → equity-research (options-implied anchor row, Brier comparator, event-vol tables) | **still PARKED** — see `ideas-parking-lot.md` and `reports/2026-07-15-options-equity-research-bridge-proposal.md` |

The parked proposal's prerequisite (a market-implied probability readout) and
its review date are unchanged by this reader. Nothing here starts that work.

Retention terms, so "descriptive only" stays checkable rather than asserted:

- **Zero callers.** No strategy, trigger, watcher, gate, receipt path, or test
  outside `tests/test_market_context.py` imports it. Verified 2026-07-22.
- Wiring it into a gate, trigger, or grading path is a **new scope decision**
  and would need owner-typed pre-registration first — the 2026-07-15 proposal
  explicitly declined narratives-into-options-gates as discretionary
  contamination, and that decline still stands.
- If it ever acquires a caller on a decision path without that registration,
  the correct move is to remove the caller, not to re-scope the reader.
