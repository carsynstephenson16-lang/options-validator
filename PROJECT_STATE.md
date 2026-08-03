# PROJECT_STATE — verified narrow path (CANONICAL)

**Audit date:** 2026-08-02

**Authority:** this is the repository's single current status and execution plan. Older plans and reports remain evidence or history; they are not an active queue.

**Checkout audited:** `/Users/carsynstephenson/options-validator`, branch `sfix`, HEAD `217a4c5e5e44303f98acb5e0f4f3913a6e208c59`.

**Original audit boundary:** read-only except for this file. No provider call,
package change, ledger/facts append, cache mutation, one-run mutation, live-book
mutation, Git write, or branch switch occurred during the planning audit.

**Execution update (2026-07-31):** the owner approved P0.6 and P0.8. The exact
report-13 correction was appended once through `research.facts.append_fact`
(`2026-08-01T00:20:49.515344+00:00`, payload SHA-256 `c489eb179e…e8`).
Strategy A now requires both exact-leg current-session bars before submission
and conservatively unwinds, costs, records, and aborts any unexpected one-leg
fill. No provider call, cache mutation, prior-result reinterpretation, verdict
change, one-run mutation, or paper-book edit occurred.

**Closeout update (2026-08-02; supersedes older task-status wording below):**
the canonical v1 manifest now verifies all 31,366 top-level files. The 33 July
24/27 files are reconciled, and the nested SPY snapshot is preserved as a
classified noncanonical alternate. The repeatable `$600` cap audit passes over
4,002 chain-days with zero allowed-fill breaches. The offline-readiness audit
passes and the options-flow lane remains DATA-GATED because no real
trade-and-quote panel exists. A separately approved v2 capture was completed
and audited on `codex/od1-v2-current`, but the branch is intentionally unmerged
pending explicit integration authority. H7 will not restart now; any later
restart requires a new registration and namespace. No strategy has demonstrated
an advantage.

## 1. Executive verdict

The Fable handoff is directionally useful but not safe as the sole execution plan.
Its claims for P0.1, P0.2, P0.4, and P0.5 are supported by current code, tests,
history, and ledger verification. P0.3's implementation and differing-quote tests
are also supported, but its dataset-wide measurement exists only as a prose report,
not as a rerunnable repository command. P0.6 and P0.8 are now complete.

The later Fable review corrected one classification and confirmed one blocker:

1. H6's hard-kill is implemented exactly as registered: three consecutive
   calendar months each realizing the full `$2,000` monthly cap as losses. That
   rule has design limitations, but changing it would be a prospective H6
   amendment, not a bug fix. It is therefore P2.5, not P0.7. The current book has
   one open and zero completed positions, so the kill rule has no present
   adjudication exposure.
2. Strategy A's separate-leg submission needed a same-session safety boundary.
   Owner-approved option (b) is now implemented without SMART_LIMIT or a pricing
   change: missing bars block submission, and an unexpected partial fill is
   conservatively unwound, costed, recorded, and fails the run.

P0.3-P0.6 and P0.8 are closed; the former P0.7 is now P2.5. The provider,
manifest, and exact-session foundation is closed. H7 remains paused, and richer
data stays isolated until a separate integration decision.
ThetaData Options Intelligence stays active as an offline lane; the separate
options-flow study remains DATA-GATED because no real trade/quote panel exists.

## 2. P0 in plain language

- **Ratios and drawdown ordering protect honest reporting.** Dividing total P&L
  by an average risk amount inflated magnitudes by the number of trades. Ordering
  closed trades differently changes the path and drawdown even when total P&L is
  unchanged. The repaired metric is descriptive, and the approved append-only
  correction is now present exactly once.
- **Fill rules protect the `$600` risk ceiling.** A spread selected on Thursday
  can have a worse executable credit on Friday. Worse credit raises maximum loss,
  can reduce allowable contracts, changes commissions, creates skipped trades,
  and can select a systematically easier subset. Assuming identical quotes makes
  a backtest look cleaner and can breach the declared cap.
- **Dates define the experiment.** Decision date, fill date, and exit date affect
  DTE, earnings/event eligibility, cohort membership, returns, holding periods,
  and drawdown order. `entry_date=fill session` with a separate
  `entry_decision_date` is now registered for future PutCreditSpread backtests;
  silently changing either would change the estimand.
- **Terminal exits need an honest exception.** An ordinary triggered exit is a
  next-session engine fill. When the dataset ends and no next session exists, the
  code now records a same-session conservative mark with explicit
  `exit_execution=terminal_conservative_mark`; it must never masquerade as a real
  next-session fill.
- **Governance must describe executable behavior.** A green suite only proves
  tested behavior. If ledger text, config, instructions, or facts describe a
  different convention, later agents can unknowingly mix incompatible results.
- **Why some conclusions still wait.** The P0 cap, reporting, date, terminal-exit,
  and atomicity defects are closed. Provider, cache-manifest, exact-as-of, and
  namespace gates still apply independently; read-only inspection continues.

## 3. Repository, branch, and evidence baseline

### 3.1 Git and worktrees

- `sfix` is at `217a4c5`; it tracks `origin/sfix` at the same SHA. `main` is at
  `ecdaeb9` in `/Users/carsynstephenson/options-validator-ops`.
- The locally cached `origin/main` is `5165144`, an ancestor of local `main`;
  this audit did not fetch the network, so no claim is made that the remote
  server still has that tip.
- `main` is an ancestor of `sfix`. Merge `9cf3ee4` has parents `61f7559` and
  `ecdaeb9`; `sfix` also reaches `88ffbb6`, `5626c3f`, `a48a7fd`, and
  `217a4c5`. The listed SHAs were inspected and are accessible.
- Later commits do not reverse the ratio, causal-fill, or terminal-exit fixes.
  They add the registered hybrid fill policy and governance documentation.
- The worktree was already dirty before this audit: the owner's unrelated edits
  in `ov/CLAUDE-md-ADDITIONS.md` remain untouched. This plan is the only audit
  write.
- Multiple active and stale-looking branches/worktrees exist. Names alone are
  not deletion proof. Classify reachability, open PRs, worktree attachment,
  unique commits, and owner intent before deleting anything.
- Attached worktrees include `deploy/research` (`f9f7d31`),
  `codex/cache-schema-v2` (`8fa0637`), `codex/causal-fill-convention`
  (`5165144`), dashboard freshness, two Luna lanes, evidence packet 8, and root
  cache hardening. Attachment itself is a preservation signal until classified.

### 3.2 Current verification

| Check | Result | Interpretation |
|---|---|---|
| `uv run python -m research.cli verify` | `ledger OK` | Research chain verified now. |
| `uv run python -m options_researcher.h7_event_ledger verify` | `VALID records=1 head=a1ea228c2abb…` | H7 store has one registration event and its README now states that explicitly. |
| P0-focused unit set | 51/51 passed | Ratio, ordering, D+1, ordinary/terminal exits, same/different quotes. |
| Provider/H5/H6/H8/flow/cache-focused set | 184/184 passed | Present behavior is pinned; some tests pin the H6 defect rather than disprove it. |
| Discovery audit | 2,284 tests discovered and executed under `tests/` | The current root test collection includes the manifest, cap, provider-disable, exact-session, and receipt-stability regressions. |
| `uv run python -m unittest discover -s tests` | 2,284/2,284 passed in 333.781s | Current full root result. Logged exceptions/retries are asserted mocks/fail-closed fixtures. |
| `uv run ruff check .` | passed | Same lint command as CI. |
| `uv run pyright` | 0 errors/warnings | Same type command as CI. |
| `uv run ruff format --check .` | failed: 260 would reformat | Pre-existing format baseline; CI does not run this command. Do not mass-format during scoped fixes. |
| `git diff --check` | passed | Existing user diff has no whitespace error. |
| `uv run python tools/cache_manifest.py verify` | `verify: OK` | All 31,366 canonical top-level files are hash/size bound. |

CI in `.github/workflows/ci.yml:13-55` runs frozen dependency sync, Ruff lint,
Pyright, unittest discovery, and gitleaks. It does not run Ruff format. Push CI
targets `main` and the obsolete `phase-1a-research-integrity` branch, while PR CI
runs for all branches. `.github/workflows/claude-review.yml` is configured but
repository evidence does not show a successful review post; configuration is not
operational proof.

