# Architecture and correctness audit

**Audit date:** 2026-08-25
**Snapshot:** `c9e74ccd05e4ecdd0de8de6f35bef714bc6f1771`
**Mode:** read-only static architecture review; no provider, watcher, paper-book,
ledger, cache, operational, or test execution occurred.

## Verdict

**NOT READY for an architecture cleanup in this audit.** The reviewed authority
and score-publication paths have substantial fail-closed counterevidence; no
executed-path defect or unauthorized state mutation was demonstrated. The
highest-value candidates reduce concentrated orchestration and interface risk,
but all overlap protected WIP and are therefore **plan-only**.

## Scope and evidence

- Verified the assigned worktree is on the stated SHA. Its only visible
  untracked items are the audit directory and `.venv`; this report is the only
  audit write.
- Read the operational authority boundary: `data/ritual_authority.py:1-120`,
  the stateful orchestrator: `tools/daily_ritual.sh:70-594`, and its guardrail
  tests: `tests/test_ritual_authority.py:42-130`,
  `tests/test_daily_ritual_provenance.py:191-285,430-510,751-865`.
- Read the display boundary and its tests:
  `options_researcher/attractiveness_dashboard.py:1-27,52-75,1156-1235,
  3980-4172` and `tests/test_attractiveness_dashboard.py:1815-1889`.
- Read the H7 finalization path and structural controls:
  `options_researcher/h7_real_scoring.py:1859-1978`,
  `tests/test_h7_real_scoring.py:508-1144`, and
  `tests/test_h7_one_door.py:228-285`.
- Reviewed the current scope/authority statements in `README.md:41-56` and
  `PROJECT_STATE.md:1-52`. Counts below are static measurements: `config.py`
  is 913 lines with 297 uppercase assignments, and 81 Python modules under
  `options_researcher/`, `data/`, and `tools/` directly import it.
- Did not run the test suite. The cited tests are evidence of intended and
  previously encoded coverage, **not** a fresh pass on this audit worktree.

## Findings

### AC-01 — State-bearing daily workflow is concentrated in one shell orchestrator

**Classification:** **VERIFIED concentration; INFERRED maintenance/failure-path
risk; no demonstrated current defect.**
**Priority:** P1 architecture candidate, but not implementation-eligible here.

`tools/daily_ritual.sh` is a 619-line shell workflow that combines authority
evaluation, source/receipt sequencing, data refreshes, feature rebuilds,
watchers, dashboard generation, terminal-status publication, Git staging,
commit/merge/push, and Restic backup. The most consequential state transition
region is not isolated from the operational sequence: it publishes terminal
status at `:491-507`, then conditionally stages and commits allow-listed
evidence at `:535-564`, merges `origin/main` and pushes at `:566-579`, and
backs up at `:582-594`. The data-tier island also calls multiple refresh/build
modules directly at `:270-323`.

The risk is temporal coupling: a new lane, exit-code convention, or artifact
writer must be correctly placed in shell order, classified for both authority
tiers, included in durability allow-lists, and reflected in terminal-state
logic. A local edit can thus change authority or persistence semantics without
changing a typed Python interface. This is an inference from the composition,
not evidence that an incorrect operation has occurred.

**Counterevidence and containment.** Authority itself is a small frozen,
side-effect-free policy object (`data/ritual_authority.py:31-84`), with an
eight-combination readiness test matrix (`tests/test_ritual_authority.py:52-70`).
The ritual test suite asserts source ordering and mutation gates
(`tests/test_daily_ritual_provenance.py:208-285`), exercises `status` without
changing guarded paths (`:430-454`), and executes two extracted shell blocks
under zsh to catch shell-semantics regressions (`:751-805`). The H5/H10b
exception is explicitly fail-closed against the shared verified-session view
(`tools/daily_ritual.sh:375-466`; tests `:833-865`). These controls materially
lower the risk; they do not provide a complete fake-filesystem, multi-stage
transaction test for commit/push/backup failure combinations.

