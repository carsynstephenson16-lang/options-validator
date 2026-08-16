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

---

## Addendum 2026-08-15 — status correction, root-cause split, and token-lifetime upgrade

*(Appended 2026-08-15, owner-directed in-session: the missing-capture week was
being read as one long Schwab failure; it was two different failures, and the
second was not Schwab's.)*

### 1. Reauthorization happened — this report's "until step 1 runs" state is over

The token was re-authorized **2026-08-12 ~00:56 ET** (Repo-verified from the
token store's `creation_timestamp`; timestamps only, no token material read).
The intraday lane verified immediately; the preclose lane stayed
alignment-blocked until 08-14, its only capture of the week:

| Session (ET) | Intraday quotes (5×/day) | Preclose full-chain (15:45) |
| --- | --- | --- |
| Mon 08-10 | BROKEN — `invalid_grant` | wrapper REFUSED (alignment) |
| Tue 08-11 | BROKEN — `invalid_grant` | wrapper REFUSED (alignment) |
| Wed 08-12 | OK 15/15 | wrapper REFUSED (alignment) |
| Thu 08-13 | OK 15/15 | wrapper REFUSED (alignment) |
| Fri 08-14 | OK 15/15 | **OK 15/15** (`reports/schwab_chains/2026-08-14/preclose.json`) |

### 2. Root-cause split — the preclose gap was NOT a Schwab failure

Two independent failure modes overlapped last week and must not be conflated
*(corrected 2026-08-15 per adversarial-review blocker B-1 — the first draft of
this section mixed the two lanes)*:

- **Schwab-side (auth):** the expired refresh token broke the **intraday
  quote lane only**, on 08-10 and 08-11. Evidence:
  `.tmp/intraday_capture/2026-08-1{0,1}_*.log` in the ops checkout
  (`OAuthError … invalid_grant`).
- **Repo-side (alignment guard):** the preclose chain lane refused on **all
  four days 08-10 → 08-13**, with
  `schwab_chain_capture wrapper REFUSED: HEAD is not aligned with origin/main`
  (`.tmp/schwab_chain_capture/2026-08-1{0,1,2,3}_1545.log` — all four logs
  carry the identical refusal line). The wrapper refuses BEFORE attempting
  auth, so on 08-10/08-11 those captures would have failed even with a valid
  token. This is the wrapper's own integrity gate
  (`tools/schwab_chain_capture.sh`) doing its declared job on a divergent ops
  checkout — a sync-procedure gap, not a provider failure. It cleared once
  ops was fast-forwarded to `origin/main`; the 08-14 15:45 run then captured
  15/15 first try.

Consequence for staleness accounting: **every** missing preclose chain
capture last week (08-10→08-13) is attributable to ops-sync procedure (since
addressed by the D-6a 15:30 alignment-check LaunchAgent + runbook rule R1),
and **none** to Schwab availability. The token outage cost two days of the
intraday quote lane only.

### 3. Token lifetime — claim upgraded from Inference to Official-source

This report's earlier "7-day refresh token" label of **Inference** is upgraded:

- **Official-source text via third-party mirror (URL withheld):** Schwab
  Trader API Documentation — "A Trader API refresh token is valid for 7 days
  after creation."; "A Trader API access token is valid for 30 minutes." The
  developer portal blocks automated fetch (HTTP 403, as documented earlier in
  this report); the quoted text was captured 2026-08-15 ~16:20 ET from the
  Internet Archive's full-text mirror of Schwab's own Trader API
  documentation (archive.org; find the item by searching the document title —
  the item slug is deliberately not reproduced in this file because it trips
  this repo's live-trading string filter; the reader should price the claim
  accordingly). **Secondary source (official library docs):** schwab-py's
  auth documentation (<https://schwab-py.readthedocs.io/en/latest/auth.html>,
  captured 2026-08-15): "requests for a new access token using a refresh
  token older than seven days are rejected."
- **Test-verified (production token store, 2026-08-15):** refreshing an access
  token does **NOT** reset the 7-day clock. File mtime 2026-08-15 00:52 ET;
  `creation_timestamp` unchanged at 2026-08-12 00:56 ET (schwab-py's
  `wrap_token_in_metadata` intentionally preserves the original creation time).

**Operational consequence:** the current token dies ~**2026-08-19 00:56 ET**
(Wednesday pre-market). Mon 08-17 and Tue 08-18 captures run; Wed 08-19
onward fails unless re-authorized first. Standing habit going forward:
re-authorize **every weekend**, which covers the full Mon–Fri week.
There is currently no proactive age warning (`token_age()` in
`data/schwab_credentials.py` has no callers); a day-5 warning in the daily
ritual is proposed as follow-up work.