### 3.3 Instruction drift (reconciled by Q1)

The root `AGENTS.md`, `CLAUDE.md`, `.cursorrules`, `pyproject.toml`, CI, and the
nested `.claude/rules/` files apply. The original audit found three stale
claims: the backtest rule treated F1-F6 as open, the H7 README treated the real
store as empty, and the provider document treated D+1 registration as owed.
Q1 corrected those claims to cite research-ledger seq 21, the one-record H7
registration store, and the current provider policy. The original audit text
is historical evidence; canonical code and append-only records remain the
truth.

## 4. Fable-versus-Sol roadmap matrix

Surface codes: **V** registered verdict, **F** facts ledger, **B** live/paper
book, **C** v1 cache bytes, **R** one-run record, **P** provider call. “None”
means the task can be scoped to avoid all six.

| ID | Fable claim | Repository evidence | Sol assessment and status | Next action and completion proof | Dependency / owner / surfaces / ordering |
|---|---|---|---|---|---|
| P0.1 | Branch reconciliation complete. | `git merge-base --is-ancestor main sfix`=0; `9cf3ee4` reaches `ecdaeb9`; `sfix` reaches all named fixes. | **VERIFIED COMPLETE WITH RESIDUAL RISK.** Main remains behind sfix; remote branch topology is untidy. | Leave history unchanged; later branch inventory identifies unique commits and worktree/PR ownership. Proof: signed-off branch table, not deletion. | None / no / None / keep complete. |
| P0.2 | Ratio and stable entry-date drawdown fixed by `5626c3f`. | `metrics.py:515-522`; `tests/test_core.py:289-300`; `tests/test_metrics_capital_family.py:60-75`; focused and full suites pass. | **VERIFIED COMPLETE.** The 13.64% regression and shuffle-invariance are current proof. | No code action. Preserve exact metric name `closed_trade_pnl_drawdown`. | P0.1 / no / None / keep. |
| P0.3 | OD-A cap mechanism implemented and dataset breach measured. | Ledger seq 21; strategy code/tests; `tools/strategy_a_cap_audit.py`; permanent receipt. | **VERIFIED COMPLETE.** The repeatable 4,002-chain-day audit found 89 allowed fills, highest risk `$556.80`, and zero `$600` breaches. | Preserve the tool and receipt; report cancellation/resize sample effects with any future result. | P0.1 / completed owner gate / None if offline / complete. |
| P0.4 | Terminal crash fixed; ordinary exits stay next-session. | `put_credit_spread.py` exit queue/terminal branch; `tests/test_causal_fill_convention.py`; full suite. | **VERIFIED COMPLETE.** Dec. 30/final-session metadata and normal next-session behavior are separately tested. | No action beyond stale-doc cleanup. | P0.1 / no / None / keep. |
| P0.5 | F2/F6 registered. | `ledger/experiments.jsonl:22` seq 21 hash `a540a074…`; config cites it; ledger verify passes. | **VERIFIED COMPLETE.** Scope is future PutCreditSpread only; no H1/H2 retrofit or H6/H7/H8 amendment. | Correct stale instruction/provider docs. Proof: docs quote seq 21 without changing code or ledger. | P0.1 / owner already typed / None / keep. |
| P0.6 | Append correction fact after owner approval. | Report 13 exact payload and reviews; `research.facts.append_fact`; facts are unchained. | **VERIFIED COMPLETE.** Owner approved the exact text; the API appended one line at `2026-08-01T00:20:49.515344+00:00`. Payload SHA-256 is `c489eb179e…e8`; duplicate count is one. | Keep the prior facts immutable; verify the research and H7 ledgers separately because neither validates `facts.log`. | P0.2 / owner approved / F / complete. |
| P2.5 (formerly P0.7) | Prospective H6 hard-kill amendment. | Registered H6 wording requires three calendar months each losing the full `$2,000` cap; `_hard_kill` implements that literally. The book has one open and zero completed positions. | **OWNER-GATED AMENDMENT / NOT A P0 BLOCKER.** Partial-deployment, entry-month, and H8-aware alternatives may be better designs, but they are not corrections to current code. | Leave current H6 meaning unchanged. If revisited, create a prospective version under the amendment process; never reinterpret existing rows. | Provider/data gates + later owner amendment / **yes** / V,B / P2.5. |
| P0.8 | Strategy A same-bar atomicity. | Owner approved D7a option (b); `put_credit_spread.py` now preflights both exact-leg current-session bars and handles a one-leg fill with a conservative same-session unwind record plus fail-loud abort. | **VERIFIED COMPLETE.** SMART_LIMIT and the frozen cost model are unchanged. The red test failed before implementation and the focused 22-test execution set passes after it. | Preserve the no-naked-leg invariant and incident cost record. Do not reinterpret prior results. | P0.5 / owner approved / None / complete. |
| P1.1 | Decide OD-1, OD-2, OD-4 before cancellation. | Initial closeout fact plus later bounded v2 approval token and isolated capture receipts. | **VERIFIED COMPLETE.** OD-2 remained declined; OD-1 was later reversed only for the isolated 18-symbol capture. Acquisition is now disabled. | Make zero new provider calls; preserve v1 and keep richer-data branches parked until explicitly integrated. | P0 / owner approved / F / complete. |
| P1.2 | Execute approved final pulls. | Canonical top-up declined; one later bounded v2 capture completed only in an isolated namespace. | **COMPLETE / CLOSED.** No new acquisition is permitted. The isolated v2 bytes do not alter v1 or authorize strategy use. | Preserve receipts and fail closed on missing data. | OD-1/2/4 / completed owner gate / C,P,F / complete. |
| P1.3 | All watches/features fail closed past coverage. | Exact-session market-data checks and mismatch/old-data refusals are implemented and tested across authoritative consumers. | **VERIFIED COMPLETE.** Missing, stale, or mismatched inputs do not yield a decision-authoritative signal. | Preserve exact-session tests as consumers evolve. | P1.4 / no / None / complete. |
| P1.4 | Remove dead ThetaData configuration after cancel. | Central owner-frozen disable policy gates the sole client constructor plus every acquisition boundary. Cached reads remain enabled; live provider selection is explicit Schwab-or-error. | **VERIFIED COMPLETE.** Zero-call sentinel tests prove refusal before construction/mutation and successful cached replay. | Preserve the hard disable and immutable cached reads. Proof: `reports/provider-transition/2026-07-31-q7-provider-disabled-proof.md`. | P1.1/Q6 / no / None; P avoided by tests / complete. |
| P1.5 (new) | Bind newest cache bytes. | Manifest verifies 31,366 canonical files; all 33 July 24/27 additions are included. The nested SPY file is classified noncanonical without rewriting it. | **VERIFIED COMPLETE.** July 27 is now the bound cache edge where present. | Never edit canonical market bytes in place; update the manifest only for a separately approved future acquisition. | P1.1/1.2 / complete / F, not C bytes / complete. |
| P2.1 | OD-3 governs H7 continuation. | H7 ledger verifies one unchanged July 20 registration. Restart review found no post-edge source or sufficient feasibility evidence. | **DECIDED: DO NOT RESTART NOW.** Any later restart must use a new registration and namespace. | Keep `h7-forward-15-v1` unchanged; satisfy the eight-item restart contract before requesting activation. | New data/feasibility/owner activation / yes later / V,F,P depending data / paused. |
| P2.2 | Merge v2 gate branch and rebuild H6/H8 with direct-v2 checks. | `codex/od1-v2-current` holds 4,608 audited v2 partitions; three partitions are quarantined; full audit has zero effective blockers. | **AUDITED BUT PARKED / UNMERGED.** The completed data audit is not integration authority and is not strategy evidence. | Preserve the branch and receipts. Merge or rebuild nothing unless the owner explicitly authorizes integration after reviewing the quarantines and warning profile. | Explicit integration decision / **yes** / C,P,V / parked. |
| P2.3 | Same-bar atomicity. | See P0.8. | **COMPLETE AS P0.8.** | No separate P2 task remains. | P0.8 / no / None / remove duplicate. |
| P2.4 | Resume evidence upgrade after review lane posts. | Workflow exists; decision log D40 records no demonstrated PR review. | **CONDITION-DEPENDENT.** | Owner enables/configures lane; prove on a no-authority PR; only then resume packet 5B. | External console/secret / **yes** / none / keep conditional. |
| P3 NAV | Spec exists. | `docs/superpowers/specs/2026-07-30-daily-nav-drawdown.md`; daily marks remain absent and chunked capital resets require a stitching decision. Defect-A language now reflects P0.2. | **PARKED.** | Later choose per-chunk vs stitched NAV and register any verdict use. | P0.8 satisfied; owner methodology decision / yes later / V if promoted / keep parked. |
| P3 1pm→2pm | Register after history/feasibility. | 13:00 display recorder exists; 180 cached intraday parquet captures; no historical intraday Greeks entitlement. | **DATA-GATED / PARKED.** | Accumulate receipt-bound captures; inventory effective sessions; run feasibility gate before drafting a new hypothesis. Never retrofit H7. | Enough history + owner registration / yes later / V,P / keep. |
| P3 feed inclusion | Broader Session-4 work parked. | Current feed truncates at first causal delta admission; future-delta regression passes. Earlier measurement found 0/310 trades changed. | **VERIFIED COMPLETE for the actual causality defect; broader admit-all work OBSOLETE.** | Leave code unchanged. Reopen only on measured missing-eligible-contract evidence. | None / no / None / remove from queue. |
| P3 skills | Consolidate and verify `/context`. | `.agents/skills` has 13; `.claude/skills` has 13 symlinks plus local `research-refresh`; symlink targets resolve. | **PARTIALLY COMPLETE.** Filesystem wiring is good; runtime `/context` is owner/tool-specific and unverified here. | Owner runs `/context`; document expected 14 entries and resolve only an actual discrepancy. | Cursor/Claude runtime / owner action / None / shrink. |
| P3 hook | Move live-trading hook to tracked `.agents/hooks` with tests. | Live hook is local/ignored under `.claude/hooks`; tracked hook directory contains ledger guard; no live-hook tests found. | **READY NOW after P0 docs.** | Add tracked hook + deterministic tests, then update local registration. Proof: malicious/benign fixtures, fail-closed missing input, full suite. | None / owner only for local settings if needed / None / move before cleanup deletion. |
| P3 ov | Deduplicate bundle. | `ov` is an installable standalone bundle; 9 skills, six byte-identical with repo skills, two divergent, one bundle-only. Owner WIP exists there. | **CONSOLIDATE, DO NOT DELETE.** | Add source-of-truth manifest/sync/check process that preserves standalone installability and intentional divergences. | Preserve user WIP / no / None / split from skills runtime. |
| P3 archive | Sweep superseded plans. | No archive convention exists; canonical file says history stays in place; documents retain evidence value. | **CONTRADICTED.** Broad moves/deletes would break references and context. | Add status headers/index in scoped batches; only archive after a tracked convention and reference scan. | None / owner for destructive moves / None / replace sweep with classification. |

