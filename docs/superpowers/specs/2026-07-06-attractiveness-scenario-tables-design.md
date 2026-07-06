# Attractiveness scenario tables — design

Date: 2026-07-06
Status: approved by owner, ready for implementation plan

## Problem

`options_researcher/attractiveness.py` prints "which options look attractive
today" candidates (sell-a-put, sell-a-covered-call, sell-a-call-against-your-
LEAPS/PMCC, buy-a-LEAPS) to the terminal only. The owner wants an interactive,
readable view of these candidates that also answers "what happens if the
stock hits price X" per candidate, without re-reading dense prose each time.

Scope decision: this covers the **attractiveness candidates only** (the
hypothetical "what if I did this" trades), not the live H5 paper book. The
existing `options_researcher/dashboard.py` ("mission control") already covers
the real book and is untouched by this work.

## Non-goals

- No mid-trade / mark-to-market valuation. Every scenario number is computed
  **at expiration** (or, for PMCC, at the short leg's expiration) using plain
  intrinsic-value math. No Black-Scholes or other pricing model is
  introduced anywhere — the codebase has none today (IV/greeks come from
  ThetaData for *today* only), and adding one would be new predictive
  machinery the project has deliberately avoided everywhere else.
- No monthly re-valuation matrix for LEAPS. Intrinsic value depends only on
  price vs. strike, not on time remaining, so a month-by-month table would
  show identical numbers in every column — that's not a real snapshot, it's
  a rendering bug waiting to happen. LEAPS instead get the same one-time
  scenario table as other structures (dated at LEAPS expiration) plus a
  plain days-remaining / roll-due countdown line.
- No client-side recomputation (no slider, no live JS math). Every value is
  computed once in Python at page-generation time; the page is static HTML,
  consistent with `dashboard.py`'s existing "no JS frameworks, no network"
  constraint.
- No changes to `attractiveness.py`'s existing terminal behavior, its public
  function signatures, or its test coverage. This is purely a new
  presentation layer that reuses its candidate-generation functions.
- No new candidate-generation / suggestion logic. This does not add a
  scanner or optimizer beyond the README roadmap — it only reformats
  candidates the approved `attractiveness.py` already computes.

## Architecture

New module: `options_researcher/attractiveness_dashboard.py`, mirroring the
existing `assemble()` / `render()` / `main()` separation already used by
`dashboard.py`:

- `assemble()` — gathers, per `config.UNIVERSE` symbol: latest cached chain,
  close, `rv21`, `iv_rank`, earnings-in-cycle, holdings/positions (same
  inputs `attractiveness.main()` already loads) and calls the **existing**
  card-builder functions (`put_card_rows`, `cc_card_rows`, `pmcc_card_rows`,
  `leaps_card_rows`) unmodified. Every argument is injectable for tests,
  matching `dashboard.assemble()`'s pattern.
- A shared pure function computes the price ladder and per-structure payoff
  rows for each candidate (see "Scenario math" below). No file I/O, no
  network.
- `render()` — pure string templating into a single self-contained HTML
  string. Reuses `dashboard.py`'s existing dark "mission control" CSS
  (panel/table/pill styling) for visual consistency. Every dynamic value is
  `html.escape`'d.
- `main()` — writes to `.tmp/dashboard/attractiveness.html` and prints the
  path, mirroring `dashboard.main()`. New CLI entry point:
  `uv run python -m options_researcher.attractiveness_dashboard`.

## Scenario math

All payoffs are per single contract (matching how `attractiveness.py`
candidates already compute `credit`/`cost`, which assume 1 contract).

**Price ladder** (shared across structures): given `close` and `rv21`,
`monthly_move = rv21 / sqrt(12)`. Candidate price points are
`close * (1 - 2*monthly_move)`, `close * (1 - monthly_move)`, `close`,
`close * (1 + monthly_move)`, `close * (1 + 2*monthly_move)`, plus the
candidate's own `strike` and (where applicable) `breakeven`. All points are
merged into one ascending, deduplicated list of rows. Rows carry an optional
plain-text tag (`strike`, `breakeven`, `today`) and otherwise show no label,
per owner feedback to drop word/percent annotations — the one relevant date
is shown once in the card header instead of repeated per row.

**Per structure, at expiration:**

- **Short put** (`put_card_rows` candidates): `payoff(price) = credit -
  max(0, strike - price) * 100`.
- **Covered call** (`cc_card_rows` candidates): `payoff(price) = credit +
  100 * (min(price, strike) - close)` — expressed as change vs. today's
  mark (shares called away at strike if price >= strike, else marked at
  the scenario price).
- **PMCC** (`pmcc_card_rows` candidates) — split honestly, since the LEAPS
  leg hasn't expired and its remaining time value isn't modeled:
  - `price >= short_strike`: `(short_strike - leaps_strike) * 100 -
    leaps_cost + credit` (the safety-gate floor; this is a real, model-free
    number because the position can always be closed by exercising the
    LEAPS).
  - `price < short_strike`: `credit` only, with an explicit inline note
    ("just the premium; LEAPS value not counted").
- **LEAPS purchase** (`leaps_card_rows` candidates): `payoff(price) =
  max(0, price - strike) * 100 - cost`, dated at the LEAPS' own expiration.
  Additionally show a plain countdown line: days to expiration and the
  calendar date the roll-due flag activates (`config.H4_THESIS_ROLL_DTE`
  days before expiration) — reusing the existing config constant, no new
  numbers invented.

## Rendering

One card per candidate (id'd by symbol + structure + strike + expiry),
grouped under symbol headers exactly like today's terminal output. Each
card shows:

1. A one-line header: what the trade is, the premium/cost, and "result by
   `<expiry date>` (`<dte>` days out)".
2. The scenario table: `Price | tag | You end up with`, colored green/red
   by sign, sorted ascending by price.
3. The existing plain-language `verdict` sentence and grade badges
   (yield/cushion/liquidity/etc.) carried over unchanged from
   `attractiveness.py`'s card dicts — the table augments this, it doesn't
   replace it.
4. For LEAPS cards only: the days-remaining / roll-due line described above.

Skipped candidates (e.g. covered call below cost basis) and "no candidates
this cycle" messages are carried over verbatim from the existing card dicts.

## Testing

Pure functions (`assemble()`, the scenario-math helper, `render()`) get
`unittest` coverage with injected fixtures, following the existing pattern
in `tests/` for `dashboard.py` and `portfolio.py` — no network, no paid API
calls, runs offline against cached parquet fixtures.
