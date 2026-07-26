# Codex implementation plan — staged packets (2026-07-25)

Owner directive 2026-07-25 (evening): Codex access restored; push/validate
parking-lot work; add NBIS/AMAT/CLSK to the visual board; build a per-stock
hypothesis-evidence overview; keep everything visual. This doc is the staged
packet queue. Ordering note: the RQ2 briefs' formal gate ("Phase-1 recorders
first") is satisfied — R1–R5 are all live lines in the daily ritual
(exit fill/monitor, real-capture door, h10_watch/observe, entry_watch,
capture receipt; log evidence 2026-07-24_0710.log) — and the owner's
directive is the reprioritization nod.

Standing constraints for every packet: research-only repo (never places
orders); every number from config.py; owner types frozen values and NEW
registrations; unittest offline; ruff/pyright/CI green before merge;
fail-visible over silent; vocabulary discipline; board-ordering/Top-3
invariance tests are merge blockers for anything touching the scanner.
Verify all Lumibot/ThetaData signatures against installed packages. Fable
reviews every Codex result before merge.

**Amendment-recording delegation (owner-directed 2026-07-25):** amendments
to already-registered specs (e.g. H7_EXIT_SCORING_SPEC_AMENDMENT_V1_3) are
NOT an owner act: Codex drafts the amendment text → independent adversarial
review → Fable sign-off → Codex records it (ledger fact + spec doc) with
the provenance label "owner-delegated standing 2026-07-25". Verified
context for V1_3: the ledger already carries V1_1 and V1_2; the seq-0
frozen payload's cost_model_hash matches current while the whole-repo
config_hash has drifted through legitimate post-registration constants —
the amendment scopes the scoring identity to the registered surface
(stage456_parameters + scorer fields + cost_model_hash), demoting global
hashes to non-authoritative provenance. Scoring remains BUILD-ONLY behind
the owner's fresh PASS; ledger events and receipts are never rewritten.

---

## WAVE 1 — this weekend

### Packet P1 — Per-stock hypothesis-evidence panel (flagship) — size M-L

**Objective:** on the attractiveness dashboard, beneath each symbol's
section, render a "hypothesis evidence" accordion aggregating that name's
standing across every live hypothesis — total overview + as-of-now scope.

**Verified current behavior:** no per-stock rollup exists anywhere; evidence
lives scattered: H5 `reports/h5/entry_watch_<date>.txt`, H6
`reports/h6_forward/<date>.json`, H7 watcher
`reports/h7_receipts/h7-forward-15-v1/watcher/<date>.json` + source-health
receipts + the immutable 9-name cohort (`h7_cohort.load_registered_cohort()`
from `ledger/h7_forward/events.jsonl`), H8 `reports/h8_forward/<date>.json`,
H10 `reports/h10/receipts/`, intraday capture
`reports/intraday_capture/<date>/`.

**Required behavior:** per symbol, one collapsible panel with one row per
hypothesis family showing: membership (e.g. "H7 registered cohort" /
"H7 excluded EARNINGS-UNKNOWN" / "not in H6"), latest receipt date, current
state chip (verbatim from the receipt: WAIT / ENTRY-OK / BANNED / WATCH /
NO_SIGNAL / REFUSED / UNKNOWN), and the receipt path. Missing receipt →
explicit "NO RECEIPT <family> — expected daily" line (fail-visible). Panel is
display-only: attaches to section dicts AFTER assembly, never a `grades`
key, never read by rank/score/pick functions.

**Files:** new `options_researcher/hypothesis_evidence.py` (pure gatherers:
latest-dated-file resolution per family + per-symbol extraction); wire in
`attractiveness_dashboard.py::assemble` post-build; render in a new
`_hypothesis_panel_html`; tests `tests/test_hypothesis_evidence.py`.
Do NOT modify: `attractiveness.py` selection/grading, `h7_*` modules,
`ledger/` (read cohort via existing API only), any receipt writer.