## 5. Verified completed work

1. Branch ancestry and all four requested SHAs are present and inspected.
2. Sum-over-sum economic-max-loss return, zero anchor, and stable entry-date
   ordering are executable and tested.
3. D+1 exact-leg freeze, adverse-credit cancellation, allowed-boundary resize,
   and never-increase/no-reselect behavior are executable and tested.
4. Ordinary next-session exit and terminal conservative-mark exception are
   distinct, metadata-bearing paths with year-boundary regressions.
5. OD-A/OD-B convention is owner-typed in chained ledger seq 21; both ledgers
   verify now.
6. The exact reviewed metric correction is appended once through the facts API;
   it changes no verdict, holdout, cache, one-run record, or paper book.
7. Strategy A blocks entry before either order without both same-session leg
   bars; an unexpected one-leg fill is conservatively unwound, fully costed,
   recorded, removed from strategy state, and aborts the run.
8. Options-flow software high-severity defects and panel assembly were repaired
   in commit `c382489`, with current focused tests passing. This is software
   verification only, not real-data validation or edge evidence.
9. CI unittest discovery currently reaches all 144 modules under `tests/` and
   2,237 tests; 11 tracked `tools/repo_rag/tests/` modules remain outside it.

## 6. Safe work available now

Safe without closing the owner gates:

- Correct stale documentation against current code and append-only records.
- Add read-only, deterministic audit commands and receipt schemas without
  running a backtest or changing a verdict.
- Inventory frozen EOD and intraday data; verify schemas, hashes, duplicates,
  as-of labels, and consumer dependencies.
- Design and test provider-disabled cached replay with all transports mocked to
  raise if constructed.
- Fix H5's mismatched-as-of FIRE path, because failing closed does not change a
  registered threshold or create authority.
- Prepare a prospective H6 amendment only if the owner later chooses to revisit
  the registered rule; do not alter current rows or meanings.
- Continue offline Options Intelligence feasibility work on EOD chain fields.
- Keep the real options-flow empirical lane visibly DATA-GATED instead of
  deleting it.

Still blocked where separately noted: changes to H1/H2/H9 or any live/paper
book; new registrations; DATA_PULL facts; v1 byte edits; one-run edits;
unapproved provider calls; integration of parked richer-data branches; and
activation of new H6/H7 semantics.

## 7. Owner decision packets

The wording below is approval-ready but **must not be treated as approval or
appended by this audit**.

### OD-A / F1 — completed historical decision

- **Decision/choices:** resize at fill; cancel beyond tolerance; accept/disclose;
  or the implemented hybrid. **Owner/Fable/Sol:** owner selected hybrid cancel
  beyond `$0.01` plus resize at the allowed boundary; Fable preferred cancel-only;
  Sol agrees with the landed hybrid because it preserves more valid exposure
  while maintaining the cap.
- **Effects/failures:** resize changes quantity and commissions but preserves an
  intent; cancel changes sample composition; accept can breach risk; pre-sizing
  all trades at worst tolerance unnecessarily under-deploys. Governance is bound
  by seq 21; no prior result is retrofitted. Safe default remains cancel.
- **Evidence:** ledger seq 21; report 16; causal-fill tests.
- **Typed record already present:** the exact `STRATEGY_A_EXECUTION_CONVENTION_REGISTRATION`
  text in `ledger/experiments.jsonl:22`. No further owner action.

### F2 entry-date semantics — completed historical decision

- **Decision/choices:** `entry_date` decision session or fill session. Owner and
  Fable chose fill session with retained `entry_decision_date`; Sol agrees.
- **Effect/failure:** decision-session naming misstates exposure and can shift
  DTE/cohorts/events; fill-session-only without the decision field loses audit
  history. Safe default is refuse ambiguous legacy rows.
- **Evidence/wording:** ledger seq 21 exact wording. No further owner action.

### F6 execution convention — completed historical decision

- **Decision/choices:** same-session close, D+1 close, or another typed model.
  Owner and Fable chose D+1; Sol agrees because EOD data cannot establish an
  earlier executable intraday fill.
- **Effect/failure:** same-session introduces noncausal assumptions; D+1 creates
  cancellations and must freeze intent. Terminal exception must stay separately
  labeled. Evidence and wording: ledger seq 21. No further owner action.

### P0.6 — correction fact approval

- **Decision completed:** the owner approved the exact reviewed report-13
  payload on 2026-07-31 and it was appended once through the typed API.
- **Operational/data/governance effect:** one append-only fact; no threshold,
  result verdict, holdout, cache, or book change. Failure modes are transcription,
  duplicate append, or falsely claiming the facts file is hash-chained. Safe
  default is no append until exact approval.
- **Evidence:** `reports/strategy-evaluations/13_correction_facts_draft.md:38-55`;
  payload SHA-256 `c489eb179e…e8`; one-line diff; duplicate count one.
- **Owner-typed wording:** `I approve the exact one-line METRIC_CORRECTION payload in reports/strategy-evaluations/13_correction_facts_draft.md lines 40-42 for one append through research.facts.append_fact. Do not alter any prior fact, ledger record, verdict, holdout, cache, or book.`

