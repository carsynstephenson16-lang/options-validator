# 08 — Repo verification of the C1–C11 audit claims

**Session 1 of the evidence-integrity arc. Read-only. No fixes applied.**

Date of run: 2026-07-30
Purpose: bucket every claim from two prior audits as VERIFIED CORRECT /
DEFECT CONFIRMED / CANNOT VERIFY against the actual working tree, with
file:line evidence. "Defect confirmed" and "claim was wrong" are equally
successful outcomes here.

---

## 1. Frozen environment

| Item | Value |
|---|---|
| Branch at time of run | `sfix` (**not** `main` — STOP gate F, see §6) |
| HEAD SHA (audited tree) | `40a6b21c5fa35eda073418ea1bc3f1cb177731a2` |
| Working tree | **clean** (`git status --porcelain` empty) |
| `main` SHA | `f9f7d318cc4445f16f64eb3944ab513554db7669` |
| Merge base `main`…`HEAD` | `3f2d19f5b75fddd9858561404f55334ca4f3d91a` (2026-07-25) |
| Divergence | main has 36 commits not in sfix; sfix has 43 not in main |
| Python | 3.12.13 |
| uv | 0.11.29 |

Locked versions read from `uv.lock` (not modified):

| Package | Locked version |
|---|---|
| lumibot | 4.5.63 |
| thetadata | 1.0.9 |
| pandas | 2.3.3 |
| numpy | 2.4.6 |
| scipy | 1.18.0 |
| pyarrow | 21.0.0 |
| polars | 1.42.1 |
| pandas-market-calendars | 5.4.0 |
| ruff | 0.15.20 |
| pyright | 1.1.411 |

**The prior audit's claim that main is at `f9f7d31` is CORRECT.** `main` is
at `f9f7d318…` right now. However, this session ran against `sfix`, by owner
decision after gate F was surfaced (see §6).

### 1a. Branch-sensitivity of the audit (why `sfix` is an acceptable tree)

Blob-hash comparison of every file the spec names:

| File | Claims | main vs sfix |
|---|---|---|
| `strategies/put_credit_spread.py` | C1, C2, C10 | identical (`0d0bbb4`) |
| `data/pandas_feed.py` | C1, C2, C3 | identical (`fb6ca2e`) |
| `metrics.py` | C6 | identical (`1a05272`) |
| `options_researcher/h6_watch.py` | C7 | identical (`967bc93`) |
| `options_researcher/h8_watch.py` | C8 | identical (`a68d4dc`) |
| `config.py` | C2, C8 | identical (`58b20f0`) |
| `options_researcher/h7_forward_scoring.py` | C9 | identical (`784280a`) |
| `data/thetadata_adapter.py` | C4, C5 | **differs** (main `544721f` / sfix `03867c5`) |
| `options_researcher/h7_real_scoring.py` | C9 | **differs** (main `d5364d9` / sfix `5cd206d`) |

The two divergent files are dual-reported in C4/C5 and C9 below. For C4/C5
the relevant regions (`CHAIN_COLUMNS` block and `_merge_chain_frames`) were
byte-compared and are **identical on both branches** — the verdicts hold on
either tree.

---

## 2. Test suite / Ruff / Pyright

| Gate | Status | Counts / evidence |
|---|---|---|
| Unit tests (`uv run python -m unittest discover -s tests`) | **PASS** | `Ran 2139 tests in 251.657s` → `OK` (0 failures, 0 errors) |
| Ruff (`uv run ruff check .`) | **PASS** | `All checks passed!` |
| Pyright (`uv run pyright`) | **PASS** | `0 errors, 0 warnings, 0 informations` |

All three run fully offline. No provider call, no network fetch.

**Read this correctly:** a green suite is evidence about the code the tests
cover, not about whether the modelled economics are honest. Every P0 below
survives a 2,139-test green suite. That is the central finding of this
session.

---

## 3. Claim-by-claim verdicts

### C1 — Look-ahead: same-session EOD chain decided and filled at 16:00 bars while the source report is generated 17:15 ET

**Verdict: DEFECT CONFIRMED — P0 (blocks any honest verdict).**

Evidence, traced end to end:

1. Decision date is the simulated session date:
   `strategies/put_credit_spread.py:248-249` — `_today()` returns
   `self.get_datetime().date()`.
