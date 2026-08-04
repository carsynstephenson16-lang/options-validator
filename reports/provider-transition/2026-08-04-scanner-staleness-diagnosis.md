# Attractiveness scanner vs. reality — staleness diagnosis and refresh options

**Date:** 2026-08-04. **Status:** diagnosis + owner decision package. **Authority:** none — this
report changes no code, config, cache, ledger, or verdict. No provider endpoint was called.

**Trigger:** the owner compared a live Schwab order ticket for NVDA against the attractiveness
scanner board and reported "a major gap." This report measures that gap, finds its causes, and
prices every way to close it.

---

## 1. The gap, measured

| | Scanner board (cache edge 2026-07-27 EOD) | Live Schwab ticket (2026-08-04 10:29 ET) |
|---|---|---|
| NVDA spot | 196.51 | 210.06 |
| NVDA 200-strike call | 08/07 exp: bid 4.45 / ask 4.60 (mid 4.53) | 08/10 exp: bid 10.95 / ask 11.30 (mid 11.13) |
| | 08/14 exp: bid 5.85 / ask 6.00 (mid 5.93) | |
| Moneyness of the 200 strike | **out of the money** by $3.49 | **in the money** by $10.06 |

Spot moved **+6.9%** (196.51 → 210.06) in the six trading sessions the board has not seen.

Two consequences, both material:

1. **Price level.** A 200-strike NVDA call reads on the board as a ~$450–590 out-of-the-money
   position. It is actually a ~$1,113 in-the-money contract. Roughly 2× on premium, and the
   moneyness sign is inverted — every downstream judgement (delta targeting, cushion, yield,
   position sizing against the sleeve cap) is computed off the wrong side of the strike.
2. **Contract existence.** The 2026-08-10 expiry the owner is actually looking at **does not exist
   in the cache at all.** The 2026-07-27 snapshot carries near-dated Mon/Wed/Fri weeklies only out
   to 2026-08-07, then jumps to 08-14. The frozen board cannot represent the live contract under
   any interpolation.

**Cross-validation that the closes lane is healthy:** `.cache/underlying/NVDA.parquet` holds
`2026-08-03 → 206.639999`; the Schwab ticket shows `Previous Close 206.64`. Level-exact. The
underlying-closes pipeline is current and correct. **Only the option-chain lane is frozen.**