### OD-1 — initial decline, later limited isolated-capture reversal

- **Decision history:** the 2026-07-31 closeout declined the original small
  backfill. A later explicit approval authorized one bounded 18-symbol capture
  under token `OD1-V2-9500-APPROVED` in an isolated worktree.
- **Effect:** 4,608 v2 partitions were captured and audited. Three whole
  partitions are quarantined. The branch remains parked and unmerged; no H6,
  H7, H8, backtest, or verdict authority was granted.
- **Evidence:** owner decision 2026-07-31; `P1_1_PROVIDER_CLOSEOUT` fact payload
  SHA-256 `4a793409a44b88a9915fb75bdf698a08cf584f02ec1416a8eebbcb2dc72b6f84`.

### OD-2 — final EOD top-up — DECLINED 2026-07-31

- **Decision:** decline the optional final EOD top-up. No ThetaData or fallback
  provider call is authorized, and P1.1 does not regenerate the manifest.
- **Effect:** the final canonical chain edge remains 2026-07-27. Every
  decision-authoritative consumer must fail closed beyond its exact cached
  coverage; P1.2/Q6 is condition-false/skipped.
- **Evidence:** owner decision 2026-07-31; the same append-only closeout fact.

### OD-4 — actual cancellation date — RECORDED 2026-07-31

- **Decision:** commercial ThetaData access ends 2026-08-01; the account
  information available to the owner does not specify an exact cutoff time.
  New acquisition is operationally disabled effective 2026-07-31 21:26:46 EDT.
- **Effect:** immutable cached reads remain enabled. Credentials were not used
  for a probe, printed, or moved into the repository. Q7/P1.4 must make the
  operational disablement fail closed at every client-construction boundary.
- **Evidence:** owner decision 2026-07-31; closeout fact appended at
  `2026-08-01T01:30:00.910690+00:00`.

### OD-3 — H7 namespace

- **Decision/choices:** continue `h7-forward-15-v1` or register a new namespace.
  Fable recommends new; Sol agrees because provider identity, cache edge, and
  receipt contract changed while the old store has only its registration.
- **Effects/failures:** continuation mixes regimes; a new namespace costs
  sample continuity but makes the boundary explicit. Safe default: no new H7
  event/registration.
- **Evidence:** H7 ledger verify (1 event); provider transition lines 101-105.
- **Owner-typed wording:** `OD-3 2026-__-__: future H7 paper observations [MUST USE NEW NAMESPACE h7-forward-__|MAY CONTINUE h7-forward-15-v1]. The prior registration and event remain immutable. The chosen namespace must bind provider, cache manifest, final as-of boundary, scope identity, source-health receipt, and activation date before any new observation.`

### H6-KILL — prospective amendment (not a defect)

The current code faithfully implements the registered rule. This packet asks
whether to create a different future H6 version; it is not a P0 correction and
has no current adjudication exposure.

- **Decision/choices:** retain full-cap exit-month rule; amend in place; or create
  prospective H6 v2. Choose comparison basis (deployed premium, fixed reference,
  exposed premium), month key, zero-deployment behavior, incomplete cohorts, and
  H8 interaction. Fable omitted this from P0. Sol recommends **new H6 version**:
  H6-only entry-month cohorts; a full-loss month means 100% of actually deployed
  premium is ultimately lost; an open position makes the cohort unevaluable;
  zero-deployment calendar months break the consecutive streak; keep H8 out of
  the H6 research verdict and implement any shared portfolio emergency stop as a
  separate risk rule.
- **Effects/failures:** in-place amendment retroactively redefines an open book;
  exit-month grouping misattributes long-DTE trades; full-cap denominator misses
  total losses after partial deployment; combined H6/H8 obscures attribution.
  Safe default: do not adjudicate/activate the hard kill under new semantics.
- **Evidence:** H6 code lines 707-730; report 10 D6d-g; H6 position file.
- **Owner-typed wording:** `H6_KILL_V2 2026-__-__: authorize a prospective new H6 version, effective only for entries on or after YYYY-MM-DD. A cohort is the H6-only calendar entry month. It is a full-loss cohort only after every position opened in that month is closed and aggregate exit proceeds are zero relative to actually deployed premium. A zero-deployment calendar month breaks the streak; an open position leaves the month unevaluable. Three consecutive evaluable calendar entry months that are full losses trigger the H6 research kill. Existing H6 rows and prior meanings remain unchanged. Any combined H6/H8 portfolio emergency stop is separate and non-verdict-bearing unless separately registered.`

### D7a — same-bar atomicity

- **Decision completed:** the owner selected option (b) on 2026-07-31. The
  exact-session precheck and conservative partial-fill unwind/fail-loud path are
  implemented; SMART_LIMIT was not adopted.
- **Effects/failures:** SMART_LIMIT changes conservative pricing; current separate
  legs can leave naked exposure until chunk-end failure; precheck/unwind is
  conservative but may add canceled trades. Safe default: cancel before submit if
  both current-session leg bars cannot be proven.
- **Evidence:** report 10 D7a; `put_credit_spread.py`; P0.8 red/green tests and
  the focused 22-test execution regression.
- **Owner-typed wording:** `STRATEGY_A_ATOMICITY 2026-__-__: use option (b). Preserve conservative_bid_ask_plus_haircut_v1 and separate-leg accounting; require both exact-leg current-session bars before either order; if an unexpected partial fill still occurs, flatten the filled leg at the same session's conservative executable mark, record the incident and costs, and fail the run. Do not adopt SMART_LIMIT or reinterpret prior results.`

### OD-D — review lane

- **Decision:** enable the managed review integration/required secret or keep
  evidence-upgrade paused. Fable and Sol agree it is condition-dependent.
- **Safe default:** paused. **Typed wording:** `OD-D 2026-__-__: enable the repository review lane for a no-authority test PR; evidence-upgrade may resume only after a review comment/check is visibly posted and captured. No silent workflow run counts as proof.`

P3 NAV and 1pm-entry choices are deliberately **not approval-ready**: the NAV
stitching evidence and 1pm feasibility counts must be produced first. Asking the
owner to type parameters now would invert the feasibility gate.

## 8. ThetaData Offline Intelligence Continuity

### 8.1 Data inventory and audit verdict

The EOD cache contains 31,367 parquet files total: 31,366 canonical top-level
symbol-day files plus one preserved noncanonical alternate at
`dolthub/SPY_2022-12-30.parquet`. A read-only
Parquet-metadata scan of the top-level files found 26 symbols, 79,519,407 rows,
one schema, no malformed filenames, no duplicate symbol/date keys, no unreadable
or zero-row files. Required fields are:

`expiration, strike, right, bid, ask, open_interest, iv, delta, gamma, theta, vega`.

This is metadata/structural evidence, not a complete quote-sanity or economic
data-quality audit. The offline-readiness verdict is **PASS** for canonical,
manifest-bound replay within frozen coverage. It is not a strategy verdict and
does not prove provider completeness, realistic fills, or an advantage.

| Symbol group | Coverage supported by filenames |
|---|---|
| AAPL, QQQ, SPY | 2018-01-02 to 2026-06-30 (2,133-2,134 sessions) |
| AMD, AMZN, AVGO, MSFT, NVDA, NOW, SMCI, VST | 2018-01-02 to 2026-07-27 (1,889-2,152; VST/most core 2,152) |
| CEG | 2022-02-09 to 2026-07-27 (1,118) |
| PLTR | 2020-10-06 to 2026-07-27 (1,457) |
| ET, IREN | 2018-10-22/2022-04-29 to 2026-07-27 (1,949/1,063) |
| AMAT, CLSK, CRWV, NBIS, TEM, USAR | partial recent histories ending 2026-07-27 (327-519 except NBIS 434) |
| HYLN | 29 sessions, 2026-05-26 to 2026-07-07 |
| CRWD, IBEX, UNH, ZS | one probe session each, 2026-07-15 |

Contract coverage cannot be inferred from filenames alone. The adapter's inner
join drops contracts lacking OI (`data/thetadata_adapter.py:14-20`); therefore
“whole OPRA chain” must not be claimed. The manifest now holds 31,366 hash/size
entries, including all 33 Jul. 24/27 additions. The nested dolthub file has a
separate classification record and is excluded from canonical use. The
2026-08-02 Q9 receipt binds the inventory, manifest, classification, exact-session
consumer checks, and provider-disabled replay.