2. The chain fetched at decision time is **that same session's** chain:
   `strategies/put_credit_spread.py:262-267` — `_get_eod_chain` calls
   `self._chain_provider(symbol, self._today().isoformat())`. The audits'
   description of "a `self._today()` chain call" is accurate.
3. Selection consumes it immediately: `strategies/put_credit_spread.py:174-185`.
4. Exit marks use the same-session chain too:
   `strategies/put_credit_spread.py:344-363` (`_spread_mark` → `_get_eod_chain`).
5. Those chain values are ThetaData's **17:15 ET EOD report**, by the repo's
   own docstring: `data/thetadata_adapter.py:9-13` — "returns NBBO (bid/ask)
   + every greek + implied_vol … generated from the 17:15 ET EOD report."
6. The bar carrying those values is stamped **16:00 America/New_York**:
   `data/pandas_feed.py:44` (`BAR_HOUR = 16`) and `data/pandas_feed.py:177-178`
   (`pd.Timestamp(f"{d} {BAR_HOUR}:00", tz=NY_TZ)`), with the rationale at
   `data/pandas_feed.py:17-18`.
7. Fills land on the **decision day's** quotes, per the repo's own spike
   evidence: `docs/superpowers/2026-07-03-offline-pandas-backtesting-spike.md:17`
   — "Fills price at the DECISION day's EOD quotes | spike fill-day
   attribution: entry decided 06-01 filled at 06-01 quotes."

So at simulated timestamp 16:00 on day D the strategy reads, decides on, and
fills against numbers that the provider does not publish until 17:15 ET on
day D. 17:15 > 16:00; the data postdates the decision. The external ThetaData
17:15 ET fact was verified independently (Official-source, per the kickoff);
everything above is Repo-verified.

Honest counter-evidence, recorded rather than suppressed: the **open-interest**
leg of the chain is genuinely look-ahead-free and the repo says so and is
right — `data/thetadata_adapter.py:14-17` documents OI as sourced from the
~06:30 ET OPRA report reflecting the *previous* day's close. The leak is in
bid/ask/greeks/IV, not OI.

Scope note: this defect is in the H1/H2 backtest path
(`PutCreditSpread` + `pandas_feed`). The H7/H8/H9 forward-paper modules use a
different lifecycle and were not traced here.

---

### C2 — Pricing divergence: unrounded selection/sizing vs adverse-rounded fills; $600 cap breached

**Verdict: DEFECT CONFIRMED — P1 (distorts metrics), bordering P0 for the risk cap.**

Three call sites found, exactly as claimed:

| Layer | Location | Rounding? |
|---|---|---|
| Selection / credit | `strategies/base.py:49-84` (`entry_credit_conservative`) | **none** — returns `short_fill - long_fill` unrounded (`:82-84`) |
| Sizing | `strategies/base.py:33-46` (`size_defined_risk`), called at `strategies/put_credit_spread.py:117` | **none** — gates on the unrounded credit |
| Engine fill | `data/pandas_feed.py:53-64` (`adverse_buy` / `adverse_sell`), applied at `data/pandas_feed.py:183-184` | **yes** — `math.ceil`/`math.floor` to the cent |
| Exit trigger / mark | `strategies/put_credit_spread.py:344-363` (`_spread_mark`) | **none** — raw `ask*(1+h) - bid*(1-h)` |

The repo states the rule and then breaks it in this path.
`data/pandas_feed.py:56-58` says the canonical helpers are where "Decide
layer, T+1 revalidation, exit marks and P&L must all price buys through."
Every later hypothesis module obeys it — `options_researcher/h8_watch.py:32`,
`h9_study.py:31`, `h7_paper_lifecycle.py:25`, `card3_study.py:56`,
`qm_watch.py:34` all import `adverse_buy`/`adverse_sell`. Neither
`strategies/put_credit_spread.py` nor `strategies/base.py` imports them.

#### C2 numeric reproduction — the REPO'S OWN functions

Run against the working tree with `entry_credit_conservative`,
`size_defined_risk`, `economic_max_loss_per_spread`, `adverse_sell`,
`adverse_buy`. Config read live: `SLIPPAGE_HAIRCUT=0.01`,
`A_SPREAD_WIDTH=2.0`, `COMMISSION_PER_CONTRACT=0.65`, `HALF_SPREAD_COST=True`,
`MAX_LOSS_PER_TRADE=600`, `round_trip_commission_per_spread()=2.6`.

