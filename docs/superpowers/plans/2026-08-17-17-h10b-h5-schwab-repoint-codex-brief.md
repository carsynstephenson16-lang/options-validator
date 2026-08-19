# Brief 17 — H10b resume + H5 observe mode on the Schwab preclose lane

**Date:** 2026-08-17
**Author:** orchestrating Claude session (Fable), 2026-08-16/17 owner-directed batch
**Executor:** Codex (high reasoning)
**Status:** DRAFT — pending independent adversarial review before hand-off.
The amendment precondition is MET: H10B_AMENDMENT_V1_1 (seq 28) and
H5_AMENDMENT_V1 (seq 29) were appended 2026-08-18 via the typed API after
the confirmation-round review + Fable sign-off
(`reports/2026-08-17-reopen-drafts-adversarial-review-receipt.md`).
**Provenance:** Repo-verified against branch
`claude/reopen-directives-2026-08-16` @`d5da03a` (base `origin/main`
@`f1fd4bd`) unless labeled otherwise.

## Why this exists (plain language)

The owner directed (2026-08-16/17, confirmations recorded in
`reports/2026-08-16-owner-directives.md`): H10b's forward-paper observation
resumes on the Schwab 15:45 ET preclose chain captures, and H5 becomes a
daily observer on the same lane with its old entry trigger retired. The
amendments carry three review-mandated safety obligations this brief closes
(round-1 receipt `reports/2026-08-17-reopen-drafts-adversarial-review-receipt.md`):
**BL-B** (closed-trial guard: H10a is ADJUDICATED and must never gain another
observation), **BL-C** (hard no-backfill floor: `--as-of` must not evaluate
pre-floor sessions), and the BL-A-adjacent normalization obligation (Schwab
IV is percent-scaled).

## Scope

**IN:**
- Re-point H10b's daily entry evaluation to verified Schwab preclose captures.
- H10a CLOSED guard in the H10 watcher, test-enforced.
- Namespaced H10b observation store (post-resumption rows cannot extend
  `reports/h10/observations.jsonl`'s closed H10a record).
- Floor constants + refusal paths (`H10B_RESUME_FLOOR_SESSION`,
  `H5_RESUME_FLOOR_SESSION`).
- New H5 observer output (prices, data availability, Schwab-IV accumulation
  count), fail-visible.
- Retire the H5 fire path in code (trigger retired per H5_AMENDMENT_V1).

**OUT (hard):** no ledger writes (the amendments are appended by the
orchestrating session, not Codex); no H10a-v2 work (separate owner-gated
registration); no new entry rule for H5; no changes to frozen config values
other than ADDING the two floor constants (mechanical landing-session dates,
provenance-labeled); no live-order paths; no authority flips; no paper-book
writes; no network calls in tests; no modification of
`schwab_chain_capture.py` (read-only consumer, the brief-14 WP-D pattern).

## Work packages

- **WP-A — H10a CLOSED guard (closes BL-B).** In
  `options_researcher/h10_watch.py` (signals computed for both hypotheses at
  `h10_watch.py:145-146`; only suppression today is window-end at
  `h10_watch.py:83-91` — Repo-verified @d5da03a): add an ADJUDICATED state
  for H10a (constant in `config.py`, provenance comment citing the
  `H10A_RESULT` fact of 2026-08-15/16) such that the watcher refuses to
  evaluate or record H10a in any mode. Test: attempting an H10a evaluation
  raises/refuses; the refusal names the adjudication.
- **WP-B — namespaced H10b store + receipt schema (closes BL-B incl.
  confirmation-round NEW-1).** Post-resumption H10b observations go to
  `reports/h10/h10b_observations.jsonl` with a per-row `hypothesis` field.
  `reports/h10/observations.jsonl` (rows have no hypothesis discriminator —
  Repo-verified) becomes read-only history; a test proves no code path
  appends to it. Per-session RECEIPTS carry
  `"signals": {"H10a": ..., "H10b": ...}` and
  `hypothesis_evidence.py:787` asserts that exact key set with a fixed
  `_HYPOTHESIS_ORDER` (Repo-verified) — post-resumption receipts must not
  contain a live H10a evaluation: emit an explicit `"H10a": "ADJUDICATED"`
  marker (or deliberately update the schema AND the invariant together),
  test-covered, so no receipt constitutes a post-adjudication H10a
  evaluation and the invariant does not silently break.
- **WP-C — no-backfill floors (closes BL-C).** `h10_watch.py:428-449`
  currently refuses only FUTURE `--as-of` dates (Repo-verified). Add
  `H10B_RESUME_FLOOR_SESSION` / `H5_RESUME_FLOOR_SESSION` to `config.py`
  (value = the LATER of the first session on/after this brief's landing
  merge and the amendments' ledger append date 2026-08-18 — amendment
  clause 5 as corrected by confirmation-round NEW-2; label "mechanical
  date, amendment clause 5"): any evaluation or record
  with `as_of` before the floor refuses, regardless of run time or receipt
  date. Tests both sides of the boundary.
- **WP-D — Schwab source adapter.** H10b admission checks (>=5 NTM monthly
  contracts, spread<=5 pct, OI>=100 — seq 16, unchanged) evaluate against
  the newest VERIFIED preclose capture for the session; missing / partial /
  failed-verification capture ⇒ session skipped + logged (fail-closed).
  Schwab IV percent→decimal normalization (÷100; `schwab_chain_view.py:223`
  stores percent — Repo-verified) with a unit test on a known fixture.
  Decision timestamp = 15:45 snapshot; close-based accounting unchanged
  (`_load_adjusted`, `h10_watch.py:99-100`); the mixed convention is stamped
  in every output row (amendment clause 2).
- **WP-E — H5 observer.** New read-only module (or `entry_watch.py`
  conversion): per name (VST/AMZN + any H5-universe names already watched),
  record price, capture availability, and the count of finite single-source
  Schwab IV observations toward 126 (`features.py:25` min-obs —
  Repo-verified). NO fire path: the retired-trigger evaluation code must be
  removed or hard-disabled with a test proving no FIRE output can be
  produced. Note: `entry_watch.py:136-137` hardcodes `.cache/chains/`
  paths (Repo-verified) — the observer reads Schwab captures instead; no
  ThetaData/Schwab IV series splicing anywhere (fabrication per
  `schwab_chain_view.py:334-337`).
- **WP-F — ritual wiring.** In `tools/daily_ritual.sh` (H10 lanes currently
  paused behind the H7 gate at `tools/daily_ritual.sh:388-395` —
  Repo-verified): route H10b + H5-observer through the Schwab-lane branch
  per the owner-confirmed D-1=F1 override (H10b and H5 watch ONLY; H6/H8
  stay paused). Fail-closed: no verified capture ⇒ skip + visible log line.

## Acceptance / verification

- `uv run python -m unittest discover -s tests` exit 0 (offline; no network).
- `uv run ruff check . && uv run pyright` exit 0.
- Proof tests the review demanded: H10a refusal (WP-A), no-append-to-legacy-
  store (WP-B), floor boundary both sides (WP-C), IV normalization fixture
  (WP-D), no-FIRE-possible (WP-E).
- `uv run python tools/irreplaceable_data_guard.py verify` exit 0 before any
  branch cleanup.
