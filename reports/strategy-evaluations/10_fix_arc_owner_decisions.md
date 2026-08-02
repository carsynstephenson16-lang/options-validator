# 10 — Fix arc: consolidated owner decision package

**Read-only investigation complete. No fix code written. Nothing registered.**

Date: 2026-07-30
Tree investigated: `sfix` @ `40a6b21` (clean)
Inputs: [`08_repo_verification.md`](08_repo_verification.md) (C1–C11 verification),
[`09_session5_refetch_gate.md`](09_session5_refetch_gate.md) (refetch scope), plus five
delegated read-only investigations (Sessions 2, 3, 4, 6, 7), each spot-checked
against the code by the orchestrating session before entering this document.

Every claim below was re-derived independently. Where a delegated finding was
wrong, the correction is stated in place and labelled.

---

## 0. The finding that changes how every session must be run

**The 2,139-test suite does not merely fail to catch these defects. In four
places it actively certifies them as correct behaviour.**

| Test | What it pins | Verified |
|---|---|---|
| `tests/test_core.py:293` | Asserts `return_on_economic_max_loss == 30.0/110.0` — the defective sum-over-mean value | Read directly |
| `tests/test_core.py:28-34` | Asserts `entry_credit_conservative` equals the raw unrounded formula | Read directly |
| `tests/test_pandas_feed.py:105-119` | Asserts `len(feed[key].df) == 2` — that the pre-admission day is retained — with a comment justifying it | Read directly |
| `tests/test_h6_watch.py:467-513` | Fixtures use `$1,000 × 2 = $2,000` (exactly the cap) and same-month entry/exit, so neither half of the H6 defect can manifest | Read directly |

**Operational consequence, and it is not optional:** "the suite is green" cannot
be the acceptance signal for Sessions 3, 4, or 6. Each of those fixes must
**first turn a currently-green test red on purpose**, and the changeset must
update the pinned assertion as part of the fix. Any Codex brief that does not
name the specific test it is expected to break is an incomplete brief, because
the implementer will otherwise read the red test as their own bug.

This is the concrete form of the warning in `08_repo_verification.md` §8.

---

## 1. Decisions, in dependency order

Nothing below is a proposal. Every value is yours to type. Where the delegated
work reached a defensible engineering conclusion that involves **no registered
number**, it is marked *no owner input needed* and moves straight to a brief.

### D1 — Target branch for the whole fix arc  ⟵ blocks everything

`sfix` @ `40a6b21` (verified tree) vs `main` @ `f9f7d31` (36 commits ahead).
The files the fixes touch are byte-identical today. They will not stay that way.

| Option | For | Against |
|---|---|---|
| Land on `main` | Where the work ultimately belongs; CI actually runs there (see D9) | Requires re-verifying against main's newer `thetadata_adapter.py` |
| Land on `sfix` | Matches the verified tree exactly | 36 commits of drift to reconcile later; CI does not run on this branch at all |
| New branch off `main` | Clean; CI runs on PR | One more re-verification pass |

**This must be answered before any code is written, not after.**

---

### D2 — Session 2: the causal clock (P0)

The clock fix has one hard constraint the investigation settled: **filling at
the next day's open is not possible.** The cache stores exactly one
end-of-day snapshot per contract per day (`data/thetadata_adapter.py:203-205`);
there is no opening quote to fill against. Any convention requiring intraday
data needs new paid ThetaData calls and a new cache schema.

| Slot | What it controls | Candidates | What breaks if wrong |
|---|---|---|---|
| **D2a Fill-day convention** | Which day's chain prices a decided trade | (i) signal D → fill D+1 EOD chain *(only option feasible on current data)*; (ii) restamp bars to publication time and let the next session decide; (iii) explicit two-clock model separating "content date" from "actionable timestamp" | (ii) risks stamping bars outside Lumibot's 09:30–16:00 ingestion window, which the 2026-07-03 spike found necessary — could break bar ingestion instead of fixing the clock. **UNVERIFIED** — needs a runtime probe |
| **D2b DTE reference day** | Which date is subtracted from expiration to gate `A_TARGET_DTE` | signal day / fill day | Shifts which expirations clear the band at the margin — silently changes the tradeable set, not just its timing |
| **D2c `entry_date`/`exit_date` meaning** | What `metrics.scoreboard`, the weekly-cohort bootstrap, and every future ledger record treat as "when this happened" | decision day / fill day | Redefining this field without renaming it corrupts comparison against existing records |
| **D2d Chunk-boundary day identity** | `entry_cutoff` / `blocked_until` in `harness/run_backtest.py:36-49` | keyed to decision day / fill day | The riskiest site in the fix. A seam entry could require a fill quote from the next chunk — or past `IN_SAMPLE_END`, which is sealed holdout |
| **D2e Invariant enforcement point** | Where `fill_ts > data_available_at` is asserted at runtime | `on_filled_order` / feed construction / both | Unit tests alone are exactly the gap §0 describes |