Inputs: short leg bid 1.05 / ask 1.10, long leg bid 0.45 / ask 0.50.
(With `HALF_SPREAD_COST=True` only short-bid and long-ask enter the credit;
the other two sides exist only to pass the quote-validity check.)

| | Selection & sizing path | Engine-fill path |
|---|---|---|
| Function | `entry_credit_conservative` + `size_defined_risk` | `adverse_sell(1.05)` − `adverse_buy(0.50)` |
| Short leg | — | fills at **1.03** |
| Long leg | — | fills at **0.51** |
| Net credit | **0.5345000000000001** | **0.52** |
| Economic max loss / spread | **149.15** | **150.60** |
| Contracts | **4** | 4 (held from sizing) |
| **Total economic max loss** | **$596.60** | **$602.40** |
| Capital at risk | $586.20 | $592.00 |

**Divergence per spread: $1.45. Cap breach: $602.40 − $600.00 = $2.40.**

The repo's own numbers reproduce the spec's worked example exactly
(149.15 ×4 vs 150.60 ×4). No discrepancy to report between spec and repo.

This is not cosmetic: `strategies/put_credit_spread.py:390-408`
(`_finalize_trade`) computes the recorded `capital_at_risk` and
`economic_max_loss` from `pos.entry_credit`, which
`strategies/put_credit_spread.py:333-334` sets from **engine fills** — i.e.
the rounded, cap-breaching number is the one that reaches the scoreboard,
while the $600 gate was evaluated on the unrounded one.

---

### C3 — Future-delta leakage in feed inclusion

**Verdict: DEFECT CONFIRMED — P1 (distorts metrics). Identical on both branches.**

`data/pandas_feed.py:169-176`:

```
for (exp, strike, right), grp in rows.groupby(["expiration", "strike", "right"]):
    ...
    if not grp["delta"].abs().between(lo, hi).any():
        continue
```

`grp` is the contract's series across the **whole loaded window**. `.any()`
means: if the contract's |delta| touches the band on *any* day in the window,
the contract is admitted and its **entire history is kept** (`data/pandas_feed.py:176-190`).
A contract's availability on day D therefore depends on its delta on days
after D. The claim is confirmed, and the code documents the behaviour itself
at `data/pandas_feed.py:20-25`.

Honest counter-argument, recorded because the repo makes it and it is
partially valid: that same docstring argues the band "is generous plumbing,
not a tunable: legs are selected from the RAW chain, and the strategy fails
loud if a selected leg has no feed Data, so a band miss can abort a run but
can never bias one." The fail-loud path is real
(`strategies/put_credit_spread.py:300-307`). This narrows the blast radius —
selection reads the raw chain, not the feed — but it does not eliminate the
defect: the feed still decides which contracts *can* be filled, and that set
was chosen with future knowledge. Whether the raw-chain selection makes the
leak inert in practice was **not** measured this session and should not be
assumed either way.

---

### C4 — Cache discards provider timestamps and model metadata; symbol-name dispute

**Verdict: DEFECT CONFIRMED — P1. Symbol dispute: the SECOND audit is right.**

Actual cached schema, `data/thetadata_adapter.py:49-53`:

```
CHAIN_COLUMNS = [
    "expiration", "strike", "right",
    "bid", "ask", "open_interest",
    "iv", "delta", "gamma", "theta", "vega",
]
```

Eleven columns. **Absent:** option quote timestamp, underlying timestamp,
underlying price, report-created time, Greek/model version, rate type, rate
value, dividend input, contract multiplier. The claim is confirmed in full.

The sharpest single piece of evidence: a provider `timestamp` column is
**read and then thrown away**. `data/thetadata_adapter.py:263-265` sorts on
`timestamp` when present (to keep the last report of the day), and
`data/thetadata_adapter.py:291` then projects to `CHAIN_COLUMNS`, which
excludes it. The information reaches the process and is deliberately not
persisted.

**Symbol-name dispute settled:**

| Symbol claimed | Exists in code? |
|---|---|
| `CHAIN_COLUMNS` | **YES** — `data/thetadata_adapter.py:49` (main: `:59`) |
| `_merge_chain_frames` | **YES** — `data/thetadata_adapter.py:268` (main: `:286`) |
| `SCHEMA_COLUMNS` | **NO** — zero hits repo-wide |
| `_merge_greeks_oi` | **NO** — zero hits in code. The only occurrence anywhere is a historical *reason-code string* in `ledger/facts.log:4380` (`reason=zero_row_merge_greeks_oi_key_mismatch`), which is almost certainly what the first audit pattern-matched on. |