There are 180 `.cache/intraday/*.parquet` captures from late July, governed as
display-only snapshots. There is **no** `.cache/options_flow` data. The only
options-flow data audited in reports was a four-row synthetic fixture
(`reports/options_flow/2026-07-28-implementation-audit.md:9-21`). Thus:

- EOD-chain Options Intelligence can proceed offline within frozen coverage.
- Trade/quote-flow analog conclusions cannot proceed; implementation exists,
  but the real raw/normalized/derived panel is absent and remains DATA-GATED.

### 8.2 Consumer map

| Consumer/path | Required source/fields/range | Offline sufficiency and cutoff behavior | Fallback/authority |
|---|---|---|---|
| `data/thetadata_adapter.py` | EOD schema above; requested symbol/session | `load_cached_chain` is offline; `get_eod_chain` can fetch a missing in-sample date and write cache. | No provider fallback, but no global disable. Foundational, not verdict itself. |
| `data/pandas_feed.py`, `strategies/put_credit_spread.py`, harness | Bid/ask, right, expiry, strike, OI, delta; registered study window | Existing cache supports replay. Loader calls `get_eod_chain`, so missing in-sample data can attempt network. | No silent alternate provider; Strategy A result-bearing. Must add offline-only mode. |
| `options_researcher/features.py`, attractiveness cards/dashboards | IV/Greeks/OI + closes over rolling history | Existing dates can rebuild; later dates stale/missing. | Descriptive dashboards may show labeled stale data; never promote it to verdict. |
| `options_researcher/entry_watch.py` (H5) | exact-session close, IV rank, LEAPS delta/liquidity | Mismatched, missing, or stale session inputs return DATA_GAP rather than FIRE. | No provider substitution; H5 remains an alert, not order authority. |
| `options_researcher/h6_features.py`, `h6_watch.py` | exact as-of EOD chain, close, earnings, feature manifest | Exact-session cache and manifest/receipt checks exist; refuses latest fallback. Frozen data sufficient only through edge. | No silent provider fallback; registered H6 paper decisions. H6 kill semantics separately blocked. |
| `options_researcher/h8_watch.py` | exact chain/close/features + H6/H8 books | Exact artifact paths and shared-cap validation exist; post-edge evaluation stops. | No silent provider fallback; H8 registered paper lane. |
| H7 source/data gate/watch/exit | exact evaluation-session chain, close, earnings, receipt and scope identity | Exact-session gate is strong; H7 remains paused and the old namespace stays unchanged. | No silent provider fallback; any later restart requires a new namespace. |
| `options_researcher/h9_census.py` and H9 artifacts | historical cache and receipt | Reproducible from existing bytes, but H9 is spent and must never rerun/refetch. | One-run record; leave unchanged. |
| `options_researcher/live_quotes.py`, `intraday_capture.py`, live dashboard | current stock/option snapshots, timestamps, Greeks/OI | Not an offline historical consumer. Live selection is explicit Schwab-or-error. | Display-only and never FIRE; ThetaData is disabled rather than used as fallback. |
| `data/cache_runner.py`, `recent_topup.py`, `smoke_test.py`, underlying fetchers | missing EOD chains/closes | Dry-run inventory and cache hits remain available; acquisition refuses before client construction or mutation. | Provider-disabled tests prove zero ThetaData calls. |
| `data/options_flow/*`, `options_researcher/flow/*`, `tools/options_flow*.py` | raw trades, strict-prior NBBO, prior-known OI, underlying midpoint, IV/Greeks, event context, ≥300 prior sessions | Software works on fixtures; real source data absent. | Capture CLI dry-runs by default and requires `--execute`; no governed authority. DATA-GATED. |

### 8.3 Frozen-data contract

1. Treat every existing v1 parquet byte as immutable. Never “repair” a file in
   place; exceptions and provenance belong in sidecars.
2. Separate raw, normalized, derived, and report namespaces. Every derived
   output carries schema/method version, code/config SHA, source paths, source
   manifest SHA, maximum as-of session, creation time, and missingness summary.
3. A file outside the active manifest is non-authoritative even if an attestation
   exists. Finalize the manifest only after the final-pull decision is closed.
4. No output may claim current-market validity after its maximum source date.
   The cache edge and each consumer's exact as-of must be visible in output.
5. No silent provider fallback and no synthetic replacement for missing market
   observations. Display-only fallback must be labeled and must never emit FIRE
   or a research verdict.
6. Cached reads remain enabled after cancellation; all client construction and
   acquisition commands fail closed under a tracked provider-disabled policy.
7. Any final pull needs separate owner approval with exact symbols, sessions,
   endpoints, and call ceiling. It must stop on scope/entitlement drift.
8. Add a network-disabled integration test that replaces every supported client
   constructor/transport with a raising sentinel, replays representative H5/H6/
   H7/H8/features/backtest cache reads, and proves zero calls and zero cache writes.
9. Options-flow remains an active planned lane but its real-data verdict stays
   `NOT AUDITED / DATA-GATED` until rights, acquisition, full audit, sample size,
   and holdout preregistration are independently satisfied.

### 8.4 Safe-now offline work

- Reconcile manifest scope and sidecar coverage without touching parquet bytes.
- Produce a versioned cache coverage/schema/missingness report.
- Add replay receipts and provider-disabled tests.
- Map each feature to required fields and exact-session policies.
- Rebuild artifacts only in temporary/output namespaces and byte-compare them to
  canonical artifacts; do not overwrite governed artifacts.
- Run options-flow software audits on synthetic fixtures and produce a real-data
  acquisition readiness checklist; do not publish empirical opinions.
- Assess whether EOD-only features have enough history inside the frozen boundary,
  clearly separating feasibility from performance.

## 9. Provider transition

The provider transition has four independent gates:

`owner date/scope decisions → optional approved pulls → manifest finalization → provider-disabled enforcement`.

Cancellation ends new acquisition; it must not disable immutable cache reads.
Schwab remains a read-only live-preview source and is not a substitute for dated
historical chains. Implementing provider-disable means guarding all construction
paths, not deleting one config constant. The technical completion proof is a
static acquisition-entrypoint inventory plus dynamic sentinel tests for each CLI
and representative cached consumer. A missing historical observation remains a
named data gap.

## 10. Dependency graph

```text
P0.6 correction append COMPLETE ─────────────> permanent metrics corrected
P0.8 Strategy A atomicity COMPLETE ──────────> trusted future Strategy A runs
P2.5 optional H6 amendment ──────────────────> future H6 version only if approved

OD-2 canonical top-up declined ─> manifest reconciled ─> provider disabled
                                              │
                                              └─> exact-session consumers verified

isolated v2 capture ─> full audit PASS WITH WARNINGS ─> PARKED / UNMERGED
OD-3 H7 decision ─> DO NOT RESTART ─> new namespace only if later approved

review-lane proof ─> evidence-upgrade packet 5B
captured intraday history ─> feasibility gate ─> owner registration ─> 1pm hypothesis
NAV mark capture evidence ─> owner stitching choice ─> optional NAV build
```

## 11. Cleanup plan

