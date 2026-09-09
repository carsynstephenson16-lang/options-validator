# Brief 41 — independent adversarial review, round 2

**Target:** `docs/superpowers/plans/2026-09-09-41-launchagent-loaded-check-codex-brief.md` rev 2 (uncommitted on `claude/brief-41-launchagent-loaded-check-2026-09-09`, base `origin/main @ 645365b`), the round-1 receipt, registry row 41.
**Reviewer:** fresh Opus subagent, read-only, dispatched 2026-09-09 ~13:20 ET; every citation checked, `launchctl` and `plistlib` facts executed.
**Verdict:** **FAIL** — 2 new blockers, 1 major, 7 minors, 5 nits. Rev 2 closed 21 of 23 round-1 findings (R1-15 and R1-16 PARTIAL).
**Disposition:** every finding applied in rev 3 (same file, same day); IDs cited in rev 3 as R2-Bn / R2-Mn / R2-mn / R2-nn. Orchestrator re-verified B-1 and B-2 independently before applying (plistlib fails on exactly one of twelve plists, regex recovers the label; `diagnostic_source_hash()` = `acf52fb1…` vs receipt `bccee0a6…`).

## Findings (reviewer's text, condensed)

**BLOCKER**
- **R2-B1** WP-A.2's `plistlib` parse crashes on `tools/launchagents/com.carsyn.options-validator.intraday-capture.plist:4` (`--` inside an XML comment; expat rejects, `plutil -lint` accepts). `tracked_labels()` would raise `ExpatError` (not the handled `ValueError`) on every real run; `|| true` swallows it; no receipt; the invisible label is the very agent whose silent unload motivates the brief. D.1's temp-tree test would stay green. Fix: regex fallback on `ExpatError` + a real-tree test asserting all twelve labels resolve; do not edit the plist (installed copy is byte-identical).
- **R2-B2** Scope OUT reasons about `config_hash()` and the feasibility closure but omits `diagnostic_source_hash()`: `research/hashing.py:132` `DIAGNOSTIC_SOURCE_PATHS_V2` includes `options_researcher` and `tools` (rglob `*.py`, `:101`); WP-A and WP-C both rotate it; it is a refusal gate at `h7_watch.py:197`, `h7_data_gate.py:748`, `h7_exit_session.py:247,267`, `h7_activation_guard.py:245`. Nothing currently valid breaks (the 09-04 receipt is already stale), but landing 41 between an activation-day regeneration and activation would silently invalidate the chain. Fix: state it; sequence before, never between.

**MAJOR**
- **R2-M3** The A.1/A.3 seam never says who assembles `loaded` for `compare()`; the natural reading hands it `launchctl list` output, bypassing the per-label `print` decision that was the R1-7 fix. Fix: name the assembler; D.1 asserts a `list`-vs-`print` disagreement.

**MINOR**
- **R2-m4** CI job runs nineteen modules at `ci.yml:89-107`, not twenty at `:86-107` (R1-16 carried the same error).
- **R2-m5** `test_every_python_module_site_is_classified` does not exist; the set-equality at `:532-535` sits inside `test_every_script_surface_is_classified` (`:528`).
- **R2-m6** `executor-handback-verification` skill is not on this branch (it lands via PR #164). Fix: cite the PR.
- **R2-m7** `print-disabled` lists only labels with a persisted state (8 of 12 today) inside a `disabled services = {` wrapper; absence = enabled. The `DISABLED` logic survives but the brief must say so.
- **R2-m8** "Renumber by the exact number of lines inserted" is not deterministic (B.2's comment block has no fixed length). Fix: recompute from the edited script; offset is a cross-check. No other line-keyed structure exists in the file.
- **R2-m9** `_copy` is at `tests/test_job_health_digest.py:49-53`, not `:47-51`.
- **R2-m10** Receipt keyed by `as_of` lets Tuesday's `LOADED` overwrite Monday's `INSTALLED_NOT_LOADED` before the digest shows it; git history is not an owner surface. Fix: key by `run_date`; digest reads the newest for the `as_of`.

**NIT**
- **R2-n11** `feasibility_source_closure` is `:115-140`; `:143` starts `FEASIBILITY_SOURCE_PATHS`. **R2-n12** The `PROJECT_STATE.md` quote covers `schwab-chain-intraday` only; `job-health-digest` needs its own source. **R2-n13** `--agents-dir` default unstated. **R2-n14** `os.getuid() == 501` under the ritual's agent is Inference. **R2-n15** A non-zero `list` collapsed the whole check to `UNAVAILABLE` although the per-label `print` path is independent.

## Verified correct by the reviewer

Contract (header, DRAFT, PR-starts-draft, D-1/D-2/D-3 recorded not made, no frozen number, no `config.py`); registry row 41 highest. All `tools/daily_ritual.sh` citations (`:119,:120,:122,:140-142,:375-383,:384-385,:387,:562-563,:647-654,:655,:666-675`); `tests/test_daily_ritual_provenance.py` `:32` docstring, `:51-66,:60,:108-109,:137-143,:180-184,:528/:531-535,:544-552`; `tests/test_shell_banner_guard.py:361-437` re-traced (no capture span, no allowlist needed); `tools/job_health_digest.py:28-35,:37-42,:716-743,:740,:750-775` incl. the `NO_SESSION` short-circuit `:728-732`; `data/atomic_io.py:66`; `ritual_status.py:120-121`; `ci.yml:68-107`; README `:39-47,:49-51,:53-58,:89-90`; `install.sh:48`; `schwab_chain_capture.py:231`; `test_ops_alignment_check.py:192`; twelve plists across four roots. Live: uid 501; `print` → 0 loaded-but-idle, 113 absent; `list` header exact; `com.carsyn.repo-reconcile` loaded today (row would be `LOADED`); `UNTRACKED` empty today; `pick-dashboard` excluded by prefix; research-refresh installed + enabled + not loaded (acceptance 6 satisfiable). Ops checkout at `645365b` holds the same twelve plists. Insertion at 386 sits between `# ---- end full-tier region B ----` (`:373`) and `# ---- Schwab preclose lane ----` (`:387`); region markers slice correctly and are additive; `test_require_data_precedes_every_mutation_surface` (`:400`) satisfied. Feasibility-closure argument sound; the one missed hash surface is `diagnostic_source_hash` (B-2).