Search performed: `grep -rn "<symbol>" .` excluding `.git`, `.tmp`,
`node_modules`, `__pycache__`.

**Dual-report (main vs sfix):** the `CHAIN_COLUMNS` block and
`_merge_chain_frames` were byte-compared across branches and are
**IDENTICAL**. On `main` they sit at `data/thetadata_adapter.py:59` and
`:286`. The branches differ elsewhere in this file (main carries additional
cache-publisher / attestation hardening that sfix predates), but nothing that
touches this verdict.

---

### C5 — Inner join silently drops contracts missing OI, no MISSING_OI reason code

**Verdict: DEFECT CONFIRMED — P2 (hygiene), with one correction to the word "silently".**

Join type: `data/thetadata_adapter.py:288-289` — `.merge(…, on=_KEY_COLS,
how="inner")` (main: `:307`). Unmatched greeks rows are dropped. Confirmed.

The "no reason code" half is confirmed: there is **no** per-contract
`MISSING_OI` code, no quarantine list, and no structured record. What exists
is a **bare count**, `data/thetadata_adapter.py:316` —
`len(normalized_greeks) - len(chain)` — surfaced only as a `print()` to
stdout at `data/thetadata_adapter.py:340-342`. That count is also
lossy: it conflates "missing OI" with any other cause of a key mismatch,
while the message asserts one cause ("dropped N contracts missing open
interest").

Correction to the claim's wording: the drop is **not** entirely silent (a
count is printed), and the inner join is a documented deliberate choice
(`data/thetadata_adapter.py:18-20`, `:269-274`) on the argument that an
OI-less contract fails the liquidity gate anyway — which is consistent with
`passes_liquidity` at `data/thetadata_adapter.py:456-465`. The defect that
survives is that the drop is unstructured, unattributed, and unrecoverable
after the fact, so no downstream consumer can distinguish "no such contract"
from "dropped at merge."

**Dual-report:** identical on `main` and `sfix` (byte-compared, see C4).

---

### C6 — Metric defects: capital efficiency uses a mean denominator; drawdown omits the zero start

**Verdict: DEFECT CONFIRMED (both halves) — P1. Plus one additional instance the audits missed.**

**C6a — capital efficiency.** `metrics.py:491`:

```
"capital_efficiency": float(pnls.sum() / cap.mean()) if cap.mean() else float("nan"),
```

Sum in the numerator, **mean** in the denominator. Reproduced with the repo's
own `scoreboard()` on identical trades (pnl $100, capital at risk $400 each —
a true 25% return per trade regardless of count):

| n identical trades | reported `capital_efficiency` |
|---|---|
| 1 | 25.00% |
| 2 | 50.00% |
| 4 | 100.00% |
| 8 | 200.00% |

The metric scales linearly with trade **count**, not with performance. The
audits' 27.27% vs 13.64% example is the same arithmetic.

**Additional instance not in the claim list:** `metrics.py:457-461`,
`return_on_economic_max_loss`, has the identical defect
(`pnls.sum() / economic_max_loss.mean()`). It is printed at
`metrics.py:544-547`. Any fix in Session 6 must cover both.

**C6b — max drawdown zero start.** `metrics.py:251-257`:

```
equity = np.cumsum(pnls)
running_max = np.maximum.accumulate(equity)
return float((running_max - equity).max())
```

No zero starting point is prepended, so the peak can never precede trade 1
and an opening loss registers no drawdown. Reproduced with the repo's own
`_max_drawdown`:

| pnl sequence | repo `_max_drawdown` | with zero start |
|---|---|---|
| `[-100, 50]` | **0.0** | 100.0 |
| `[-100]` | **0.0** | 100.0 |
| `[100, -100]` | 100.0 | 100.0 |

A strategy whose first trade loses $100 reports max drawdown $0. Confirmed.
Note also that the curve is trade-indexed, not daily-NAV — the audits' broader
point, listed for Session 6.

---

### C7 — H6 hard kill compares to the full $2,000 cap; entry-month vs exit-month cohort mismatch

**Verdict: DEFECT CONFIRMED (both halves) — P1.**

The function is `_hard_kill` at `options_researcher/h6_watch.py:707`, exactly
as the audits claimed.