| Priority/action | Target | Evidence-based disposition | Completion proof |
|---|---|---|---|
| Register later | Prospective H6 kill amendment | Current implementation matches registration; change only through a future version after owner choice. | New-version provenance, red/green tests, unchanged old book. |
| Complete | Strategy A atomicity | Exact-session precheck plus conservative one-leg unwind/fail-loud path landed without SMART_LIMIT. | Red/green test, 22 focused tests, unchanged config/cost model. |
| Consolidate | Canonical status and docs | Keep this file as sole queue; add `Status: historical`/`Superseded by` headers only when a referenced doc is edited. | Reference scan; no broken links; docs match ledgers/code. |
| Correct | `.claude/rules/backtest-engine.md`, H7 README, provider doc, NAV spec | Update stale statements in one docs-only session. | Exact diff and ledger verifies; no code/config. |
| Add test | Provider-disabled boundary and H5 as-of | Central policy + sentinel integration tests; do not rely on `DATA_PROVIDER`. | All acquisition constructors covered; zero-call cache replay. |
| Leave unchanged | v1 parquet bytes, one-run/H9 artifacts, open books, old H7 event | Governed/immutable evidence. | Hash/ledger verification only. |
| Register | New H6/H7 semantics and approved facts/pulls | Typed owner actions only after packets. | Append-only record and unchanged prior chain/history. |
| Consolidate | `.agents/skills` / `.claude/skills` | Current symlink model is adequate; verify runtime before editing. | `/context` output captured by owner. |
| Move + add tests | `block_live_trading.py` | Track under `.agents/hooks`, then register local path. | Hook fixtures and no ignored-only authority logic. |
| Consolidate | `ov` skill bundle | Keep standalone distribution; add manifest/sync checker and document intentional variants. | Clean checker, preserved user WIP, install smoke in temp dir. |
| Classify | branches/worktrees | Table: branch, SHA, upstream, merged, unique commits, worktree, PR, owner. Delete only after explicit approval. | Owner-approved deletion list; no broad prune. |
| Remove later | dead provider config | Only after central disable policy and reference inventory. | `rg` clean for dead setting; cached replay passes. |
| Consolidate later | duplicated receipt/hash/as-of helpers | Extract only exact duplicates with characterization tests; no broad refactor. | Same bytes/errors in golden tests. |
| Leave/mark obsolete | Session-4 admit-all feature | Current causal prefix fix and regression already close the defect; measured impact zero. | Remove from active queue only. |
| Do not archive yet | superseded plans | No archive convention; files are referenced evidence. | Introduce convention/index before any move. |

### Minimal stable instruction outline for a later AGENTS.md edit

Keep only durable rules: canonical roadmap=`PROJECT_STATE.md`; live scope=
README “Scope status”; no live orders; owner-gated ledger/facts/cache/book writes;
v1 immutable; offline replay must not acquire; exact-as-of/fail-closed policy;
one-run and holdout rules; current supported quality commands; and a pointer to
nested domain rules. Volatile counts, open defect lists, branch SHAs, and provider
dates belong here, not in always-loaded instructions.

## 12. One-task-per-session execution queue

Each task below fits one focused session. A session stops instead of spilling
into the next task.

### Q0 — Owner correction fact — COMPLETE

- **Result:** P0.6 closed. Exact payload appended once through the API; prior
  lines are unchanged and the payload hash is recorded above.
- **Files/discovery:** report 13, `research/facts.py`, final `facts.log` line.
- **Allowed:** one API append after exact approval, read-only hash/diff/verify.
  **Forbidden:** editing old facts/ledgers, changing text, code, verdicts, books,
  caches, one-run files. **Prerequisite/gate:** exact owner wording above.
- **Implementation:** hash approved payload; assert absent; call append API once;
  inspect exactly one appended line; separately verify ledgers.
- **Tests/quality/evidence:** facts API targeted tests; `research.cli verify`; H7
  verify; `git diff --check`; payload hash + one-line diff.
- **Rollback/failure/stop:** append-only means no rollback. Stop before append on
  text/hash mismatch or duplicate; convene owner on any verification failure.
- **Artifact/proof:** approved wording, hash, append receipt/diff. **One session:** yes.

### Q1 — Documentation truth repair — COMPLETE

- **Result:** stale instruction, provider, cache-miss, cancellation-checklist,
  and H7-restart claims are reconciled with current code, ledger seq 21, the
  one-record H7 store, and the paused H7 decision. Historical evidence remains
  explicitly historical.
- **Files:** `.claude/rules/backtest-engine.md`, `ledger/h7_forward/README.md`,
  `docs/provider-transition.md`, NAV spec, README status figures if stale.
- **Allowed:** documentation only. **Forbidden:** code/config/ledgers/cache/books.
  **Prerequisite/gate:** none; no owner approval for factual corrections.
- **Implementation:** replace stale claims with references to seq 21, current H7
  status, and canonical roadmap; label historical text rather than erasing it.
- **Tests/quality/evidence:** research ledger `ledger OK`; H7 ledger
  `VALID records=1 head=a1ea228c2abb…`; changed-reference and stale-phrase
  scans; docs-only inventory; `git diff --check`. No full suite needed.
- **Failure/stop:** stop on a conflict requiring semantic choice. Revert only this
  task's uncommitted doc hunks if needed.
- **Proof:** docs-only diff with current command outputs. **One session:** yes.

### Q2 / P2.5 — Prospective H6 amendment — COMPLETE

- **Result:** the owner-authorized H6 hard-kill v2 applies only to
  entries on or after 2026-08-03. Current code remains faithful to v1 for older
  rows; v2 uses H6 entry-month cohorts, treats open cohorts as unevaluable,
  requires zero aggregate exit proceeds, and treats absent/positive-recovery
  months as streak breaks. V1 and v2 rows cannot enter one another's calculation.
- **Files:** config H6/H8 constants, `h6_watch.py`, H6/H8 tests, registration docs;
  inspect the book read-only.
- **Allowed:** new prospective version, tests, config only as owner typed.
  **Forbidden:** editing existing rows, retrospective rescoring, H7/H9, provider calls.
  **Prerequisite/gate:** satisfied by owner authorization dated 2026-08-02 and
  chained research-ledger seq 22, record hash
  `4c552641d5a56f96d6e2c12904e7b20467a56bd1c7804d9de18969a3bb548b04`
  (`trial_count=23`).
- **Implementation:** entry-date dispatch preserves the original exit-month/
  full-cap rule for older rows and adds the registered zero-proceeds entry-cohort
  rule for newer rows. Receipt-v1 remains historical-only; receipt-v2 is required
  for decisions on/after the effective date and binds both H6 registration hashes.
  The CSV schema, `H6Score`, eight-position bootstrap, entries, exits, costs,
  sizing, and H8 remain unchanged.
- **Tests/quality/evidence:** red proof had six expected v2 failures; green H6
  39/39 and unchanged H8 40/40. The unrestricted offline root suite passed
  2,308/2,308; Ruff passed; Pyright reported 0 errors/warnings; both ledgers
  verified. The historical `H6-0001` v1 receipt/book loads without rewrite.
  `FILL_MODEL_ID=conservative_bid_ask_plus_haircut_v1` and `cost_model_hash`
  `af71c7f65984c259eed7ffc259be72535f35a792bfc0157cadaebf66ff62fa80`
  match the clean base. CodeRabbit could not run because its CLI is not
  installed; the credential scan was clean and the repository-native complete
  diff/invariant review found no critical or warning defects.
- **Failure/stop:** fail closed on ambiguous legacy rows/open cohorts; stop if
  existing book meaning or verdict changes retroactively.
- **Proof:** typed record above; unchanged H6 book SHA-256
  `d9c65cab1a58e2ca0e571ead8c78fe408e19208c5cbbb05b189ccb67d7eab528`;
  unchanged historical receipt SHA-256 `b113ee62655e…674c5`. **One session:** yes.

### Q3 — Strategy A same-bar atomicity — COMPLETE

- **Result:** P0.8 closed. Both same-session bars are required before either
  order; an unexpected one-leg fill is conservatively unwound, costed, recorded,
  removed from strategy state, and aborts the run.
- **Files:** spread strategy, Pandas feed, harness, causal-fill/backtest tests.
- **Allowed:** owner-approved option-b mechanics/tests. **Forbidden:** SMART_LIMIT,
  fill-model change, prior result/ledger rewrite, running a real backtest.
  **Prerequisite/gate:** D7a owner wording.
- **Implementation:** current-session two-bar precheck; instrument partial outcome;
  conservative flatten+fail; never leave `pending_entry` with one leg.
- **Tests/quality/evidence:** missing-bar, one-leg-fill, unwind-price/cost, ordinary
  two-leg regression; full suite; Ruff/Pyright; cost-model hash unchanged.
- **Failure/stop:** stop if Lumibot cannot support deterministic unwind without a
  new price convention. No partial implementation.
- **Proof:** red/green and no-naked-leg invariant. **One session:** yes.

### Q4 — H5 and consumer exact-as-of gate

