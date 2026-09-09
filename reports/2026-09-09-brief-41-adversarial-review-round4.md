# Brief 41 — independent adversarial review, round 4 (scoped)

**Target:** `docs/superpowers/plans/2026-09-09-41-launchagent-loaded-check-codex-brief.md` rev 4 (uncommitted on `claude/brief-41-launchagent-loaded-check-2026-09-09`, base `origin/main @ 645365b`), scoped per round 3 to WP-A.1/A.2/A.3, A.5, WP-B `--as-of`, WP-C.1, D.2, the R2-B2 replacement paragraph, and three nit citations.
**Reviewer:** fresh Opus subagent, read-only, dispatched 2026-09-09 ~13:44 ET; set algebra, zsh/argparse empty-argument behaviour, `job_health_digest.sh:14`, `collect_health` on both dates, and all `h7_activation_day.sh` citations executed.
**Verdict:** **PASS WITH FIXES** — 2 minors, 2 nits, all exact wording, no further round required. R3-1/2/3/5/6/7/8/9/10 CLOSED; R3-4 PARTIAL (totality claim over-stated) → closed by R4-1.
**Disposition:** all four applied verbatim in rev 5; Status flipped to READY FOR HAND-OFF.

## Findings

- **R4-1 (MINOR)** `compare()`'s label universe was undefined and the sixteen-combination totality assertion was unsatisfiable: two tuples (`tracked=False, installed=False, loaded=False`) match no branch, and the inputs are unbounded (`~/Library/LaunchAgents` holds 37 plists, 31 neither tracked nor prefixed; `print-disabled` marks four `com.apple.*` labels disabled). Fix: define the universe as tracked ∪ prefixed-installed ∪ prefixed-loaded; the two unreachable tuples raise; D.1 asserts fourteen states + two raises + no-row cases.
- **R4-2 (MINOR)** E.1 documented the receipt as `launchagent_state_<as_of>.json`, contradicting A.4's `run_date` key. Fix: `<run_date>` with the reason.
- **R4-3 (NIT)** `observe()` signature omitted the `prefix` its body uses. Fix: `prefix: str = OWN_PREFIX`.
- **R4-4 (NIT)** "receipt absent" named two conditions in C.1. Fix: "no `launchagent_state_*.json` on disk at all → `NOT_INSTRUMENTED`".

## Verified correct by the reviewer

R3-1 algebra: `untracked_seen ∩ tracked = ∅`, so for every tracked label `t ∈ loaded ⟺ print_loaded(t)`. zsh passes `--as-of ""` as an empty argv element under the quoted form in WP-B and argparse yields `as_of=''` — A.5's empty semantics are implementable. `tools/job_health_digest.sh:14` sets the digest `as_of` to the New York calendar date; `_ritual_overall` at `tools/job_health_digest.py:102-104`; `collect_health(Path('.'),'2026-09-09')` → `Ritual overall MISSING`, `'2026-09-08'` → real rows; newest `run_status_` is 2026-09-08. R2-B2 paragraph: `h7_watch.py:197` / `h7_data_gate.py:748` `raise ValueError`; `h7_exit_session.py:247,267` `raise ExitSessionRefused`; `h7_activation_guard.py:245` failing `Check`; `h7_activation_day.sh:58`, `:59-63`, `:81-89`, `:196` exact. D.2 fixture rule matches C.1's OK-suppression. Twelve plists across four roots; `.bak` excluded; `pick-dashboard` outside prefix; `repo-reconcile` tracked + installed. README `:34-37`, provenance `:31-32`, `HealthStatus :28-34`, `HealthRow :37-42`. Contract: DRAFT at review time, PR-starts-draft with the no-authority list, D-1/D-2/D-3 recorded not made, zero `${AS_OF:-…}` fallbacks, registry row 41 records rounds 1–3.
