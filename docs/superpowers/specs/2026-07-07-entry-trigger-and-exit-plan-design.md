# Entry trigger, ThetaData exit, and scanner polish — design (2026-07-07)

**Status: APPROVED by owner 2026-07-07.** Five tracks survived a triage of a
larger idea list; everything else was parked or rejected (see "Triage record"
at the bottom — rejections are recorded so they are not re-litigated).

Owner context driving this design: the current phase is *waiting for a LEAPS
entry*. The owner wants frozen entry triggers (VST ≤ $140, AMZN ≤ $220, both
IV-aware), daily PMCC scanning only after an entry exists, scheduled-event
awareness, a clean repo with automatic commits, and a plan for canceling the
ThetaData subscription (~2026-07-25) without losing anything.

## Track 1 — ThetaData exit plan (deadline ~2026-07-25)

Finding: **no bulk history pull is needed.** The cache already holds full
daily EOD chains (every strike, every expiration) for all four names through
the most recent finalized day; the parked enrichment ideas' raw material
(IV term structure, event windows) is derivable from that cache offline.

Deliverables:

1. `docs/superpowers/2026-07-07-thetadata-cancel-checklist.md` — the
   cancel-day checklist:
   - run `uv run python data/recent_topup.py` one final time (it catches all
     missing days in a single run);
   - confirm the audit prints PASS (with-warnings acceptable per the
     established deep-ITM IV=0 pattern);
   - append a `THETADATA_CANCEL` line to `ledger/facts.log` recording the
     final cache extent per symbol;
   - cancel the subscription.
2. A ledger line **now** pre-declaring the plan: cancel on schedule;
   trigger-watching uses free underlying closes only; re-subscribe for one
   month when a trigger fires (to price the entry with audited data), then
   re-evaluate whether ongoing chain data is worth paying for during the
   holding period (actual short-call cadence is monthly, and broker quotes
   are free at execution time).

## Track 2 — Pre-registered LEAPS entry trigger

New frozen constants in `config.py` (H5 block; no magic numbers elsewhere):

```python
H5_ENTRY_TRIGGERS = {"VST": 140.0, "AMZN": 220.0}  # close at/below → evaluate
H5_ENTRY_IVR_MAX = 0.5   # and IV-rank at/below its own median
```

Rule text (appended to `ledger/facts.log` BEFORE any entry exists, per
pre-registration discipline):

> Evaluate (never auto-enter) a 0.70Δ LEAPS per H5 CORE rules on a name when
> ALL of: (a) underlying close ≤ its `H5_ENTRY_TRIGGERS` level, (b) IV-rank
> ≤ `H5_ENTRY_IVR_MAX`, (c) the candidate LEAPS passes the frozen liquidity
> gates (OI ≥ MIN_OPEN_INTEREST, spread ≤ MAX_SPREAD_PCT). At most one LEAPS
> is entered first. The tool alerts; the owner records any entry manually in
> `data/positions/positions.csv`. Rationale note: the IV condition exists
> because a pullback lowers the stock price but typically raises IV — a
> price-only trigger can deliver a cheap stock with an expensive option.
> `H5_ENTRY_IVR_MAX` is 0.5 (not the GREEN 0.3) because demanding a fresh
> pullback AND bottom-tercile IV simultaneously risks a trigger that can
> never fire.

New CLI `options_researcher/entry_watch.py` (`uv run python -m
options_researcher.entry_watch`):

- For each name in `H5_ENTRY_TRIGGERS`: latest underlying close (free
  source — `data/underlying_closes.py`, `allow_oos=True`), latest IV-rank
  from the feature layer, and the best 0.70Δ LEAPS candidate's liquidity
  status from the latest **cached** chain (clearly labeled with the chain's
  as-of date, since chains go stale after the subscription cancels).
- Prints one line per name with a **WAIT** or **FIRE** verdict and which
  condition(s) are unmet. FIRE means "evaluate now", never "buy".
- Read-only; never writes positions; unit-tested with injected frames
  (offline, no network).
- The dashboard watch cards show the same trigger status.

## Track 3 — FOMC scheduled-event flag

- `data/events/fomc_dates.csv`: FOMC meeting dates through 2027 from the
  Federal Reserve's published calendar (Official-source; URL in the file
  header). Static file, no network at runtime.
- A loader in the events/earnings layer plus an AMBER "FOMC meeting inside
  this option's cycle" flag on scanner cards, following the existing
  earnings-flag pattern exactly.
- **Descriptive only. It never gates, scores, or ranks a candidate.**
- Explicitly out of scope: general news watching, Fed-speech parsing,
  institutional-flow alerts (see Triage record).

## Track 4 — Repo cleanup + commit policy

- Commit the outstanding `ledger/facts.log` append (append-only; never
  rewritten).
- Merge `feat/recent-topup-tool` (21 commits) into `main` after the owner's
  merge-judgment gates pass: CI green on the branch, no concurrent-session
  churn on `origin/main`.
- The parked `data-layer` branch is kept. No published history is ever
  rewritten.
- **Commit policy going forward:** the agent commits automatically whenever
  a unit of work is complete and tests are green ("done and green = commit"),
  with conventional-commit messages. The owner does not need to manage
  commit timing.

## Track 5 — LEAPS card Greeks enrichment (descriptive)

The cached chains carry `iv`, `delta`, `gamma`, `theta`, `vega` per
contract; today's LEAPS card only surfaces delta and a derived theta-per-day
line. Add plain-English lines to the LEAPS and tactical long-call cards:

- vega: "if implied vol drops 1 point, this option loses ~$X" (vega × 100);
- IV: the contract's own implied vol, next to the name-level IV-rank already
  shown;
- gamma omitted from prose (not decision-relevant at 365-DTE for a beginner;
  avoid noise) unless review argues otherwise.

Constraints: display only — no new grades, no gate changes, no ranking
changes; the frozen H5 rubric is untouched. Unit-tested like the existing
card builders.

## Sequencing

1. Track 4 first (clean base, merge to main), then a fresh feature branch.
2. Tracks 2 → 3 → 5 as test-driven units, each auto-committed when green.
3. Track 1 is a doc + ledger line now, and a calendar-day action ~07-25.

## Testing

Every new code path (entry_watch, FOMC loader/flag, Greeks lines) gets
offline unittest coverage with injected data, consistent with the existing
suite (370 tests green as of 2026-07-07). No network, no paid API calls in
tests.

## Triage record (owner decisions 2026-07-07)

- **Approved:** the five tracks above.
- **Still parked** (owner chose not to unpark): IV term-structure badge;
  earnings implied-vs-realized-move badge. Their raw data is already in the
  local cache, so the ThetaData cancellation does NOT kill them.
- **Rejected:** real-time institutional/hedge-fund selling alerts (13F data
  is quarterly and up to 45 days delayed — Official-source: SEC Form 13F;
  no usable real-time signal exists, and the parking lot already bars
  narrative contamination); general news-watching pipeline (discretionary
  noise; belongs in the equity-research repo if anywhere); Greeks-based
  "best price" predictor (violates attractiveness ≠ prediction);
  multi-project launcher hub (fine idea, separate repo, parked as its own
  future mini-project).