- **Goal/position:** eliminate the proven stale-local-data FIRE path before
  provider cutoff.
- **Files:** `entry_watch.py`, features/cache loaders, relevant tests; enumerate
  H5/H6/H7/H8 consumers first.
- **Allowed:** fail-closed checks/tests and clearer labels. **Forbidden:** threshold
  or trigger changes, provider calls, cache writes, new authority. **Gate:** none.
- **Implementation:** derive one requested/evaluation session; require close,
  features, and chain exactly match; WAIT/DATA_GAP otherwise.
- **Tests/quality/evidence:** mismatched each-way dates, beyond edge, exact match,
  missing files; targeted set; full suite if behavior change; Ruff/Pyright.
- **Failure/stop:** never substitute latest. Stop on a consumer whose registration
  defines a different date and escalate that semantic choice.
- **Proof:** consumer matrix + tests. **One session:** yes.

### Q5 — Provider owner closeout — COMPLETE

- **Goal/result:** OD-1, OD-2, and OD-4 were resolved before acquisition or
  technical disablement work. OD-2 remained declined; OD-1 later received a
  separate, bounded isolated-capture approval.
- **Scope preserved:** canonical v1 bytes were not rewritten and no credential
  entered source control. Immutable cached reads remain enabled.
- **Evidence:** owner decision 2026-07-31; one `P1_1_PROVIDER_CLOSEOUT` fact at
  `2026-08-01T01:30:00.910690+00:00`; payload SHA-256
  `4a793409a44b88a9915fb75bdf698a08cf584f02ec1416a8eebbcb2dc72b6f84`.
- **Routing:** Q6 canonical manifest finalization, Q7 provider disablement, and
  Q4 exact-session enforcement are complete. **One session:** complete.

### Q6 — Optional approved pull and manifest finalization

- **Status:** **COMPLETE.** The canonical top-up remained declined; the 33
  existing July additions were provenance-checked and added to the manifest
  without rewriting market bytes. The separate v2 capture stayed isolated.
- **Goal/position:** preserve the final canonical binding.
- **Files:** approved acquisition CLI, attestation namespace, manifest, facts API.
- **Allowed:** exact approved calls/new files/sidecars/manifest/fact. **Forbidden:**
  overwrite v1 files, retries above ceiling, other symbols/dates, fallbacks.
  **Gate:** explicit per-pull approval; provider active.
- **Implementation:** preflight, execute bounded list, stop on first scope/rights
  deviation, audit files, regenerate manifest once, append DATA_PULL after success.
- **Tests/quality/evidence:** acquisition dry-run; manifest verify zero; schema and
  duplicate scan; call log/count; ledger verifies; targeted cache tests.
- **Failure/rollback:** retain failed new bytes quarantined outside canonical
  namespace; never rewrite old bytes; do not append success fact.
- **Proof:** `tools/cache_manifest.py verify` returns `verify: OK`; reconciliation
  report records all 33 additions and the nested SPY classification. **One
  session:** complete.

### Q7 — Provider-disabled enforcement — COMPLETE

- **Goal/result:** cancellation is technically enforced while offline reads remain usable.
- **Files:** Theta adapter, live provider selection, cache/top-up/smoke/flow/intraday/
  underlying CLIs, config, tests.
- **Allowed:** central disable guard, explicit acquisition errors, dead-config
  removal after coverage. **Forbidden:** provider call, cached-read disablement,
  fallback provider, cache mutation. **Prerequisite:** OD-4/date and Q6 complete/skipped.
- **Implementation:** the sole constructor and every acquisition entry boundary
  are gated; cache hits remain readable; missing cache refuses; live selection is
  explicit Schwab-or-error with no Theta fallback.
- **Tests/quality/evidence:** 14 zero-call sentinel tests; 294 neighboring tests;
  2,251-test full discovery; Ruff/Pyright; constructor/guard `rg` inventory.
- **Failure/stop:** any client constructed in disabled test or any cached read
  blocked => not ready; leave provider disabled fail-closed.
- **Proof:** `reports/provider-transition/2026-07-31-q7-provider-disabled-proof.md`.
  **One session:** complete.

### Q8 — Reproducible cap-audit command

- **Status:** **COMPLETE.** `tools/strategy_a_cap_audit.py` and its permanent
  receipt reproduce the full bound-cache measurement.
- **Goal/position:** preserve P0.3's reproducible evidence.
- **Files:** new read-only tool + tests + report schema; production selector/risk
  helpers only. **Allowed:** measurement code/tests/temp output. **Forbidden:**
  backtest, holdout, cache write, result/fact append. **Gate:** P0.8 is complete;
  any new receipt may now identify the engine as post-atomicity.
- **Implementation:** explicit in-sample symbols/dates; load cache-only; bind
  manifest/code/config; emit counts/worst rows and cancellation/resize rates.
- **Tests/quality/evidence:** tiny golden fixture, determinism, missing-leg, manifest
  mismatch block; targeted/full suite; Ruff/Pyright.
- **Failure/stop:** manifest mismatch blocks authoritative receipt; no guessing.
- **Proof:** 4,002 chain-days, 192 accepted candidates, 102 cancellations, 89
  allowed fills, one unavailable fill, highest risk `$556.80`, zero cap
  breaches. **One session:** complete.

### Q9 — Offline Intelligence readiness and replay

- **Status:** **COMPLETE FOR EOD / DATA-GATED FOR FLOW.** The 2026-08-02 EOD
  receipt passes; the paired flow receipt correctly refuses empirical use.
- **Goal/position:** keep the research lane active without manufacturing real flow data.
- **Files:** cache inventory tool/report, options-flow audits, consumer map.
- **Allowed:** structural/data-quality scans, temporary derived outputs, docs/tests.
  **Forbidden:** empirical opinion, provider call, raw mutation, verdict use.
  **Prerequisite:** manifest scope identified; Q7 desirable.
- **Implementation:** audit EOD fields/coverage and network-disabled replay; emit a
  separate `DATA-GATED` flow readiness report showing `.cache/options_flow` absent.
- **Tests/quality/evidence:** deterministic inventory, schema/missingness/duplicate
  checks, source manifest binding; Ruff/Pyright and focused tests.
- **Failure/stop:** malformed/unmanifested input => BLOCK; never silently drop.
- **Proof:** manifest-bound inventory of 31,366 files and 79,519,407 rows plus
  network-disabled consumer replay; real flow dataset absent. **One session:**
  complete.

### Q10 — Conditional v2 path — CLOSED 2026-08-03

- **Status:** **CLOSED / BRANCH RETIRED.** The v2 lane reached `main` on
  2026-08-02 by a different route (`codex/main-phase-a-integration-20260802`),
  and main's implementation is strictly ahead of the parked branch: a
  20-column v2 schema versus the branch's 11, and a verdict gate that refuses
  v1 partitions earlier. Comparison evidence: 13 merge conflicts, all of which
  resolve to "take main"; 8 of the branch's 9 `test_cache_schema_v2.py` tests
  fail against main because they pin the branch's superseded API, not because
  main lost coverage. The wholesale merge this task forbade was therefore also
  pointless. Owner authorized retirement 2026-08-03.
- **What was salvaged:** the branch's only unique content — the parked
  future-ticker audit (`tools/future_ticker_data_audit.py`, its tests, and the
  two `reports/future_tickers/` artifacts) — was ported in `56afc10`; its two
  tests pass against main. `codex/od1-v2-current` and its worktree were then
  deleted. `codex/od1-v2-backfill` was verified to contain ZERO unique files
  and is likewise superseded.
- **Incident recorded:** the branch's worktree (under `~/Downloads`) held the
  ONLY copy of the 1,536-partition future-ticker capture — 110 MB, 3,072
  provider calls, taken before cancellation and therefore unrecoverable. The
  bytes are gitignored and `tools/cache_manifest.py` covers only
  `.cache/chains`, so no manifest, test, or CI check would have flagged their
  loss. They were copied to `.cache/future_tickers` and verified byte-identical
  by SHA-256 across all 1,536 partitions BEFORE deletion. Prevention landed as
  `tools/irreplaceable_data_guard.py` plus
  `data/irreplaceable_data_inventory.json`; see `.claude/rules/data-and-providers.md`.
