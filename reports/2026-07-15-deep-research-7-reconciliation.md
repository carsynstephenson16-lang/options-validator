# Reconciliation — external deep-research report (7) vs. repo state

**Date:** 2026-07-15
**Source graded:** `Downloads/deep-research-report (7).md` (an external LLM
grade of this repo's `config.py`-style rules; it graded the framework
**72/100, B**, and explicitly declined to grade a live book because none was
supplied).
**Purpose:** map each report demand to what the repo already does, what would
be genuinely new, and where the report overreaches. Every claim about repo
state is cited `file:line`. Every number lifted from the external report is
labeled **report-asserted** (the report's own market figures — VIX, CPI, index
levels — are not verified by this repo and carry that label per `.cursorrules`
claim discipline). Nothing here changes any parameter; Section 2 ends with a
block for the **owner** to type personally.

Scope note: this is a reconciliation memo, not a hypothesis and not a verdict.
It moves no live hypothesis toward a verdict on its own; it exists to keep the
external grade from being acted on carelessly.

---

## SECTION 1 — Already satisfied

Demands the report makes that the repo has already met. Verified before
claiming.

### 1.1 The H5 VST trigger — the repo took the report's *second* branch

The report grades the VST trigger loosening (140 → 160) a **D** and calls it a
governance problem (report-asserted, report table row "H5 VST trigger
amendment"). But the report's own prescribed fix offers two branches:
"Revert to original trigger, **or** re-register a new version and treat prior
signal history as stale" (report-asserted, scorecard row H5).

The repo took the second branch, explicitly and in writing:

- `config.py:226-229` records the change as `H5_ENTRY_TRIGGER_AMENDMENT_V2`,
  owner-directed 2026-07-15, and states any entry graded under it "is trigger
  v2, **not** the original 2026-07-07 pre-registration firing."
- `config.py:230` — `H5_ENTRY_TRIGGERS = {"VST": 160.0, "AMZN": 220.0}` is the
  live value; the prior 140.0 pre-registration is superseded, not silently
  overwritten in place of its record.
- The change is logged as a distinct ledger amendment id
  (`config.py:226`, ledger `H5_ENTRY_TRIGGER_AMENDMENT_V2`), i.e. versioned
  rather than mutated.

**Owner's position (adopted by this document):** a logged, forward-only,
owner-typed amendment is condition-adjustment done honestly, not a rule break.
The discipline the repo owes is **versioning plus a fresh signal history** —
not immutability of a discretionary entry level. The repo satisfies both: the
new level carries a new version id, and prior signal history under the 140
trigger is declared stale (`config.py:228-229`). Under the report's own second
branch, this is the fix, already applied.

**One honest caveat (not a lecture):** a trigger loosened to just above spot
fires its price leg immediately — `config.py:227-228` discloses VST's close
was 158.43 at amendment, already below 160, "so the price leg is instantly
satisfied." So v2's *evidence value starts from zero at registration*: the
forward record under v2 begins now, and no pre-2026-07-15 signal counts toward
it.

### 1.2 The report's "keep paper-only" escape clause is the current state

For H6 (IVR 0.70) and H7 ($6k/month) the report offers "or keep paper-only"
as an acceptable alternative to tightening (report-asserted, scorecard rows H6
and H7). That alternative is not a future option here — it is the present
state of all three live hypotheses:

- `README.md:183` — "**Scope status: three live hypotheses, forward paper
  windows.**"
- H5/H6/H7 carry **zero live capital**: `README.md:37` — `positions.csv` is
  empty, "no options are currently open or paper-tracked"; `README.md:274` —
  "Current recorded holdings: 39 VST shares and no options."
- H6 is declared forward-paper with no live path: `config.py:236` — "Forward-
  paper only; no live-order path."
- H7's sole verdict-bearing path is the forward paper window; live activation
  (Stage 8) is explicitly not open: `README.md:236-237`, `README.md:267-268`.
- The no-live-order boundary is hook-enforced repo-wide (project CLAUDE.md
  "Project boundary"), not merely a convention.

So the report's escape clause describes what already holds. There is no live
book behind any of these caps today.

### 1.3 The withdrawn H7 historical diagnostic is permanently retired

The report praises the withdrawal and says "keep it" (report-asserted,
narrative under the scorecard). Confirmed retired, with a frozen gate:

- `config.py:391-399` — `H7_HISTORICAL_WITHDRAWAL_HASH` pins the ledger record
  (`H7_AMENDMENT_V1_3`) that "permanently WITHDREW the 2018-2026 historical H7
  diagnostic as verdict-capable evidence," and every historical-diagnostic
  entry point "refuses BEFORE reading market data."
- `README.md:232-234` — "the 2018–2026 historical diagnostic is PERMANENTLY
  WITHDRAWN as verdict-capable evidence (amendment v1.3, 2026-07-11)."
- `README.md:271-273` — the frozen retirement gate makes every historical-
  diagnostic entry point refuse before reading market data.

Reopening it "requires a NEW hypothesis and a NEW registration; it may not
reopen H7" (`config.py:396-397`). This is retired, not paused.

### 1.4 Loss-gated verdicts already exist

The report wants verdicts gated on losses, not trades (report-asserted,
executive summary and scope section). Present:

- `config.py:137-140` — `MIN_LOSSES_FOR_VERDICT = 10`; below this many losing
  trades the harness returns INSUFFICIENT SAMPLE instead of pass/fail, with the
  rationale that "a long win streak in a short-vol strategy is expected and
  proves nothing."
- Reinforced in the discipline layer description (`README.md:20`, `.cursorrules`
  "Verdict rule").

---

## SECTION 2 — Genuinely new, sturdy proposals

Things the repo does **not** currently do. Each item: what the report
proposes, the exact **report-asserted** number, whether repo state confirms the
gap (cited), and a proposed config parameter name. No value is set here.

### 2.1 VRP proxy as a hard entry gate for all short-premium

- **Report proposes:** make `IV − RV ≥ 0` a **hard live-entry gate** for every
  short-premium trade, plus no entries into an earnings blackout
  (report-asserted).
- **Gap confirmed:** today the VRP proxy is descriptive/tag-only, not a gate.
  `config.py:205` — "**DESCRIPTIVE ONLY** and a PROXY"; `config.py:210` —
  `H5_VRP_SELL_GREEN = 0.0` is a badge threshold, not an entry condition. The
  H5 entry gate (`config.py:219-231`) turns on price + IV-rank + liquidity, not
  on VRP. (H7c selects *structure* from IV-vs-RV at `config.py:304-306`, but
  that chooses a lane, it does not block a short-premium entry.) So no
  short-premium entry anywhere is currently VRP-gated.
- **Proposed parameter name:** `H5_VRP_ENTRY_GATE_HARD` (a forward-only
  amendment; boolean gate that blocks short-premium entry when
  `iv_minus_rv < H5_VRP_SELL_GREEN`).

### 2.2 Tighter liquidity for short-premium legs

- **Report proposes:** `OI > 200` and `max spread ≤ 5%` for all short-premium
  equity legs (report-asserted).
- **Gap confirmed:** the general gates are looser — `config.py:91`
  `MIN_OPEN_INTEREST = 100`; `config.py:92` `MAX_SPREAD_PCT = 0.10`. (Note: H7
  admission already uses the tighter 5% at `config.py:327`
  `H7_ADMIT_MAX_SPREAD_PCT = 0.05` with `OI >= MIN_OPEN_INTEREST`; the gap is
  that H5/general short-premium still runs on 100 / 10%.)
- **Proposed parameter names:** `SHORT_PREMIUM_MIN_OPEN_INTEREST` (report-
  asserted 200) and `SHORT_PREMIUM_MAX_SPREAD_PCT` (report-asserted 0.05),
  applied to both legs of any short-premium structure.

### 2.3 Cluster concurrency cap

- **Report proposes:** at most **2 concurrent short-premium names**, never
  VST + CEG (both power) together, and never all four at once — cutting
  simultaneous cluster risk from ~17.1% to ~8.6% of the sleeve (all
  report-asserted).
- **Gap confirmed:** there is no cross-strategy cluster concurrency cap in
  `config.py`. Concurrency caps are per-strategy only —
  `config.py:180` `H4_TACTICAL_MAX_OPEN = 2`, `config.py:250`
  `H6_MAX_CONCURRENT = 3`, `config.py:322` `H7C_MAX_CONCURRENT = 1`. The
  ~17.1% simultaneous-cluster figure is acknowledged as a *flag*, not a cap
  (`config.py:36-39`; `README.md:117-119`). The report-asserted VST+CEG
  exclusion has no representation in config today.
- **Proposed parameter names:** `MAX_CONCURRENT_SHORT_PREMIUM_NAMES` (report-
  asserted 2) and `SHORT_PREMIUM_EXCLUSIVE_CLUSTERS` (a rule set that forbids
  holding both power names — VST and CEG — as concurrent short-premium
  positions).

### 2.4 H4 LEAPS premium caps vs. the honest sleeve

- **Report proposes:** cap H4 at **$7k per name and $10k total** until the
  sleeve is larger (report-asserted), because the current caps can reach or
  exceed the $14k honest sleeve.
- **Gap confirmed:** `config.py:162` `H4_THESIS_MAX_PREMIUM_PER_NAME = 10_000`;
  `config.py:167` `H4_THESIS_MAX_PREMIUM_TOTAL = 16_000`. The total ($16k)
  exceeds the honest sleeve `RISK_SLEEVE = 14_000` (`config.py:30`). No LEAPS
  are open (`config.py:169-170`), so a tightening is clean.
- **Proposed parameter names:** reuse the existing names via a forward-only
  amendment — `H4_THESIS_MAX_PREMIUM_PER_NAME` (report-asserted 7_000) and
  `H4_THESIS_MAX_PREMIUM_TOTAL` (report-asserted 10_000).

### 2.5 H7 monthly at-risk budget

- **Report proposes:** cut the H7 monthly premium-at-risk from $6,000 to
  **$2,000**, or keep H7 paper-only (report-asserted; the report calls $6k =
  42.9% of the sleeve too large).
- **Gap confirmed:** `config.py:324` `H7_MONTHLY_AT_RISK = 6000`. (Per 1.2, H7
  is already paper-only, so the "keep paper-only" half of the report's
  alternative is met; the *number* is the open item if the owner ever narrows
  it.)
- **Proposed parameter name:** `H7_MONTHLY_AT_RISK` (report-asserted 2_000),
  forward-only.

### 2.6 H6 IVR ceiling back to 0.50

- **Report proposes:** revert the H6 post-earnings IVR ceiling from 0.70 to
  **0.50**, or keep H6 paper-only (report-asserted).
- **Gap confirmed:** `config.py:241` `H6_IVR_MAX = 0.70`. The comment there
  already discloses the reason to reconsider — "naked long calls at IVR
  0.50-0.70 carry higher vega-crush risk" — and records that the book/receipts
  were empty at amendment (`config.py:241-244`), so a forward-only tightening
  is clean.
- **Proposed parameter name:** `H6_IVR_MAX` (report-asserted 0.50), forward-
  only.

### Consolidated block for the OWNER to type

The lines below are a **proposal to transcribe, not applied config.** Per repo
practice (project CLAUDE.md "You own the numbers"; global operating manual rule
3), the **owner types these personally**. None takes effect until it is (a)
typed by the owner into `config.py` and (b) registered in `ledger/` as a
**forward-only amendment** with its own version id. None may be applied
retroactively to any existing receipt or signal history: every existing H5/H6
receipt and every pre-amendment signal keeps its original parameters, exactly
as v2 of the VST trigger treats pre-2026-07-15 signals as stale.

```python
# --- PROPOSED forward-only amendments (OWNER TO TYPE + REGISTER) ---
# All numbers below are REPORT-ASSERTED (external deep-research report 7),
# not repo-measured. Nothing here is active until typed AND logged in
# ledger/ as a versioned forward-only amendment. Never apply retroactively.

# 2.1  VRP hard gate for ALL short-premium entries (new)
#   ledger id e.g. H5_VRP_GATE_AMENDMENT_V1
# H5_VRP_ENTRY_GATE_HARD          = True   # block short premium when iv_minus_rv < H5_VRP_SELL_GREEN

# 2.2  Tighter short-premium liquidity (new; H7 already uses 0.05)
#   ledger id e.g. SHORT_PREMIUM_LIQUIDITY_AMENDMENT_V1
# SHORT_PREMIUM_MIN_OPEN_INTEREST  = 200    # report-asserted (vs MIN_OPEN_INTEREST=100)
# SHORT_PREMIUM_MAX_SPREAD_PCT     = 0.05   # report-asserted (vs MAX_SPREAD_PCT=0.10)

# 2.3  Cluster concurrency cap (new)
#   ledger id e.g. CLUSTER_CONCURRENCY_AMENDMENT_V1
# MAX_CONCURRENT_SHORT_PREMIUM_NAMES = 2               # report-asserted
# SHORT_PREMIUM_EXCLUSIVE_CLUSTERS   = (("VST", "CEG"),)  # never both power names concurrently

# 2.4  H4 LEAPS caps down to the honest sleeve (forward-only; no LEAPS open)
#   ledger id e.g. H4_LEAPS_CAP_AMENDMENT_V1
# H4_THESIS_MAX_PREMIUM_PER_NAME   = 7_000   # report-asserted (was 10_000)
# H4_THESIS_MAX_PREMIUM_TOTAL      = 10_000  # report-asserted (was 16_000)

# 2.5  H7 monthly at-risk (forward-only; H7 already paper-only)
#   ledger id e.g. H7_MONTHLY_AT_RISK_AMENDMENT_V1
# H7_MONTHLY_AT_RISK               = 2_000   # report-asserted (was 6_000)

# 2.6  H6 IVR ceiling (forward-only; book empty)
#   ledger id e.g. H6_IVR_MAX_AMENDMENT_V2
# H6_IVR_MAX                       = 0.50    # report-asserted (was 0.70)
```

---

## SECTION 3 — Where the report overreaches or is not actionable here

### 3.1 It grades a live portfolio that does not exist

The report repeatedly concedes there is no live book, no positions, no entry
prices, no broker marks (report-asserted: executive summary; "Assumptions and
scope"; final "Live portfolio verdict: Not gradable"). Repo state matches:
`README.md:37` (`positions.csv` empty) and `README.md:274` (39 VST shares, no
options). So every sentence in the report that reads as a portfolio judgment is
a judgment of a *rules document*, not of holdings. Treat its "portfolio
footprint," stress-table, and per-name Greeks sections as commentary on a
hypothetical, not a book audit.

### 3.2 Its Greeks / IV / payoff tables are self-declared illustrative

The report states its ATM-IV table and one-lot Greeks are "illustrative
scenario calculations… not broker-book marks" and "I would not trade off this
table" (report-asserted, "Assumptions and scope" and the IV-proxy table). Under
repo claim discipline these are **Assumption**-grade at best; none is repo-
verified or test-verified. The specific net-delta/vega/theta figures and the
stress-scenario dollar P/Ls (e.g. "about −$2,164") are report-asserted model
outputs and should not be cited as this repo's numbers.

### 3.3 Its market-level numbers are report-asserted, not repo-verified

VIX 15.67, S&P 7,572.40, June CPI −0.4% m/m, the Fed range 3.50–3.75%, the
spot prices (MSFT 384.93, AMZN 254.96, VST 160.23, CEG 257.57 as of 07-13),
and the like are all **report-asserted** — sourced to the report's own browser
session, not verified against this repo's parquet cache or any official source
here. Per `.cursorrules` claim discipline, do not promote any of them to
repo-verified. Where they matter (e.g. VST near 160 driving the trigger caveat
in 1.1), the repo has its own figure — `config.py:227` records VST close
158.43 at amendment — and that is the one to cite.

### 3.4 The concentration warning cuts AGAINST simply adding more AI-adjacent tickers

The report's strongest and most repeated point is that MSFT/AMZN/VST/CEG are
**one AI-infrastructure cluster, not four independent bets** (report-asserted;
matches `config.py:52-55` and `README.md:117-119`). That warning argues against
the intuitive "diversify by adding more names" move when the new names are
themselves AI/semis/power. This repo has in fact been *adding* AI-adjacent
story names to the H7 watch — CRWV, TEM, SMCI, NVDA, AMD, AVGO, IREN, USAR
(`config.py:264-265`) — which raises single-factor concentration rather than
lowering it. Diversification only helps if a new name sits **outside** the
existing AI/semis/power factor.

This is a **decision for the owner**, not something to encode. If the owner
wants genuine diversification, the criteria (not ticker picks) are:

- **Non-AI sector** — outside cloud/semis/power/data-center/AI-supply-chain;
  the owner's standing single-factor concentration (global operating manual,
  "Standing analytical corrections") is the thing being diversified away from.
- **Liquid options** — penny-quoted, tight bid/ask, deep open interest and
  volume at monthly expiries (the repo already targets monthlies;
  `README.md:146`), so the tightened liquidity gates in 2.2 are clearable.
- **No overlap** — low fundamental and return correlation with the existing
  four-name cluster; a name that gaps with the AI trade is not diversification
  regardless of its sector label.

No tickers are proposed here; ticker selection is an owner decision and, per
the scope gate (`README.md` "Scope status"; project CLAUDE.md "Scope guard"),
any new name belongs in `ideas-parking-lot.md` until it is shown to move a live
hypothesis toward its verdict.

---

## Factual issues found in the report (about repo state)

1. **The "D / restore evidence integrity" framing on the VST trigger is
   already substantially addressed.** The report grades the trigger a D and its
   top-three fixes include "restore evidence integrity where triggers were
   loosened." But the report's *own* second acceptable branch (re-register a
   new version, treat prior history as stale) is exactly what the repo did
   (`config.py:226-230`). The D reflects the report reading the change as an
   in-place loosening; the repo treated it as a versioned, forward-only
   amendment. Not a repo error — a report characterization that its own
   prescription supersedes.