**Boundary case you must resolve explicitly (D2d):** a decision made *on*
`IN_SAMPLE_END` (2022-12-31) would need to fill on 2023-01-01 — which raises
`OOSDataTouchError` by design. The chunking already reserves `MAX_HOLD_DAYS`
before the window end for exits; whether it also absorbs the fill-day offset is
a design call, not a mechanical one.

**Correction to the delegated finding.** The Session 2 investigation concluded
that landing this fix *"permanently forecloses OOS-reveal for H1 and H2."* The
reasoning is sound — `research/hashing.py` hashes `data`, `harness`,
`strategies`, `metrics.py`, `config.py`, and `research/experiments.py:276`
refuses a reveal on any drift. **But I ran the gate against the live ledger and
that door is already shut:**

| | H1 registered | Current tree | Match |
|---|---|---|---|
| `source_hash` | `c3925cf9…` | `c304f288…` | **No** |
| `config_hash` | `8ad8a17b…` | `bbf1db4a…` | **No** |
| `cost_model_hash` | `af71c7f6…` | `af71c7f6…` | Yes |

H1 and H2 both fail the drift check **today, before any fix**, from unrelated
repo evolution. This is therefore **not a new cost of the fix** and creates no
urgency to reveal anything first. It is also not irreversible in principle —
the hash is computed from files on disk and re-derives from a clean checkout of
the registered commit (this repo has already retracted one false alarm on
exactly this point).

**D2f — the real registration question that remains:** re-testing this strategy
under a corrected engine is not a parameter amendment. The ledger is write-once
with no amendment path for a code hash, so it is effectively a **new hypothesis
registration** — owner-typed. No IDs or numbers proposed here.

---

### D3 — Session 3: one canonical pricing path

**No owner input needed. Proceeding to a full Codex brief.**

Every constant stays exactly as registered. The fix is "compute the credit
through the same rounding function the engine already fills at" — pure logic
consistency, not calibration. Recorded here only so the absence of a decision
is deliberate rather than an oversight.

Two facts worth your attention anyway:

**The breach is five times larger than the Session 1 example.** Re-derived
independently with the repo's own functions across the registered width sweep:

| Width | Worst breach | % of cap | Contracts |
|---:|---:|---:|---:|
| $1 | **$12.80** | 2.13% | 8 |
| $2 (production) | **$6.40** | 1.07% | 4 |
| $5 | none found | — | — |

*(Correction: the delegated table listed the width-$2 long leg as `6.35/6.40`;
that combination does not breach. The actual worst case is `6.30/6.35` — the
leg was priced off the bid rather than the ask in that one row. The breach
magnitude was right; the quote was mistranscribed, and it was headed into a
test fixture.)*

Unconstrained, the mechanism has no structural bound: as the long leg
approaches worthless, the sizing denominator collapses toward the round-trip
commission floor, permitting **228 contracts and a $448.80 breach — 74.8% over
the cap**. Not a realistic 30-delta quote, but it establishes that the cap is
protected by nothing except the quotes happening to be sane.

**The fix is one-directional and will shrink your sample.** Adverse rounding
only ever moves the credit down, which only ever moves required capital up,
which can only reduce the contract count. It can turn currently-accepted trades
into rejections. It can never create a trade. If this path ever feeds a new
loss-gated registration, that rejection count is an input to the registration
feasibility gate (`docs/superpowers/2026-07-24-registration-feasibility-gate.md`).

**You have already solved this once.** `strategies/h7_lanes.py:63-73` routes H7
through the canonical transform, citing "7b-2R finding 5." H1/H2 is the single
path never migrated. This is finishing a migration, not new design.

---

