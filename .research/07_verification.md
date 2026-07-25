# Phase 3 — Adversarial verification of the decision

- **Verification date:** 2026-07-25
- **Verifier:** fresh-context, READ-ONLY adversarial pass. Mandate: try to
  DISPROVE the `RESEARCH-VALID, IMPLEMENTATION-REJECTED` decision and the
  routing of C2 (OI-change line) to an owner-gated brief. Rewarded for real
  flaws, not agreement.
- **Branch:** `feature/strategy-enhancement`.

## Verification scope and method

Read in full: `.research/00_baseline.md`, `01_periodicity.md`,
`02_licensing.md`, `03_strategy_candidates.md`, `04_repo_architecture.md`
(both pages), `decision.md`, `05_lead_candidate_brief.md`, and the three
`ideas-parking-lot.md` entries parked 2026-07-25.

Read-only checks performed:
- `git status --short`, `git diff --stat`, and full `git diff` on both
  tracked-modified files.
- Re-read of every repo artifact the decision cites: `reports/live_probe/
  2026-07-24.json`; `data/thetadata_adapter.py:1-60`; grep of `open_interest`/
  `passes_liquidity` call sites in `options_researcher/attractiveness.py`;
  grep of volume/OI/skew constants in `config.py`; `options_researcher/
  features.py` grain.
- Independent WebFetch re-verification of the three load-bearing licensing
  claims + WebSearch falsification hunt for a missed free full-market live
  feed (all fetched web content treated as untrusted data; no embedded
  instructions followed).
- `uv run ruff check .` (read-only in effect). Did NOT run pyright or the
  unittest suite (parent is running it; prohibited).

---

## Findings that WEAKEN or DISPROVE the decision

No CRITICAL or MAJOR finding. I actively attacked the decision on six axes and
each attack failed; the residue is three cosmetic/editorial items only.

**Attacks attempted that FAILED to disprove anything:**
- *Hunt for a hidden production-code change.* `git status` shows only two
  tracked-modified files, both `.md`; untracked additions are `.research/`
  (this workstream) and `reports/live_probe/` (pre-existing). No `.py`,
  `config.py`, or `tests/` file is modified. Attack failed.
