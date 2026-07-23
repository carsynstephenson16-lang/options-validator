# 2026-07-23 — Integrity Hardening Batch v1 — Codex brief

**Executor:** Codex implements; Claude Code orchestrated and reviews; the owner types every
frozen number and ratifies every gate flip. If a cited interface, path, or line does not match
the installed code, STOP and report — do not improvise around it.

**Provenance.** An external (ChatGPT) plan proposed a repo-wide "Phase 1 research-controls
layer": four global execution modes (EXPLORE / IMPLEMENT / VALIDATE / OOS_REVEAL), a
registered-run wrapper, an OOS path guard, a manifest validator, an append-only OOS ledger, an
exploration logger, hash caching, a research-integrity CI lane, and adversarial tests. A
2026-07-23 three-agent evaluation (guardrail inventory; workflow/queue fit; incident history)
found:

- **5 of 10 proposed components already exist**, several twice: manifest validation
  (`research/experiments.py::register` + `options_researcher/robustness/models.py::ExperimentSpec`
  + `options_researcher/h7_window_registration.py`), append-only hash-chained ledgers
  (`research/ledger.py` + `options_researcher/h7_event_ledger.py`), OOS gating
  (`research/windows.py` + `research/diagnostics.py::authorize_oos_run` +
  `research/experiments.py::reveal_oos`), exploration logging
  (`research/experiments.py::log_trial_intent`), and large adversarial suites
  (`tests/test_research_integrity.py`, `tests/test_block_ledger_edits.py`).
- **The two genuinely missing components — a global mode resolver and a distinct CI lane —
  have zero real incidents behind them** in the repo's documented history. Worse, incident
  `H7_STAGE1_INDEPENDENT_HARDENING` (facts.log, 2026-07-12) records green CI *missing* six
  integrity gaps that adversarial review caught — evidence against leaning on a CI lane.
- Every documented real incident maps to: adversarial tests (3), manifest/hash checks (2),
  frozen-value guarding (2), append-only enforcement (2), receipt-chain linkage (1), hash
  reproducibility (1), capture receipts (1) — plus two classes no proposal named
  (hook deploy-order discipline; doc-rewrite content preservation).

**Verdict: the external plan is REJECTED as written** (duplication + a second competing source
of truth over the existing function-level gates). The repo-wide mode layer and a data-layer OOS
read guard are PARKED in `ideas-parking-lot.md` (2026-07-23 entry). What survives is this
batch: four small, independent, incident-backed guards, plus one optional item.

**Queue placement (binding):** this batch is fill-in work. It must NOT displace EX9
(earnings-variance capture — calendar-urgent, August prints) or EX8 (A2 runner, unblocked).
Tasks are independent; do them singly whenever a queue item is blocked on an owner input.

**Global rules (as in the 2026-07-22 recorders brief):** strict TDD (failing test first, watch
it fail, implement, full `uv run python -m unittest discover -s tests` + `uv run ruff check .`
+ `uv run pyright` green before each commit). Never hand-edit
`ledger/facts.log`, `ledger/experiments.jsonl`, `ledger/HEAD`, or
`ledger/h7_forward/{events.jsonl,HEAD}`. Tests stay offline. No new dependencies.

**Wording caution for this batch:** the live-trading guard hook pattern-matches tool payloads
for order-placement-shaped strings. When writing tests or docs for Task 1, construct the
forbidden strings programmatically in fixtures (e.g. join fragments at runtime) rather than
writing them literally, or the guard will (correctly) block your own edit. This brief
deliberately describes those patterns indirectly for the same reason.

---

## Task 1 — Promote and adversarially test the live-order-blocking hook

**Scope guard:** protects the absolute "never a live-order bot" boundary that every live
hypothesis's verdict depends on; it is currently the only guard hook with zero test coverage.

**Existing assets:** live registered copy at `.claude/hooks/block_live_trading.py`
(gitignored, unreachable by CI); a tracked copy of unknown freshness at
`ov/.claude/hooks/block_live_trading.py`; precedent: `.agents/hooks/block_ledger_edits.py`
(tracked) + `tests/test_block_ledger_edits.py` (subprocess-driven suite — copy its harness
pattern exactly, including `REPO_ROOT / ".agents" / "hooks"` resolution and exit-code
assertions).

**Files:** Create `.agents/hooks/block_live_trading.py` (copied from the canonical source —
see step 1), Create `tests/test_block_live_trading.py`. Do NOT delete `.claude/hooks/`'s copy
and do NOT edit `.claude/settings.local.json` (owner-gated final step below).

