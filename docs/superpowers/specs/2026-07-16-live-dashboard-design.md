# Live mission-control dashboard — design (2026-07-16)

Owner-requested: mission-control dashboard (`.tmp/dashboard/index.html`)
gets live intraday numbers that refresh while the page is open, instead of
a stale snapshot from whenever the generator last ran.

Owner review (2026-07-16) rejected the first draft's central mechanism —
feeding live quotes into `trigger_status()` — because the pre-registered H5
rule (`H5_ENTRY_TRIGGER_PREREG`, amendment v2) gates on a **completed-session
close**, not an intraday print. Substituting an intraday mid would silently
change a frozen rule; the repo has already caught this exact error class
(`drop_same_day_rows`, 7b-0 NO-GO remediation). This design implements the
owner's corrected requirements verbatim.

## Non-negotiables (owner, 2026-07-16)

1. **Two statuses, never merged.**
   - **OFFICIAL H5 STATUS** — computed exactly as today by
     `entry_watch._gather()` from completed-session closes + cached
     features/chains. This is the only lane that may say FIRE.
   - **LIVE PREVIEW — awaiting close** — intraday spot (and, when armed,
     live IV/liquidity reads). May prompt a fresh manual review; can NEVER
     display FIRE or any FIRE-equivalent green state. Distinct visual
     treatment and explicit "awaiting close" label.
2. **Throttle paid calls.** Browser polls every 30 s, but the server returns
   an in-memory cached payload (TTL ~25 s); at most ONE in-flight provider
   refresh at a time (lock; concurrent pollers get the cache). Live OPTION
   data is fetched only for H5 trigger names (`config.H5_ENTRY_TRIGGERS`:
   VST, AMZN) and only while live spot is at-or-through the frozen price
   level ("armed"). Stock spot for all `config.UNIVERSE` names is one
   batched `stock_snapshot_quote` call.
3. **Adapter spec'd against the installed client, validated live before
   implementation.** `option_snapshot_greeks_all` requires an `expiration`
   argument — there is no single full-chain snapshot assumption. Expiry
   resolution is a distinct step:
   - live ATM-IV read: nearest MONTHLY expiry, 15–60 DTE
     (`chains.is_monthly` on `option_list_expirations` output; same
     definition as `features.py`);
   - LEAPS candidate: expiry in `config.H4_THESIS_DTE_BAND` (270, 500)
     nearest 365 DTE, then |delta| nearest `config.H4_THESIS_DELTA` (0.70)
     within `config.H5_INCOME_DELTA_BAND` (0.15) — the same selection rule
     as `studies.long_call_carry._leaps_candidate`, applied to snapshot
     rows.
   A one-shot probe script validates real response shapes for every
   endpoint used, during regular session, before the adapter is written.
   Probe findings are recorded in `reports/2026-07-16-live-snapshot-probe.md`.
4. **Open interest is not intraday.** OPRA OI is reported ~06:30 ET and
   reflects the PRIOR close (repo-verified: `data/thetadata_adapter.py`
   docstring). Display it as "OI as of YYYY-MM-DD (prior official report)";
   source it from `option_snapshot_open_interest` memoized once per NY date
   per symbol (fallback: none — if OI is absent the liquidity gate reads
   UNKNOWN and the preview fails closed). Liquidity math reuses
   `passes_liquidity` (MIN_OPEN_INTEREST=100, MAX_SPREAD_PCT=0.10)
   unchanged.
5. **Fail closed, visibly.** Any fetch failure or stale quote ⇒ that
   symbol's live panel shows LIVE DATA UNAVAILABLE with the timestamp of
   the last good snapshot; all live gate readouts become UNKNOWN; a prior
   green/armed badge is never left standing. No provider calls outside the
   regular session (NY weekday, 09:30–16:00 ET window AND, if the probe
   shows quote timestamps, a max-age staleness check on the quote itself —
   which also handles half-days). Outside the session the page shows
   OFFICIAL status only, with "market closed / live off".

## Architecture

Two new modules; existing files effectively untouched.

