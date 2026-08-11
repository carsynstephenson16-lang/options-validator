# Short-positioning context — design spec (Phases 1–4)

**Date:** 2026-08-11
**Status:** display-only instrumentation, disabled by default.
**Not** a hypothesis, not a registration, not a signal, not verdict-bearing.
Promotion beyond experimental status requires a separate owner decision and
every applicable registration or feasibility gate (2026-07-24).

Data contract: `docs/data/short-positioning-contract.md`.
Claim ledger: `reports/2026-08-11-short-positioning-claim-ledger.md`.

## 1. What is being built and why

The repository has no view of how heavily its watchlist names are shorted.
This adds one: a provider-neutral subsystem that captures FINRA Consolidated
Short Interest to local storage, validates it hard, and shows it in a separate
`EXP-SHORT` lane on the display-only experiments dashboard.

The point is instrumentation, not edge. A future study would need its own
registration; nothing here anticipates one.

## 2. Architecture

A provider-neutral subsystem inside the existing modular monolith:

```text
tools/short_positioning_capture.py     operator CLI, dry-run by default
  -> data/short_positioning/providers/finra.py   request build + parse + normalize
  -> data/short_positioning/raw_store.py         immutable raw bytes + SHA-256
  -> data/short_positioning/normalize.py         atomic normalized partitions
tools/short_positioning_audit.py       offline audit, never repairs
  -> data/short_positioning/audit.py
data/short_positioning/identity.py     effective-dated aliases
data/short_positioning/snapshots.py    causal as-of resolution
  -> options_researcher/short_positioning_context.py   card build + render
  -> options_researcher/exp_short_positioning.py       EXP-SHORT lane
  -> options_researcher/experiments_dashboard.py       lane registration
```

Acquisition and display are strictly separated. The display path imports no
provider module and makes zero network calls. Ranking, strategy, book,
verdict, and live-order code import none of the above.

## 3. Phase boundaries

| Phase | Delivers |
|---|---|
| 1 | Normalized v1 schemas, synthetic fixtures, contract and claim ledger |
| 2 | FINRA adapter, raw store, normalization, capture CLI (dry-run default) |
| 3 | Identity resolution, causal snapshot resolution, offline audit |
| 4 | `EXP-SHORT` display lane, disabled by default |

Phases 5 and beyond (S&P adapters, forward accumulation, `SI-RQ1`
pre-registration, research runner, promotion) are out of scope and unbuilt.

## 4. Point-in-time discipline

`available_at` is publication date 16:40 America/New_York in UTC;
`available_session` is the next XNYS session from the exchange calendar. A
record that is not available at the requested as-of timestamp is refused with
`FUTURE_DATA` — it is never shown as pending-but-known. Revisions are
additional immutable captures, never overwrites. Current float never backfills
a historical denominator. `max_asof` is the latest causal timestamp among all
inputs; the settlement date never supplies it.

## 5. Failure behaviour

Every failure is visible. The status taxonomy and precedence live in the data
contract, section 8. The rules that matter most:

- Missing data never inherits a prior value ("last good" is forbidden).
- A missing value never becomes zero.
- A malformed payload renders a visible `SCHEMA_ERROR` card, not an empty lane.
- A license failure renders `LICENSE_BLOCKED`, never empty metrics labelled `OK`.
- An exception inside the lane becomes a visible error card.

## 6. Display

Lane heading `EXP-SHORT` / `Short positioning context`, with the exact
lane text, card caveat, and days-to-cover note fixed in
`options_researcher/short_positioning_context.py` and asserted by tests.

Visual rules: no directional green or red; neutral styling for valid metrics;
amber for stale, revised, float-unavailable, and pending; red reserved for
integrity failures (schema, hash, future data, missing provenance, partial
capture, license). No bull, bear, squeeze, edge, opportunity, warning, or
conviction wording. Every provider-controlled string is HTML-escaped.

## 7. Configuration

```python
EXP_SHORT_ENABLED = False
SHORT_POSITIONING_ROOT = ".cache/short_positioning"
SHORT_POSITIONING_MAX_AGE_RELEASES = 1
SHORT_POSITIONING_PROVIDER_ORDER = ("finra",)
```

`SHORT_POSITIONING_MAX_AGE_RELEASES` is a display-health setting, not a
predictive threshold: beyond one missed release the card reads `STALE`.

## 8. Invariance guarantees (tested)

With `EXP_SHORT_ENABLED = False`:

1. Production attractiveness ranking objects are unchanged.
2. Top-3 selection is unchanged.
3. The experiments artifact contains no `EXP-SHORT` text and is byte-identical
   for identical inputs.
4. Existing experiment lanes are semantically unchanged.
5. Strategy, ranking, book, verdict, and live-order modules import no
   short-positioning module.

## 9. Rollback

1. Operational rollback: keep `EXP_SHORT_ENABLED = False`. The lane disappears
   with no other effect.
2. Before merge: leave the branch unmerged.
3. After a future merge: `git revert` the single implementation commit.
4. Stored raw captures are untouched by any rollback; normalized partitions can
   be rebuilt from immutable raw artifacts.
5. No data migration, strategy rollback, ranking repair, or book repair is
   required — this subsystem owns no strategy or book state.