**Behavioral contract:**
1. First, diff `.claude/hooks/block_live_trading.py` against `ov/.claude/hooks/block_live_trading.py`.
   If they differ materially, STOP and report the diff — do not pick a winner yourself.
2. The tracked copy must be byte-identical to the live `.claude/hooks/` copy at promotion time.
3. Tests invoke the hook as a subprocess with PreToolUse-shaped JSON on stdin (same as the
   ledger-guard tests). Enumerate the regex families from the hook source itself; every family
   gets at least one BLOCKED case (the order-placement verb patterns, the broker-SDK patterns,
   and the paper-mode-disabling assignment patterns) across Bash `command`, Write `content`,
   and Edit `new_string` payloads, plus one benign near-miss ALLOWED case (e.g. a docstring
   saying trading is forbidden, `ls`, running the test suite). Build blocked-case strings by
   concatenating fragments at runtime per the wording caution above.
4. Unparseable stdin must exit 2 (fail closed) — asserted by a test.

**Acceptance:** every regex family enumerated in the hook source is named in a test; suite
green offline; ruff + pyright green.

**Owner-gated final step (do NOT do in this task):** repoint
`.claude/settings.local.json` from `.claude/hooks/block_live_trading.py` to
`.agents/hooks/block_live_trading.py`. Per the 2026-07-15 lockout lesson: script committed and
tested FIRST, registration change LAST, old copy left in place until the repoint is verified in
a live session.

## Task 2 — Hook-registration doctor (lockout-recurrence guard)

**Scope guard:** the daily ritual operates H7's LIVE forward window; on 2026-07-15 a hook
registered before its script existed fail-closed every session. This check makes that
unrepeatable.

**Files:** Create `tools/check_hooks.py`, Create `tests/test_check_hooks.py`.

**Behavioral contract:**
1. Read-only. Parses `.claude/settings.local.json` (and any hooks it references); for every
   registered hook command: the script file exists, is readable, and passes
   `py_compile` parsing. Exit 0 all-good; exit 1 naming each failing hook and why.
2. If `.claude/settings.local.json` is absent (CI, fresh clone), exit 0 with a "no local
   settings — nothing to check" line. Tests use temp-dir fixtures with a settings-file path
   parameter; never touch the real `.claude/`.
3. No side effects, no network, no repo mutation.

**Acceptance tests (named):** missing-script → exit 1; unparseable-script → exit 1; valid
registration → exit 0; absent settings file → exit 0 skip.

**Owner-gated wiring:** adding `check_hooks` as a pre-step in `tools/daily_ritual.sh` changes
the frozen operator order (H7 amendment v1.4) — owner decision `[OWNER: yes/no]`. The tool
itself is unblocked now.

## Task 3 — Frozen-values drift check (warn-only until owner ratifies)

**Scope guard:** protects H6/H7/H8/RQ2/A2 registered parameters from silent drift between
registration and verdict — the machine version of what caught the H6 "amendment-2" unregistered
draft (fact `H6_TRIAL7_AMENDMENT_2_WITHDRAWN`, 2026-07-15) and the preflight registered-scope
default flip (fact `H7_PREFLIGHT_SCOPE_CORRECTION`, 2026-07-20) only after the fact.

**Files:** Create `research/frozen_values.json`, Create `tools/check_frozen_values.py`,
Create `tests/test_frozen_values_check.py`.

**Behavioral contract:**
1. `frozen_values.json` maps registration → list of `config.py` symbol names → the registered
   value, each entry citing the ledger fact / registration that froze it. Codex populates it by
   COPYING current `config.py` values for the starter symbol list below — Codex decides no
   values; every value must already exist in code and in a registration.
2. `check_frozen_values.py` imports `config`, compares each listed symbol's current value to
   the manifest, and reports mismatches naming the symbol, both values, and the citing
   registration. **Warn-only mode** (always exit 0, print findings) until the owner ratifies;
   a single `ENFORCE = false` flag at the top of the manifest file flips it to exit 1.
3. Updating a manifest value requires citing a new ledger amendment fact in the same entry —
   the checker rejects (in enforce mode) any manifest entry without a citation string.
4. Starter symbol list `[OWNER: ratify or edit before the enforce flip]`: `IN_SAMPLE_END`,
   `OOS_LOOK_BUDGET`, `MIN_LOSSES_FOR_VERDICT`, `H6_IVR_MAX`, the H6 trial-7 DTE/exit/cap
   band, the H7 lane definitions and sleeve cap, the H8 parameter set, `UNIVERSE`.
   If any named symbol does not exist in `config.py` under that name, STOP and report the
   actual names — do not guess mappings.