Method: `Repo-verified` (parquet read directly from `.cache/chains/NVDA_2026-07-27.parquet` and
`.cache/underlying/NVDA.parquet`); live side is `Official-source` (the owner's own broker screen).

---

## 2. Root causes — three independent, only two are defects

### RC-1 — Chain cache frozen at 2026-07-27 (governed, NOT a defect)

The newest chain parquet for the core names is `2026-07-27`. This is the intended state:

- **OD-2** declined the final EOD top-up: "The final canonical chain edge remains 2026-07-27"
  (`docs/provider-transition.md:90-93`).
- **OD-4** records commercial ThetaData access ending 2026-08-01, with acquisition operationally
  disabled 2026-07-31 21:26:46 EDT (`docs/provider-transition.md:97-101`).
- Enforced in code, with no escape hatch: `data/provider_policy.py:11-12` sets
  `THETADATA_ACQUISITION_DISABLED = True` and the module docstring states "This policy has no
  environment-variable override."

The scanner is behaving correctly here — it reads `max(available chain dates)` per symbol
(`attractiveness_dashboard.py:1019`) and that is genuinely the newest byte on disk. Nothing to fix.

### RC-2 — The board has no wall-clock staleness gate (DEFECT — display)

`options_researcher/top3_snapshot.py:83-106` (`integrity_status`) is the freshness gate. It compares
`features_as_of` against the section's `as_of` — **both internal to the same snapshot** — and its
docstring commits to classifying "without reading disk." It never receives, and never consults,
today's date.

Consequence: as long as the features row and the chain file agree on 2026-07-27, the status is
`ELIGIBLE`. A board that is six sessions old — or six months old — renders as normal. Grep across
`attractiveness.py`, `attractiveness_dashboard.py`, and `data/pandas_feed.py` finds no `age_days`,
`MAX_CACHE_AGE`, or any comparison to the wall clock.

The existing `features_stale` warning is an *internal consistency* check and correctly stays silent
here, because both sides are equally stale. `_page_data_as_of()`
(`attractiveness_dashboard.py:766-772`) does the right thing by surfacing the *earliest* date across
symbols, but it prints a bare date string with no age.

**This is what makes the gap invisible.** The rendered board at
`~/options-validator-ops/.tmp/dashboard/attractiveness.html` was regenerated **today at 09:56**, and
its dominant date string is `2026-07-27` (221 occurrences). Fresh file timestamp, six-session-old
quotes, no warning.

### RC-3 — The Schwab live lane is broken (DEFECT — operations)

The `com.carsyn.options-validator.intraday-capture` LaunchAgent is exiting 1. Reproduced from
today's log, `~/options-validator-ops/.tmp/intraday_capture/2026-08-04_0935.log`:

```
File ".../options_researcher/live_quotes.py", line 247, in _configured_provider
    raise RuntimeError(
RuntimeError: LIVE_MARKET_DATA_PROVIDER must be set explicitly to 'schwab';
ThetaData acquisition is disabled and no fallback is permitted.
>>> CRITICAL: intraday_capture (open): FAILED (exit 1)
RITUAL STATUS: BROKEN
```

Cause: `live_quotes._configured_provider()` (`live_quotes.py:240-262`) reads
`LIVE_MARKET_DATA_PROVIDER` from the environment and fails closed if unset — correct, deliberate
behaviour introduced by the Q7 provider-disable work that landed 2026-07-31.

But the LaunchAgent runs in the ops execution dir and loads
`/Users/carsynstephenson/options-validator-ops/.env`, which contains **none** of the six Schwab keys.
Key-name comparison (values never read):

| `.env` location | Schwab keys present |
|---|---|
| `/Users/carsynstephenson/options-validator/.env` (main repo) | `SCHWAB_API_KEY`, `SCHWAB_CALLBACK_URL`, `SCHWAB_TOKEN_PATH`, `SCHWAB_ENTITLEMENT`, `SCHWAB_TRADING_ENABLED`, `LIVE_MARKET_DATA_PROVIDER` |
| `/Users/carsynstephenson/options-validator-ops/.env` (LaunchAgent execution dir) | **none** — only ThetaData, AlphaVantage, restic keys |

The Q7 change tightened the gate; the ops environment was never updated to match. Every scheduled
capture since has failed. Capture receipts and parquet files stop at **2026-07-28** — so the live
lane died at almost exactly the moment the historical lane froze, which is why there is no fallback
showing the gap.

**Honest limit:** the confirmed failure explains 2026-08-03 and 2026-08-04. There are no capture
logs at all for 2026-07-29 / 07-30 / 07-31, which this error does not explain (it postdates Q7).
Machine sleep or a plist reload are plausible but unverified. Recorded as UNKNOWN.

### RC-4 — Cache paths resolve against CWD, not repo root (LATENT TRAP)

`data/thetadata_adapter.py:75-76` sets `CACHE_DIR = Path(os.environ.get("OPTIONS_CACHE_DIR",
".cache/chains"))` and immediately `mkdir(parents=True, exist_ok=True)`. The path is **relative to
the process working directory**. `data/underlying_closes.py:21` and `data/underlying_ohlcv.py:33`
do the same and have **no env override at all**.

Any session run from a git worktree therefore reads an *empty* cache and silently creates an empty
`.cache/chains/` as an import side-effect. This happened during this very audit and was cleaned up
(`irreplaceable_data_guard verify` → `irreplaceable data: OK`; the removed directory was empty and
contained no data). Not the cause of the reported gap, but it is a live footgun for exactly this
class of investigation.

---

## 3. What it costs to fix — provider survey

Eighteen providers were priced against the "under $10/month" constraint on 2026-08-04.

### The answer is $0, and it is already built

**Schwab Trader API.** Free with the brokerage account the owner already holds — the order ticket
that triggered this investigation *is* a Schwab screen. Critically, this is not a new integration to
evaluate; it is already in this repository and on this branch:

- `data/schwab_adapter.py` (454 lines) + `data/schwab_credentials.py` + `tools/setup_schwab.py`,
  landed 2026-07-29 in commit `54b0e76`, with 353 tests in `tests/test_schwab_adapter.py`.
- `_fetch_chain` (`schwab_adapter.py:238-302`) parses `callExpDateMap`/`putExpDateMap` and returns
  bid, ask, `delta`, `implied_vol`, `open_interest` per contract.
- Fails closed on `isDelayed`, `isChainTruncated`, and non-`SUCCESS` status
  (`schwab_adapter.py:264-269`) — the exemplar the provider rule cites.
- Live chains + Greeks were probe-verified 2026-07-29/30
  (`docs/provider-transition.md:46-47`; `reports/live_probe/2026-07-29.json`).

Repo-verified and Test-verified. This is stronger evidence than a vendor pricing page — note that
the web survey could **not** reach `developer.schwab.com` directly (HTTP 403) and rated Schwab
*Inference* on secondary sources alone.

### Everything else, briefly

| Option | Cost/mo | Verdict |
|---|---|---|
| **Schwab Trader API** | **$0** | **Recommended.** Already integrated, probe-verified, official API, ~120 req/min, full chain + Greeks + IV + OI. |
| yfinance | $0 | Only other true zero-cost, no-account path. Unofficial scraper against undocumented endpoints, against Yahoo's TOS for automated access, no SLA, current chain only. Acceptable as a cross-check, not as a source of record for a platform whose entire premise is data integrity. |
| Interactive Brokers | ~$0–11.50 | Technically in budget (fees waivable on commission). Requires $500 funded account and routes market data through live-brokerage plumbing — in direct tension with this repo's validator-only posture and the `block_live_trading` hook. Reject on principle, not price. |
| Tradier | $0 API on a funded account | Real-time gated to funded brokerage holders; sandbox is delayed with unverified funding requirements. Strictly worse than Schwab here, since the Schwab account already exists. |
| Massive.com (formerly Polygon.io) | $29 Options Starter | Cleanest self-serve paid API found; 15-min delayed, real Greeks/IV, official Python client. **3× over budget.** Free tier is EOD-reference only — no bid/ask. |
| Marketdata.app | $30 ($12/mo annual) | Over budget. Free tier is 24h delayed. |
| Alpha Vantage | $49.99 | Over budget. Free tier confirmed to have no options data by this repo's own prior probe. |
| CBOE delayed quotes | $0 | **Disqualified** — explicitly prohibits automated/scripted access. |
| ORATS / Intrinio / Databento / Barchart / dxFeed / Unusual Whales | $48 – $2,500 | All far over budget. |
| Finnhub / Twelve Data / Nasdaq Data Link / EODHD | unresolved | Could not verify an options-chain product and price from the vendor's own page. Flagged low-confidence rather than guessed. |

Naming note: **Polygon.io was renamed Massive** (massive.com) on 2025-10-30; `polygon.io` now
301-redirects. Existing keys and SDKs still work. Worth knowing before any future note cites
"Polygon" as if it were a separate vendor.

**Security note:** the `unusualwhales.com` pricing page was found to contain embedded text
addressed at AI agents, structured as instructions. It was treated as untrusted page content, not
followed, and is recorded here only as a caution for future fetches of that domain.

### Call-count estimate (required by `.claude/rules/data-and-providers.md`)

`ATTRACTIVENESS_UNIVERSE` = 18 symbols. `A_LADDER_BUCKETS` = 5 target DTEs → 5 expiries per symbol.

`_fetch_chain` pins `from_date=exp, to_date=exp` and **hard-raises** if the response contains any
other expiration (`schwab_adapter.py:274-277`), so one call per symbol-expiry:

- **Full board refresh: 18 × 5 = 90 chain calls + 1 batched quote call = 91 calls.**
- Once daily (preclose only): ~91/day, ~1,820/month.
- All five `INTRADAY_CAPTURE_TIMES` slots: ~455/day, ~9,100/month.
- Against a ~120 req/min limit, a single refresh needs throttling across roughly one minute.

**Efficiency note, not a recommendation:** Schwab's `/chains` endpoint accepts a `fromDate`/`toDate`
range, so one call could return all five ladder expiries — 18 calls + 1 quote = **19 per refresh**,
a ~79% reduction. This requires relaxing the single-expiration guard at `schwab_adapter.py:274-277`,
which is deliberate strictness in a hardened, well-tested adapter. That is a Codex brief with its
own red/green tests, not an incidental edit.

---

## 4. What cannot be fixed at any price under $10

**The 2026-07-28 → 2026-08-04 hole in the historical chain cache is permanent.**

Schwab has no dated historical option-chain endpoint — stated in
`docs/provider-transition.md:44` and `.claude/rules/data-and-providers.md`. Every provider that does
sell dated historical chains starts at $29/mo (Massive) and runs to $2,500/mo (Intrinio). ThetaData
could have filled it and is now both commercially ended and code-disabled.

This is not a new problem introduced by anything found here — it is the known, accepted price of
OD-2 and OD-4, both owner decisions already on the record. It is restated because "make the scanner
current" and "make the scanner's history complete" are different asks, and only the first is
achievable.

Binding constraint on any fix: **no Schwab response may be written into `.cache/chains` or any
blind-study cache** (`.claude/rules/data-and-providers.md`; `docs/schwab-market-data-setup.md:92`).
A live refresh is therefore an **overlay in a separate namespace**, never a backfill.

---

## 5. Recommended path — three layers, increasing cost and gating

### Layer 1 — Make the board tell the truth about its own age

**Cost $0. No provider call. No owner gate. Offline. Highest value per unit of risk.**

Explicitly listed as safe work in `PROJECT_STATE.md` §6 ("descriptive dashboards may show labeled
stale data; never promote it to verdict") and consistent with the display-only precedent set by the
Wasserstein and composite-signal lanes.

- Extend `integrity_status()` to accept an injected `today` (preserving its pure, no-disk contract)
  and emit a `CHAIN_STALE_VS_TODAY` reason code past a threshold in trading sessions.
- Render the age, not just the date: "Chain data as of 2026-07-27 — **6 trading sessions old**",
  styled as a warning, at the top of the board.
- Past the threshold, return `DATA_BLOCKED` so stale rows drop out of the Top-3 admissible pool
  exactly as `FEATURES_STALE` already does.

The threshold is a number, so per the operating manual it is the owner's to type. A starting point
for that decision: 1 session = warn, 3 sessions = block.

This layer alone resolves the reported complaint. The board stops looking current when it isn't.

### Layer 2 — Restore the live Schwab overlay

**Cost $0/mo. Requires owner action and an owner gate.**

1. Add the six Schwab keys and `LIVE_MARKET_DATA_PROVIDER=schwab` to
   `~/options-validator-ops/.env` to match the main repo. This unblocks RC-3.
2. Re-authorize Schwab. The refresh token has a hard 7-day life; the token file was last written
   2026-08-02 23:11 and the original OAuth appears to date from 2026-07-29, so it is **likely
   expired or expiring imminently**. Not verifiable without a network call, which was not made.
   Owner runs `uv run python tools/setup_schwab.py`.
3. Run `uv run python -m options_researcher.live_quotes --probe` **during the regular session** —
   required by the provider rules before the live lane turns on.
4. Display live bid/ask/mid as a clearly-labeled overlay beside the frozen board. Never written to
   `.cache/chains`. Never verdict-bearing, never FIRE-capable.

**Recurring operational cost, stated honestly:** the 7-day refresh-token expiry will break this
unattended roughly weekly. This is the exact reason today's HEAD commit
(`1bddfa0`) rejected Schwab for underlying closes in favour of Yahoo. It is tolerable for a
display overlay that fails closed and visibly; it would not be tolerable for a gate. A second
recorded risk: this account's Schwab stock entitlement was observed to flip between the 07-24 and
07-29 probes.

### Layer 3 — Do not backfill

Accept the permanent hole from §4. Any historical-chain purchase is a separate owner decision at
$29/mo minimum, outside the stated budget, and would need its own registration.

---

## 6. Open items for the owner

| # | Item | Why it needs the owner |
|---|---|---|
| 1 | Staleness thresholds (warn at N sessions, block at M) | A number that changes what the board shows — owner types numbers. |
| 2 | Approve the Schwab live overlay and its ~91 calls per refresh | Provider endpoint calls require owner approval per `.claude/rules/data-and-providers.md`. |
| 3 | Re-run `tools/setup_schwab.py` | Interactive OAuth; cannot be automated, and credentials are never handled by an agent. |
| 4 | Refresh cadence (preclose only ≈1,820 calls/mo, vs all five slots ≈9,100) | Determines call volume and token-refresh exposure. |
| 5 | Whether to brief the range-fetch optimization (91 → 19 calls) | Touches a hardened adapter guard; needs red/green tests. |
| 6 | Whether to harden the CWD-relative cache paths (RC-4) | Latent, unrelated to this gap, but a real footgun. |

---

## 7. Layer 1 — implemented 2026-08-04

Owner selected Layer 1 in-session. Implemented, test-first, offline, with no provider call.

**Changes**

- `config.py` — `CHAIN_STALE_WARN_SESSIONS = 1`, `CHAIN_STALE_BLOCK_SESSIONS = 3`.
  Labelled `LLM-asserted 2026-08-04, pending owner confirmation`; display gates only, binding no
  hypothesis, verdict, or registered trigger.
- `options_researcher/top3_snapshot.py` — `integrity_status(section, *, today=None)` gains the
  wall-clock check and returns `chain_age_sessions`. New reason codes `CHAIN_STALE_VS_TODAY`,
  `CHAIN_SESSION_IN_FUTURE`, `EVALUATION_DATE_INVALID`. New helper
  `trading_sessions_between()`. `snapshot_candidate()` forwards `today`.
- `options_researcher/attractiveness_dashboard.py` — `assemble()` gains `today`, defaulting to the
  current `America/New_York` date on a real assembly only; new `_chain_age_html()` banner and
  `_page_chain_age_sessions()`.

**Design decisions**

- `today` is **optional everywhere**. Omitting it reproduces the prior behaviour exactly, so all
  pre-existing callers and fixtures are untouched and no test is aged out by the wall clock.
- Age is counted in weekday sessions. Market holidays count as sessions, which over-states age and
  therefore fails safe — the gate can block a board one session fresher than measured, never show
  one older than measured.
- Unknown age renders as an explicit `UNKNOWN` warning, never as silence. Silence would be
  indistinguishable from "fresh", which is the exact failure being fixed.
- The gate touches integrity only. It does not influence lane portfolio policy in either direction
  (pinned by `test_one_session_old_warns_without_blocking`).

**Verification**

| Check | Result |
|---|---|
| Red phase | 8 new tests failed on the missing `today` argument before implementation |
| `tests/test_top3_snapshot.py` | 20/20 pass (12 pre-existing unchanged) |
| `tests/test_attractiveness_dashboard.py` | 109/109 pass |
| `uv run python -m unittest discover -s tests` | **2,520/2,520 pass, exit 0**, 178s, real cache present |
| `uv run ruff check .` | All checks passed |
| `uv run pyright` | 0 errors, 0 warnings |
| `tools/irreplaceable_data_guard.py verify` | `irreplaceable data: OK`; 31,366 canonical chain files intact |

**End-to-end on real data (2026-08-04):** 18 symbols assembled, `data_as_of=2026-07-27`,
`chain_age_sessions=6`, banner renders "STALE BOARD — option quotes are 6 trading sessions old",
and **183/183 cards** carry `CHAIN_STALE_VS_TODAY` and drop out of the shortlist.

**Verification note:** the first full-suite run was performed before the worktree cache symlink was
correctly established and therefore executed against an empty cache — RC-4 biting during its own
investigation. The result recorded above is the re-run with the real cache present. Temporary
verification symlinks were removed afterwards and the canonical file count re-verified.

**Not done:** Layer 2 (Schwab live overlay) and Layer 3 remain owner-gated; RC-3 and RC-4 are
diagnosed but unfixed.

## 8. Claim labels

- `Repo-verified`: cache edge 2026-07-27; NVDA quote levels; missing 2026-08-10 expiry;
  `integrity_status` has no wall-clock input; ops `.env` missing all Schwab keys; adapter capability
  and one-expiry-per-call structure; universe size 18; ladder depth 5.
- `Test-verified`: 353 Schwab adapter tests present on this branch (test *existence and count*
  verified; the suite was not executed in this session).
- `Official-source`: the live NVDA quotes, from the owner's own broker screen; OD-2/OD-4 as recorded
  in `docs/provider-transition.md`.
- `Inference`: Schwab refresh-token expiry timing (derived from file mtimes, not probed); vendor
  pricing where the survey could not reach the vendor's own page — flagged inline in §3.
- `UNKNOWN`: why intraday captures are absent for 2026-07-29 through 07-31.

No verdict, registration, threshold, ledger entry, cache byte, or paper-book row was created or
changed by this investigation.
