# Five-Day Verification Audit — Options-Flow Intelligence System

**Audit role:** independent audit owner, fresh context, no authorship stake in the
audited work. Prior plans, reports, and test results were treated as claims to
verify, not instructions to defend.

## 1. Audited time window

- Start timestamp: **2026-07-28T20:35:54-04:00** (America/New_York, repo host TZ).
- Cutoff (start − 120 h): **2026-07-23T20:35:54-04:00**.
- Timestamp basis for uncommitted files: filesystem mtime (see §3 uncertainty note).

## 2. Base and ending commits

- Base (last commit at/before cutoff): `eb927c8` — 2026-07-23T12:54:39-04:00,
  "Merge branch 'main' into docs/replan-2026-07-22".
- Ending commit: `d9fc8ad` (HEAD, branch `feature/strategy-enhancement`) —
  2026-07-28T00:29:22-04:00.
- Window contents: **50 commits (39 non-merge)**, **122 tracked files changed**,
  plus the uncommitted working tree.

## 3. Scoped files

**Primary audit target (untracked, all created 2026-07-28 10:58–14:04 ET):**

- `data/options_flow/` — `__init__.py`, `raw_store.py`, `adapter.py`,
  `normalize.py`, `classify.py`, `aggregate.py`, `audit.py`
- `options_researcher/flow/` — `__init__.py`, `features.py`, `context.py`,
  `schema.py`, `display.py`, `study.py`, `analogs.py`, `opinion.py`
- `tools/options_flow.py`, `tools/options_flow_audit.py`, `tools/options_flow_analogs.py`
- `tests/test_options_flow_{adapter,analogs,audit,classification,context,features,study}.py`
- `tests/fixtures/options_flow/{trade_quote,open_interest}.jsonl`
- `docs/superpowers/plans/2026-07-28-thetadata-options-flow-intelligence-plan.md`
- `reports/options_flow/2026-07-28-implementation-audit.md`

**Unstaged tracked modifications:** `AGENTS.md` (Codex workflow guidance),
`pyrightconfig.json` (adds the two new flow paths to type checking).

**Tracked commits in window:** predominantly the 2026-07-24 integration wave
(ritual grace, IV solver, DSR/CSCV, intraday capture) and 2026-07-25 work
(research refresh, board panels, H7 scoring identity, OI Δ1d line), all
previously reviewed in earlier sessions; swept here for boundary/provenance
anomalies only (§5, P-findings), not re-reviewed line-by-line.

**Timestamp uncertainty:** untracked-file mtimes can postdate true creation if
edited after creation; all flow-system mtimes cluster tightly on 2026-07-28 and
are consistent with the plan/report's own dating, so in-window membership is not
in doubt. `__pycache__` and `.DS_Store` artifacts were excluded from scope.

## 4. Claims evaluated

From the plan and implementation-audit report: (a) nine capability additions
(timestamp-safe DTE/moneyness, IV+event context, gross-exposure proxies,
shrinkage-Mahalanobis analogs, RMS stability, pooled sensitivity, calibrated
opinions, explicit abstention, offline CLIs); (b) four defect-fix claims
(sweep/ISO separation, OI denominator dedup, after-close event leakage,
restored baseline regressor); (c) seven verification claims (31 focused tests,
2,085 full suite, ruff, pyright 0, `git diff --check`, synthetic audit PASS,
no paid/live requests); (d) display-only / fail-closed / point-in-time /
H5–H10-preserving authority claims.

**The four defect-fix claims all verify as really fixed:**

1. Sweep/ISO: only condition 95 maps to `CONFIRMED_INTERMARKET_SWEEP`; 126/128
   (auction-ISO/cross-ISO) map to AUCTION/CROSS. Externally validated
   line-by-line against ThetaData's trade-condition table (§6 Q1). **Correct.**
2. OI dedup: denominator counts each contract's OI once regardless of trade
   count (reproduced numerically). **Correct but weakly tested** — no committed
   test asserts the arithmetic.
3. Event cutoff: 16:00 America/New_York cutoff via tz-aware conversion,
   DST-verified by execution; `published ≤ cutoff` inclusive. **Correct**, with
   test gaps (no DST-crossing or exact-boundary test).
4. Baseline regressor: baseline and expanded design matrices share the named
   baseline plus context on identical complete cases (dropna over the superset
   before either fit). **Correct**, with a weak assertion in the covering test.

**Reported verification, re-audited against this session's own runs:** all
seven claims reproduced (see §9). No discrepancy found.

## 5. Findings by severity