### D4 — Session 4: feed inclusion (future-delta)

**Priority downgrade, on measurement.** The delegated investigation measured
real cached 2022 data across all four core names and found:

- The defect is real and common — **~1 in 5** admitted contracts (2,445 of
  12,011; 27,117 rows) enter the feed *only* because a later day's delta pulled
  them into band.
- **It never reached a real trade.** Of **310 accepted trade selections**
  (MSFT and AMZN; VST and CEG accepted none in 2022), **zero** had a leg
  admitted on future information. The reason is structural: the strategy picks
  a ~0.30-delta short leg, comfortably inside the 0.03–0.65 band, and a $1–$5
  long leg barely moves from it.

So the repo's own defense (`data/pandas_feed.py:20-25`) holds **empirically for
this strategy on this data** — which makes C3 the lowest-urgency confirmed
defect, not the P1 it looked like.

**What still bites:** whether a backtest *crashes* is decided with future
information. If a needed leg never touches the band anywhere in the window the
run dies loudly; if a later selloff pulls it in, the same code trades instead.
Future data deciding a present-day pass/fail.

**Scope caveats, stated plainly:** 2022 only, puts only, four names, and H7/H8
were never traced — they call the same admission function with different deltas
and both rights.

| Slot | Candidates | Note |
|---|---|---|
| **D4a Fix approach** | (a) point-in-time — truncate the prefix before first in-band day; (b) static identity — evaluate inclusion once from first-observation attributes; (c) admit everything, let liquidity gates filter | Architecture decision, no number to type. (a) is cheapest and keeps contract counts unchanged; (c) costs the most (raw chains are 500K–1.2M rows per symbol-year vs 2.4K–9.2K admitted contracts today) |
| **D4b Priority** | Keep at Session 4 / defer behind Sessions 2, 3, 6 | On the measurement above, deferring is defensible |

`FEED_PUT_DELTA_BAND` and `FEED_CALL_DELTA_BAND` need **no value change** under
(a) or (c). Under (b) they may become dead config.

**Implementation trap for whoever writes this (must be in the brief):** fix (a)
must truncate a **prefix only**. Dropping individually out-of-band days scattered
through the middle would create interior gaps and let Lumibot forward-fill stale
quotes into them — trading one bug for another. That hazard is precisely why
the current design exists.

---

### D5 — Session 5: cache schema v2 + refetch

Fully scoped in [`09_session5_refetch_gate.md`](09_session5_refetch_gate.md).
Headline: **31,367 cached symbol-days, ~2.95 GB, ≈62,734 provider calls** for a
full refetch. Subscription is live through 2026-11-30, but your own standing
rule (ledger, 2026-07-16) is that renewal *"does NOT authorize paid pulls —
per-pull owner approval."*

**Not a blocker on Session 2.** Availability time can be derived as a constant
per chain-date (17:15 ET) without any new column. Schema v2 is what converts
that **Assumption** into a verified fact — a strengthening reason, not a
blocking one.

Decisions: refetch authorization · scope · v2 column set · v1 disposition ·
timing. Table in `09_…` §5.

---

### D6 — Session 6: metrics + H6

**A research-integrity decision sits inside this one — see D8.**