**Half 1 — comparison against the full cap.** `options_researcher/h6_watch.py:716-720`:

```
full_loss = {
    key
    for key, pnl in realized.items()
    if pnl <= -config.H6_MONTHLY_PREMIUM_AT_RISK
}
```

`H6_MONTHLY_PREMIUM_AT_RISK = 2000` (`config.py:332`). The test is against the
**cap**, never against what was actually deployed. Reproduced by calling the
repo's own `_hard_kill`:

| Scenario | `_hard_kill` |
|---|---|
| 3 consecutive months, $900 deployed each, **100% loss** each (realized −900/mo) | **False** |
| 3 consecutive months, $2,000 deployed each, 100% loss each | True |

A strategy that loses every dollar it deploys for three straight months does
not trip its own kill switch, because it did not deploy enough to lose $2,000.
Confirmed.

**Half 2 — cohort mismatch.** Two different month keys:

| Purpose | Location | Key |
|---|---|---|
| Capacity / deployment | `options_researcher/h6_watch.py:339-343` (`_book_state`) | `(pos.entry_date.year, pos.entry_date.month)` |
| Hard-kill realized P&L | `options_researcher/h6_watch.py:712` | `(pos.exit_date.year, pos.exit_date.month)` |

An H6 position with 45–90 DTE routinely enters one month and exits another,
so the month that consumed the budget and the month charged with the loss are
systematically different months. Confirmed by code; the runtime demo of this
half was not completed because `validate_book` (`h6_watch.py:504`) rejects
synthetic positions outside the registered 45–90 DTE band — the two literal
key expressions above are the evidence.

`_hard_kill` is reached from `score_book` at `options_researcher/h6_watch.py:743`,
ahead of the sample-size gate, so it governs the H6 REJECT verdict.

---

### C8 — `H8_MIN_COMPLETED_POSITIONS` defined but never consumed; H8 has a watcher and no scorer

**Verdict: VERIFIED CORRECT (i.e. defect confirmed) — P1.**

Exact repo-wide search for `H8_MIN_COMPLETED_POSITIONS`, excluding `.git`,
`.tmp`, `node_modules`, `__pycache__`. **Complete list of references — two,
neither of them code that consumes it:**

1. `config.py:366` — the definition, `H8_MIN_COMPLETED_POSITIONS = 8`
2. `wiki/hypotheses.md:52` — prose describing the intended rule

Zero consumers. Contrast with H6's structural twin, which *is* consumed:
`H6_MIN_COMPLETED_POSITIONS` (`config.py:337`) is read at
`options_researcher/h6_watch.py:753` and `:759` and feeds the
`INSUFFICIENT_SAMPLE` verdict.

The "watcher but no scorer" half also holds. `options_researcher/h8_watch.py`
exposes `choose_contract`, `entry_window_state`, `evaluate_entry`,
`evaluate_exit`, `validate_book`, `load_book`, `build_snapshot`, `main` — and
**no** `score_book`, no verdict function, no CI/expectancy path. H6's
equivalent module has `score_book` at `options_researcher/h6_watch.py:733`.
`options_researcher/` contains no other H8 module (`ls | grep -i h8` returns
`h8_watch.py` only). H8 can therefore open and close positions in the paper
book but has no code path that can ever reach a verdict.

---

### C9 — H7 real scoring gated inactive; synthetic scorer only

**Verdict: VERIFIED CORRECT — no defect. Not-a-defect confirmations matter; this one is working as designed.**

**The synthetic scorer declares itself.** `options_researcher/h7_forward_scoring.py:1-6`:
"Stage 6 H7 forward-window scoring. BUILD-ONLY; SYNTHETIC-ONLY; INACTIVE.
This is a pure read over an explicit synthetic Stage-3 ledger. It does not
register a window, append an event, or provide a CLI. Stage 8 remains the
only activation gate."

**The real scorer is gate-blocked.** `options_researcher/h7_real_scoring.py:1`
— "Receipt-gated real-store H7 scoring wrapper (BUILD-ONLY; INACTIVE)."
The gate is `_require_review_passes` at
`options_researcher/h7_real_scoring.py:1692-1746`: finalization requires three
ledger facts whose *latest* instance carries specific tokens —
`AMENDMENT_FACT_TAG` (`:1703`), `REVIEW_PASS_TAG` (`:1711`), `OWNER_PASS_TAG`
(`:1719`) — each pinned to the live spec hashes; any miss raises
`RealScoringRefused` (`:1738`).