Verdict vocabulary: CORRECT / CORRECT-WEAKLY-TESTED / PARTIALLY-CORRECT /
INCORRECT / UNSUPPORTED / BLOCKED-FROM-VERIFICATION.

### High

- **F1 — Moving-block bootstrap resamples in similarity order, not time order.**
  `options_researcher/flow/opinion.py:35-53,69-75` + `analogs.py:390-406`.
  Analogs are sorted by ascending Mahalanobis distance and never re-sorted by
  session before the block bootstrap, so "blocks" pair similarity-rank
  neighbors, not temporal neighbors. Demonstrated: identical 10 values in time
  order vs. rank-interleaved order (same seed) flip the 90% interval from
  spanning zero to excluding zero — the gate meant to prevent false-confident
  directional leans is defeatable by construction. **INCORRECT** relative to its
  stated dependence-aware purpose. → Codex brief B1.
- **F2 — `attach_prior_open_interest` enforces no temporal/session relation.**
  `data/options_flow/aggregate.py:17-35`. Join is purely on contract identity;
  an OI row dated after the trade session joins silently (reproduced). The
  point-in-time OI property currently holds only by caller convention.
  **INCORRECT as a code-enforced guarantee** (current sole caller is safe).
  → Codex brief B2.
- **F3 — Dead quotes pass the data audit clean.** `data/options_flow/
  normalize.py:157-176` + `audit.py` checks 4–8. A `bid=0, ask=0, price=0` row
  normalizes without error and `audit_options_data` returns PASS with zero
  findings (reproduced). Counterexample to the fail-closed claim. **INCORRECT**
  for this input class. → Codex brief B3.
- **F4 — Walk-forward purge width unlinked to target horizon.**
  `options_researcher/flow/study.py:97-120`. `purge_observations` is a free
  caller int (default 21, which happens to cover both `return_5` and
  `future_rv21`); `compare_walk_forward(..., target="return_5",
  purge_observations=0)` runs without error or warning (executed). Leak-by-
  configuration at any future call site. **PARTIALLY-CORRECT** (mechanism
  sound and boundary-exact; contract unenforced). → Codex brief B4.
- **F5 — The analog regime gate requires a `skew_z` column no code produces.**
  `analogs.py:167,267` demand `skew_z` (caliper ±1.0); `context.py:219` emits
  `put_skew` as a raw IV-point difference (`put25_iv − atm30`); a repo-wide
  search finds no z-scoring producer — the only `skew_z` in the repo is a
  hand-typed fixture value. The registered skew-eligibility gate cannot run as
  specified, and if raw IV differences were fed under that name the ±1.0
  caliper would pass essentially everything silently. **INCORRECT / integration
  gap**; name implies information no input supports. → Codex brief B5.
- **F22 — `rv_tercile` is a second phantom regime column** (found by the fresh
  verifier §10a; confirmed first-hand). `analogs.py:168,268` require it for the
  realized-volatility regime match; no code in the repo computes it — the only
  other occurrence is a hand-typed fixture constant
  (`tests/test_options_flow_analogs.py:30`). Same class as F5; fixing F5 alone
  would leave the regime gate equally unable to run. **INCORRECT / integration
  gap.** → Codex brief B5 (broadened).

### Medium

- **F6 — Analog outcome windows may cross the query date.** `analogs.py:206-213`:
  selection requires only `session < query`; an analog 1–4 sessions before the
  query contributes a T+5 outcome not knowable at query time in any as-of
  deployment. Valid for batch retrospection only; that restriction is nowhere
  enforced or declared. **PARTIALLY-CORRECT.** → Codex brief B6.
- **F7 — Mahalanobis/RMS Jaccard compares structurally different pools.**
  `analogs.py:387-420`: Mahalanobis neighbors come cutoff-constrained, RMS
  neighbors from the unconstrained pool capped at 20. Demonstrated: sparse pool
  → 0 vs 20 neighbors → Jaccard 0.0 → `METRIC_INSTABILITY` co-triggered by
  starvation, not metric disagreement. **PARTIALLY-CORRECT.** → Codex brief B7.
- **F8 — `matched_base_positive_frequency` is an unvalidated external input.**
  `opinion.py:56-60`, `tools/options_flow_analogs.py:39`: the base-rate gate's
  comparator is a bare CLI float with no [0,1] bounds check, no provenance, no
  prior-only proof; `None` fails closed but a wrong number silently defeats the
  gate. **CORRECT-WEAKLY-TESTED / fail-open on bad input.** → Codex brief B8.
