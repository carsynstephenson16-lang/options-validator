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
- **PMCC enrichment.** `pmcc_card_rows()`'s returned dicts carry only
  `strike/expiry/dte/credit/yield_mo/grades/verdict` — they omit the
  `leaps_strike`/`leaps_premium` the PMCC scenario math needs. `assemble()`
  therefore rebuilds `held_leaps` the same way `attractiveness.main()` does
  (`symbol -> (leaps_strike, leaps_entry_price)` from the positions frame)
  and attaches `leaps_strike` + `leaps_cost` (= `leaps_premium * 100`) to
  each PMCC card before handing it to the scenario-math helper. The
  card-builder functions themselves stay unmodified.
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
`monthly_move = rv21 / sqrt(12)`. When `monthly_move` is valid
(finite and > 0) the candidate price points are
`close * (1 - 2*monthly_move)`, `close * (1 - monthly_move)`, `close`,
`close * (1 + monthly_move)`, `close * (1 + 2*monthly_move)`, plus the
candidate's own `strike` and (where applicable) `breakeven`.

**Invalid / missing vol.** `rv21` can be missing or non-positive, in which
case `attractiveness.py` already yields a non-finite monthly move
([attractiveness.py:58](../../../options_researcher/attractiveness.py#L58)).
When `monthly_move` is not finite or `<= 0`, drop the ±move points entirely
and build the ladder from just `close`, `strike`, and (where applicable)
`breakeven` — never invent price points from a bad vol number.

**Rounding / sanity.** Round every ladder price to cents before use;
deduplicate rows by the rounded-cents value; drop any non-positive price
(a stock can't trade at or below $0, and `close * (1 - 2*monthly_move)`
can go negative for a high-vol name). All surviving points are merged into
one ascending list of rows. Rows carry an optional plain-text tag
(`strike`, `breakeven`, `today`) and otherwise show no label, per owner
feedback to drop word/percent annotations — the one relevant date is shown
once in the card header instead of repeated per row.

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
2. The scenario table: `Price | tag | Your gain or loss`, colored green/red
   by sign, sorted ascending by price. The column reads "Your gain or loss"
   (not "You end up with") because every cell is a P&L delta, not a single
   cash-account ending balance — the numbers mix option-only P&L (put),
   share-movement-vs-today (covered call), and the PMCC credit-only /
   safe-floor split, so the label must not imply one uniform ending value.
   The wording stays plain per the owner's less-jargon constraint (no
   literal "P&L" abbreviation in the UI).
3. The existing plain-language `verdict` sentence and grade badges
   (yield/cushion/liquidity/etc.) carried over unchanged from
   `attractiveness.py`'s card dicts — the table augments this, it doesn't
   replace it.
4. For LEAPS cards only: the days-remaining / roll-due line described above.

**Skipped and no-candidate cases are different shapes — handle them
separately.** A skipped covered call is a real card dict carrying a
`"skipped"` string ([attractiveness.py:104-108](../../../options_researcher/attractiveness.py#L104-L108));
render it as a plain one-line note with **no scenario table, no expiry
header, no payoff chart**. The "no candidates near the target delta this
cycle" case is not card data at all — it is a bare `print` in the terminal
path ([attractiveness.py:281-282](../../../options_researcher/attractiveness.py#L281-L282));
in the HTML it surfaces as an empty-state line under that structure's
heading, again with no table or header. Only fully-formed candidate dicts
(those with `strike`/`expiry`/`credit`-or-`cost`) get scenario tables and
expiry headers.

## Testing

Pure functions (`assemble()`, the scenario-math helper, `render()`) get
`unittest` coverage with injected fixtures, following the existing pattern
in `tests/` for `dashboard.py` and `portfolio.py` — no network, no paid API
calls, runs offline against cached parquet fixtures.