| Slot | Candidates | Note |
|---|---|---|
| **D6a Denominator convention** | `sum/sum` (dollar-weighted) vs `mean(pnl_i / capital_i)` (equal-weight per trade) | Identical only for equal-sized trades; they diverge under varying position size, which is the normal case |
| **D6b Scope of "four capital metrics"** | ship the 2 cheap denominator fixes / commit to building all 4 | **The phrase does not exist anywhere in this repo.** It comes from the Session 6 stub in the kickoff document. Two of the four (return on deployed capital, return on sleeve) need inputs `scoreboard()` does not accept — a interface change, not a formula fix. You need to say what you actually want |
| **D6c Daily-NAV drawdown** | (a) log the daily mark the strategy already computes; (b) capture Lumibot's own per-iteration portfolio value; (c) zero-start fix only, disclosed as interim | The ingredient exists **twice** and is discarded twice: `put_credit_spread.py:344-363` computes an honest daily mark and uses it only for exit triggers; `harness/run_backtest.py:69` discards Lumibot's result object entirely. The catch is the harness runs one backtest per symbol per year with capital reset each time, so there is no single equity curve — it needs stitching. Shipping (c) under the "daily-NAV" label without disclosure would be exactly the green-suite-wrong-answer failure §0 warns about |
| **D6d H6 governance category** | new H6 version (owner-typed) / in-place amendment (delegatable) | Precedent exists for parameter amendments (`config.py:325`, `H6_IVR_MAX` retune). This is a structural redefinition of the kill function on a **currently-open book** — changing it in place would retroactively change what "kill" meant for accrued history |
| **D6e H6 comparison basis** | deployed-that-month / fixed reference / exposed-during-month | Verified: 3 consecutive months deploying $900 each and losing 100% each does **not** trigger the kill, because $900 < the $2,000 cap it compares against |
| **D6f H6 month key** | exit-month / entry-month / abandon calendar months and use per-position streaks | H6's 45–90 DTE band makes cross-month positions the common case, not an edge case. The per-position option sidesteps both defects structurally but changes what `H6_HARD_KILL_FULL_LOSS_MONTHS` means |
| **D6g H6 vs H8 shared cap** | H6 book only / combined H6+H8 | `config.py:360` sets `H8_CAP_SHARED_WITH_H6 = True`, but `_hard_kill` cannot see H8's book at all. Not in the original claim list |

**H6 edge cases the new version must answer explicitly:** a zero-deployment
month (does it break the streak or skip it?); a position spanning three months;
a month with one total loss and one still-open position (can the kill fire on
incomplete data?).

---

### D7 — Session 7: probes and release gates

**The question the safety hook blocked in Session 1 now has an answer, verified
directly in the installed library.**

**Yes — lumibot 4.5.63's *backtesting* broker supports genuine atomic
net-priced multi-leg fills. But only via `SMART_LIMIT`.**

- `Order.OrderClass.MULTILEG` exists — `.venv/…/lumibot/entities/order.py:162`.
- The atomic package fill is gated on the parent order type being `SMART_LIMIT`
  — `.venv/…/lumibot/backtesting/backtesting_broker.py:1209-1219`, whose own
  comment reads *"Package SMART_LIMIT: treat the multileg parent as the smart
  order and fill the child legs atomically when the parent becomes executable."*
- Wrapping plain market orders as multileg gets you a bookkeeping parent only —
  **each leg still prices independently, exactly as today.**

**The catch, and it is a real one.** `SMART_LIMIT` brings ladder-based execution
semantics — the price walks from mid toward the worse side over configured
steps. That is a fundamentally different fill philosophy from this repo's
"cross the spread once, then apply `SLIPPAGE_HAIRCUT`." A ladder that *starts*
at mid can produce fills **better** than the current conservative model, which
would loosen `.cursorrules`' binding CONSERVATIVE FILLS guardrail ("fill at the
quote MID or WORSE — never the favorable side"). Adopting it is a coupled
cost-model decision, not a drop-in.

**A second, previously undocumented failure mode found alongside C10.** Both
legs are day orders. If one leg fills and the other cannot (a missing bar on
the decision day survives the `tradeable_assets` pre-check, which only verifies
the contract has *some* data, not data *today*), the unfilled order is cancelled
at session close rather than carried over. The spread then sits in
`pending_entry` **permanently** — a real, cash-affecting naked leg that the
strategy's own exit logic never touches again. The only backstop is
`harness/run_backtest.py:96-100`, which raises at **chunk end**. Verified: it
fails loud, so no silently biased number — but it fails late, and diagnosing it
means digging back through the whole chunk.

| Slot | Candidates | Note |
|---|---|---|
| **D7a C10 mechanism** | (a) adopt MULTILEG + SMART_LIMIT; (b) keep two legs, add an explicit same-bar atomicity check that rejects/unwinds a half-filled spread; (c) leave as-is and document | (b) closes the naked-leg risk without touching the cost model. (a) is the only route to true net pricing but requires re-deriving the fill model against the conservative-fills guardrail |
| **D7b Probe scope** | full offline set (signatures + fixture-based behaviour) / signatures only | Signature-only catches renames but not behaviour drift. The fixture probes — fill price equals the pre-widened bid/ask, bar timing at 16:00, callback signature — are the ones that would catch a real upstream change |
| **D7c Status vocabulary** | retrofit the three existing gates / new lanes only | `tools/daily_ritual.sh` matches the literal strings `GO`/`NO_GO`. Retrofitting without updating it breaks the daily ritual silently |
| **D7d BLOCKED vs N-A** | for deliberately-inactive lanes (H7 Stage 8, H8) | Changes whether a dashboard reads "something is holding this back" or "nothing to see here" |