**Edge cases:** receipt families with per-symbol dicts vs whole-board files
(inspect each schema first — do not guess); names outside a family (show
"not tracked"); weekend (latest receipt = Friday's, show its date, not
"stale"); ledger cohort read must tolerate BUILD-ONLY stores.

**Tests:** per-family extraction on fixture receipts; missing-receipt
fail-visible line; board ordering + Top-3 byte-identical with panel on/off;
wording pinned for state chips.

**Acceptance:** panel renders for all 15 names on the real cache;
`uv run python -m unittest discover -s tests` exit 0; ruff/pyright clean;
screenshots/HTML grep evidence in the report.

### Packet P2 — Display-extension universe: NBIS, AMAT, CLSK — size M

**Objective:** show the three new names on the board WITHOUT touching the
registered H7 scope.

**Verified constraints (audit 2026-07-25):**
`h7_scope.scope_symbols()` hard-raises unless exactly 15 names
(`h7_scope.py:18-28`); `tests/test_config_h7.py:11-22` freeze-pins the
literal H7 lists; `tests/test_attractiveness_universe.py:16-17` pins
`ATTRACTIVENESS_UNIVERSE == watch_universe()`; the real 9-name entry cohort
is immutable in `ledger/h7_forward/events.jsonl` regardless of config. The
owner declined NBIS for H7_WATCHLIST on 2026-07-16
(`reports/2026-07-16-h7-amendment-v1_7-proposal.md:113`) — display-only
addition does NOT reverse that and must not imply H7 membership.

**Required behavior:** new `config.ATTRACTIVENESS_EXTRA_NAMES` (owner-typed:
`["NBIS", "AMAT", "CLSK"]`); `ATTRACTIVENESS_UNIVERSE` becomes the 15-name
scope + extras; `h7_scope.py` and all H7 constants UNTOUCHED (the ==15
assert must survive); amend `test_attractiveness_universe.py` to assert
(a) the H7 scope is a strict prefix/subset, (b) extras are disjoint from all
H7 lists, (c) extras carry no H7 receipts. UI: extras' section headers carry
a pinned "DISPLAY-ONLY — not in any registered hypothesis" chip; P1's panel
shows "not tracked" rows for them. Earnings badges resolve UNKNOWN honestly
(no gating rows exist). Note: `intraday_capture.py:693` iterates
`ATTRACTIVENESS_UNIVERSE` → captures grow to 18 names (accepted; note the
extra remote calls in the report). `features.build_all()` also follows
automatically once chains+closes exist (backfill in flight 2026-07-25;
DATA_BLOCKED fail-visible sections are the acceptable interim).

**Edge cases:** config_hash changes with any config.py edit — confirm the
daily ritual re-derives health→gate same-session (it does; verify nothing
compares against the frozen registration source_hash for daily ops).
NBIS single-day chain file from 2026-07-15 must not masquerade as history.

**Tests:** universe composition asserts; DATA_BLOCKED rendering for a
data-less extra name; display-only chip pinned; board invariance for the
15 originals (their ordering unchanged by adding extras).

**Acceptance:** suite exit 0; the three names render (cards or DATA_BLOCKED);
no H7 receipt/test regression; CI green.

### Packet P3 — Mission-control banner date fix — size S

`dashboard.py::_default_data_as_of` (L123-143) pins the yellow banner to
`config.BACKTEST_END` (2026-06-30 forever). Change the closes window end to
today (`allow_oos=True`, precedent: entry_watch closes-to-today, fix
f248d29), keeping the "earliest across UNIVERSE so a stale name can't hide"
rule. Check `test_dashboard.py` pins. Do not touch the legacy backtest
window constants themselves.

### Packet P4 — Early-assignment dividend flag + T-bill comparison — size S-M

Top value-for-effort per the RQ2 survey (rank 6, "highest-value blocked
item" — now unblocked: `data/rates/expected_dividends.csv` +
`data/rates/treasury_cmt.csv` landed b06416e). Spec source: the rank-6 entry
in `reports/2026-07-22-scanner-quant-methods-survey.md` + the briefs doc's
delegated-values table. Display-only card line (early-assignment risk flag
on short calls when dividend > remaining extrinsic; T-bill yield comparison
on CSP collateral). OCC/official mechanics citations required in the brief;
NVDA 25x dividend-raise spot-check note from memory applies — treat the
dividends CSV as owner-spot-check-pending and label the line accordingly.