- **F9 — Raw provider timestamp timezone is assumed, not verified.**
  `normalize.py:151-155`: `pd.to_datetime(..., utc=True)` treats tz-naive
  strings as UTC; the rest of the repo's ThetaData code treats market times as
  naive America/New_York and localizes explicitly. Fixtures are all
  `Z`-suffixed so the naive path is untested; the real feed's format is
  unverifiable offline. A naive-ET feed would shift every timestamp 4–5 h
  self-consistently (internal prior-quote checks would still pass).
  **BLOCKED-FROM-VERIFICATION**; fail-closed guard delegated (B8), format
  verification added to real-data gates (§12).
- **F10 — Plan §7 claimed unimplemented capabilities as present.** Multiplicity
  correction, ticker-aware negative controls, and dependence-aware inference
  exist nowhere in the flow code (grep-verified; the placebo is a flat seeded
  sign permutation with no ticker argument). **Documentation INCORRECT —
  corrected in-session** (§7).
- **F11 — Audit BLOCK severity is caller-controlled.** `audit.py:110-114,
  310-317`: findings on rows the caller's `tradeable_mask` marks non-tradeable
  downgrade to WARN. Judged intended design (non-tradeable rows are context,
  not gates) but it makes verdict strength contingent on an upstream mask this
  audit did not certify. **Accepted design; noted, no change.**
- **F23 — No panel-assembly layer exists between the context builders and the
  analog engine** (fresh verifier §10a; confirmed first-hand). `tools/
  options_flow_analogs.py` accepts an arbitrary external panel with zero
  in-repo producer; beyond F5/F22, `analogs.py:257-258` consumes `event_type`
  as a scalar while `context.py:20,85` produces `event_types` as a tuple
  (possibly empty/multi-valued) with no collapsing rule anywhere. F5 and F22
  are instances of this broader gap. **The analog subsystem is not wired to
  any real data path yet**; the gap must close before the three-session pilot,
  not after. → Codex brief B5 (broadened).
- **F12 — `display.py` ships no disclaimer and is unwired and untested.**
  The full noncausal/authority disclaimer attaches only on the
  `schema.build_session_record` path; `descriptive_flow_view` (docstring:
  "report-safe") renders a table with no authority field, is imported nowhere,
  and has zero tests. **PARTIALLY-CORRECT vs the display-contract claim.**
  → Codex brief B8.

### Low

- **F13** `classify.py:60-67` — `astype(int)` truncates fractional condition
  codes into potentially valid neighbors instead of rejecting. → B8.
- **F14** `classify.py:34-50` — substring-order-dependent condition-class
  mapping; correct for the current dict, fragile to future names. Noted.
- **F15** `aggregate.py:28-31` — duplicate-OI conflict check uses exact float
  equality; noise between equal observations raises rather than deduping. Noted.
- **F16** — OI-dedup arithmetic has zero direct test coverage (see §4 claim 2).
  Regression test specified in B2.
- **F17** — `tools/options_flow.py` boots LumiBot and loads `.env` on import via
  `raw_store → research.hashing`; the same banner-pollution class commit
  `8ad796f` exterminated elsewhere. Hygiene only (receipts are file-written,
  not stdout-scraped). Noted.
- **F18** — Test gaps: no DST-crossing or exact-cutoff-boundary event test; the
  walk-forward test asserts only `rmse_improvement.notna()` (a
  flow-columns-dropped regression would pass). Specified in B4/B8.
- **F19** — Analog standardization/covariance learn from the most recent ≤252
  observations while eligible candidates come from unbounded prior history;
  older candidates are z-scored against a possibly unrepresentative recent
  regime. Stationarity note; no change ordered.
- **F20** — Bootstrap small-n asymptotics caveat absent from plan §6 —
  **corrected in-session** (§7).
- **F21** — Effective-rank ≥ 0.75p gate (participation ratio) is coherent but
  its strictness is correlation-structure-dependent and uncalibrated against
  real flow-feature correlations. Real-data gate note.

### Provenance/boundary sweep (tracked commits + working tree)

- **P1 — Authority boundary INTACT.** No import of `config` strategy numbers,
  ledger, watchers, attractiveness, portfolio, dashboard, harness, or
  strategies anywhere in the flow tree; no reverse import of flow modules from
  any ranking/scoring/watcher/dashboard code; no writes to `ledger/`,
  `data/positions/`, or any H5–H10 report/receipt path. H5–H10 preserved.
- **P2 — No default-reachable network path.** The only network surface is
  `adapter.default_client()` → pre-existing `data.thetadata_adapter._client()`,
  reachable solely via an explicit human-typed `--execute`; dry-run is the
  default (verified by execution); no automation references `--execute`; no new
  HTTP/socket paths in any changed file in the window. Installed `thetadata`
  1.0.9 exposes both endpoint methods with matching signatures (verified
  against the installed package). Note: the `--execute` authority gate is a
  bare CLI flag — weaker than the repo's receipt-gated norms; acquisition
  remains blocked by the §12 gates regardless.