2. **The report treats the H4/H6/H7 caps as live-capital authorizations.** It
   scores them as if they put real money at risk relative to the $14k sleeve.
   Repo state is zero live capital and no live-order path on all three
   (`README.md:37`, `README.md:183`, `README.md:274`, `config.py:236`; hook-
   enforced). The caps bound a *paper* book. The report's own "or keep
   paper-only" alternative is therefore already the state, which softens the
   C-/C grades it assigns those rows.

3. **Internal repo inconsistency the report did not catch (worth an owner
   fix):** `config.py:230` sets the live VST entry trigger to 160.0 (v2), but
   `README.md:280-281` still reads "VST $140." The README narrative is stale
   relative to config after the 2026-07-15 amendment. This is a repo-internal
   drift, not a report error, but it should be corrected by the owner so the
   README matches the frozen config value. (Not fixed here — this memo edits no
   existing file.)

4. **The report's spot/Greeks arithmetic is self-labeled illustrative and
   should not be read back as repo findings** (see 3.2). No repo test or cache
   produced those numbers.

Everything else the report asserts about the rules (the $14k honest sleeve at
`config.py:23-30`; the $600 per-trade cap at `config.py:42`; $0.65/contract/leg
each way at `config.py:84`; 1% slippage haircut at `config.py:85`; OI>100 /
10% spread at `config.py:91-92`; the loss-gated verdict at `config.py:140`; the
VRP proxy being descriptive-only at `config.py:205`) is an accurate reading of
the current config.
