# Brief 41 — independent adversarial review, round 1

**Target:** `docs/superpowers/plans/2026-09-09-41-launchagent-loaded-check-codex-brief.md` rev 1 (uncommitted draft on `claude/brief-41-launchagent-loaded-check-2026-09-09`, base `origin/main @ 645365b`) and registry row 41.
**Reviewer:** Opus subagent, read-only, dispatched by the orchestrating session 2026-09-09 ~13:05 ET; citations executed against the working tree, closure and `launchctl` facts run, not assumed.
**Verdict:** **FAIL** — 3 blockers, 4 majors, 11 minors, 5 nits.
**Disposition:** every finding applied in rev 2 (same file, same day). Orchestrator note on R1-8: the reviewer's replacement line numbers for `2026-09-03.md` (6/9/21) were themselves wrong — the quotes sit at lines 25/28/40 — but the underlying finding (the file is gitignored, Codex cannot read it) stands, so rev 2 quotes the three sentences inline and keeps 25/28/40.

## Findings (reviewer's text, condensed; IDs as cited in rev 2)

**BLOCKER**
- **R1-1** WP-A.2 scanned only `tools/launchagents/` and `tools/repo_rag/launchd/`; `git ls-files '*.plist'` shows a third root, `tools/launchd/com.carsyn.options-validator.research-refresh.plist`. Under rev 1 the brief's flagship example (research-refresh, owner decision D-2) would classify `UNTRACKED` → `DEGRADED`, and acceptance step 6 was unsatisfiable. Fix: third (and fourth, `tools/anti-stranding/`) discovery root.
- **R1-2** Inserting lines after `tools/daily_ritual.sh:385` shifts every later line; `tests/test_daily_ritual_provenance.py` registries 2 and 3 are keyed by line number (`PYTHON_DASH_C_CLASSIFICATION` keys `{406, 449}` at `:108-109`; `MUTATION_VERB_SITES` values `{428, 592, 601, 613, 614, 615, 632}` at `:137-143`) and fail closed. Rev 1 put that file OUT of scope. Fix: renumbering in WP-D, file IN scope.
- **R1-3** `test_every_python_module_site_is_classified` (`:531-535`) asserts set equality over `DATA_TIER_MODULES + …`; rev 1 never registered the new module. Fix: add to `DATA_TIER_MODULES` (`:51-66`).

**MAJOR**
- **R1-4** D-1 named the digest `FAILED` row as the escalation surface, but the digest agent is tracked-but-uninstalled; nothing produces it. Fix: the ritual echo is the only live surface; digest work kept but marked dormant; new D-3.
- **R1-5** `loaded_labels -> frozenset[str]` but "return None" on failure; pyright fails. Fix: `frozenset[str] | None`.
- **R1-6** A `launchctl disable`d agent is absent from `list` exactly like an unloaded one, and `bootstrap` refuses it; `print-disabled gui/501` (run: all eight labels `=> enabled` today) discriminates for free. Fix: `DISABLED` state + `launchctl enable` remedy text.
- **R1-7** Bare `launchctl list` runs in the caller's domain; the precedent (`tools/anti-stranding/install.sh:48`) pins `gui/$(id -u)`. Test-verified the ritual's agent is `domain = gui/501`, `PATH => /usr/bin:/bin:/usr/sbin:/sbin`. Fix: pin the domain; add the fact to Provenance.

**MINOR**
- **R1-8** Session-note citations; file is gitignored so Codex cannot read it. Fix: quote inline.
- **R1-9** `tools/launchagents/README.md:5-11` cited for the `.bak` exclusion says nothing about `.bak`; the exclusion is a property of the `*.plist` glob. Fix: drop the citation.
- **R1-10** "Only honest verification" sentence is at `:49-51`, bootstrap block is `:39-47`.
- **R1-11** The undated classifier claim is at `:89-90`; `:53-58` is already retracted. Fix: retarget WP-E.
- **R1-12** `rg -n launchctl --glob '!*.md'` also hits `tests/test_ops_alignment_check.py:192` and four plists. Fix: narrow claim.
- **R1-13** Status-semantics blocks are `:647-654` and `:666-675`; token advisory comment starts `:375` and carries the "DELIBERATELY OUTSIDE the Schwab preclose lane region" rationale.
- **R1-14** `collect_health` is `:716-743` (insert after `:740`); `HealthRow` is `:37-42`; `render_digest` is `:750-775`.
- **R1-15** Receipt keyed by lagging `AS_OF`; two run dates can share one `AS_OF` and overwrite. Fix: surface `run_at_utc` in the digest reason; note the overwrite.
- **R1-16** The macOS CI job runs twenty modules (`ci.yml:86-107`), not the two implied. Fix: reproduce the full list.
- **R1-17** `launchctl list` has a `PID\tStatus\tLabel` header and labels may contain spaces. Fix: header skip, `.split("\t", 2)`.
- **R1-18** `com.carsyn.repo-reconcile` (tracked, `tools/anti-stranding/`) was excluded by the prefix. Fix: every tracked label compared; prefix bounds only `UNTRACKED` discovery.

**NIT**
- **R1-19** "Twice this summer" unlabeled; one instance evidenced. **R1-20** Pin `/bin/launchctl`. **R1-21** Prefix literal gets a module constant with provenance. **R1-22** `ci.yml` was edited by WP-D.4 but absent from Scope IN. **R1-23** Registry row 41 records no receipt path.

## Verified correct by the reviewer

Header order and `Status: DRAFT`; PR-starts-draft rule; D-1/D-2 recorded not made; no frozen number invented; no `config.py` change; registry row 41 present and highest. `tools/daily_ritual.sh` `:119` `RUN_DATE`, `:120` `AS_OF`, `:122`, `:140-142`, `:562-563` (`reports/ritual` first on the data tier), `:385`, and that inserting after `:385` stays outside the Schwab lane region (`:387`). Region markers slice correctly via `_region()` (`:180-184`). **WP-B passes `tests/test_shell_banner_guard.py`** (traced against `:361-437`: no capture spans; no echo rule). `HealthStatus` vocabulary; `_PROBLEM_STATUSES`; `_copy` fixture idiom; `data/atomic_io.py:66`; `ritual_status.py:120-121`. **Closure executed:** 50 paths equal to `FEASIBILITY_SOURCE_PATHS`; `options_researcher/__init__.py` IN (imports no submodule); ritual, digest, token-age, ritual_status OUT. No `config_hash`, ledger, live-order, or paper-book surface touched. `reports/ritual/` prefix fresh. Nine `tools/launchagents` labels + `repo_rag/launchd` label exact; `NOT_INSTALLED` today = `job-health-digest`, `schwab-chain-intraday`; research-refresh `print` exits 113; 3,905 tests on `645365b`.