- **Historical goal/position:** preserve the audited v2 work until explicit integration authority exists.
- **Files/discovery:** diff `codex/od1-v2-current` against current sfix; schema
  modules, H6/H8/H7 exit gates/tests. **Allowed:** port minimal current-base code,
  tests, new artifacts. **Forbidden:** wholesale merge, H9 rerun, v1 edits, bypass.
  **Gate:** explicit owner integration authorization, Q6 verified, H6-KILL decision.
- **Implementation:** port schema primitives; enforce direct source provenance at
  every consumer; rebuild H6/H8 in new versioned namespace.
- **Tests/quality/evidence:** bypass/mixed-schema/missing-provenance tests; artifact
  lineage; full suite/Ruff/Pyright.
- **Failure/stop:** no explicit integration decision => do not merge, rebuild,
  activate, or claim edge.
- **Proof:** branch `codex/od1-v2-current` plus its full-audit receipt. **Current
  action:** parked.

### Q11 — H7 namespace

- **Status:** **DO NOT RESTART NOW.** If reconsidered later, use a new clean
  registration and namespace.
- **Goal/position:** resume H7 only under a provider/cache identity the ledger describes.
- **Files:** H7 event/activation modules, scope/data receipts, new namespace docs/tests.
- **Allowed:** new append-only namespace after approval. **Forbidden:** mutate old
  event/store, fabricate coverage, use stale receipt. **Gate:** OD-3 and Q5-Q7.
- **Implementation:** build/validate registration with final manifest and provider
  policy; append through one door; leave old store unchanged.
- **Tests/quality/evidence:** synthetic registration, real preflight read-only,
  both stores verify, full suite/Ruff/Pyright.
- **Failure/stop:** any source/receipt mismatch or old-store diff => stop.
- **Proof:** `reports/h7_forward/2026-08-02-restart-decision.md`; old ledger
  remains `VALID records=1 head=a1ea228c2abb`. **Current action:** paused.

### Q12 — Review-lane proof

- **Goal/position:** unblock evidence-upgrade without mistaking YAML for service.
- **Files:** workflow and no-authority PR. **Allowed:** owner console setup and test
  PR. **Forbidden:** packet 5B work before visible review. **Gate:** OD-D.
- **Implementation:** enable least-privilege integration; open trivial draft PR;
  capture posted review/check and permissions.
- **Tests/evidence:** visible GitHub artifact, not local success.
- **Failure/stop:** silence or secret error keeps program paused; remove test PR if
  owner wants, without changing production.
- **Proof:** review URL/check ID. **One session:** yes.

### Q13 — Hook and skills hardening

- **Goal/position:** remove ignored-only governance logic after correctness/provider work.
- **Files:** `.agents/hooks`, `.claude/hooks`, settings, hook tests, skill symlinks.
- **Allowed:** tracked hook/tests; runtime verification. **Forbidden:** claim hooks
  are a security boundary, copy skill trees, overwrite local custom skill.
  **Gate:** owner runs `/context` for the runtime-only check.
- **Implementation:** track live guard, test inputs/failures, repoint local setting;
  record 14 expected Claude skill entries.
- **Tests/quality/evidence:** hook unit tests, symlink resolution, `/context` capture,
  full suite if Python hook changes; Ruff/Pyright.
- **Failure/rollback:** retain old local hook until tracked version passes.
- **Proof:** tracked tests + runtime list. **One session:** yes.

### Q14 — Bundle/docs/branch classification

- **Goal/position:** reduce repeated context safely, last because it has no research urgency.
- **Files:** `ov` manifest, supersession index, branch/worktree/PR inventory.
- **Allowed:** manifests/status headers/checkers and owner-approved branch cleanup
  in a later destructive session. **Forbidden:** touch user WIP, broad archive,
  delete on name/age, break standalone bundle.
- **Implementation:** classify six identical/two divergent/one bundle-only skills;
  status-index plans; inventory unique branch commits.
- **Tests/quality/evidence:** temp install smoke, link scan, sync checker, branch table.
- **Failure/stop:** unknown reference/PR/worktree/unique commit => leave unchanged.
- **Proof:** classification artifacts; any deletion requires a separate owner-approved
  session. **One session for classification:** yes.

### Q15 — Optional research designs

- **Goal/position:** revisit NAV or 1pm hypothesis only after prerequisites.
- **Files:** NAV spec or intraday receipts/feasibility tool. **Allowed:** one design
  lane per session. **Forbidden:** combine lanes, register before evidence, call old
  data current, retrofit H7.
- **Prerequisite/gate:** NAV: Q3 plus owner stitching choice after diagnostics;
  1pm: enough captured sessions and registration-feasibility gate.
- **Implementation/tests/evidence:** NAV deep-adverse/recovery fixture and chunk
  accounting, or intraday coverage/base-rate calculation with receipt hashes;
  full relevant quality suite.
- **Failure/stop:** insufficient data remains DATA-GATED, not “zero edge.”
- **Proof:** decision-grade feasibility packet, not a verdict. **One lane/session:** yes.

## 13. Exact stop conditions

Stop and convene the owner immediately if:

1. Any action would change H1, H2, H9, a registered verdict, an unrevealed
   holdout, a one-run record, or an existing live/paper-book row.
2. Research-ledger, H7-ledger, manifest, approved-payload, or source-artifact
   verification fails or produces an unexplained mismatch.
3. A task needs to overwrite/delete a v1 cache byte, silently fill a missing
   observation, or use a provider/fallback outside the exact approval.
4. A provider scope, entitlement, endpoint, session list, call count, effective
   date, or destination namespace differs from the approved packet.
5. H6 implementation would retroactively reinterpret the open book or H7 work
   would mutate the existing event/namespace.
6. Atomicity cannot be achieved without changing the registered fill model or
   leaving a naked leg.
7. A full test/quality failure relates to the scoped change, or a baseline
   failure cannot be separated from it.
8. Unexpected unrelated changes appear in files the task needs to edit.

The cache-manifest blocker is closed. Both ledgers verify. The active stops are
H7 restart without a new contract, richer-data integration without explicit
authority, and empirical options-flow claims without a real dataset.

## 14. Residual risks and unknowns

- The cap audit is reproducible, but cancellations change the observed sample
  and must be disclosed with any future result.
- No full value-level audit of 79.5 million chain rows was performed here;
  structural metadata cannot prove quote, Greek, OI, split, or contract completeness.
- Provider acquisition is disabled; no new historical continuity is assumed.
- The isolated v2 audit has 10,394 warnings and three quarantined partitions;
  its branch remains unmerged.
- Options-flow has no real raw dataset; its empirical sample size, rights,
  coverage, and usefulness are unknown.
- The live review integration and `/context` result require external UI evidence.
- Branches may have external PR/owner value not inferable from local names.
- Ruff format has a 260-file baseline drift; scoped changes must not disguise it
  with a mass format.

## 15. Final self-audit

- P0.1-P0.6, P1.1-P1.5, P0.8, and every named P3 item were independently
  checked; the former P0.7 is reclassified as optional P2.5.
- Commits `9cf3ee4`, `88ffbb6`, `ecdaeb9`, and `5626c3f` were inspected and are
  reachable from `sfix`; later relevant commits were also checked.
- Branch/worktree state and pre-existing user WIP were recorded.
- Trusted conclusions are separated from safe read-only work.
- ThetaData Options Intelligence remains active offline; real flow conclusions
  are labeled DATA-GATED, not deleted or falsely completed.
- The execution update made one approved facts append plus scoped Strategy A,
  test, and documentation edits. No provider call, package operation, branch
  switch, cache/one-run/book mutation, prior-result rewrite, or verdict change
  occurred.
- Current test discovery, full suite, lint, types, ledger checks, and passing
  manifest verification are reported; unknowns remain explicit.
- Every active task has scope, gates, tests, proof, rollback/failure behavior,
  stop conditions, and a one-session boundary.
- Sol's disagreements with Fable are explicit: H6 and atomicity priority,
  provider-disable breadth, v2-task splitting, H5 fail-closed gap, flow-data
  absence, and no broad archive/delete sweep.