Good news on D7c: the repo already has ~90% of this taxonomy, just scattered —
three modules share an identical 0/1/2 exit convention, and
`tools/thetadata_cutoff_preflight.py` already uses the literal `NOT_RUN`. This
is a naming-and-consolidation job, not a design job.

---

### D8 — Research integrity: correction facts for three permanent records

**This is not an engineering decision and does not belong to any session.**

The capital-efficiency defect inflates by exactly the trade count (dividing by
mean instead of sum multiplies by *n*). Three permanent, append-only records
therefore carry numbers wrong by 226×, 196×, and 16×:

| Record | Trades | Recorded | Honest |
|---|---:|---:|---:|
| H1 — `ledger/experiments.jsonl` seq 0 | 226 | **−4,510.21%** | **−19.96%** |
| H2 — `ledger/experiments.jsonl` seq 3 | 196 | **−1,835.34%** | **−9.36%** |
| H9 — `reports/h9/receipt.json` | 16 | **+1,387.30%** | **+86.71%** |

H9's max drawdown of **$361.30** is additionally understated (trade-indexed, no
zero start) and is quoted in **prose** in `ledger/facts.log:17892`, not only
inside a JSON blob.

**The adjudicated verdicts are safe.** `metrics.py:462-474` computes the verdict
from the loss count, cohort count, and confidence interval only — it never
reads any of these three fields. **FAIL, FAIL, and INSUFFICIENT_SAMPLE all
stand.** What is wrong is the descriptive record around them.

**Your decision:** whether each record gets an append-only correction fact. The
ledger cannot be edited, so the alternatives are "append a correction" or "leave
it and document the defect elsewhere." No correction text is drafted here.

**Not determined:** whether Card 3's recorded result carries the same defective
values — no dedicated receipt was located.

---

### D9 — CI coverage (small, cheap, independent of everything else)

`.github/workflows/ci.yml` runs on pull requests to any branch, and on pushes to
`main` and `phase-1a-research-integrity` **only**. Pushes to `sfix` — the branch
this arc has been working on — run **no** Ruff, Pyright, tests, or gitleaks.

A secret committed to `sfix` is caught only once a PR exists or it reaches
`main`. Whether branch protection forces a PR before merge lives in GitHub
settings, not in the repo, and was **not** checked (network).

Interacts with D1: choosing a branch with CI coverage resolves this for free.

---

## 2. Suggested sequencing (yours to override)

1. **D1** — branch. Blocks all code.
2. **D8** — correction facts. Independent of all engineering; the longer it
   waits the longer the record stands uncorrected.
3. **Session 3** — no decision needed, brief ready, and it is the only fix that
   is pure logic with every constant unchanged.
4. **D2 → Session 2** — the P0. Needs your convention first.
5. **D6 → Session 6** — metrics are cheap; the H6 half needs D6d–D6g.
6. **D7 → Session 7** — probes are cheap and would have caught real drift.
7. **D4 → Session 4** — measured inert for the registered strategy; defer is
   defensible.
8. **D5 → Session 5** — costs money; buy last, once the fixes have shown which
   provenance fields they actually consume.

## 3. What this investigation did not do

- **No fix code written.** Every session remains unimplemented.
- **No file modified** except the three reports in `reports/strategy-evaluations/`.
- **No network, no provider call, no spend, no git writes, no ledger writes.**
- **No impact measured.** Every defect is confirmed to exist; none is quantified
  against real results. Nobody has measured how much C1's look-ahead moved
  H1/H2's numbers.
- **No runtime probes.** The 17:15-vs-16:00 bar-ingestion question (D2a option
  ii) and the half-filled-spread scenario (D7) were both traced through code,
  not reproduced by running a backtest.
- **H7/H8 largely untraced.** They share `build_option_data` and the same
  same-day chain-fetch pattern as `put_credit_spread.py`. `strategies/h7_backtest.py`
  carries the identical C1 defect, though it is currently withdrawn as
  verdict-capable evidence (`config.py:533-541`).