- **P3 — `ledger/facts.log` strictly append-only** across the window (single
  addition hunk, zero deletions; old file is an exact line-prefix of new).
- **P4 — All `config.py` constant changes in the window carry provenance
  labels** (owner-typed / owner-ratified / LLM-proposed+owner-delegated) tied
  to specific commits and specs; the four watcher/scoring diffs
  (`entry_watch.py`, `h7_real_scoring.py`, `h7_window_registration.py`,
  `h8_watch.py`) match their commit messages and tighten rather than loosen
  authority. No execution/order/broker path touched anywhere in the window.

## 6. Research used

- **Q1 Condition codes** — ThetaData "Trade Conditions" table
  (http-docs.thetadata.us, accessed 2026-07-28): every numeric ID in
  `classify.py` matches (95=ISO sweep; 125–129 single-leg auction/cross/floor;
  130–133 multi-leg; 145/146 aggressor; 40–44 cancels); 126/128 are ISO-routed
  orders *executed through* auction/cross mechanisms, so routing them to
  AUCTION/CROSS is correct. Limitation: vendor transcription of the OPRA spec;
  the primary OPRA Pillar PDF was not independently parseable this session.
- **Q2 Side inference** — Savickas & Wilson 2003 (pre-2016 foundational
  exception, JFQA; CBOE ground truth: quote rule ≈83% on options); Grauer,
  Schuster & Uhrig-Homburg (SSRN 4098475, 2022, rev. 2025: stock-style rules
  degrade on options; limit-order customers); Battalio et al. (SSRN 5907665,
  2026: consolidated-feed latency can report post-trade quote reactions before
  the trade — "prior by reported timestamp" ≠ "prior by event sequence").
  Strict-prior NBBO is the defensible rule; latency mis-ordering becomes a
  real-data audit check (§12).
- **Q3 Shrinkage** — Ledoit & Wolf 2004 (pre-2016 foundational exception) and
  2020 (Annals of Statistics): literature prefers data-driven intensity; fixed
  0.5 is heavy but fail-safe for neighbor matching (worst case: partial
  reversion toward variance-weighted Euclidean). No change ordered.
- **Q4 Block bootstrap** — Künsch/Politis-Romano foundations (pre-2016
  exceptions): consistency is asymptotic; at n=10–20 with block ≥5 only ~2–4
  blocks exist — the interval is a rough indicator, not a certified CI.
  Plan caveat added (§7); ordering defect is F1.
- **Q5 Purged walk-forward** — López de Prado 2018 ch. 7 (via secondary
  restatements): purge ≥ label horizon plus a separate embargo — confirms both
  the mechanism and finding F4's demanded contract.
