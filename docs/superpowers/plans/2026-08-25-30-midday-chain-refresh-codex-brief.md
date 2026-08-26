# Codex brief 30 — midday Schwab chain capture + board quote-refresh overlay (isolated lane)

*(Renumbered from 29 — that slot was taken same-day by another session's Schwab-inventory-binding brief.)*

**Date:** 2026-08-26 (rev 7, final-review correction)
**Author:** Claude orchestrating session (Fable), 2026-08-25
**Executor:** Codex (GPT-5-class), high reasoning tier
**Status:** CORRECTION CANDIDATE — final-head independent review pending. The prior correction review passed `bc760a2`, but the subsequent final-head review found a stale train-order passage, an incomplete hashing citation, and an absent-cache bootstrap gap in WP-D.3. Rev 7 repairs those findings while preserving the revised five-parameter capture-core contract and the tracked-receipt durability ruling. The prior adversarial review round 4 verdict was **PASS WITH FIXES**, with all six round-4 minors applied. WP-A remains staged (WP-A alone → one green 15:45 ops cycle → remainder). Receipt: `reports/2026-08-25-briefs-28-30-adversarial-review-receipt.md`.
**Landing order (binding):** 26 → 25 → 28 → 27 → 30 (this brief remains last: its overlay golden is captured against the post-28/post-27 board, and its coordination notes assume Brief 27's picks artifact exists). NOTE: adds modules under `options_researcher/` and `tools/`, both included in and therefore shifting `diagnostic_source_hash` (`research/hashing.py:132-154`); batch with this train. No new `config.py` constant → `config_hash` untouched.
**Provenance:** Repo-verified against post-Brief-25 `origin/main@8a6920a2449094f4e5db5ad6ff00741f2d388023` unless labeled otherwise (capture-lane mechanics mapped by a dedicated scout pass 2026-08-25; ordering, current line references, and the landed Brief-25 dashboard surface re-verified 2026-08-26 against that base).
**Owner authorization (provider calls):** owner-directed in-session 2026-08-25, spoken: "we should pull schwab options data mid day as well to update it for more accuracy in these picks." Written call-count estimate per `.claude/rules/data-and-providers.md`: +15 Schwab `get_option_chain` calls per trading day (15-name universe × 1 full-chain call), additive to the existing 15/day pre-close capture and the 5×/day spot snapshots. $0 marginal cost; no new entitlement.

## Why this exists (plain language)

The board's candidate quotes come from ONE capture a day (15:45 pre-close),
so for most of the trading day the "current picks" carry yesterday-afternoon
prices — on 2026-08-25 the hero cards' premiums and breakevens were a full
session stale during a triple-event week. The owner wants a midday chain
pull so the displayed picks are priced twice a day.

The dangerous way to do this is to write midday data into the existing
pre-close lane. That lane is load-bearing for registered work (H5/H10b
consume it; RQ2's registration pins its price source to "the daily 15:45 ET
pre-close Schwab chain captures", ledger seq 26 clause 3) and its
verification machinery makes contamination structurally fatal — Repo-verified:
- the capture module hardcodes the "preclose" tag (15:45 ±10min;
  `schwab_chain_capture.py:257`, schedule/tolerance `config.py:759-770`) and refuses
  to run at midday at all;
- `verify_session` requires captured-at inside the pre-close window
  (`tools/schwab_chain_manifest.py:60-77,178`) and convention
  `preclose_snapshot_v1` (`:18,157,181`);
- filenames carry NO time component (`.cache/schwab_chains/{SYM}_{DATE}.parquet`,
  `reports/schwab_chains/{DATE}/preclose.json`), and the exact-set globs
  (`schwab_chain_manifest.py:91,165`) mean ANY extra same-date file makes
  the real 15:45 session UNVERIFIABLE;
- the H7 gate asserts exactly one manifest/receipt/chain-dir per session
  (`h7_schwab_data_gate.py:57-58`);
- the capture's ledger fact dedupes on `SCHWAB_CHAIN_CAPTURE session=<date>`
  (`schwab_chain_capture.py:330-336`) — a second same-day capture collides.

Therefore: a **parallel, isolated midday lane** with its own namespace,
convention, receipt name, fact prefix, wrapper, and plist — and a display
overlay that refreshes the EXISTING picks' quotes without re-running
selection.

## Scope

**IN**
- WP-A: parameterize the capture/manifest core (defaults byte-identical to
  today's pre-close behavior).
- WP-B: the midday lane (module, namespace, receipt, fact prefix).
- WP-C: midday view boundary + dashboard quote-refresh overlay.
- WP-D: wrapper, plist, schedule tests, durability (commit allowlist +
  irreplaceable-data namespaces).
- WP-E: isolation proofs.

**OUT (hard stops)**
- NOTHING writes into `.cache/schwab_chains/` or `reports/schwab_chains/`
  except the existing pre-close lane. No change to the pre-close plist,
  wrapper, schedule, receipt contents, or convention string.
- No re-running of candidate selection, grading, or ranking on midday data
  — the frozen recipe's inputs stay the pre-close/frozen sources. The
  overlay updates DISPLAYED quotes for already-selected cards only.
- No registered-lane coupling: H5 `entry_watch`, `h10_watch`, the H7 gate,
  and (future) RQ2/pick-tracker scored records never read the midday
  namespace (proof tests in WP-E). The (brief 27) picks artifact
  `picks_snapshot.json` is NEVER written by a midday refresh.
- No live-order paths; `SCHWAB_TRADING_ENABLED=false` stays; read-only
  client allowlist untouched.
- No new frozen time number: midday = the EXISTING
  `config.INTRADAY_CAPTURE_TIMES["midday"] == "13:00"` ± the existing
  10-minute tolerance (`config.py:759-770`). If the owner later wants a
  different time, that is a config amendment with its own provenance.

## Work packages

### WP-A — parameterize the shared core (byte-identical defaults)

1. `schwab_chain_capture.capture()` already accepts `chain_dir`,
   `reports_dir`, `universe`, `client`, `now_ny` (Repo-verified `:228-236`).
   Add FIVE keyword-only parameters with defaults equal to today's
   hardcoded literals: `session_tag="preclose"` (used at `:257` and receipt
   `:310` — rev-1 finding 15 corrected the line),
   `receipt_filename="preclose.json"` (`:324`),
   `fact_prefix="SCHWAB_CHAIN_CAPTURE"` (`:330-336`),
   `receipt_kind="schwab_chain_capture/v1"` (receipt `:305`), and
   `convention=SESSION_CHAIN_CONVENTION` (receipt `:307`).
   *(Amended 2026-08-26 per PR #90 Codex review P1: the original
   three-parameter list could not produce WP-B's distinct midday identity —
   `receipt_kind` and the convention stayed hardcoded pre-close values that
   WP-B's own verifier is required to reject. Thread both new parameters
   through capture/build/verify; extend the step-3 golden byte-identity
   test to also assert the default `receipt_kind` and convention
   explicitly.)*
2. `tools/schwab_chain_manifest.py`: `build_manifest` and `verify_session`
   gain `convention=SESSION_CHAIN_CONVENTION`, `receipt_filename=
   "preclose.json"`, and `session_tag="preclose"` (the tag drives the
   timing check at `:72`); defaults preserve current behavior exactly.
3. Proof (this is the load-bearing step; rev-1 finding 13 — output
   equality alone is insufficient for the one artifact that cannot be
   re-bought):
   (a) every existing pre-close test passes UNMODIFIED;
   (b) golden test: default-parameter capture on the existing fixture
   produces byte-identical manifest and receipt JSON to the
   pre-parameterization code;
   (c) SIGNATURE-PINNING test: all five new capture parameters are keyword-only
   with exactly the current literals as defaults;
   (d) CALL-SITE test: the pre-close wrapper's actual invocation
   (`python -m options_researcher.schwab_chain_capture`, no new args)
   resolves to the preclose defaults;
   (e) **STAGED DEPLOY (binding):** WP-A merges ALONE first; only after
   ONE full green 15:45 capture cycle in ops (verified receipt committed)
   do WP-B/C/D merge. Converts an all-at-once risk on the live lane into
   a checkpointed one for the cost of one day.
   The duplicate convention constant at
   `h7_schwab_window_registration.py:37` is NOT touched (rev-1 finding 15
   corrected the line).

### WP-B — the midday lane

1. New thin module `options_researcher/schwab_chain_midday.py` (CLI
   `python -m options_researcher.schwab_chain_midday`) calling the WP-A
   core with: `session_tag="midday"`, `chain_dir=".cache/schwab_chains_midday"`,
   `reports_dir="reports/schwab_chains_midday"`,
   `receipt_filename="midday.json"`,
   `receipt_kind="schwab_chain_midday/v1"`,
   `convention="midday_snapshot_v1"`, and
   `fact_prefix="SCHWAB_CHAIN_MIDDAY"`. Same 15-name universe
   (`watch_universe()`, `h7_scope.py:63-65`), same write-once/refuse
   discipline, same force-refusal, same invocation-source provenance.
2. Receipt kind is DISTINCT: `receipt_kind: "schwab_chain_midday/v1"`
   (rev-1 finding 18, decided — the kind is the first thing a human greps
   when a receipt turns up in the wrong directory; "same kind, different
   convention" is one careless glob from the contamination WP-E.2
   prevents). Applied consistently in writer AND verifier; the convention
   string `"midday_snapshot_v1"` and `scheduled_session_tag: "midday"`
   remain additional discriminators. Verification of a midday session =
   WP-A's `verify_session` with midday parameters (including the midday
   receipt kind).
3. The midday timing check reuses `validate_session_tag("midday", ...)`
   against the existing 13:00 ± 10min window — a midday run at 15:40
   refuses exactly as a pre-close run at 13:00 does today.

### WP-C — view boundary + board overlay

1. New `options_researcher/schwab_midday_view.py` mirroring the boundary
   doctrine of `schwab_chain_view.py` ("Nothing else may read the
   namespace for rendering"): `verified_midday_sessions()`,
   `load_midday_chain(symbol, session)`, labels
   `CONVENTION_LABEL = "13:00 midday (Schwab)"`,
   `CLOSE_KIND = "midday_mid_1300"`. The existing `schwab_chain_view.py`
   is byte-untouched (its module-literal paths are deliberate —
   `:39-42` — and every registered consumer resolves through it).
2. Dashboard overlay (render-layer only): when a verified midday package
   exists for the BOARD'S OWN evaluation date... it will not, normally —
   the board is built at 07:10 from yesterday's pre-close. So the overlay
   condition is: a verified midday session NEWER than the board's chain
   session exists. Then each hero/pinned card renders one extra line:
   "MIDDAY REFRESH <session> 13:00 (Schwab): premium $X (was $Y), spot
   $Z — display refresh only; selection, grades, and rank are from the
   <board session> pre-close capture." Spot source for $Z, named (round-2
   finding NEW-5): the MIDDAY intraday-capture receipt
   (`reports/intraday_capture/<session>/midday.json`, `spot_source ==
   "stock_snapshot"` — symmetric to `load_preclose_spot`'s pairing rule);
   absent midday intraday receipt → the spot figure is omitted with a
   visible notice, never substituted. Missing name in the midday package
   → "midday refresh unavailable for this name" (fail-visible, never a
   silent carry). **Structural universe gap, disclosed (rev-1 finding
   14):** the capture universe is the 15-name `watch_universe()`; the
   board renders 18 (`ATTRACTIVENESS_UNIVERSE` adds NBIS/AMAT/CLSK).
   Those three can NEVER be midday-refreshed — they render a distinct,
   honest label "not in the capture universe" (not the generic
   unavailable notice), so the permanent state doesn't read as a daily
   bug. Widening the capture universe is a separate owner decision (it
   changes the pre-close lane's universe too and every receipt's
   universe field).
3. A small refresh runner (invoked by WP-D's wrapper after capture)
   rebuilds ONLY the overlay input: writes
   `.tmp/dashboard/midday_refresh.json` (atomic) with MANDATORY fields
   (rev-1 finding 12): `{"schema": "midday_refresh/v1", "session":
   <midday capture session>, "board_session_at_write": <the board's chain
   session at write time>, "captured_at_et", "candidates": {candidate_id:
   {premium_mid, worse_side, spot, ...}}}` for the morning board's
   hero/pinned candidate_ids. It does NOT call `assemble()`, does NOT
   re-select, does NOT write `picks_snapshot.json`, and does NOT rebuild
   the board HTML. **The render route is a STANDALONE MIDDAY PAGE,
   mandated, no alternative.** Route decision history: rev 1 let Codex
   choose — reviewed FAIL; rev 2 mandated a client-side fetch — reviewed
   FAIL (round-2 NEW-2: breaks `render()`'s self-contained
   no-external-assets contract, `attractiveness_dashboard.py:4463-4466`,
   and dies SILENTLY under `file://` CORS); "inject at next board build"
   was rejected because on a normal day the newest midday JSON at the
   07:10 build carries the SAME session date as that build's pre-close
   chain (not strictly newer — round-3 NEW-7 corrected rev 3's "older"
   phrasing), so it would display ONLY on days the prior pre-close
   capture failed — a mechanism that appears exactly when the pipeline
   is broken is not a display route.
   The midday runner renders `.tmp/dashboard/midday_refresh.html` — a
   small SELF-CONTAINED page (same pure-string-templating doctrine as
   the board) built from the JSON: per-candidate midday-vs-preclose
   quote lines, its own session stamped prominently in the header, the
   note "superseded by the 15:45 pre-close capture once that lands", and
   the standing disclaimer that selection/grades/rank are unchanged
   pre-close values.
   **Freshness guard (round-3 NEW-6 — rev 3's guard compared two fields
   written by the same runner in the same instant, a tautology; the
   comparands must be TWO NAMED, INDEPENDENTLY-SOURCED VALUES, evaluated
   at each writer's runtime):**
   - Comparand A: newest `schwab_midday_view.verified_midday_sessions()`.
   - Comparand B: newest `schwab_chain_view.verified_sessions()`
     (pre-close). B is DELIBERATELY the newest VERIFIED pre-close, not
     the board's displayed session (round-4 finding 6): the two diverge
     between 15:50 and the next 07:10, and newest-verified is the
     conservative comparand — it hides the midday page SOONER, never
     later; do not "correct" it to the board's session.
   - The midday runner (13:05) writes the quote-line page ONLY when
     A > B (strictly newer); otherwise it writes the "outdated" page.
     A EMPTY (no verified midday session yet, e.g. between merge and the
     first successful 13:00 capture) counts as A > B false → the
     outdated page is written, which is what makes the unconditional
     shelf link safe from day one (round-4 finding 2).
   - JANITOR SWEEP: the 07:10 board build ALSO evaluates A > B and, when
     false (including A empty), REWRITES `midday_refresh.html` as the
     "outdated" page — a midday page left over from a prior day (e.g.
     the 13:00 job silently not running) is neutralized every morning
     before it can mislead; if the 13:00 job never runs again, the page
     reads "outdated" forever — honest. Exception, disclosed (round-4
     finding 5): on a morning the board build itself fails (the ritual's
     fail-soft `|| note`), the sweep is skipped and the page's own
     "superseded by the 15:45 pre-close" header note remains the
     disclosure. The sweep is gated on the same real-assembly /
     invocation-source condition the composite self-build uses (round-4
     finding 4 — otherwise every offline test run of the dashboard
     module would rewrite a developer's real midday page; the
     module-executing baseline test must ALSO snapshot/restore
     `midday_refresh.html`).
   - Both HTML writes (runner and janitor) are ATOMIC — tmp file +
     `os.replace`, matching the board `OUTPUT_PATH` convention (round-4
     finding 3: a manual rebuild concurrent with the 13:05 runner must
     not interleave two writers on one file).
   - `board_session_at_write` stays in the JSON as PROVENANCE ONLY,
     never a comparand.
   The board links to the page ONCE, UNCONDITIONALLY, from the
   Experiments-shelf passive-links block (`_experiments_shelf_html`
   passive local-view links — the link target is always in a correct
   state because two writers maintain it, so NEW-3's pinned-content test
   stays single-case). Named tests: (a) runner with A == B (same date)
   writes the outdated page, never quote lines; (b) stale quote-line
   page + next-morning board build → file rewritten to outdated, AND
   A-empty (no midday session at all) → outdated page written (round-4
   finding 2); (c) A > B at 13:05 → quote-line page with its session in
   the header.
   Coordination note for brief 27: the recorder must ignore
   `midday_refresh.json` and `midday_refresh.html` entirely; its
   decision inputs stay pre-close.

### WP-D — schedule + durability

1. New wrapper `tools/schwab_chain_midday.sh` cloned from
   `tools/schwab_chain_capture.sh` (branch-main guard, bounded fetch,
   alignment gate incl. the evidence-only-ahead allowance extended to
   `reports/schwab_chains_midday`, failure taxonomy, notification, logs
   to `.tmp/schwab_chain_midday/`). The existing wrapper and its pinned
   tests (`tests/test_schwab_chain_schedule.py:24-36,56-79`) are
   untouched; new mirror tests pin the new wrapper + plist (13:00,
   weekdays, RunAtLoad false, no KeepAlive, and the pre-close plist
   asserts must still pass).
2. New plist `tools/launchagents/com.carsyn.options-validator.schwab-chain-midday.plist`
   modeled on the pre-close one (`WorkingDirectory` = ops checkout,
   `OPTIONS_VALIDATOR_INVOCATION_SOURCE=launchd`, TZ, Weekday 1-5 Hour 13
   Minute 0, logs). Install steps appended to `tools/launchagents/README.md`
   (bootout/bootstrap recipe as for pre-close). Installation itself is an
   OWNER/ops action after merge — the brief ships files + runbook only.
3. Durability: add `reports/schwab_chains_midday` to the daily ritual's
   DATA-TIER commit set (data tier: midday display data must commit even
   on gate-blocked days). Scout addendum 2026-08-25: PR #76 (merged to
   main same day) moved `reports/schwab_chains` itself into
   DATA_TIER_PATHS — the exact receipts-never-committed hole this
   session's task chip diagnosed — so verify the allowlist edit against
   the POST-#76 `daily_ritual.sh` on main, not this branch's copy. Also
   add ONLY `.cache/schwab_chains_midday` (gitignored, unrepurchasable) to
   `tools/irreplaceable_data_guard.py` namespaces. The implementation is
   BLOCKED until brief 29's guard-semantic repair, or an equivalent narrow
   prerequisite, has landed: when an inventory entry records `present: false`
   and that namespace later contains bytes, `verify` must fail as
   newly populated but unbaselined instead of skipping it. Pin that behavior,
   the still-absent healthy case, and unchanged enforcement of existing
   present floors in tests. In the cache-namespace code commit, regenerate
   `data/irreplaceable_data_inventory.json` so the new cache key is recorded
   even while absent; do not invent a nonzero floor.

   Schedule installation and unattended midday capture remain BLOCKED while
   that cache entry has no committed positive floor. Bootstrap it with one
   supervised, owner-operated midday capture after merge. Immediately run
   guard verification (which must fail specifically as newly populated but
   unbaselined), regenerate the inventory from those real bytes under the
   repository's owner-controlled inventory procedure, review the exact
   additive cache delta, and commit the positive floor before enabling the
   plist or permitting cleanup/reconciliation. This makes the first
   population fail closed and every later loss/shrink enforceable.

   *(Amended 2026-08-26 per PR #90 Codex review P1: the tracked,
   ritual-grown `reports/schwab_chains_midday` must NOT carry an inventory
   floor — the main checkout routinely sits on branches lagging
   origin/main, a floor recorded from main then false-alarms, and a guard
   failure halts the daily reconciler for the whole repo. Same
   adjudication as brief-29 round-1 findings A1/B5, the brief-29 blocking
   receipt findings 4/6, and brief 27's WP-E coordination flag. The
   tracked receipts' durability comes from `DATA_TIER_PATHS` plus
   git/remote. The backup allowlist derives from guard namespaces
   (PR #66), so the cache namespace gains backup coverage automatically
   while the tracked receipts rely on git — say so in the runbook. The
   inventory regeneration steps above apply only to the gitignored cache;
   `reports/schwab_chains_midday` must be asserted absent from the inventory.)*
4. Deploy preconditions: (a) the ops-health repair (task chip 2026-08-25;
   root cause fixed by PR #76) verified by ≥1 clean auto-committed
   pre-close receipt; (b) rev-1 finding 16 — the Schwab refresh token
   dies 7 days after creation and needs a manual weekend re-auth; a
   second daily job DOUBLES the dead-token blast radius (two failure
   notifications/day, two missing-receipt classes). The runbook addition
   must say so, and the midday wrapper's failure notification must name
   the token-expiry case distinctly (the pre-close wrapper's taxonomy is
   the template). Code can merge before these; plist installation waits.

### WP-E — isolation proofs (named tests)

1. Pre-close byte-identity: golden manifest/receipt equality under default
   parameters (WP-A.3).
2. Cross-contamination refusals: (a) a midday package placed into the
   PRE-CLOSE dirs makes `verify_session` fail loudly (extra-file glob) —
   pin it; (b) `verify_session` with midday parameters REJECTS a package
   whose receipt says `scheduled_session_tag: "preclose"` and vice versa;
   (c) a 13:00-captured receipt can never verify as pre-close (timing
   check) and a 15:45-captured receipt never verifies as midday.
3. Registered-consumer blindness: tests asserting `entry_watch`,
   `h10_watch`, and `h7_schwab_data_gate` resolve zero paths under
   `schwab_chains_midday` (path-injection or AST-level import/constant
   scan — mirror the experiments import-boundary test pattern,
   `tests/test_experiments_baseline.py:47-93`). SCOUT ADDENDUM (fourth
   consumer, on origin/main via brief 22): `tools/chain_consistency_audit.py`
   reads `.cache/schwab_chains` DIRECTLY (`:26` DEFAULT_CHAIN_DIR,
   `run_audit :199-240`) with a date-keyed adjacent-session pairing model
   (`data/chain_consistency.py:192-222`) whose frozen flag calibration
   (`config.py:838-865` on the provenance base) was measured on 15:45-only pairs — a
   same-directory midday capture would corrupt it into FALSE
   DELTA/SPREAD flags rather than an error. The separate namespace
   protects it; ADD a blindness test for this tool too, and note in its
   runbook that midday data lives elsewhere by design.
4. Overlay honesty (restated for the standalone-page route; round-2
   NEW-3, round-3 NEW-6): the midday PAGE renders quote lines only when
   newest `verified_midday_sessions()` is strictly newer than newest
   pre-close `verified_sessions()` (the WP-C.3 comparands — never a
   same-writer field); absent/partial midday data renders the
   outdated/unavailable notices; the 07:10 janitor sweep test (WP-C.3
   test b) is part of this package.
   The BOARD changes by exactly ONE static shelf link line and nothing
   else: board byte-identity before/after this brief holds everywhere
   except that line, asserted by a pinned-content test (the exact link
   HTML) plus byte-equality of the rest. No grade, rank, badge, or
   selection byte moves.
5. Ledger fact: midday capture appends under `SCHWAB_CHAIN_MIDDAY` prefix;
   a same-day pre-close fact and midday fact coexist without dedupe
   collision.

## Acceptance / verification

```bash
uv run python -m unittest discover -s tests    # exit 0, offline
uv run ruff check . && uv run pyright          # exit 0
```
Plus WP-E's named tests, and the pinned pre-close schedule/wrapper tests
passing UNMODIFIED.

## Claim-discipline register

- All capture/verify/collision mechanics cited above: Repo-verified on
  post-Brief-25 `origin/main@8a6920a` (lines quoted inline).
- RQ2 price-source pin to 15:45 pre-close: Repo-verified ledger seq 26
  clause 3.
- `midday` 13:00 ±10min already exists as a config constant:
  Repo-verified `config.py:759-770`.
- Existing per-capture cost 15 calls/session, no daily quota in code:
  Repo-verified (`data/schwab_adapter.py:360-371`; no counter found in
  adapter/credentials/policy modules).
- Receipt kind: DISTINCT `schwab_chain_midday/v1` (decided per rev-1
  finding 18; applied in writer and verifier consistently).
- Fourth chain-store consumer (`tools/chain_consistency_audit.py`, brief
  22): Repo-verified at `tools/chain_consistency_audit.py:26,199-240` on
  post-Brief-25 `origin/main@8a6920a`.
- `reports/schwab_chains` now DATA_TIER on main: Repo-verified, PR #76
  merged 2026-08-25 (@31215c5); current allowlist at
  `tools/daily_ritual.sh:543-545` on `origin/main@8a6920a`.
- Owner authorization for the +15 calls/day: owner-directed in-session
  2026-08-25 (spoken), quoted in the header.
