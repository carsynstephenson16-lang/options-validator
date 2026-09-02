# PR #146 — independent adversarial review receipt (2026-09-02)

**Reviewer:** fresh Opus instance, read-only, in-worktree test execution only.
**Object:** branch `claude/ops-fixes-2026-09-02` @ 13c608a (4 commits on `origin/main` @ c128925).
**Verdict:** **PASS** — no blockers; two low, non-blocking follow-ups (both applied in bb0c0db); one informational note for the owner.

## Findings (transcribed)

### Fix 1 — expired-token classifier (`options_researcher/schwab_auth_failure.py`)
- Test-verified: the reconstructed 2026-09-01 exception (`OAuthError: unsupported_token_type: 400 Bad Request: "{"error_description":"Refresh token is invalid, expired or revoked","error":"invalid_grant"}"`, 15× in `reports/schwab_chains/2026-09-01/preclose.json`) now classifies `True`.
- Test-verified: eight constructed non-expiry `OAuthError`s (rate limit, `invalid_client`, `invalid_request`, `invalid_scope`, `server_error`, `temporarily_unavailable`, expired *access* token, bad client secret) and a non-OAuth `ValueError` all classify `False`.
- Repo-verified: `schwab_chain_capture.py:295` and `intraday_capture.py:755/775` re-raise on classification, so an expiry day stops early and the wrapper's `CRITICAL: SCHWAB REAUTH REQUIRED` line (`tools/schwab_chain_capture.sh:143`) is reached.
- **Follow-up A (applied bb0c0db):** `OAuthError(error="invalid_grant", description="")` was `False`; added the `.error == "invalid_grant"` arm plus a test.
- **Informational (owner note):** because the re-raise escapes `capture()` before `_write_receipt`, an expiry day now writes NO `preclose.json` (09-01 wrote a 15×failed one). This is the 2026-08-11 M1 design, not new code; `tools/job_health_digest.py:432-440` still emits a FAILED row for the absent receipt.

### Fix 2 — token-age advisory (`options_researcher/schwab_token_age.py`, both shell wrappers)
- Test-verified: no network-capable module imported (httpx/authlib/schwab/requests/urllib3/socket/http all absent); only `creation_timestamp` read; token contents never printed.
- Repo-verified: ritual line uses raw `echo`, cannot touch `SUMMARY`/`CRITICAL`/`CRIT_COUNT`/`STARVED_CRIT`/`DATA_STARVED`/`RITUAL_TERMINAL_STATUS`; `main()` always returns 0; `|| true`.
- Repo-verified: token-path precedence matches `data/schwab_adapter.py:55-66` (env > `.env` > shared default).
- Repo-verified: `config.py` constants carry Official-source (7 days) and LLM-proposed/display-only (36 h) labels; the only literal in the module is a seconds→hours unit conversion.
- Repo-verified: the disclosed placement deviation (12 lines before the Schwab lane marker) is safe; all provenance re-pins are exactly +12 with zero reclassification; lane invariants hold.
- **Follow-up B (applied bb0c0db):** `DATA_TIER_MODULES` registration comment now states the call site is outside the data-tier island.

### Fix 3 — gitleaks (`.gitleaksignore`, `.gitleaks.toml`)
- Test-verified (gitleaks 8.30.1): config parses; scan → exactly one pre-existing finding (`tools/thetadata_v2_backfill.py:71`); main's config on the same tree → two. One silenced, zero newly raised.
- Test-verified: CI Secret Scan passed (12 s) on this PR at the pinned action `gitleaks/gitleaks-action@…  # v2.3.9` — the `[[allowlists]]` form parses in CI as shipped.
- Repo-verified: fingerprint `6e08cf8…:options_researcher/a2_runner.py:generic-api-key:49` is real (line 49 = `PIN_FACT_TOKEN = "RQ2_A2_PIN_ADDENDUM_V1"`).
- Inference (low): allowlist is `AND`-scoped to the file path + literal label + `regexTarget = "line"`; a secret pasted onto that same physical line would be hidden. Optional tightening `targetRules = ["generic-api-key"]` was NOT applied (support in the CI-default binary unverified offline).

### Fix 4 — ritual final status (`tools/daily_ritual.sh`)
- Repo-verified: the carve-out predicate is byte-identical at all three sites (`:516`, `:631`, `:649`) and the test asserts exactly 3 occurrences.
- Repo-verified: `STARVED_CRIT=1` is set at exactly one site (`:502`) and `crit()` increments `CRIT_COUNT` on every CRITICAL, so `CRIT_COUNT==1 && STARVED_CRIT==1` provably identifies the starvation CRITICAL; any second CRITICAL forces BROKEN.
- Repo-verified: no downstream consumer (LaunchAgent plist, `job_health_digest.py`, `research_refresh_guard.py`) keys on this script's exit code.

### Cross-cutting
No hardcoded strategy numbers outside `config.py`; no `ledger/`, verdict, FIRE, watcher, or H7 path in the diff; ruff clean.

## Test counts at review
| File | Result |
|---|---|
| `tests/test_schwab_token_age.py` | 18 OK |
| `tests/test_schwab_auth_failure.py` | 9 OK (10 after follow-up A) |
| `tests/test_daily_ritual_provenance.py` | 43 OK |
| full suite (implementer, pre-follow-ups) | 3662 OK, skipped=5, exit 0 |