### Packet P5 — RQ2 Brief H1 cost/annualization hygiene — size XS

Wording-only honesty bundle, spec fully written in the briefs doc. Ship
first if Codex wants a warm-up.

### Packet P6 — Ritual signal taxonomy: BROKEN vs declined-to-enter — size S
(source: hard audit 2026-07-25, finding 10a)

**Verified current behavior:** `tools/daily_ritual.sh` marks CRITICAL — and
exits 1 / notifies "[BROKEN]" — when the capture receipt reports a
hypothesis REFUSED, even when the refusal is the fail-closed design working
(e.g. H7 preflight refusing on a source-unhealthy registered name). Friday
2026-07-24's BROKEN was exactly this. Alarm fatigue: the owner cannot
distinguish "no entry today (expected)" from "pipeline failed."

**Required behavior:** three-way summary taxonomy: OK / DEGRADED (a
hypothesis declined or was fail-closed banned — expected states, exit 0,
yellow notification) / BROKEN (a step crashed, a receipt could not be
written, evidence could not commit — exit 1, red). The per-hypothesis lines
keep their exact wording; only the roll-up classification and exit code
change. Preserve: FIRE still promotes to CRITICAL (review-forcing by
design). Tests: extend the ritual-receipt/banner test files; every existing
CRITICAL case must be re-classified in the test, not silently dropped.

### Packet P7 — Intraday-capture per-snapshot durability — size XS-S
(source: hard audit 2026-07-25, finding item 7)

**Verified current behavior:** `intraday_capture.py`/`.sh` never commit;
Friday-afternoon receipts sit untracked in ops until Monday's ritual —
a weekend disk failure loses up to ~72h of forward snapshots.

**Required behavior:** after each successful snapshot, `git add
reports/intraday_capture reports/live_probe && git commit` (fail-soft,
message pattern `evidence(intraday): <session_tag> <date>`) — commit only,
no push (the ritual's morning push and restic remain the durability chain;
an optional push is owner's call). Branch guard already ensures main.
Tests: shell-level dry-run guard; no commit on failed/skipped snapshots.

---

## WAVE 2 — owner-sequenced (specs already exist; do not start until Wave 1 merges)

In triage order (value-for-effort): beta-to-QQQ line (rank 15, data landed);
N3-1 market-implied expectations; V1 VRP calibration pair; B1 term-structure
corner (reconcile `feature/bs-attractiveness-descriptive` branch first);
A1 bounce lens (H11 blanks are a separate owner task); C1 board
concentration panel. Full specs: `docs/superpowers/plans/2026-07-22-rq2-scanner-enrichment-briefs.md`
(delegated values resolved 2026-07-24). Plus, after owner fills the
acceptance blanks: OI-v2 calibration runner per
`docs/superpowers/plans/2026-07-25-oi-v2-calibration-design.md`; and the
IV-skew badge after the owner approves
`docs/superpowers/plans/2026-07-25-iv-skew-steepness-onepager.md`.

## Owner actions (nothing here is Codex's)

1. Type `ATTRACTIVENESS_EXTRA_NAMES` values (P2) and the P4 label wording nod.
2. Run `uv run python tools/h7_refresh_earnings.py` for IREN/CRWV (and the
   other 4 unhealthy names) — that is ALL they need to go healthy; chains
   and closes are already current.
3. Approve/adjust the IV-skew one-pager blanks; fill OI-v2 acceptance blanks.
4. Decide the preserved 2026-07-24T1500Z probe receipt (auto-commits Monday
   otherwise).
5. VIXEQ note: Cboe publishes VIXEQ (free daily CSV, launched 2024-11-04 —
   pre-launch rows are back-tested reconstructions). The two parked
   dispersion badges' data blocker is resolved; they stay parked pending
   your scope call.
