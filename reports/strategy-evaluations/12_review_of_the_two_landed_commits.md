# 12 — Adversarial review of the two fix commits that landed on `main`

**Date:** 2026-07-30
**Reviewed:** `5165144` (causal clock + canonical pricing) and `88ffbb6` (capital metrics)
**Tree:** `main` @ `88ffbb6`, worktree `/Users/carsynstephenson/options-validator-ops`, clean apart from
untracked `reports/`
**Method:** read every changed hunk against the working tree; recomputed the numeric
claims with the repo's own functions; ran the suite and Ruff.
**Requested by owner** 2026-07-30 ("Plan + adversarial review of tonight's two commits").

Framing per the standing rule: this review looks for how the change could be
lying, not for reasons to approve it. Findings that turn out wrong are as
useful as findings that stick.

---

## 0. Verified environment

| | |
|---|---|
| `main` HEAD | `88ffbb6` |
| Pushed to `origin/main` | `5165144` **yes** · `88ffbb6` **no** (local only) |
| Test suite | **PASS** — 2,131 tests, `OK`, exit 0, 255 s |
| Ruff | **PASS** — all checks passed |
| Pyright | **NOT_RUN** this session |
| Ledger facts written by either commit | **none** — last entry in `ledger/facts.log` is 2026-07-28 |

---

## 1. What the commits get right

Stated first, because the rest of this document is adversarial and the change is
mostly good work.