**Smallest safe proposal.** First model a display-only, side-effect-free typed
workflow plan (steps, prerequisites, declared writes, expected receipt, and
terminal effect) and compare it against the shell's current sequence in tests.
Only after exact parity and explicit owner approval should writer execution
migrate one tier at a time. Preserve the existing authority evaluator and
evidence allow-lists; do not rewrite historical receipts, ledgers, or live
operations.

**Eligibility:** **PLAN-ONLY / BLOCKED.** `tools/daily_ritual.sh` is protected
by `00-preflight-and-wip.md:157`; its normal behavior mutates operational
evidence and can push Git state. Any implementation also needs separate owner
authority and an isolated operational verification plan.

### AC-02 — Attractiveness dashboard has a global-state and exit-contract seam

**Classification:** **VERIFIED interface hazard and responsibility
concentration; impact is INFERRED and display-only.**
**Priority:** P2 plan-only candidate.

`options_researcher/attractiveness_dashboard.py` is 4,172 lines and combines
candidate gathering, cache/provenance and freshness interpretation, selection
policy presentation, scenario calculations, HTML rendering, and output-file
publication. `assemble()` can gather runtime state and imports configuration
inside the function (`:1156-1192`); `render()` is pure HTML templating
(`:3990-4121`); `_build_and_write()` then performs input-root switching,
assembly, context loading, rendering, atomic file replacement, printing, and
exit-code computation (`:4124-4155`). This places several independently
changing contracts behind a single large module.

There are two concrete seams to keep stable:

1. `_input_root_cwd()` changes the process-global current directory
   (`:52-75`) so that runtime board reads occur in a different checkout, then
   restores it before output context and file writing (`:4130-4149`). A
   concurrent in-process caller or a new helper that retains a relative path
   across the context can read from the wrong checkout. No concurrent caller
   was found in the static search, so this is a conditional hazard, not a
   demonstrated race.
2. `_build_and_write()` computes nonzero for an unexpected symbol/QM failure
   (`:3980-3987,4151-4155`), and the module CLI propagates that exit code
   (`:4166-4172`), but public `main()` discards it and returns a path
   unconditionally (`:4158-4163`). A direct caller could therefore receive a
   success-shaped path while the generated page contains an
   `UNEXPECTED_ERROR`. No direct callers outside this module were found, so
   current CLI use is protected.

**Counterevidence and containment.** The module is explicitly display-only
(`README.md:55`; module docstring `:15-22`), writes only a `.tmp` HTML page via
temporary file plus `os.replace` (`:4142-4148`), and render escapes inserted
values (`:3998-4005`). It converts per-symbol failures into visible blocked
records and CLI failure (`:3980-3987`). The 2,681-line dashboard test module
checks input/output-root restoration (`tests/test_attractiveness_dashboard.py:
1827-1866`) and basic `main()` file output (`:1868-1889`).

**Smallest safe proposal.** Keep data and policy behavior unchanged; first
extract injected, root-explicit input adapters and a typed build result
`(output_path, exit_code, blocked)` behind the existing API. Migrate callers to
the result/CLI contract before making `main()` expose failure. Split pure
payload assembly and HTML rendering only after parity fixtures cover the
current output. Avoid `chdir` by passing resolved roots through the input
adapters.

**Eligibility:** **PLAN-ONLY / BLOCKED.** The module is listed as protected
source at `00-preflight-and-wip.md:130`. It is also a presentation boundary,
so this must not alter candidate ordering, policy gates, or position state.

### AC-03 — `config.py` is a broad, untyped cross-domain dependency hub

**Classification:** **VERIFIED coupling; INFERRED change-blast-radius risk.**
**Priority:** P2 sequencing/design candidate; do not do a broad refactor.