- *Hunt for the workstream secretly editing the RQ2 briefs doc.* The doc IS
  modified on the working branch, but the diff is entirely the 2026-07-24
  owner-delegated RQ2 `[OWNER]`-blank values (B1/A1/C1/N3-1/V1 + RQ2 params) —
  unrelated to C1/C2/C4, adds NO sixth "OI" brief, and was recorded as a
  pre-existing ` M` in `00_baseline.md` before branch creation (corroborated
  by the memory index "2026-07-24 mega-session … RQ2 blanks delegated"). The
  lead brief itself leaves folding-in to the owner ("if ratified, the owner
  may fold this text"), and no such fold is present. Attack failed.
- *Hunt for a decision-gate citation that does not say what is claimed.* Every
  cited artifact was re-read and matches (see Confirmations). Attack failed.
- *Hunt for a missed free, full-market, live intraday equity-volume source.*
  Independent search of Databento, Cboe One, Nasdaq Basic, Finazon, Intrinio
  turned up no $0 sustainable full-consolidated live feed. Attack failed.
- *Hunt for a brief that violates repo rules (look-ahead / config-only /
  display-must-not-rank / offline tests).* The brief obeys all four. Attack
  failed.
- *Hunt for banned backtest-result vocabulary or unlabeled load-bearing
  claims.* None found (see Discipline audit). Attack failed.

**MINOR-1 (editorial, decision.md).** `decision.md` line 5 says the parent read
"all **four** Phase 1 files in full" but then names **five** files
(`00_baseline.md`, `01_periodicity.md`, `02_licensing.md`,
`03_strategy_candidates.md`, `04_repo_architecture.md`). Miscount only; `00` is
a Phase-0 baseline and `01-04` are four Phase-1 files, so the prose count is
wrong or the parenthetical over-includes. No effect on any gate. Severity
MINOR.

**MINOR-2 (universe-size wording, cross-file).** Files variously call the
attractiveness board "14-name" and "15-name" (`decision.md` uses "15-name" and
"14-name" in different lines; `03_strategy_candidates.md` mixes both). This is
disclosed and explained in `02_licensing.md` §0 (the task brief's list of 14
omitted `USAR`; `ATTRACTIVENESS_UNIVERSE` is 15), and every provider cap was
evaluated against the more conservative 15. Immaterial to every gate outcome.
Severity MINOR.

**MINOR-3 (audit completeness, not error).** `02_licensing.md`'s 11-provider
sweep did not explicitly enumerate Databento (one-time $125 credit, then
$199/mo subscription), Cboe One (paid; partial-venue), or Nasdaq Basic (paid).
My independent search confirms none of them is a free full-consolidated live
feed, so none would flip Gate 1 — this is a coverage gap in the enumeration,
not a wrong conclusion. Severity MINOR.

---

## Confirmations (claims re-verified true, with evidence)

**Unrelated-changes (git):** `git diff --stat` = exactly two tracked files:
`ideas-parking-lot.md` (+58) and `docs/superpowers/plans/2026-07-22-rq2-
scanner-enrichment-briefs.md` (+43). Both additive (no deletions). The
`ideas-parking-lot.md` diff hunk is `@@ -1048,4 +1048,62 @@` — a pure append
at the END of the file (three "parked 2026-07-25" entries: volume periodicity,
OI build-up line, IV skew), exactly the three entries the decision describes.
No `.py`/`config`/`tests` file modified. The daily note `2026-07-25.md` exists
(1845 bytes, created 07-25 00:04) and is correctly invisible to git (root
dated notes are gitignored per CLAUDE.md) — consistent with the "touched only
.research/, parking-lot append, daily note" claim.

**Live probe receipt (`reports/live_probe/2026-07-24.json`):** `stock_entitled:
false`; `stock_snapshot_quote` ok=false, error `PERMISSION_DENIED … Requesting
a stock endpoint requiring a value subscription, but you only have a FREE
subscript…`; `option_snapshot_open_interest` ok=true with an `open_interest`
column; `option_snapshot_greeks_all` ok=false (PROFESSIONAL). Exactly as the
decision's C1-Gate-1 and C2-Gate-1 cite.

**Adapter look-ahead-free OI (`data/thetadata_adapter.py:14-17`):** verbatim —
open interest "sourced from the ~06:30 ET OPRA report reflecting the PREVIOUS
day's close — i.e. the OI figure already known during day D, so joining day-D
OI is look-ahead-free." Matches C2-Gate-3.

**CHAIN_COLUMNS lacks volume (`data/thetadata_adapter.py:49-53`):**
`[expiration, strike, right, bid, ask, open_interest, iv, delta, gamma, theta,
vega]` — no volume field. Matches C3/C1 orthogonality claims.

**`open_interest` only via liquidity level checks:** appears in
`attractiveness.py` at lines 176/233/293/335/376 — every occurrence is an
argument to `passes_liquidity(...)` (called at 175/232/292/334/375). Exactly
five call sites, no flow/change use. Matches C2-Gate-4.

**config.py has no volume/OI-change/skew constants:** the only match for
volume/rvol/periodic/skew/oi_change/oi_delta is `QM_VOL_DRYUP_RATIO = 0.65`
(retired-QM study), exactly as `decision.md` Gate 4 states. `MIN_OPEN_INTEREST
= 100` confirmed (config.py:125), so the brief's `OI_CHANGE_MIN_BASE = 100 =
MIN_OPEN_INTEREST` reasoning is accurate.

**Feature layer is EOD-grain (`options_researcher/features.py`):** docstring
line 3 "One row per cached chain day"; `build_daily_features` loops `for d in
days` over cached chain days; `RV_WINDOW=21`, `PCT_WINDOW=252`. Matches
C1-Gate-6.

**Baseline lint claim:** `uv run ruff check .` → "All checks passed!", exit 0.
Confirms the `00_baseline.md` ruff-exit-0 baseline still holds. (pyright and
the full unittest run were not executed, per prohibition; the 1774-test count
was not re-verified and is out of scope.)

**Gate-9 governance consistency:** `decision.md` Gate 9 and the brief both rest
on the owner directive that the owner types every frozen number and Codex
implements from briefs. This matches CLAUDE.md "Division of labor (owner
directive 2026-07-22)" verbatim ("The owner types every frozen number,
registration, and ratification… Claude writes code directly only for docs,
briefs, and trivial mechanical fixes — not strategy or ledger code"). Choosing
a lookback window / percentile / min-base is frozen-number work, not a trivial
mechanical fix, so routing C2 to a brief rather than self-freezing thresholds
is the doctrinally-correct call, not a dodge. The scope-guard sentence is also
consistent: because the badge does not move a hypothesis to verdict, parking it
(with a brief pointer) is exactly what `.cursorrules`/CLAUDE.md require.

**Brief obeys repo guardrails (`05_lead_candidate_brief.md`):** display line is
"never a GREEN/AMBER/RED grade, never a ranking input," attached to the card
dict "NOT a `grades` key" (respects display-must-not-rank + the RQ2
byte-identical-board acceptance test); all four constants go in `config.py`
owner-typed (config-only-numbers); percentile uses a strictly-trailing causal
window with a truncation property test and D/D-1 sessions only, never intraday
(no look-ahead); tests are a new offline `tests/test_oi_change_line.py`
(offline-unittest rule). No rule violation found.

---

## Unrelated-changes audit result

**PASS.** Only two tracked files changed, both `.md`, both additive:
1. `ideas-parking-lot.md` — this workstream's append at the file's end (three
   2026-07-25 parking entries). Legitimate and disclosed.
2. `docs/superpowers/plans/2026-07-22-rq2-scanner-enrichment-briefs.md` —
   pre-existing 2026-07-24 owner-delegated-values work, NOT this workstream's;
   recorded as pre-existing in the baseline, unrelated in content, and adds no
   OI/C2 brief. Plausibly (and on the evidence, actually) someone else's docs
   work.
No `.py`, `config.py`, or `tests/` file was modified — the critical-finding
trigger did NOT fire. `reports/live_probe/` remains untracked/pre-existing and
was consumed read-only.

---

## Licensing spot-check results (incl. missed-free-source search)

Independently re-verified via WebFetch (2026-07-25), all three load-bearing
claims TRUE:
- **(a) QuantConnect datasets licensing** — verbatim: "This download is for the
  licensed organization's internal LEAN use only and cannot be redistributed or
  converted in any format." Confirmed.
- **(b) ThetaData stock tiers** — FREE = EOD only (from 2023-06-01, 1-day
  delay); VALUE = 1-minute, 15-minute delayed; STANDARD = 1-minute real-time;
  PRO = tick real-time. Confirmed exactly as `02_licensing.md` §2 states.
- **(c) Alpaca Basic** — free Basic = "Real-time market coverage | IEX"; Algo
  Trader Plus = "All US Stock Exchanges" (CTA+UTP, 100% volume). Confirmed
  IEX-only on the free tier.

**Missed-free-source hunt (attempt to falsify the audit's negative claim):**
searched for any free, full-consolidated (SIP), live intraday US equity volume
source. Result — the search was performed and FAILED to find one. Databento =
one-time $125 credit then a paid subscription ($199/mo Standard; live equities
no longer usage-based); Cboe One = paid, and a partial-venue consolidation, not
full SIP; Nasdaq Basic = paid (single-SIP BBO/last-sale, cost-advantaged but
not free); Finazon = from $4/mo (non-pro) + exchange fees; Intrinio SIP =
Enterprise/contact-sales. None provides $0 sustainable full-market real-time
volume. The audit's conclusion — Alpaca IEX is the only $0 real-time feed and
it is a ~3–6% venue slice — is not overturned. (Databento/Cboe One/Nasdaq
Basic were not individually enumerated in the audit; see MINOR-3.)

---

## Discipline audit (vocabulary / labels)

**Vocabulary:** CLEAN. Grep for banned backtest-result vocabulary
("proven"/"edge found"/"guaranteed") across `.research/` returns only the
files' own meta-statements declaring the discipline — no live claim uses them.
"works" appears once (`01_periodicity.md:180`) meaning "the treatment operates
at tick resolution" (a data-resolution description), not "the strategy works" —
not a backtest-result claim, so not a violation. "confirmed" appears 27 times
but exclusively about verifiable empirical facts (a probe endpoint returned ok;
a citation independently corroborated; an API entitlement), never about a
backtest result — and this workstream ran zero backtests, so the letter and
spirit of the rule (which governs backtest-result claims) are both intact. The
QuantConnect page's own reported Sharpe is correctly hedged as "not yet
rejected … for THAT construction."

**Labels:** load-bearing claims carry Official-source / Repo-verified /
Inference / Assumption labels throughout; the QC page's unverified backtest
numbers are explicitly down-graded to "moderate, not independently corroborated"
in both `01` §10 and `03` row 1. No unlabeled load-bearing claim found.

---

## Overall verdict: UPHELD-WITH-CORRECTIONS

The decision survives adversarial verification. The central factual spine —
stock feed is PERMISSION_DENIED on a FREE tier; no free full-market live
intraday equity-volume source exists; OI is already entitled, cached, and
documented look-ahead-free; the scanner uses OI only as a static liquidity
level; the feature layer is EOD-grain; config has no volume/OI-change/skew
constants — is independently confirmed at every point I checked, including a
verbatim re-fetch of all three load-bearing licensing pages and a genuine (and
failed) hunt for a missed free source. The "no production code written" claim
is git-verified true: only two additive `.md` changes, one of them a
pre-existing unrelated docs edit, zero `.py`/config/test modifications. The
Gate-9 governance rejection of direct implementation is consistent with the
repo's own documented owner directives, and the routing to an owner-ratifiable
brief obeys every applicable guardrail. The only defects are three cosmetic
items (a "four vs five files" miscount, a disclosed 14-vs-15 universe wording
drift, and a licensing-enumeration completeness gap that does not change the
result) — hence UPHELD-WITH-CORRECTIONS rather than a clean UPHELD. None of the
corrections touches the `RESEARCH-VALID, IMPLEMENTATION-REJECTED` outcome or the
C2-to-brief routing.