- **The clock defect (C1) is genuinely closed for entries.** `_try_enter` now
  freezes an intent on day D and `_execute_pending_entry` submits on D+1
  ([`strategies/put_credit_spread.py:242-304`](../../strategies/put_credit_spread.py#L242-L304)).
  The comment at line 277 is explicit that the D+1 chain must not be read,
  which is the right instinct — reading it would reintroduce the same defect
  one day later.
- **The pricing divergence (C2) is closed for the same-day case.** Selector,
  sizing, exit marks and fills all route through `adverse_buy` / `adverse_sell`
  ([`strategies/put_credit_spread.py:485-487`](../../strategies/put_credit_spread.py#L485-L487)).
  `tests/test_canonical_pricing.py` proves selector credit equals engine fill
  credit when the quotes are held constant.
- **Point-in-time feed availability is fail-closed.** `_assets_available`
  requires the contract in both the global set and that specific session's set,
  and refuses otherwise
  ([`strategies/put_credit_spread.py:398-408`](../../strategies/put_credit_spread.py#L398-L408)).
- **Two metric defects are genuinely fixed.** `capital_efficiency` became
  `trade_weighted_return_on_risk` and now divides by total capital, and
  `_max_drawdown` is anchored at zero
  ([`metrics.py:270-276`](../../metrics.py#L270-L276)). Both renames are honest:
  the new names say what the number is.

---

## 2. Findings

### F1 — The $600 cap can no longer be enforced. **P0.**

**The mechanism.** Position size is frozen on day D from day-D prices. The fill
happens on D+1 at D+1 prices. `capital_at_risk` is then recorded from the *fill*
credit:

- `contracts` is computed in `_try_enter` from the day-D `credit`
  ([`strategies/put_credit_spread.py:111`](../../strategies/put_credit_spread.py#L111)).
- That contract count is frozen into `_PendingEntry.contracts` and submitted
  unchanged the next session ([line 296](../../strategies/put_credit_spread.py#L296)).
- `pos.entry_credit` is then overwritten from the **actual engine fills**
  ([line 456](../../strategies/put_credit_spread.py#L456)).
- `capital_at_risk` and `economic_max_loss` are computed from that fill credit
  ([lines 551, 556](../../strategies/put_credit_spread.py#L551-L556)).

So the cap is checked against one day's credit and realised against another's.
The engine is **structurally unable** to re-check, because line 277 deliberately
forbids reading the D+1 chain.

**Worked example.** A $2-wide spread sized at 4 contracts on a $0.50 day-D
credit puts $600 at risk — exactly the cap. If the credit is $0.35 by the D+1
close, realised capital at risk is `(2.00 − 0.35) × 100 × 4 = $660`: a **10%
breach from one ordinary day of drift**, with no upper bound in a gap.

**Why this matters more than it looks.** Session 3 existed to close a $6.40
breach on a $600 cap (1.07%). This change reopens the same hole an order of
magnitude wider, in the same changeset. The two fixes are in tension and neither
commit message notes it.

**Why no test caught it.** Every cap test holds the quotes constant between
selection and fill — the giveaway is in the test's own name,
`test_selector_credit_equals_engine_fill_credit_for_same_quotes`
([`tests/test_canonical_pricing.py:98`](../../tests/test_canonical_pricing.py#L98)).
The clock fix's entire purpose is that the quotes are now from a *different*
day. The cap suite verifies a precondition the clock fix deliberately removed.

**Not proposing a fix or a number here.** The options (re-size at fill, cancel
if the fill-day credit is worse than a tolerance, accept and disclose) all
involve either reading the D+1 chain or typing a new frozen tolerance. Both are
owner decisions.

---

### F2 — `entry_date` silently changed meaning, and it feeds the verdict. **P1.**

`closed_trades["entry_date"]` is now `pos.entry_fill_date`, with the old
value preserved separately as `entry_decision_date`
([`strategies/put_credit_spread.py:552-553`](../../strategies/put_credit_spread.py#L552-L553)).

This is not cosmetic. `metrics.scoreboard` builds weekly cohorts from
`entry_date`, `COHORT_GRANULARITY = "week"`, and those cohorts are the unit of
the block bootstrap that produces the confidence interval the verdict gates on.
Shifting every entry forward one session moves any Friday decision into the
following ISO week, which changes cohort membership, which changes the CI, which
can change a verdict at the margin.

`10_fix_arc_owner_decisions.md` §D2c named this exact hazard in advance:
*"Redefining this field without renaming it corrupts comparison against existing
records."* The field was redefined and not renamed.

The choice itself (fill day) is defensible — arguably more correct. The problem
is that it is an unregistered redefinition of an input to the verdict machinery,
made by an implementing agent.

---

### F3 — An exit trigger on the last session of a chunk now crashes the run. **P1.**

`_close` needs a next session to queue into. On the final session of a chunk
`_next_session` returns `None`, so `_close` logs and returns **without setting
`queued_exit`** ([`strategies/put_credit_spread.py:494-497`](../../strategies/put_credit_spread.py#L494-L497)).
The position stays open. The chunk-end guard then raises
([`harness/run_backtest.py:105-113`](../../harness/run_backtest.py#L105-L113)).

Sessions are chunk-scoped — `sessions = tuple(trading_days(sim_start, sim_end))`
([`harness/run_backtest.py:71`](../../harness/run_backtest.py#L71)) — so this is
reachable at every year boundary, not just once.

Before this commit the same trigger submitted its orders immediately and the
position resolved. **A previously-working path is now a hard failure.** It fails
loud rather than silently, which is the right direction, but it fails at chunk
end rather than at the trigger, so diagnosing it means digging back through a
whole year of the run.

The same `None` branch on the entry side is harmless — it just skips the trade.

Note this interacts with the sealed holdout: a decision on `IN_SAMPLE_END`
(2022-12-31) needs a 2023-01-01 fill, which is past the seal. `10_…` §D2d
flagged this as "the riskiest site in the fix." The chunk-scoped session list
means the run skips rather than touches the holdout — good — but nothing
records that a trade was dropped for that reason.

---

### F4 — The metrics commit fixed one sum-over-mean bug and left its twin. **P1.**

`return_on_economic_max_loss` still divides total P&L by the **mean** economic
max loss ([`metrics.py:515-519`](../../metrics.py#L515-L519)) — the identical
defect that `capital_efficiency` was renamed and fixed for, in the same commit,
twelve lines away. It still inflates by the trade count.

[`tests/test_core.py:297`](../../tests/test_core.py#L297) still asserts
`30.0 / 110.0` (27.27%) where the honest sum-over-sum value is `30.0 / 220.0`
(13.64%). The green suite is certifying the wrong answer, exactly as
`10_…` §0 predicted.

---

### F5 — The H9 drawdown is wrong for a reason nobody had identified. **P1, and it changes a recorded number.**

`10_…` §D8 attributed H9's understated `max_drawdown` to the missing zero start.
That is true but secondary. Recomputed from the receipt's own `trades` array:

| Ordering of the trade list | Drawdown |
|---|---:|
| As recorded — **alphabetical by ticker**, no zero start | **$361.30** |
| Alphabetical, zero-anchored | $482.30 |
| **Chronological by entry date** | **$718.50** |
| Chronological by exit date | $572.20 |

The recorded $361.30 reproduces *exactly* under the alphabetical, no-zero-start
computation and under no other ordering, which is conclusive: the trade list was
handed to `scoreboard` sorted by symbol. A drawdown computed over a
non-chronological sequence is not a drawdown of anything.

`_max_drawdown` has no ordering contract and `scoreboard` does not sort. The
zero-anchor fix in `88ffbb6` does not address this, and the H9 receipt is a
permanent record.

---

### F6 — The config line asserting owner provenance is unbacked, and a test enshrines the assertion. **P2, integrity.**

[`config.py:238`](../../config.py#L238) reads:

```python
BACKTEST_EXECUTION_CONVENTION = "D_PLUS_1_CLOSE"  # owner-typed 2026-07-30
```

No ledger fact records it; `ledger/facts.log` ends 2026-07-28.
[`tests/test_causal_fill_convention.py:143`](../../tests/test_causal_fill_convention.py#L143)
is named `test_owner_froze_d_plus_1_close` and asserts the constant's value —
a test cannot establish who typed something, so this reads as corroboration
while providing none.

The chosen value is almost certainly right (see §4). The defect is the label.
Under CLAUDE.md the owner types frozen values and new registrations; an
implementing agent may record *amendments* only after independent adversarial
review plus sign-off, carrying the provenance label "owner-delegated standing
2026-07-25". Neither path was followed here.

**Owner resolution 2026-07-30:** the owner did not confirm authorship and
instead directed a different convention be evaluated (§4). Treat the current
value as **UNREGISTERED** pending an owner-typed decision.

---

## 3. Verdict

**Do not build further on `5165144` until F1 and F3 have owner decisions.**

The commit closes the defect it set out to close. It also, in the same
changeset, reopens the cap breach that its companion fix had just closed (F1)
and converts a working chunk-seam path into a crash (F3). Neither is visible to
the test suite. `88ffbb6` is good as far as it goes but is half of its job (F4).

`5165144` is already on `origin/main`. Nothing here justifies rewriting pushed
history; the corrections belong in follow-on commits.

**Not done in this review:** no backtest was run, so F1's real-world magnitude
across the registered window is unmeasured — the mechanism is proven from code,
the size is not. Pyright was not run. H7/H8 share `build_option_data` and were
not re-traced against these changes.

---

## 4. The owner's 1pm-snapshot / 2pm-fill question

Asked 2026-07-30: *"I want to make it that it caches at 1pm and I look to buy at
like 2; if this isn't possible then come up with the next best thing."*

The answer splits in two, because the repo has two different clocks.

### For the historical backtest (what these commits touch) — not possible today

| Requirement | Status |
|---|---|
| Historical intraday option quotes | **Endpoint exists** — `option_at_time_quote`, `option_history_quote` on the installed `ThetaClient` (Repo-verified: enumerated from `thetadata` 's installed class). |
| Those quotes in the local cache | **No.** `data/thetadata_adapter.py` fetches only `option_history_greeks_eod` — one end-of-day snapshot per contract per day ([lines 9, 221](../../data/thetadata_adapter.py#L221)). |
| Intraday **delta**, needed to pick the ~30-delta short leg | **Not entitled.** Probe-verified 2026-07-24: `option_snapshot_greeks_all` returns `PERMISSION_DENIED`; greeks need ThetaData's PROFESSIONAL tier and this account is on STANDARD ($80/mo, ledger fact 2026-07-16). |
| Cost of a refetch | `09_session5_refetch_gate.md` puts a plain EOD refetch at ~31,367 symbol-days and ≈62,734 provider calls. An intraday refetch multiplies that by the number of timestamps per day. |

Two of those four are hard blockers, and the delta one is not solvable with
money alone at the current tier. Whether *historical* interval greeks are
entitled on STANDARD is **UNVERIFIED** and would need a network probe — owner
approval required, and not attempted this session.

**Next best thing: keep D+1 close.** It is the only convention the existing
cache can support, it removes the look-ahead, and it costs nothing. Its honest
price is that you wait a full session and lose the trades that don't survive
overnight. That price is real and should be recorded when the convention is
registered.

### For live forward operation — a 13:00 snapshot already exists

This is the encouraging half. `config.INTRADAY_CAPTURE_TIMES` already contains
`"midday": "13:00"` — **owner-typed 2026-07-24** — alongside four other daily
capture times ([`config.py:728-734`](../../config.py#L728-L734)). Receipts have
been accumulating since then under `reports/intraday_capture/`.

What is missing is not data. It is **authority**: `intraday_capture.py` is
declared zero-verdict, alerts-and-display only, and is storage-isolated from the
backtest cache by design.

Turning that recorder into something that can open a position is a **new
hypothesis registration**, not an amendment — and it cannot be retrofitted onto
H7's live forward window, which is registered and scores ~2026-10-26. Changing
entry timing mid-window would void the registration.

**Recommendation:** keep D+1 close for the backtest; let the 13:00 recorder keep
accumulating; revisit an intraday-entry hypothesis once there is enough captured
history to design one honestly. Parked, not rejected.

---

## 5. Scope justification

Tested against `.cursorrules`: *"Does this move one of the live hypotheses
toward its declared verdict?"*

| Work | In scope? | Why |
|---|---|---|
| `metrics.py` corrections | **Yes, strongly** | `scoreboard` is the single function that will adjudicate H5, H6, H7, H8 and H10. A denominator wrong by the trade count corrupts the descriptive record of every future verdict, not just past ones. |
| H6 hard-kill defects (§D6e/f) | **Yes** | H6 is a live book with an open position. `_hard_kill` compares monthly P&L to the full $2,000 cap regardless of deployment, so three consecutive months losing 100% of $900 do not trigger the kill ([`options_researcher/h6_watch.py:707-730`](../../options_researcher/h6_watch.py#L707-L730)). A safety rule that cannot fire is a live risk. |
| Causal clock + pricing | **Yes** | Any future frozen backtest — including H10a/H10b, registered on the live chain — runs through this engine. Leaving a known look-ahead in it makes every future run un-defensible. |
| D8 correction facts | **Yes** | Research integrity is the project's product. Three permanent records carry inflated numbers. |
| Feed inclusion (C3 / Session 4) | **Marginal — defer** | Measured inert for the registered strategy: 0 of 310 accepted selections had a future-admitted leg. Real but lowest urgency. |
| Probes / release gates (Session 7) | **Hygiene** | Would have caught upstream drift. Not verdict-bearing. |

Nothing here starts a fourth venture, adds a ticker, adds a strategy, or moves
the repo toward live order placement. The standing pre-verdict rule is not
engaged.

---

## 6. Files touched by this session

- `reports/strategy-evaluations/08_repo_verification.md` — copied from the `sfix`
  checkout, unmodified
- `reports/strategy-evaluations/09_session5_refetch_gate.md` — copied, unmodified
- `reports/strategy-evaluations/10_fix_arc_owner_decisions.md` — copied, unmodified
- `reports/strategy-evaluations/11_codex_brief_session3_canonical_pricing.md` — copied, unmodified
- `reports/strategy-evaluations/12_review_of_the_two_landed_commits.md` — this file
- `docs/superpowers/specs/2026-07-30-daily-nav-drawdown.md` — new spec
- `reports/strategy-evaluations/13_correction_facts_draft.md` — draft correction text

No code file was modified. No ledger write. No network call. No git commit.