**Acceptance tests (named):** matching manifest → clean; drifted value → finding naming
symbol + citation; enforce-mode drifted → exit 1; enforce-mode entry missing citation →
exit 1; warn-mode drifted → exit 0 with finding printed.

**Owner gates:** `[OWNER: ratify starter symbol list]`, `[OWNER: flip ENFORCE]` — both blank
until typed by the owner.

## Task 4 — Parking-lot section-preservation check (pre-commit)

**Scope guard:** on 2026-07-22 a parking-lot rewrite silently deleted two entries (restored in
`4318160`); the parking lot is the scope-guard's overflow valve, so silent loss there corrupts
scope decisions.

**Files:** Create `tools/check_parking_lot_sections.py`, Create
`tests/test_parking_lot_sections.py`, Modify `.pre-commit-config.yaml` (add a local hook
running the checker when `ideas-parking-lot.md` is staged).

**Behavioral contract:**
1. Compares `## ` section headers in the staged `ideas-parking-lot.md` against `git show
   HEAD:ideas-parking-lot.md`. Any header present in HEAD but absent from the staged version
   fails the commit UNLESS the staged file contains an explicit tombstone line
   `REMOVED <YYYY-MM-DD>: <exact header text>`.
2. New headers, reordering, and body edits are always allowed. File absent in HEAD (first
   commit) → pass.
3. Core comparison is a pure function over two strings so tests need no git fixtures;
   a thin wrapper does the git plumbing.

**Acceptance tests (named):** header removed without tombstone → fail naming the header;
removed with tombstone → pass; header added/reordered → pass; unchanged → pass.

## Task 5 (OPTIONAL — owner decides inclusion) — Network-off enforcement in robustness runs

**Scope guard:** registered RQ2/A2 robustness artifacts self-report `"network_calls": 0`;
this makes the claim machine-true instead of asserted.

**Ordering gate:** `options_researcher/robustness/` is uncommitted on branch
`docs/replan-2026-07-22` as of this writing — do this task only AFTER that layer lands on its
final branch, and coordinate with its author session. `[OWNER: include this task? yes/no]`

**Files:** Create `options_researcher/robustness/netguard.py`, Modify
`options_researcher/robustness/runner.py` (wrap `run`/`resume` execution), Test additions in
`tests/test_robustness_layer.py`.

**Behavioral contract:** a context manager that patches `socket.socket` (and
`socket.create_connection`) to raise during experiment execution; `doctor` and report writing
unaffected; any attempted connection inside a run raises with a message naming the netguard.

---

## Explicit non-goals (do not build; reasons recorded)

- **Four-mode execution resolver** — zero incidents; would create a second source of truth
  competing with the existing function-level gates (`authorize_oos_run`, `reveal_oos`,
  robustness `doctor`); PARKED.
- **New registered-run CLI wrapper** — would be the third implementation
  (`research/cli.py`, `robustness/cli.py` exist); extend those instead, case-by-case.
- **New manifest validator / OOS ledger / exploration logger** — exist (twice, twice, once).
- **Data-layer OOS read guard** — real gap (ad hoc code can read post-`IN_SAMPLE_END` parquet
  outside sanctioned entry points), but zero incidents and the sealed holdout is intact at
  0/3; PARKED with a revisit trigger.
- **Distinct research-integrity CI lane** — integrity tests already run in the single CI job;
  the 2026-07-12 fact shows green CI is not the safety net here; cosmetic renaming deferred.
- **Hash caching** — `research/hashing.source_hash` is only called at gate time
  (register/reveal/doctor), never per tool action; no hook needs it; no perf problem exists.

## Plan self-review (done at write time)

- Every task cites the incident or fact that motivates it; the two zero-incident proposals are
  explicitly parked, not silently dropped.
- No task touches verdict-bearing code paths (H7 forward window, scoring, ledger writers);
  Task 5 is the only one touching a research runner and is ordering-gated + owner-gated.
- Owner blanks: Task 2 ritual wiring, Task 3 symbol list + enforce flip, Task 5 inclusion,
  Task 1 settings repoint. Codex checks none of these boxes itself.
- Known deviation: Task 1 leaves a temporary duplicate of the hook (tracked + gitignored
  copies) until the owner-gated repoint — deliberate, per the lockout lesson.
- The Task 1 test-fixture wording caution exists because this brief itself was blocked once by
  the live-trading guard while quoting its patterns literally — evidence the hook fires.
