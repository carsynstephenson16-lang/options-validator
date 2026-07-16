# Options-validator × equity-research — bridge proposal

**Date:** 2026-07-15
**Status:** PROPOSAL ONLY. Nothing here is built. Build items are parked with
a gate (see end). Owner requested this investigation this session.
**Evidence base:** read-only subagent map of `~/equity-research` (463 commits
since 2026-05-09, 92 in the last 30 days — actively maintained; all structural
claims below cite its files).

## What the other book actually is

- Systematic single-author equity research: dated memos per ticker under
  `tickers/<TICKER>/`, mechanical validators, verdicts journaled in
  `decisions.md` (40 rows, 25 unique tickers).
- **The asset is the calibration record**: every verdict — including HOLD —
  states `P(beats SPY, 180d)` and gets Brier-scored at T+180
  (`AGENTS.md` §12; `data/calibration.md`, schema v3). First outcomes resolve
  ~2026-11-05; today the record has zero filled T+180 cells.
- **Valuation is multi-method with an anchor-independence audit**
  (`AGENTS.md` §6, §6F): forward DCF, reverse DCF vs base rates, named-peer
  multiples, optional SOTP — each tagged Primary / Independent confirmation /
  Shared-anchor / Tautological in a required method-summary table.
- **Micro-caps already live there**: `scripts/microcap_edgar_kill_screen.py`
  triages ~$20M–$500M names (two cohorts run; ESEA/IBEX/PRCT/IREN graduated to
  full coverage), graded only on 12–24-month permanent-loss outcomes.
- **Zero existing options integration**: greps for option-implied /
  IV / risk-neutral / cross-book across the repo return nothing. Blank
  surface, no conflicting conventions to fight.
- **Ticker overlap today:** VST, CEG, AVGO, NVDA, TEM, CRWV, IREN, USAR,
  HYLN, NOW appear in both books in some form.

## The combination that is honest (and the one that isn't)

The owner's phrase was "engine gate for defining stocks values." The honest
version: **the options market is an independent, tradable-price-derived
opinion about a stock's distribution. Use it as a comparator and a
confirmation anchor — never as the valuation itself.** Three concrete plugs:

### 1. Options-implied anchor row in the §6F method table (equity-research side)

For overlap names with liquid chains, options-validator can produce from its
cached chains: option-implied forward price, implied move to a given date,
and risk-neutral P(price ≤ X by expiry) — the exact readout already parked in
this repo's lot ("Market-implied probability readout", parked 2026-07-09,
still parked). That becomes ONE row in equity-research's method-summary
table, tagged **Independent confirmation** — it shares no anchor with DCF or
multiples, which is precisely what §6F's circularity audit wants. Label
requirement carried over verbatim: **risk-neutral ≠ real-world**, displayed
on every number.

### 2. Brier comparator: analyst P vs market-implied P (the highest-value plug)

Equity-research's scoreable proposition — `P(beats SPY, 180d)` — has a
natural market-implied twin computable from options (the name's and SPY's
option-implied distributions at the ~180d tenor). Logging BOTH probabilities
per verdict, then Brier-scoring both at T+180, answers the question every
calibration record eventually faces: **does the analyst beat the market's
own probability, not just the coin-flip 0.25 baseline?** This is the "engine
gate" worth having: a verdict process that can't outscore the options market
at T+180 is measurably not adding information. Cost: one number logged per
verdict at decision time. Requires: chains for the name (see limits below).

### 3. Event-edge readout shared across books

The Phase E1 descriptive study (implied vs realized earnings moves, promoted
from this repo's lot 2026-07-15) produces per-name event-vol profiles.
Equity-research memos covering the same names get that table as context
(labeled descriptive, never a forecast). One artifact, two consumers.

### The dishonest combination, explicitly declined

Feeding equity-research's discretionary narratives INTO options-validator's
entry gates. This repo rejected chart-quality/narrative scores on 2026-07-07
as discretionary contamination, and its rules route all such judgment to the
equity-research book. The bridge flows **options → equity-research** (hard
numbers into a judgment process), plus at most display-only context back.
Cross-portfolio risk stays where it already lives: the chat-side
cross-book-review ritual.

## Micro-caps: the reality check

Measured in this repo 2026-07-08: HYLN's entire chain was ~128 rows/day and
micro-cap options broadly fail MIN_OPEN_INTEREST/MAX_SPREAD_PCT — under this
cost model there is no tradable micro-cap options output, and most
$20M–$500M kill-screen names have no listed options at all. So: **micro-cap
involvement stays equity-side** (the kill-screen already does this well);
the options plugs above apply only to overlap names with liquid chains
(VST/CEG/NVDA/AVGO today; graduates like IREN only if their chains pass the
same gates). No micro-cap options scanner will be proposed; that idea stays
dead per the parking lot's microcaps note.

## Mechanics (deliberately file-based, no code coupling)

Options-validator writes dated readout files (e.g.
`reports/implied_readouts/YYYY-MM-DD-<TICKER>.md`) from cached chains;
equity-research memos cite them by path as anchor rows / comparator values.
No imports across repos, no shared config, no live data dependency. If the
bridge proves useful, tightening it is a later, separate decision.

## Build items — PARKED pending gates

1. **Risk-neutral readout tool** (this repo): already parked 2026-07-09;
   gate unchanged — owner nod + one-page spec. It is the prerequisite for
   plugs 1 and 2.
2. **Brier comparator logging** (equity-research side): needs the readout
   tool + a one-line schema addition to `data/calibration.md` — that schema
   is governed by equity-research's own validator freeze (no new check
   functions until ≥5 filled T+180 rows, ~2026-11), so the *scored* version
   waits for that freeze to lift; the *logged* number can start earlier if
   the owner types it into the memo template.
3. **Event-edge cross-cite**: free once Phase E1's report exists.

Data caveat binding all three: the ThetaData subscription lapses ~2026-07-29.
Readouts from the cached parquet remain reproducible after lapse, but fresh
chains stop. A ~180d-tenor implied probability for the Brier comparator needs
reasonably current chains — so this bridge either uses cache-as-of dates, or
waits on the renewal decision (gate 2026-07-25).

**Review date:** at the first H5/H6 verdict, at the ThetaData renewal decision
(2026-07-25), or the 2026-10-06 quarterly audit — whichever forces the
question first.