- `options_researcher/live_quotes.py` — adapter + pure logic.
  - `in_regular_session(now_ny) -> bool` (pure).
  - `resolve_expiries(expirations, today) -> LiveExpiries` (pure): monthly
    15–60 DTE pick + LEAPS-band pick from a plain list of dates.
  - `live_preview(...) -> dict` (pure): given injected frames/rows, builds
    the per-symbol preview payload (spot, armed flag, atm_iv, live IV-rank
    context, LEAPS row gates, as-of labels, status). NaN/missing ⇒ UNKNOWN.
  - Live IV-rank context: today's live ATM IV ranked against the trailing
    EOD `atm_iv` distribution from `features.load_features(symbol)` using
    the identical inclusive-percentile formula (`mean(window <= v)`,
    window = trailing ≤252 finite obs, ≥126 required). Labeled as PREVIEW.
  - Fetch layer (thin, unte­sted-by-unit-tests, mirrors `_fetch_raw`
    conventions): batched `stock_snapshot_quote(UNIVERSE)`;
    `option_list_expirations(sym)` memoized per NY date;
    `option_snapshot_greeks_all(sym, expiration=...)` per resolved expiry,
    only when armed; `option_snapshot_open_interest(sym, expiration=...)`
    memoized per NY date. Column resolution via `_pick_col` idiom; any
    schema surprise raises rather than guesses.
- `options_researcher/live_dashboard.py` — stdlib `http.server` bound to
  127.0.0.1, `--port` default 8642.
  - Startup: regenerate static HTML via existing `dashboard.assemble()` /
    `render()`, inject the LIVE panel div + polling `<script>` before
    `</body>` (string injection; `dashboard.py` itself unchanged).
  - `GET /` serves the augmented HTML; `GET /live.json` serves the cached
    payload (TTL + single-flight refresh).
  - Payload always carries: `generated_at_utc`, `session_state`
    (`open|closed`), per-symbol `status` (`ok|unavailable|off`),
    `last_good_utc`, and the OFFICIAL rows verbatim from
    `entry_watch._gather()` so the page can render both lanes.
  - Read-only guarantee: no writes to `data/positions/`, ledger, or
    reports; no order placement; module docstring states this and tests
    assert the module imports without touching the network.

## Testing

`unittest`, offline, no network (repo rule): all pure functions tested
directly; fetch layer covered by injecting fake client objects; server
tested with `http.client` against a `live_dashboard` instance constructed
with a stubbed refresher (loopback socket, no external network). Explicit
tests for: FIRE never appears in preview lane payloads; failed refresh
flips status to `unavailable` and clears armed/green fields; session-window
edge cases; single-flight lock under concurrent requests; TTL behavior;
IV-rank preview formula parity against `features.build_daily_features` on
synthetic data.

## Scope-guard sentence

This moves H5 (registered forward hypothesis) toward its verdict by making
its pre-registered entry triggers reviewable intraday without altering the
frozen rule, while conserving the lapsing ThetaData subscription (renewal
gate 2026-07-25).

## Probe findings addendum (2026-07-16, pre-implementation)

- The live probe was attempted 2026-07-16 16:00:30 ET and **refused itself**
  (30 s after the close) — the session guard working as specified. The
  schema probe therefore runs next regular session via
  `python -m options_researcher.live_quotes --probe`.
- Installed-source finding (Repo-verified, `thetadata/client.py`
  `_convert_response_stream`): response COLUMNS are server-defined DataTable
  headers arriving with the data — they cannot be known offline. The
  recorded probe is therefore a RUNTIME PRECONDITION: `probe_ok()` must
  pass (matching installed client version, ≤ LIVE_PROBE_MAX_AGE_DAYS old,
  required endpoints ok) or the live lane stays off with a visible reason.
- Installed-source finding: `stock_snapshot_quote` requires a stocks
  standard/pro (real-time) or value (15-min delayed) subscription; this
  account's stock tier was FREE as of 2026-07-04 (facts.log, provider
  rationale). Entitlement is classified by the probe. Fallback when denied:
  live spot for the TRIGGER NAMES ONLY via put-call parity on the nearest
  monthly (`parity_spot_from_chain`, documented <1% bias), labeled
  "parity-derived"; MSFT/CEG then show official close only ("no live stock
  feed on current tier"). This preserves the call-conservation goal.
- Timestamps: `_convert_response_stream` converts timestamp fields to
  tz-aware datetimes, so the quote-staleness check
  (LIVE_QUOTE_MAX_AGE_SECONDS) is implementable when the probe records a
  timestamp column; if none exists, the session window alone guards, and
  the limitation is documented.

## Out of scope

Attractiveness dashboard (owner chose mission control only), any change to
`trigger_status()` / `entry_watch`, any new strategy number, background
pollers/launchd, websockets.
