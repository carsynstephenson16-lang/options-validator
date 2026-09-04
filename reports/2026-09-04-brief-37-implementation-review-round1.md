# Brief 37 implementation — independent adversarial review, round 1 (2026-09-04)

**Reviewer:** Opus subagent dispatched by the orchestrating Claude session (read-only on the tracked tree; ran tests and builds inside the worktree).
**Target:** draft PR #156, branch `codex/brief37-dashboard-presentation`, HEAD `72096a7` (Codex implementation commits `f1a486d`, `3963040`, `f0718f4`, `b6ada76`, `72096a7` on top of the brief's four docs commits), base `origin/main` @`039d76e`.
**Spec:** `docs/superpowers/plans/2026-09-04-37-dashboard-presentation-fixes-codex-brief.md` rev 5.
**Standing rule applied:** Codex's own "Terra" review claims were not committed anywhere and are void as evidence; this receipt is the review of record.

## Verdict: PASS WITH FIXES

No blocker. All eight work packages implement the specified behaviour; the H7 feasibility import closure is untouched; both manual proofs land. The three MEDIUM code findings below were applied by the orchestrating session in the commit that carries this receipt (comment/docstring truth and one loud default — trivial mechanical fixes under CLAUDE.md's division of labor); the scope findings are disclosed in the PR body for the owner.

## Findings (severity · disposition)

1. **MEDIUM** · `attractiveness_dashboard.py:1053-1056` docstring still promised "must never degrade quietly" after WP-G narrowed that guarantee. → Docstring now states the retention rule (applied).
2. **MEDIUM** · `attractiveness_dashboard.py:1973-1976` comment still asserted "the closes store ends earlier", the falsehood DR-6 was filed against, directly contradicted by the new sentence 23 lines below. → Comment now states the true cause (held for DR-5b; NaN never defaulted) (applied).
3. **MEDIUM** · `dashboard.py:545` `party_roles.get(symbol, "Watch")` silently rendered a held position as "Watch" when `party_roles` was absent (reproduced via `render({"h7_window": …})`, the branch's own test input). → Loud sentinel `ROLE UNAVAILABLE (assemble() supplied no party_roles)`, matching the `h7_window` house pattern, plus a test (applied).
4. **MEDIUM (scope)** · `options_researcher/dashboard.py` and `tests/test_dashboard.py` were wholesale ruff-formatted beyond the four fixes (the base file was not format-clean; 268 repo files are red). Functionally inert — the reviewer diffed every module-level literal with `ast.literal_eval`: only `_PARTY` differs, as WP-B requires. → Disclosed in the PR body; not reverted (reverting would be a second cosmetic churn).
5. **MEDIUM (scope)** · WP-E's whole-page `, before this ` assertion lives in `tests/test_schwab_freshness_gather.py:250` (which does render a page) instead of the named `tests/test_attractiveness_dashboard.py`. Equivalent coverage. → Disclosed.
6. **MEDIUM (scope)** · new test in `tests/test_ritual_receipt.py:244-273`, a file outside the brief's Scope IN. Hermetic, offline, non-mutating, passing; its name oversells (it constructs the ordering in Python; the real ordering proof is `tests/test_daily_ritual_provenance.py:233-241`). → Disclosed for owner acknowledgement.
7. **LOW** · WP-A's "END bound past the store is safe" Inference is proven empirically (banner reads 2026-09-03 against the real `load_closes`) but the new test mocks the loader. Suggest one test against a fixture parquet. → Recorded.
8. **LOW** · two bare `except Exception:` in new code (`:1089` WP-G, `:2005` WP-E), both brief-sanctioned and fail-safe, matching local precedent. → Recorded.
9. **LOW** · the rendered "Unavailable" line now reads `rv21: rv21 and iv_minus_rv are not computed …; iv_minus_rv: rv21 and iv_minus_rv …` — the brief's mandated wording stutters against the per-field label. Brief defect, not implementation. → Owner may shorten the sentence in a follow-up.
10. **LOW** · WP-C is flag-gated: if `h7_active` flips True, the panel prints "live, scores once 2026-10-26" for the OD-3-closed `h7-forward-15-v1` window again. Brief-mandated. → Residual recorded for the owner (namespace-gating belongs with the H7 activation work).
11. **LOW** · the digest OK row embeds an absolute home path (`chains: /Users/…/.cache/schwab_chains`), as the brief's example showed. → Consider `$HOME`-relative later.
12. **LOW** · `job_health_digest.py:98` message "receipt path escapes root" is now also used for a chain parquet escaping the cache root. → Noun could be widened later.
13. **LOW** · miscellanea: module-level `import pandas as pd` used only for an annotation; `a.get('count')` interpolated outside `_esc()` (internal ints only); watch role strings duplicated in `assemble()`; `Held — 1 shares` possible; `CHAIN_STALE_BLOCK_SESSIONS` (a gate constant) reused as a display-retention threshold (brief-mandated).

## Scope deviations (complete)

1. `tests/test_ritual_receipt.py` modified (not in Scope IN) — finding 6.
2. `dashboard.py` / `tests/test_dashboard.py` ruff-formatted — finding 4.
3. WP-E page assertion placed in `tests/test_schwab_freshness_gather.py` — finding 5.
4. WP-F executed as the inverse move (11-line dashboard + pick-tracker block moved down past the receipt block, instead of the 16-line receipt block moved up). **Acceptable:** pure permutation (657 lines before and after; sorted-line diff empty); resulting order receipt → dashboard → record → evaluate → terminal; `tests/test_daily_ritual_provenance.py` passes with its pinned line-number sets; every `note`/`crit` string byte-identical; `bash -n` clean.
5. WP-C added an unrequested fail-closed path (non-dict/absent `h7_authority` → PAUSED sentinel). Sound; `h7_active=True` output proven byte-identical to `origin/main`. Keep.
6. `assemble()` computes `h7_authority` with no try/except (an import failure kills the build — fail-closed; the ritual logs `dashboard: FAILED`). Recorded.

## Verified correct (reviewer's commands, from the worktree)

| Check | Result |
|---|---|
| `uv run python -m unittest discover -s tests` | `Ran 3802 tests … OK (skipped=3)`, exit 0 |
| `uv run ruff check .` / `uv run pyright` | all checks passed / 0 errors, 0 warnings |
| `bash -n tools/daily_ritual.sh` | exit 0 |
| `tests/test_h7_schwab_window_registration.py` (37 tests incl. recomputed closure) | OK; changed-path overlap with the 50-file closure: `[]` |
| forbidden-path grep on the diff (`display_rank`, `attractiveness.py`, `features.py`, `underlying_closes`, `config.py`, `ledger/`, event chips, `test_event_awareness`) and network/provider imports in added lines | none |
| `_h7_window_panel` base vs HEAD on the same window dict, `h7_active=True` path | byte-identical |
| `evaluate_full_ritual(RitualAuthority(h7_active=False, True, True))` | exactly one blocker, the `:83` sentence |
| Mission Control build | `DATA AS-OF 2026-09-03 CLOSE`; `38 shares` ×0; `Held — 39 shares, no options`; `live,` ×0; `Study Hall: C ×18` one tile; `H7 FORWARD WINDOW — PAUSED (H7 authority not granted)` |
| Attractiveness build against `~/options-validator-ops` | `, before this ` ×0; one red `2026-09-01 FAILED verification` + one collapsed `1 earlier capture session failed verification (2026-08-31; older than 3 sessions)`; grades 449 GREEN / 234 AMBER and 478 event-chip spans identical to the ops 09:12 build |
| `tools.job_health_digest --as-of 2026-09-03 --root ~/options-validator-ops` | `Schwab preclose \| OK \| … manifest verified; chains: /Users/…/options-validator/.cache/schwab_chains` — DR-9 fixed (base rule reproduced the FAILED row) |
| `git status --short` after review | clean |

The orchestrating session independently reproduced the suite (3802 OK), ruff, pyright, both dashboard builds and the digest proof before dispatching this review.
