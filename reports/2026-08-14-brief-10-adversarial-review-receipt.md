# Adversarial review receipt — brief 10 (switch-on decoupling + 10:00 chain session)

**Date:** 2026-08-14 (morning, pre-canary)
**Target:** `docs/superpowers/plans/2026-08-14-10-switch-on-decoupling-and-ten-am-chain-session-codex-brief.md`
(commit 79be87f on branch `claude/options-validator-handoff-8a4133`; unmerged)
**Reviewer:** independent Opus subagent (adversarial charter, read-only), commissioned
by the orchestrating Fable session per the house review rule.
**Verdict: FAIL — do not implement as written.** Brief 10 is WITHDRAWN as an
implementation instruction; it remains on its branch as history. A rev-2 spec
must resolve every blocker below and pass its own independent review.

## Blockers (condensed; full reasoning preserved in session transcript)

- **B1 — chain-cache poisoning unaddressed.** The brief isolates only
  `reports/` paths; `options_researcher/schwab_chain_capture.py:42` writes
  `.cache/schwab_chains` with `{symbol}_{session}.parquet`, session = DATE.
  A 10:00 capture with default `chain_dir` makes the 15:45 preclose fail
  hash-match per symbol → failed receipt, first-write-wins → session
  unrecoverable. The exact catastrophe the brief claims to prevent.
- **B2 — `ledger/facts.log` dedupe collision.** Fact prefix
  `SCHWAB_CHAIN_CAPTURE session=<date>` is shared; second capture crashes
  AFTER artifacts are immutable (`research/facts.py:45-49` dedupe refusal,
  uncaught) → artifacts without ledger anchor, no retry.
- **B3 — manifest convention + glob kill vector.**
  `tools/schwab_chain_manifest.py` hardcodes `preclose_snapshot_v1` and
  `validate_session_tag("preclose", …)`; a 10:00 receipt can never verify
  honestly. Its `*_{session}.parquet` glob raises on extra files BEFORE the
  preclose receipt writes — a second same-dir capture kills the canary.
- **B4 — the research-refresh resume promise is false.**
  `attractiveness_research_v2.py` requires ALL of H5/H6/H7/H8/H10 CAPTURED,
  and the H7 leg requires data-gate + watcher + entry-preflight receipts —
  precisely what the decoupled source tier keeps OFF. The only escape moves
  `h10_observe` (registered-ledger appends) and `entry_watch` (can FIRE)
  under source-only authority — a pre-registration honesty breach requiring
  its own owner decision, not a silent fence move.
- **B5 — the flip asserts a source that feeds nothing.** The ritual's data
  gate reads `.cache/chains` (frozen 2026-07-27; OD-4 forbids refill), NOT
  `.cache/schwab_chains`; `daily_ritual.sh` never invokes the Schwab
  evidence mode. Flipping `exact_session_source_active=True` would turn on
  a data phase that NO_GOs on a stale cache. "Dashboards fresh same day" is
  unsupported. Also: one canary ≠ "approved ONGOING source" — state the
  honest claim or add a multi-session bar.
- **B6 — new canary kill vector.** `daily_ritual.sh`'s fail-soft
  commit/push can leave ops HEAD ahead of origin/main all day → the 15:45
  wrapper (which now hard-fetches) refuses → that session's chains are lost
  forever. Unanalyzed coupling created by the flip. Runbook must add
  ops+research fast-forward after ANY merge to origin/main.
- **B7 — provenance tests must be replaced, not weakened.**
  `tests/test_daily_ritual_provenance.py` asserts `require-full` precedes
  every mutation surface; Task A necessarily rewrites these. Replacement
  invariant must be explicit: `require-source` precedes EVERY mutation
  surface; `require-full` precedes every H7 surface.
- **B8 — `config_hash()` blast radius.** A new session tag requires a
  `config.INTRADAY_CAPTURE_TIMES` entry; `config_hash()` hashes all
  uppercase constants and is a refusal binding in `h7_exit_session`,
  `h7_schwab_window_registration`, `intraday_capture`, `intraday_preview`.
  The change invalidates same-session receipt reuse mid-day.

## Cautions (must be dispositioned in rev-2)

C1 feasibility receipt config-hash already stale (registration-day work
regardless); C2 rev-2 must NAME that it supersedes runbook 08's
"flip last, after registration" line (owner may supersede; record it);
C3 data-phase enumeration doesn't match `daily_ritual.sh` (no closes/quotes
steps; source health IS an H7 receipt writer); C4 new plists need explicit
owner `launchctl bootstrap` steps (research-refresh precedent); C5 provider
call-count estimate required for any added capture (data-and-providers
rule); C6 `daily_ritual.sh:388` would commit morning chains labeled as H7
forward evidence; C7 mandated tests must share `chain_dir` + ledger dir or
they pass vacuously; C8 guard/backup namespace coverage decision +
inventory regeneration; C9 minor factual drift (authority file created
2026-08-02, not 07-28; `nearest_session_tag` silently gains new tags).

## Disposition (orchestrating session, same day)

1. Brief 10 WITHDRAWN as implementation instruction (this receipt).
2. Task C (10:00 capture) SPLIT OFF entirely — deferred until after the
   switch-on lands; needs its own spec resolving B1/B2/B3/B8/C5/C7/C8.
   (Independently, the completion-path review recommended deferring it as
   off-critical-path.)
3. Switch-on rev-2 design commissioned (Opus) with this receipt as charter;
   central design question: what "on" honestly means while `.cache/chains`
   is frozen — wire ritual consumers to Schwab evidence, or re-scope the
   data phase honestly. B4's fence question (which registered hypotheses'
   observation resumes under source-only authority) is an OWNER decision
   rev-2 must surface, not decide.
