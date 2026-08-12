# Schwab read-only auth — diagnosis and reauthorization preparation (2026-08-12)

**Scope:** read-only diagnosis performed from a cloud checkout (audit-cleanup
session, branch `claude/options-validator-audit-cleanup-h6svzl`). No provider
call, no token read/write, no credential probe, no account/order/trading
surface touched. `SCHWAB_TRADING_ENABLED=false` is unchanged and enforced in
code (`data/schwab_adapter.py`; read-only method allowlist).

## The four things people conflate, separated

| Layer | State | Evidence | Label |
|---|---|---|---|
| Developer app key (client ID/secret) | ACTIVE as of last use — nothing suggests app-level revocation or misconfiguration | OAuth flow worked end-to-end as recently as 2026-08-05 (probe) and 2026-08-07 19:45:12 UTC (successful 15/15 preclose intraday capture receipt) | Repo-verified |
| Access token (short-lived session token) | Moot — derived from the refresh token; cannot be minted while refresh fails | Authlib refresh path is the only minting path in the adapter | Repo-verified |
| Refresh token | **EXPIRED or REVOKED — this is the fault** | The 2026-08-10 ops-failure receipt records the *observed* exception: authlib `OAuthError`, `error="invalid_grant"`, description "Refresh token is invalid, expired or revoked" (`reports/2026-08-10-ops-failure-classification-receipt.md` §"Scope and diagnosis") | Repo-verified |
| Callback / client configuration | No evidence of mismatch — the exact loopback callback `https://127.0.0.1:8182` completed successfully in the last setup and is pinned in `tools/setup_schwab.py:25`; the setup helper refuses a client-ID mismatch across the two repos | Repo-verified |

**Bounding the failure window:** last proven-healthy call 2026-08-07
19:45:12 UTC (receipt `reports/intraday_capture/2026-08-07/preclose.json`,
15/15 names, zero errors); first recorded classification of the failure
2026-08-10. Onset therefore between Aug 7 evening and Aug 10.

**Token lifetime:** Schwab's individual-trader refresh tokens are widely
documented as expiring seven days after issuance, which fits the observed
window — but the official page (`developer.schwab.com`) is unreachable from
this environment (network egress blocked), so this specific lifetime is
labeled **Inference**, not Official-source. The repo's own setup doc
deliberately assumes no fixed lifetime ("Re-run the setup command if Schwab
reports that browser authorization is required" — `docs/schwab-market-data-setup.md`
§Security). Nothing in this diagnosis depends on the exact number.

**Local clock / environment variables:** not inspectable from this checkout
(production Mac only). No repo evidence implicates either; the error is a
server-side `invalid_grant`, not a TLS/clock-skew failure shape. Label:
production-host state UNVERIFIED here.

## Why the outage looked like a generic zero-coverage failure

Until this session, an expired refresh token inside the intraday capture's
steady-state path (fresh schema probe) was swallowed by per-batch/per-symbol
`except Exception` handlers: exit 0, `coverage: 0/N`, no banner (audit
finding M1). That is fixed on this branch: both capture lanes now re-raise
the classified `OAuthError` and print
`... auth EXPIRED: Refresh token is invalid, expired or revoked; run uv run
python tools/setup_schwab.py` with exit 1.

## Reauthorization — exact owner steps (production Mac; browser required)

1. ```bash
   cd /Users/carsynstephenson/options-validator
   uv run python tools/setup_schwab.py
   ```
   Paste the Schwab **Client Secret** at the macOS Keychain prompt, complete
   the single Schwab sign-in/approval page. The loopback callback is exactly
   `https://127.0.0.1:8182`; a browser certificate warning for that address is
   expected — proceed only when the warning page shows this exact address.
2. If setup runs during NYSE regular hours it self-checks quotes and the
   option-chain schema. If the market is closed, run the deferred probe during
   the next regular session:
   ```bash
   uv run python -m options_researcher.live_quotes --probe
   ```
   (the approved read-only probe; writes `reports/live_probe/<date>.json`).
3. Nothing else changes: token store stays
   `~/Library/Application Support/Carsyn Research/Schwab/shared-market-data-tokens.json`
   (dir 0700 / file 0600); no account, order, or trading method is enabled.

Until step 1 runs, every Schwab-dependent lane (intraday capture, preclose
capture, live dashboard, H7 Monday canary) will fail — now loudly, with the
reauth banner.
