# Brief 41 — independent adversarial review, round 3

**Target:** `docs/superpowers/plans/2026-09-09-41-launchagent-loaded-check-codex-brief.md` rev 3 (uncommitted on `claude/brief-41-launchagent-loaded-check-2026-09-09`, base `origin/main @ 645365b`), receipts rounds 1–2, registry row 41.
**Reviewer:** fresh Opus subagent, read-only, dispatched 2026-09-09 ~13:33 ET; every citation checked; `plistlib`, regex, `launchctl`, closure, `diagnostic_source_hash`, and `collect_health` executed.
**Verdict:** **FAIL** — 1 blocker, 2 majors, 3 minors, 4 nits; all fixes supplied as exact wording. Rev 3 closed 11 of 15 round-2 findings outright (R2-B2, R2-M3, R2-m10 PARTIAL).
**Disposition:** every finding applied verbatim in rev 4 (same file, same day); IDs cited in rev 4 as R3-n. Round 4 scoped to the edited sections.

## Findings (reviewer's text, condensed)

**BLOCKER**
- **R3-1** WP-A.3's assembler union `{print-loaded tracked} | {listed ∩ prefix}` re-adds any tracked label that `list` reports while `print gui/<uid>/<label>` refuses → classifies `LOADED` instead of `INSTALLED_NOT_LOADED`, masking the incident class; contradicts the brief's own D.1 requirement that `print` wins. Latent today (no live disagreement). Fix: `untracked_seen = listed∩prefix − tracked`; `loaded = {print-loaded tracked} | untracked_seen`.

**MAJOR**
- **R3-2** `--as-of "${AS_OF:-$RUN_DATE}"` fabricates a session identity on the empty-`AS_OF` path; the repo's precedent is skip, never substitute (`daily_ritual.sh:122-124` crits, `:140` guards with `[ -n "$AS_OF" ]`). Fix: pass `"$AS_OF"` as-is; receipt `as_of: null`; C.1 → `DEGRADED`.
- **R3-3** C.1's lookup by receipt `as_of` never matches: `tools/job_health_digest.sh:14` sets the digest's `as_of` to today's calendar date (= ritual `RUN_DATE`), not the lagging session (Test-verified: `collect_health(root,'2026-09-09')` → `Ritual overall MISSING`; `'2026-09-08'` → real rows — a pre-existing digest defect, never observed because the agent is uninstalled). D.2's fixtures would pass green while production emitted `NOT_INSTRUMENTED` daily. Fix: read `launchagent_state_{as_of}.json` directly (`_ritual_overall` idiom `:102-104`), keyed by `run_date`; fallback to newest → `DEGRADED`.

**MINOR**
- **R3-4** `State` set not total: a loaded job whose installed plist was deleted reads as benign `NOT_INSTALLED`; `DISABLED`/`LOADED` overlap unordered. Fix: add `LOADED_NOT_INSTALLED` → `DEGRADED`; ordered `if/elif` chain; totality test over sixteen combinations.
- **R3-5** R2-B2 clause: "silently invalidate" is wrong (all five gates refuse loudly); "never between" is uncheckable; `tools/h7_activation_day.sh:58,59-63,81-89,:196` already pin regeneration and activation to one HEAD. Fix: replace with the loud-refusal statement and a checkable SHA obligation.
- **R3-6** Fallback catches only `ExpatError`; `plistlib.InvalidFileException` (a `ValueError` subclass) would escape indistinguishably; match selection unspecified. Fix: catch both; `re.findall`, exactly one distinct label. Attack (c) inert today: each of twelve plists has exactly one `Label`, none in a comment.

**NIT**
- **R3-7** README byte-identical claim is `:34-37`. **R3-8** provenance docstring is `:31-32`. **R3-9** `HealthStatus` is `:28-34`. **R3-10** `installed` assumes filename stem == `Label` (true for all twelve; label it).

## Verified correct by the reviewer

Executed: `plistlib.load` ExpatError on exactly one of twelve plists, `plutil -lint` OK, regex recovers all twelve (one match each); uid 501; `print` → 0 / 113 / 113; `print-disabled` shape (wrapper + 8 of 12 labels, all enabled); closure 50 paths, `__init__.py` in, ritual/digest/ritual_status/token-age out; `diagnostic_source_hash()` `acf52fb1…` vs receipt `bccee0a6…`; 3,905 tests. Citations: `research/hashing.py:101,:132`; all five `source_hash` refusal sites genuine; `h7_schwab_window_registration.py:115-140,:143`; `ci.yml:89-107` nineteen modules; provenance `:51-66,:60,:98-110,:137-143,:180-184,:528,:532-535,:544-552`; `test_job_health_digest.py:49-53`; `test_shell_banner_guard.py:361-437`; digest `:37-42`, row builders, `:716-743`, `:740`, `:750-775`; ritual `:119,:120,:122,:140-142,:373,:375-383,:384-385,:387,:562-563,:647-654,:655,:666-675`; `atomic_io.py:66`; `ritual_status.py:116,120-123`; README `:39-47,:49-51,:53-58,:89-90`; `install.sh:44-54,:48`; both `PROJECT_STATE.md` quotes verbatim; twelve plists / four roots; `.bak` excluded; `reports/ritual/` prefix fresh; ops checkout at `645365b` holds all twelve. Contract: header, DRAFT, PR-starts-draft, D-1/D-2/D-3 recorded not made, no frozen number, no single-source value restated, registry row 41 records both receipts. Attack (e) clean: no `config.py`, ledger, live-order, paper-book, or closure surface; `config_hash()` unaffected.