**Empirically, on this tree, the gate is shut.** Checking the actual
`ledger/facts.log` against the module's own constants and live spec hashes:

| Required fact | Present? | Satisfies gate? |
|---|---|---|
| `H7_EXIT_SCORING_SPEC_AMENDMENT_V1_3` | **0 facts** | **No** |
| `H7_REAL_EXIT_SCORING_INDEPENDENT_REVIEW_PASS` | 1 fact (`ledger/facts.log:17977`, 2026-07-23) | **No** — pinned to the pre-amendment spec; missing `spec_sha256=a9131a41…`, `base_spec_sha256=…`, `amendment_spec_sha256=…` |
| `H7_REAL_EXIT_SCORING_OWNER_PASS` | 1 fact (`ledger/facts.log:17978`, 2026-07-23) | **No** — same three tokens missing, plus `owner=carsyn` |

The owner-pass fact says so in its own words: *"This closes the section-9
build-review gate only; it does not authorize Task 7 wiring, real H7 events,
scoring, or live trading."*

No verdict path is reachable. Confirmed.

**Dual-report (main vs sfix).** This file differs between branches, and the
difference is the *gate itself*, so it is worth stating precisely:

| | `main` (`d5364d9`) | `sfix` (`5cd206d`) |
|---|---|---|
| Spec pinned | single `SPEC_PATH` (2026-07-22 base spec) | base + **amendment v1.3** (2026-07-25), with `PINNED_BASE_SPEC_SHA256` |
| Gate tokens | `verdict=PASS` + `spec_sha256={spec_sha256}` (`main:1643-1651`) | adds amendment fact, both spec hashes, and provenance (`sfix:1701-1746`) |
| `h7_scoring_identity.py` | **absent** | present |

sfix's gate is **strictly stricter** than main's. The C9 verdict (inactive, no
reachable verdict path) holds on both; sfix additionally requires an amendment
fact that has never been recorded.

---

### C10 — Two separate leg orders submitted, no net-priced package

**Verdict: VERIFIED CORRECT (defect confirmed) — P1 for fill realism.**

Entry, `strategies/put_credit_spread.py:308-309`: two independent
single-leg market orders — a sell of the short-put asset, then a buy of the
long-put asset. Exit, `strategies/put_credit_spread.py:369-370`: the same
structure in reverse. There is no combo/spread order object, no net-limit
price, and no atomic package anywhere in the file.

The consequence is visible in the fill-state machine: the strategy has to
wait for two independent fills to reconcile before it knows its own entry
credit (`strategies/put_credit_spread.py:326-337`, where `entry_credit` is
only computed once *both* legs report), and each leg is separately priced by
the feed at `data/pandas_feed.py:183-184`. A real broker executing a spread
as a package would not price the legs independently.

**Method note:** the `block_live_trading` hook (correctly) blocked a shell
command whose text contained an order-submission token, so I did not run the
lumibot-API introspection I had planned to check whether a net-priced
multi-leg order type is available in 4.5.63. That question is a *fix-design*
question and out of Session 1 scope anyway. The claim as stated — what the
repo does — is verified from the file directly.

---

### C11 — CI workflow exists but no run evidence at the current revision

**Verdict: VERIFIED CORRECT (workflow exists) / CANNOT VERIFY (run evidence at this revision).**

Workflows present: `.github/workflows/ci.yml` and
`.github/workflows/claude-review.yml`.

`.github/workflows/ci.yml` defines exactly the four gates claimed:

| Gate | Step |
|---|---|
| Ruff | `uv run ruff check .` |
| Pyright | `uv run pyright` |
| Tests | `uv run python -m unittest discover -s tests` |
| Secret scan | `gitleaks/gitleaks-action@v2` (separate `secrets` job) |

**Trigger analysis — and this is the substantive finding.** The workflow fires
on `pull_request`, and on `push` to `main` or `phase-1a-research-integrity`
only. The audited branch is **`sfix`**, which is on neither list. CI therefore
does **not** run on pushes to this branch; only a PR would trigger it. That is
a structural gap, not merely absent evidence.

**CANNOT VERIFY, and why:** confirming whether a CI run exists for
`40a6b21` would require querying GitHub over the network, which STOP gate B
forbids. No local run artifact exists (`.github/` contains only `workflows/`).
I did not query GitHub and am not inferring a result either way.