- **Q6 8-K timing** — SEC Investor.gov "How to Read an 8-K": most 8-K items due
  within four business days after the triggering event — confirms
  `published_at` (not event time) as the knowability bound. (SEC rulemaking
  page returned 403 to WebFetch, the repo's documented limitation.)
- **Codex delegation** — OpenAI Codex Best Practices and Prompting docs
  (learn.chatgpt.com/guides/best-practices, /docs/prompting), GPT-5.2 Prompting
  Guide (OpenAI Cookbook), Reasoning-models guide, and the GPT-5.6 Terra model
  page (developers.openai.com): Goal/Context/Constraints/Done-when structure;
  one chat per coherent unit of work; explicit paths and exact verification
  commands; at high/xhigh effort give goals and boundaries, not step-by-step
  walkthroughs. Terra = mid-tier GPT-5.6 (1.05M ctx), `xhigh` officially
  supported.

## 7. Corrections made (this session)

Per the division-of-labor directive (Claude edits docs; Codex implements
code), only documentation defects were corrected directly:

1. Plan §7: the two present-tense bullets claiming ticker-aware negative
   controls, dependence-aware inference, and multiplicity correction were
   replaced with an explicit "registered but NOT yet implemented" statement
   (fixes F10).
2. Plan §6: added the small-sample bootstrap caveat (fixes F20).

No code, test, config, or ledger file was modified. All code fixes are
delegated via the briefs in §14.

## 8. Tests added

None in-session, deliberately: every verified code defect's regression test is
specified inside its Codex brief (§14) so that tests land in the same change as
the fix. Adding the failing tests now would leave the working tree red,
against the repo's done-and-green policy, while fixing the code here would
violate the delegation directive.

## 9. Commands run and outcomes (this session, in order)

- Focused flow suite (7 modules): **31 tests, OK, 4.5 s** — matches the
  reported claim.
- `uv run ruff check .` — **All checks passed.**
- `uv run pyright` — **0 errors, 0 warnings** (flow paths included via the
  unstaged `pyrightconfig.json`).
- `git diff --check` — clean.
- `tools/options_flow_audit.py` on the normalized fixture — **Verdict PASS,
  rows=4, findings=0, exit 0** (reproduces the reported synthetic-audit PASS).
- Three CLI default-invocation smokes — all refuse to act without explicit
  arguments; capture tool prints `dry_run=true network=false` and exits before
  any client construction.
- Installed-package check — `thetadata` 1.0.9; both adapter endpoint methods
  present with matching keyword signatures.
- Import-chain probes — LumiBot import traced to `research.hashing` (F17);
  lazy client construction confirmed network-free at import.
- Full repository suite — RESULT RECORDED IN §9a.
- Subagent verification runs (read-only): focused suites re-run independently
  by three review agents (31/31 confirmed twice), plus numerical spot-checks
  (shrinkage algebra, eigen-inverse vs `np.linalg.inv`, hand-computed
  Mahalanobis, bootstrap order-sensitivity demonstration, OI join and
  dead-quote reproductions).

### 9a. Full-suite result

`uv run python -m unittest discover -s tests` — **Ran 2,089 tests in 243.7 s,
exit 0 (all passed)**, run twice this session (both exit 0; count captured on
the second run). Consistent with the reported "2,085 passed before the
isolated CLI addition" — four tests landed after that earlier count. This
session's count includes the audited flow tests and the two §7 doc edits
(which touch no code).

## 10. Fresh-verifier findings

### 10a. Independent adversarial verification pass

A fresh Sonnet verifier with no prior conclusions was given the scope, the
original and final scoped diffs, the requirements, test results, and research
evidence, and instructed to refute the audit and hunt for what it missed.

- **F1–F5: all CONFIRMED**, each independently reproduced by direct code
  execution (bootstrap order-sensitivity with fixed seed; a June OI row
  joining January trades silently; the zero/zero row passing normalize and
  audit with zero findings; `purge_observations=0` with a `return_5` target
  running cleanly; repo-wide greps for the phantom column). The verifier also
  noted `volume_oi_ratio` sits in `DISTANCE_FEATURES`, so F2 feeds analog
  matching directly, not just display.
- **Missed by the initial audit, added as findings:** F22 (`rv_tercile`
  phantom regime column, HIGH) and F23 (no panel-assembly layer;
  `event_type` scalar-vs-tuple mismatch, MEDIUM). Both re-confirmed
  first-hand before inclusion. Brief B5 was broadened accordingly before
  finalizing the verdict.
- **Explicitly re-checked and found clean:** no cross-imports between flow
  and ranking/scoring/watcher/dashboard/ledger code; all CLIs refuse default
  action; `_prior_spike` appends to history only after scoring (genuinely
  prior-only); `merge_asof(direction="backward")` point-in-time; the
  `SESSION_PRICE_PROXY` fallback is labeled, not hidden (added to §12).
- **Audit session's own edits:** no defects found; file:line anchors verified;
  no banned backtest vocabulary; no unrelated changes. Full suite re-run
  independently: 2,089 tests, OK. Verifier's overall assessment: NEEDS REPAIR
  is correct "and if anything slightly conservative"; B1–B4 well-scoped;
  B5-as-originally-scoped incomplete (hence the broadening).

## 11. Unrelated changes preserved

Untouched and intentionally excluded from audit depth (in-window by mtime,
unrelated to the flow system): `reports/attractiveness_critic/2026-07-27-critic-report.md`
(self-labeled LEGACY/UNTRUSTED critic artifact), `reports/crwv_options_review/2026-07-28/`
(CRWV chain-review data bundle; contains a gitignored `.DS_Store`), and all
tracked in-window commits outside the boundary sweep. No working-tree change
outside the two §7 doc edits was made by this audit.

## 12. Remaining real-data gates (unchanged by this audit, plus additions)

Still open from the plan (§9): entitlement + endpoint column verification;
retention/derived-data rights; three-session pilot + executable audit on real
data; storage cap measurement; explicit owner approval for the bounded paid
pull. **Added by this audit:** (a) verify the real feed's timestamp timezone/
format before trusting any point-in-time property (F9); (b) add a
latency-reordering check to the executable audit before trusting strict-prior
side inference on real data (Battalio et al. 2026); (c) calibrate the
effective-rank gate and starvation projections on the real panel (F21, and the
plan's own CEG/VST warning); (d) the `SESSION_PRICE_PROXY` moneyness fallback
applies one session price uniformly across a day's trades — labeled, not
hidden, but early-session trades under it carry soft same-day information;
measure its share on real data before trusting proxy-sourced moneyness
features (fresh-verifier note). Synthetic-test success establishes none of
these.

## 13. Final verdict

> **Superseded 2026-07-29 by §15:** all high-severity defects repaired and
> independently verified — **VERIFIED WITH FIXES** (software scope only).
> The 2026-07-28 verdict below is preserved unedited as the audit-time record.

**NEEDS REPAIR.**

Six high-severity defects are verified and unrepaired in code (F1–F5, F22,
plus the F23 assembly gap they instantiate); fixes are fully specified and
delegated (§14) per the standing division of labor, and the fresh verifier
independently confirmed every high finding and the verdict.
The system's authority claims — display-only, H5–H10 untouched, no
default-reachable paid path, append-only ledger — all verified INTACT, and the
four previously reported defect fixes are real. Software correctness remains
separate from empirical validity: even after F1–F5 are repaired and verified,
every §12 real-data gate still stands; nothing here is evidence of edge, and a
clean audit of synthetic behavior does not pass the historical-data gate.

## 14. Codex delegation plan — fix briefs (Terra, reasoning effort xhigh)

Per OpenAI's official guidance (§6): **eight small scoped briefs, not one
combined prompt** — one chat per coherent unit of work, each with explicit
paths, minimal-fix boundaries, and exact "done when" commands. At xhigh
effort, briefs state goals and boundaries, not step-by-step implementations.
Run order: B1–B5 first (high severity); B6/B7 after B1 (all touch
`analogs.py`/`opinion.py` — run sequentially, never in parallel worktrees);
B8 last (independent small hardenings). After each brief: run its Done-when
commands; after the last: full suite + ruff + pyright must be green.

Shared constraints for every brief (paste into each Codex session):

> Research-only repo; never place orders, never call ThetaData or any network
> endpoint; tests must run offline. Keep the fix minimal — no refactors, no new
> abstractions, no surrounding cleanup. Do not weaken any existing test,
> abstention path, or fail-closed behavior. Every new threshold/constant goes
> to an explicit named location, provenance-labeled "audit-directed
> 2026-07-28". Do not touch `ledger/`, `config.py` strategy numbers, or any
> `h5`–`h10`/watcher/dashboard file. Verify with:
> `uv run python -m unittest discover -s tests`, `uv run ruff check .`,
> `uv run pyright`.

**B1 — Bootstrap must resample in time order (F1, HIGH).**
Goal: `synthesize_historical_opinion`'s moving-block bootstrap operates on
analog outcomes sorted chronologically by analog session, so blocks pair
temporal neighbors. Context: `options_researcher/flow/opinion.py:35-53,69-75`;
analogs arrive distance-sorted from `analogs.py:390-406`. Constraints: keep
the interval deterministic (seeded) and the public signature stable; do not
change gate thresholds. Done when: a new test feeds identical outcome values
in two different input orders and asserts the interval is identical (order
established from session dates inside the function), plus existing
`tests/test_options_flow_analogs.py` stays green.

**B2 — Temporal guard in `attach_prior_open_interest` (F2, HIGH).**
Goal: the OI join refuses (raises) any OI observation not strictly prior-known
relative to the trade session, so point-in-time OI is code-enforced, not
caller-convention. Context: `data/options_flow/aggregate.py:17-35`; the OI
frame carries its own timestamp/session fields from `normalize.py`. Constraints:
missing OI must remain missing-and-present (never zero, never dropped);
existing sole caller in `options_researcher/flow/features.py` must still pass.
Done when: new tests prove (a) an OI row dated after the trade session raises,
(b) same-session prior-known OI joins, (c) the N-trades/one-contract
denominator equals the single OI value (closes the F16 coverage gap).

**B3 — Dead-quote detection in the executable audit (F3, HIGH).**
Goal: a trade row whose bid and ask are both non-positive (dead market) can
never contribute to a PASS silently — it must surface as a finding, BLOCK-level
for tradeable rows. Context: `data/options_flow/audit.py` checks 4–8;
`normalize.py:157-176` (relative_spread NaN-suppression is how it slips
through). Constraints: add a check, don't rewrite existing ones; no row
dropping. Done when: a new test with `bid=0, ask=0, price=0` yields a
non-PASS verdict with an explicit finding, and the clean-fixture test still
returns PASS.

**B4 — Purge width must cover the target horizon (F4, HIGH).**
Goal: `compare_walk_forward` cannot run with a purge smaller than the target's
look-ahead horizon. Context: `options_researcher/flow/study.py:87-129`;
`make_forward_labels` knows each label's horizon (return_5 → 5, future_rv21 →
21). Constraints: make the horizon an explicit required parameter (or derived
from a declared label→horizon mapping) and validate `purge_observations >=
horizon`; keep `WalkForwardSplitter` untouched. Done when: a new test asserts
`purge_observations < horizon` raises, an equal-boundary case runs, and a
positive-signal test asserts `rmse_improvement` actually improves when the
target depends on a flow column (closing the `notna()`-only gap, F18).

**B5 — Build the analog panel-assembly layer: every regime column must have a
real prior-only producer (F5, F22, F23; HIGH).**
Goal: every column `match_historical_analogs` requires exists with an in-repo,
prior-only, tested producer — no phantom columns, no hand-typed panel fields.
Specifically: (1) `skew_z` — a prior-only z-score of `put_skew` (e.g., against
the same 252-session window the IV percentile uses), or rename the field and
re-derive the caliper to match raw units; (2) `rv_tercile` — a prior-only
realized-volatility tercile with a declared estimator and window; (3)
`event_type` — a declared, tested rule collapsing `EventContext.event_types`
(a tuple, possibly empty or multi-valued) to the scalar the gate compares,
including what the no-event and multi-event cases map to. Context:
`options_researcher/flow/analogs.py:163-168,257-268`,
`options_researcher/flow/context.py:20,85,212-221`; the only current `skew_z`/
`rv_tercile` values in the repo are fixture constants
(`tests/test_options_flow_analogs.py:29-30`). Constraints: all computations
prior-only; explicit unknown state → abstention when history is insufficient
(never a default); do not change the ±1.0 caliper or the tercile gate
semantics without renaming them. Done when: tests compute each column from
constructed prior windows verifying value and insufficient-history abstention;
analog tests consume produced columns instead of hand-typed constants; a
panel assembled end-to-end from `context.py`/`features.py` outputs feeds
`match_historical_analogs` without KeyError.

**B6 — Analog outcome knowability (F6, MEDIUM).** Goal: either (a) analog
selection for opinion inputs requires `analog session + outcome horizon ≤
query session`, or (b) the module explicitly declares batch-retrospective-only
semantics in its docstring/schema and the opinion output labels it. Decide (a)
unless it starves the sample below the plan's own minimums in the synthetic
tests; then implement (b). Context: `analogs.py:206-213`, `_nonoverlapping`.
Done when: a test proves an analog 2 sessions before the query cannot
contribute a T+5 outcome to a lean under (a), or the batch-only label is
asserted under (b).

**B7 — Jaccard pool parity (F7, MEDIUM).** Goal: `metric_jaccard` compares
like with like: RMS neighbors drawn under an equivalent outcome-blind
cutoff/pool discipline as Mahalanobis neighbors, so `METRIC_INSTABILITY`
means metric disagreement, not cutoff starvation. Context:
`analogs.py:387-421`. Done when: the sparse-pool scenario (24 eligible rows)
no longer yields a 0-vs-20 comparison; starvation surfaces as the existing
insufficient-analogs state instead.

**B8 — Fail-closed input hardening batch (F8, F9, F12, F13, F18; LOW/MED).**
One session, four independent small guards, each with its own test:
(1) `opinion.py`/`tools/options_flow_analogs.py`: reject
`matched_base_positive_frequency` outside [0,1] (None stays valid and
abstaining). (2) `data/options_flow/normalize.py`: reject tz-naive raw
timestamps with a message pointing to the entitlement-probe gate (fixtures are
`Z`-suffixed and must still pass). (3) `data/options_flow/classify.py`: reject
non-integral condition codes instead of truncating. (4) either wire
`options_researcher/flow/display.py:descriptive_flow_view` to carry the
authority/disclaimer field and add its first test, or delete the module if the
owner confirms it is dead — do not leave it shipped, unwired, and untested.
Also add the two context-boundary tests from F18 (DST-crossing session;
`published_at == cutoff` inclusive boundary). Done when: each guard has a
failing-input test and all prior tests stay green.

---

## 15. Batch repair verification addendum (2026-07-29)

An external Codex session applied all eight briefs between 2026-07-28 22:40
and 2026-07-29 09:10 ET (B2–B4 evening; B5's new
`options_researcher/flow/panel.py` + tests after midnight; B6/B7 rewriting
`analogs.py` and B8 finishing 09:10). Verification was independent throughout:
Codex's completion reports were treated as claims.

**Method.** (1) B1 red-green verified 07-28 (revert → test fails → restore →
passes). (2) Three read-only Sonnet verifiers on 07-29 — data guards
(B2/B3/B8), statistics (B4–B7), integration/boundary — each re-executing the
original defect inputs from §5 against the fixed code plus adversarial edge
probes (equality boundaries, non-UTC offsets, NaN/inf, the 24-row pathological
Jaccard pool, future-row mutation leakage probes, an engineered genuine
Mahalanobis-vs-RMS disagreement). (3) Red-green by this session on all seven
remaining small guards with byte-exact restores — **all seven OK** (each
checked-in test fails when its guard is neutralized). (4) Static checks and
the full suite.

**Per-brief verdicts.** B1, B2, B3, B5, B7, B8 (all four guards): **VERIFIED**.
B4, B6: **VERIFIED-WITH-CAVEAT** — each brief's contract is met (under-purge
now raises; a T+5 outcome unknowable at query time can no longer reach a
lean), with residuals R1/R2 below. No pre-existing test was deleted or
weakened (all ten audit-era data-layer tests and all four analog tests present
with original assertions); registered numerics unchanged (0.5 shrinkage,
eigenvalue floor, 0.75p participation-ratio gate, outcome-blind cutoff);
authority/network boundary re-swept clean; the audit artifacts themselves
untouched by Codex; `wiki/log.md` gained one benign append-only RAG-health
entry (preserved).