`config.py` co-locates risk limits, cache dates, backtest conventions,
strategy settings, H5/H6/H7/H8/H9/H10 controls, experimental/display values,
and source paths in 913 lines (`config.py:30-617` contains examples across
those domains). Static search finds 81 direct importers; H7-prefixed values
alone are referenced from 24 modules, H5 from 9, H6 from 7, and
`ATTRACTIVENESS_` from 7. The public values include mutable lists and dicts,
for example `UNIVERSE` and `STUDY_ERA_START` (`config.py:60-69`), alongside
frozen tuples and scalar settings. A caller can thus acquire unrelated policy
dependencies merely by importing the hub, and a review of a config diff has a
large, non-obvious fan-out.

The current scoring path demonstrates both the need for and the burden of
this coupling: it reads `config.H7_LANE_PRIORITY` while constructing the
ledger event (`options_researcher/h7_real_scoring.py:1932-1951`) and hashes a
runtime configuration provenance for the receipt (`:1749-1781`). This protects
final scoring from silent drift, but does not make module-level configuration
dependencies self-describing at the interface level.

**Counterevidence and containment.** Config values are deliberately visible
and versioned rather than silently fetched. H7 finalization revalidates its
session, writes an immutable receipt before the one expected-head ledger append,
and explicitly refuses an orphan/conflict (`options_researcher/h7_real_scoring.py:
1859-1971`). Its authority/publication tests cover numerous refusal cases
(`tests/test_h7_real_scoring.py:508-1144`), and structural one-door tests
constrain real-store append paths (`tests/test_h7_one_door.py:228-285`). This
is not evidence for changing any frozen number or strategy parameter.

**Smallest safe proposal.** Introduce read-only, immutable per-domain views
only at new or already-isolated interfaces (for example a scoring-policy view
or display-policy view), with an explicit canonical serialization used in
provenance. Retain compatibility re-exports while proving byte-identical policy
values and receipt hashes. Do not migrate all 81 importers and do not convert
an architecture cleanup into a strategy/configuration change.

**Eligibility:** **PLAN-ONLY / BLOCKED.** `config.py` is protected at
`00-preflight-and-wip.md:55`. Any migration that changes receipt/hash shape,
authority checks, or registered settings requires dedicated registration and
compatibility review.

## Additional candidates and non-findings

- **H7 score publication ordering — verified intentional, not a current
  finding.** `finalize_real_score()` writes an immutable score receipt before
  appending its causal ledger event; an append refusal produces an explicitly
  named orphan and is retryable only at the same input head
  (`options_researcher/h7_real_scoring.py:1924-1971`). This non-atomic boundary
  is a residual operational risk, but the code refuses divergence and tests
  cover orphan/conflict cases. Do not “fix” it with a destructive rewrite or
  by weakening immutability without a separate design review.
- **Dead/duplicated code — UNKNOWN.** Static discovery found many deliberate
  legacy/compatibility paths (for example `options_researcher/h10_observe.py:
322-478` and `options_researcher/h7_scoring_identity.py:175`). The audit did
  not establish that any is dead: legacy history and compatibility are often
  correctness requirements here. No deletion candidate is recommended.
- **Silent failures — no unsupported claim.** The reviewed dashboard converts
  expected data errors to visible unavailable/blocked states
  (`options_researcher/attractiveness_dashboard.py:1067-1073,1422-1427,
  1499-1504`), while scoring wraps invalid persisted state as refusal. The
  broad dashboard assertion-loading catch is display-grade degradation, not a
  demonstrated hidden authority failure.

## Priority and decision

1. **AC-01:** design a typed shadow workflow map for the ritual, because it
   concentrates the only reviewed path that can persist, merge, push, and
   back up operational evidence.
2. **AC-02:** stabilize the dashboard's root and exit contracts before future
   UI growth; this is low authority but high maintenance coupling.
3. **AC-03:** define narrow immutable policy views only when an isolated
   feature needs one; avoid a repository-wide config rewrite.

**Final ready decision:** **NOT READY** for code changes from this audit. The
findings are ready as evidence-backed, protected-path implementation proposals
only. No strategy, parameter, provider, ledger, cache, receipt, or operational
behavior change is supported by this review.