What I can state is the local substitute, run at `40a6b21` this session:
**Ruff PASS, Pyright PASS (0 errors), unittest PASS (2,139 tests)** — the same
three commands `ci.yml` runs, minus gitleaks, which was **NOT_RUN**.

---

## 4. Verdict summary

| # | Claim | Verdict | Severity |
|---|---|---|---|
| C1 | Same-session chain decided and filled vs 17:15 ET report | **DEFECT CONFIRMED** | **P0** |
| C2 | Unrounded selection/sizing/exit vs rounded fills; $600 cap breach | **DEFECT CONFIRMED** | P1 (P0 for the cap) |
| C3 | Future-delta feed inclusion | **DEFECT CONFIRMED** | P1 |
| C4 | Cache discards provider timestamps/model metadata | **DEFECT CONFIRMED** | P1 |
| C5 | Inner join drops missing-OI contracts, no reason code | **DEFECT CONFIRMED** (wording corrected) | P2 |
| C6 | sum/mean capital efficiency; drawdown missing zero start | **DEFECT CONFIRMED** (+1 extra instance) | P1 |
| C7 | H6 hard kill vs full cap; entry/exit cohort mismatch | **DEFECT CONFIRMED** | P1 |
| C8 | `H8_MIN_COMPLETED_POSITIONS` unconsumed; no H8 scorer | **VERIFIED CORRECT** | P1 |
| C9 | H7 real scoring gated inactive; synthetic only | **VERIFIED CORRECT** (no defect — by design) | — |
| C10 | Two leg orders, no net-priced package | **VERIFIED CORRECT** | P1 |
| C11 | CI exists; no run evidence at this revision | **VERIFIED CORRECT** / **CANNOT VERIFY** (run evidence) | P2 |

Ten of eleven claims survived contact with the code. The audits were
substantially right. Two corrections were required: the C4 symbol dispute
(second audit correct; `SCHEMA_COLUMNS`/`_merge_greeks_oi` do not exist), and
C5's "silently" (a count is printed, though it is unstructured and lossy).

Three findings the claim list did not contain, surfaced during verification:

1. `metrics.py:457-461` `return_on_economic_max_loss` carries the same
   sum/mean denominator defect as `capital_efficiency`.
2. Every post-H1 hypothesis module already routes through the canonical
   `adverse_buy`/`adverse_sell`; only the H1 backtest path does not. The fix
   surface for C2 is narrower than it looks.
3. `.github/workflows/ci.yml` does not trigger on the `sfix` branch at all
   (push triggers are `main` and `phase-1a-research-integrity` only).

---

## 5. Proposed values (STOP gate E)

**None.** No check in this session surfaced a frozen or registered parameter
needing a new value. Every threshold examined (`MAX_LOSS_PER_TRADE`,
`SLIPPAGE_HAIRCUT`, `H6_MONTHLY_PREMIUM_AT_RISK`,
`H6_HARD_KILL_FULL_LOSS_MONTHS`, `H8_MIN_COMPLETED_POSITIONS`,
`MIN_LOSSES_FOR_VERDICT`) was read as-is and reported as-is. The defects above
are logic defects, not calibration defects — C2's cap breach, for instance, is
fixed by rounding consistently, not by changing $600.

---

## 6. STOP gates — status

| Gate | Status |
|---|---|
| A — modify/create any file other than this report | **Not triggered.** This report is the only file created. Its parent directory `reports/strategy-evaluations/` did not exist and was created implicitly by writing the file. |
| B — ThetaData / paid API / network / Theta Terminal | **Not triggered.** No provider call, no network fetch. Deliberately declined to query GitHub for C11 run evidence, which is why C11 is partly CANNOT VERIFY. |
| C — git operations beyond reading | **Not triggered.** Read-only git only: `rev-parse`, `status`, `log`, `diff`, `show`, `ls-tree`, `cat-file`, `merge-base`, `rev-list`. No commit, push, branch, checkout, worktree, or stash. |
| D — credentials / launchd / cron / env config / `uv.lock` | **Not triggered.** `uv.lock` was read for version freezing, never written. No `uv sync` was run. |
| E — proposing frozen/registered parameter values | **Not triggered.** See §5 — none needed. |
| F — dirty tree or branch ≠ `main` | **TRIGGERED AND SURFACED.** HEAD was on `sfix` (tree clean). Halted before any verification work, reported the divergence and its blast radius (§1a), and proceeded only on the owner's explicit instruction to stay on `sfix` and dual-report the two divergent files. |