**Residuals (none reproduce an original high defect):**

- **R1 (from B4):** `target_horizon_observations` is caller-declared and not
  cross-checked against the target — `target="return_5"` with a declared
  horizon of 1 was demonstrated to under-purge silently. Original defect
  (no enforcement at all) is fixed; this is a misuse-hardening gap.
- **R2 (from B6):** non-T+5 outcome columns (`return_21`, `future_rv21`)
  in per-analog records are not knowability-gated and ship unlabeled in the
  CLI JSON; `opinion.py` never reads them, so no lean is contaminated.
- **R3:** `aggregate.py`'s own `pd.to_datetime(..., utc=True)` calls would
  accept naive timestamps if a future caller bypassed `normalize_*`
  (unreachable today; F9's guard lives in `normalize.py`).
- **R4:** the F18 boundary pair tests inclusion at the exact cutoff but
  exclusion only at +1 h, not +1 s. F15 (float-equality OI dedup) remains a
  noted low item with no test; F17 (LumiBot import on capture-tool import)
  remains open by design.

**Methodology note:** one red-green cycle (B3) initially reported a
post-restore failure caused by Python's mtime+size `.pyc` validation serving
stale mutated bytecode after a same-length, same-second restore — an artifact
of this audit's harness, not a repo defect; re-run with cache invalidation:
clean.

**Commands and outcomes (2026-07-29):** focused flow suite 51/51 (run
independently by all three verifiers and this session); `uv run ruff check .`
passed; `uv run pyright` 0 errors; `git diff --check` clean; red-green driver
7/7 OK; full suite **2,109 tests, exit 0** (baseline 2,089 + exactly the 20
new focused tests).

**Follow-up brief B9 (residual hardening, one Codex session, optional but
recommended before real-data wiring; same shared constraints as §14):**
Goal: close R1–R4. (1) `study.py`: derive/validate the horizon from a declared
`{target → horizon}` mapping (e.g. `return_1:1, return_5:5, future_rv21:21`)
so a wrong declared horizon raises; (2) `analogs.py`/CLI: strip, gate per
horizon, or explicitly label non-T+5 outcome fields in per-analog records;
(3) `aggregate.py`: route its datetime parsing through the same naive-
timestamp rejection `normalize.py` uses; (4) add the cutoff+1s exclusion test.
Done when: each item has a failing-input or boundary test and the full suite
stays green.

**Re-verdict: VERIFIED WITH FIXES** — software scope only. All six
high-severity defects (F1–F5, F22) and the F23 assembly gap are repaired and
independently verified; the analog panel now assembles end-to-end from real
producers with fail-closed abstention. Every §12 real-data gate remains open
and binding: nothing in this addendum authorizes a paid pull, constitutes
data validation, or is evidence of edge.

---

*Audit performed 2026-07-28 by the independent audit session; subagent
workstreams: data-layer review, features/context/study review,
analogs/opinion statistical review, provenance/boundary sweep,
market-structure & statistics research, Codex-guidance research, plus a fresh
adversarial verifier (§10a). Batch repair verification (§15) performed
2026-07-29 with three additional independent verifiers and a red-green pass.
No paid or live data request was made at any point.*