**One additional halt, not a listed gate:** the repo's own
`block_live_trading` hook blocked a shell command during C10 because the
command text contained an order-submission token. Per `CLAUDE.md` the block
was treated as correct and not worked around; the C10 evidence was taken from
reading the file instead. See the method note in C10.

### Files created or modified

Exactly one:

- `reports/strategy-evaluations/08_repo_verification.md` (this file)

Nothing else was written. Temporary comparison output was written to `/tmp`
(`/tmp/adapter_main.py`, from `git show main:…`), outside the repo.

---

## 7. Honest limitations — what this session did NOT verify

- **No provider calls.** Nothing was fetched from ThetaData. The 17:15 ET EOD
  report-generation time underpinning C1 is taken from the kickoff's
  independently verified Official-source check plus the repo's own docstring
  (`data/thetadata_adapter.py:9-13`) — I did not re-verify it against
  ThetaData's documentation myself.
- **No Lumibot runtime fill probes.** I did not execute a backtest and watch
  fills land. C1's fill-day attribution rests on the repo's own spike record
  (`docs/superpowers/2026-07-03-offline-pandas-backtesting-spike.md:17`) and
  on code reading, not on a fill I observed. A runtime probe pinned to
  lumibot 4.5.63 remains genuinely unverified and is Session 7's job.
- **No cache-content verification.** No parquet file was opened. I did not
  check whether cached chains actually lack the metadata columns C4 says are
  missing — I verified the *schema the writer produces*. A cache written by
  an older schema could differ.
- **No measurement of impact.** Every defect above is confirmed to exist. None
  is quantified. I did not measure how much C1's look-ahead inflates results,
  how often C2's rounding breaches the cap in real data, or whether C3's
  inclusion rule changes any actual trade. "Confirmed" here means "the code
  does this," not "this changed the answer by X."
- **C10 fix-space unexplored.** Whether lumibot 4.5.63 offers a net-priced
  multi-leg order was not determined (see the C10 method note).
- **C11 run evidence.** Not checkable without network. Stated as CANNOT
  VERIFY rather than guessed.
- **Scope.** C1/C2/C3/C10 were traced through the H1/H2 `PutCreditSpread` +
  `pandas_feed` path only. The H7/H8/H9/QM forward-paper modules use a
  different lifecycle and were not traced; the C2 import survey suggests they
  are cleaner on rounding, but that is a survey, not an audit.
- **Branch.** Verified against `sfix` @ `40a6b21`, not `main` @ `f9f7d31`.
  Nine of eleven claims land on byte-identical files; C4/C5's relevant regions
  were byte-compared and are identical; C9 was dual-reported. No claim's
  verdict flips between branches — but main carries cache-publisher hardening
  in `thetadata_adapter.py` that sfix predates, and that code was not audited.

---

## 8. Go / no-go for Session 2 (causal clock fix)

**GO.** C1 is confirmed at P0 with a complete, quoted decision→fill trace, and
it is the correct next target: it is the only defect on the list that makes
every downstream number untrustworthy rather than merely distorted, so
fixing metrics or rounding first would just produce precise wrong answers. The
evidence Session 2 needs is now in hand and unambiguous — the decision-date
chain call (`strategies/put_credit_spread.py:262-267`), the 16:00 bar stamp
(`data/pandas_feed.py:44`, `:177-178`), the 17:15 ET report provenance
(`data/thetadata_adapter.py:9-13`), and the same-day fill attribution
(spike doc line 17) — which is exactly the input set required to choose a
registered D-signal → D+1-fill convention. Two conditions attach. First, the
branch question is now a real decision, not a formality: this verification ran
on `sfix`, `main` has 36 commits sfix lacks, and a clock fix touches
`pandas_feed.py` and `put_credit_spread.py`, which are byte-identical today
but will not stay that way — pick the target branch before writing code, not
after. Second, the fill convention is a **registered** parameter and stays
owner-typed; this report deliberately proposes no value for it (§5). One
caution worth carrying into Session 2: the 2,139-test suite passes green over
all seven confirmed defects, so it will very likely pass green over a clock
fix that is subtly wrong too. Session 2 needs a test that fails *before* the
fix — the existing suite is not going to catch this class of error on its own.
