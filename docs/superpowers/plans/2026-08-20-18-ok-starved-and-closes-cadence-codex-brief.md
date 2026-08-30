# Codex brief 18 — OK_STARVED ritual status + guarded daily closes refresh

**Date:** 2026-08-20
**Author:** orchestrating Claude session (owner decision packet
`reports/2026-08-20-chain-source-owner-decision-packet.md`; owner rulings
in-session 2026-08-20: Decision 1 = A, Decision 2 = yes; lane rule ruled
in-session 2026-08-20 after adversarial review finding 1: "Excuse chain lanes
only" — on OK_STARVED days H6/H7/H8 are excused, H5 and H10 must still be
healthy)
**Executor:** Codex (default reasoning tier)
**Status:** REVIEWED — independent adversarial review passed 2026-08-20
(Opus, two rounds: round 1 FAIL with findings 1-10, all closed; round 2
conditional pass with text amendments N1-N4, applied verbatim). Ready for
hand-off.
**Provenance:** Repo-verified against branch `claude/reopen-directives-2026-08-16`
@`bd31fd0` (origin/main @`378230f`) unless labeled otherwise. Every file:line
was re-verified by the 2026-08-20 adversarial review; if a line has moved,
match on the quoted code, not the number.

## Why this exists (plain language)

The chain-history cache is permanently frozen at 2026-07-27 (owner ruling
OD-2/OD-4; provider cancelled). The daily ritual therefore ends every day with
one expected critical line — the starved capture receipt — which forces the
terminal status to `BROKEN` (`tools/daily_ritual.sh:426-430`), which blocks
the downstream research refresh. The owner chose (Decision 1 = A) an honest
`OK_STARVED` status for such days, with research allowed to proceed when the
LIVE (Schwab) lanes are healthy even though the chain-starved lanes can never
be. Separately (Decision 2 = yes) the owner authorized automating the
already-approved Yahoo underlying-closes refresh as a guarded daily ritual
step; nothing schedules it today and the cache went 12 sessions stale before
the 2026-08-20 manual fix (DATA_PULL fact, commit `0a22cd4`).

Honest expectation-setting (owner has seen this): `OK_STARVED` alone does not
resurrect research. Research resumes only on days H5 and H10 are actually
healthy — which the closes automation (WP-C) helps make true for H5. Days a
live lane genuinely fails remain blocked, by the owner's lane rule. Under the
CURRENT authority flags (`data/ritual_authority.py:38-43`, both source and H7
flags false), H5 and H10 watchers never run — they sit inside full-tier
region B (`tools/daily_ritual.sh:314-393`) — so the lane rule unblocks no
days until the owner flips `exact_session_source_active`. This change makes
the status honest and the gate correct in advance; it is not expected to
produce a research run this week.

This brief implements exactly these mechanical changes. It does NOT touch the
H6/H8 wind-down (separate delegated-amendment work), any registration, or any
frozen value.

## Scope

**IN:**
- `tools/daily_ritual.sh`: terminal-status block, one new data-tier step,
  one `DATA_TIER_PATHS` addition.
- `options_researcher/ritual_status.py`: accept `OK_STARVED` in both
  validation sites.
- `options_researcher/attractiveness_research_v2.py`: preflight accepts
  `OK_STARVED` (WP-B.2) and applies the owner's lane rule (WP-B.3).
- `data/recent_topup.py`: one new function `refresh_closes_guarded`, plus
  the two docstring amendments in WP-C.5.
- Vocabulary updates (one line each) in the three documents that hardcode
  `status: OK`: `.claude/skills/research-refresh/SKILL.md:36-37`,
  `.agents/skills/independent-research-critic/SKILL.md:39-41`,
  `docs/research-context-refresh-runbook.md:21-24`.
- Tests per WP-D (offline `unittest`, existing files' patterns).

**OUT (do not touch):**
- `options_researcher/ritual_receipt.py` — receipt vocabulary
  (`CaptureStatus`, exit-code rule) is unchanged.
- `SUCCESSFUL_RITUAL_STATUSES` (`options_researcher/attractiveness_research_v2.py:27`)
  — its CONTENTS stay `{"CAPTURED", "NO_SIGNAL"}`; WP-B.3 changes which lanes
  it is applied to on OK_STARVED days, never what counts as successful.
- `ledger/**`, `research/facts.py`, `research/ledger.py` — no ledger writes
  except the ONE existing `DATA_PULL` append path (WP-C.4).
- Any LaunchAgent plist (the daily-ritual plist is not tracked in this repo —
  NOT FOUND at `bd31fd0`; schedule prose-documented at
  `tools/launchagents/README.md:174`). The new step rides the existing ritual.
- H6/H8 status, README "Scope status", registrations, verdicts, frozen
  numbers, provider endpoints (no ThetaData, no Schwab), live-order paths.
- `config.py` — no new constants there. Symbol scope is glob-driven (WP-C.1).
- `tools/daily_ritual.sh:532-537` (final `RITUAL STATUS:` print + exit code):
  UNCHANGED. An OK_STARVED day still exits 1 there today; leave it. Do not
  "improve" this.
- No `set -e` / `set -u` added to the ritual script (it has none; the
  `&& note || note` idiom depends on that).

## Work packages

### WP-A — `OK_STARVED` terminal status in the ritual

`tools/daily_ritual.sh` already computes the starvation predicate for its
notification title at :522-529 (Repo-verified):

```
if [ "$DATA_STARVED" -eq 1 ] && [ "$STARVED_CRIT" -eq 1 ] && [ "$CRIT_COUNT" -eq 1 ]; then
```

(`DATA_STARVED` set at :131-133; `STARVED_CRIT` set ONLY at :414;
`CRIT_COUNT` incremented only inside `crit()` at :80.)

Change the terminal-status block (:426-430) to a three-way choice using the
SAME predicate, verbatim — do not invent a new one, and do not read the
receipt JSON for a "starved" field (none exists; `grep -i starv` over
`ritual_receipt.py` is empty, Repo-verified):

- `CRITICAL==0` → `OK` (unchanged)
- `CRITICAL==1` and `DATA_STARVED==1 && STARVED_CRIT==1 && CRIT_COUNT==1`
  → `OK_STARVED`
- any other `CRITICAL==1` → `BROKEN` (unchanged)

Constraints (all Repo-verified):
- `tests/test_daily_ritual_provenance.py:475-486` pins the literals
  `RITUAL_TERMINAL_STATUS="BROKEN"` and `RITUAL_TERMINAL_STATUS="OK"` and the
  ordering `--status RUNNING` < receipt < `--status "$RITUAL_TERMINAL_STATUS"`
  < `# Step 8 — DURABILITY`. Both literals must survive the rewrite and the
  block must not move relative to Step 8. Do not reorder anything else — the
  publication-before-Step-8 ordering is pinned by that test (a late push
  failure leaving a published OK_STARVED next to a [BROKEN] title is a
  pre-existing, accepted asymmetry).
- The `[DATA-STARVED]`/`[BROKEN]` title logic at :522-529 stays exactly as is.

**What OK_STARVED does NOT prove:** OK_STARVED asserts only that the capture
receipt was the run's single CRITICAL. It does not prove the receipt failed
for chain-starvation reasons: a Schwab-lane H10 refusal, an H6
exit-evaluation block, or all lanes being PAUSED under data-tier authority
produce the identical shape. Narrowing further would require reading
per-hypothesis receipt statuses inside the shell, which is out of scope here —
the per-hypothesis protection lives in WP-B.3 instead. (Owner saw this
caveat before ruling the lane rule.)

### WP-B — `OK_STARVED` accepted downstream

1. `options_researcher/ritual_status.py`: add `"OK_STARVED"` to BOTH
   validation sites — `build_status()`'s set at :58-59 and the argparse
   `choices=("RUNNING", "OK", "BROKEN")` at :133. `SCHEMA_VERSION`
   (`daily_ritual/run_status/v1`, :22) is UNCHANGED — additive enum value,
   not a schema break; do not bump it. The `.previous`-file move at :117-119
   fires only on `RUNNING` and needs no change (Repo-verified).
2. `options_researcher/attractiveness_research_v2.py:366` — change
   `if status.get("status") != "OK":` to accept exactly `{"OK", "OK_STARVED"}`.
   Keep the raise-message shape. `RUNNING` and `BROKEN` still block. The
   `run_status_sha256` lineage binding (:83-95, :425-426, :751, :1407) hashes
   file content and needs no change.
3. **Lane rule (owner-ruled 2026-08-20, "Excuse chain lanes only"):** the
   per-hypothesis loop at `attractiveness_research_v2.py:401-411` currently
   raises `UpstreamBlocked` for ANY hypothesis whose status is not in
   `SUCCESSFUL_RITUAL_STATUSES` (:27). Amend it so that WHEN the run status
   is `OK_STARVED`, hypotheses belonging to the chain-starved set are excused
   from that check, while all others (H5, H10) are still required to be in
   `SUCCESSFUL_RITUAL_STATUSES`. On plain-`OK` days, behavior is unchanged
   (all hypotheses required). Define
   `CHAIN_STARVED_HYPOTHESES: Final = frozenset({"H6", "H7", "H8"})`
   immediately below `RITUAL_HYPOTHESES` (:28 — a flat tuple with no
   chain/live grouping), with a one-line comment citing this brief and the
   2026-08-20 owner ruling. Do NOT slice or subtract from
   `RITUAL_HYPOTHESES` (slicing breaks silently the day a hypothesis is
   added). Instead add a test asserting
   `CHAIN_STARVED_HYPOTHESES <= frozenset(RITUAL_HYPOTHESES)` and that the
   complement is exactly `{"H5", "H10"}` — that is the single-source-of-truth
   guarantee. Excused hypotheses are also omitted from `evidence_sha256`
   (the loop body at :422 is skipped); a two-key evidence map on OK_STARVED
   days is expected, not broken lineage.
4. Vocabulary updates in the three documents named in Scope IN: each
   currently instructs an agent to stop unless `status: OK`; change each to
   accept `OK` or `OK_STARVED` (one-line edit each, no other rewording) —
   except `.agents/skills/independent-research-critic/SKILL.md`, whose edit
   additionally notes that on OK_STARVED days the `evidence_sha256` map
   contains only the non-excused lanes (expected, not broken lineage).

### WP-C — Guarded closes refresh as a ritual data-tier step

New function in `data/recent_topup.py` (no new module, no new CLI flag —
`main()`'s `--refresh-closes` path stays untouched behind its ThetaData
gate):

```python
def refresh_closes_guarded(*, today: str, ledger_dir: str = "ledger",
                           fetch_fn=None) -> dict
```

Algorithm (validated live 2026-08-20; provenance = the DATA_PULL fact
appended that day, commit `0a22cd4` on `claude/reopen-directives-2026-08-16`):

1. Symbols = the stems of the existing `*.parquet` files in the cache
   directory, resolved AT CALL TIME as a module attribute:
   `from data import underlying_closes` then
   `Path(underlying_closes.CACHE_DIR)` — the idiom already used at
   `options_researcher/attractiveness_dashboard.py:1117-1123`. Do NOT add a
   `cache_dir` parameter (the writers `store_closes`/`fetch_underlying_eod_yahoo`
   hardcode `CACHE_DIR` at `data/underlying_closes.py:21`, so a parameter
   would desynchronize reader and writer; tests monkeypatch
   `underlying_closes.CACHE_DIR` instead — never `from ... import CACHE_DIR`).
   Repo-verified reason for glob-driven scope: no config constant or union of
   constants covers all 25 cached symbols (`BE, CRWD, HIMS, QQQ, SPY, UBER,
   ZS` belong to no active constant); a constants-based list would silently
   stop refreshing 7 names. Refresh what exists; never create a new symbol.
2. Per symbol: read the existing frame into memory FIRST, then call
   `fetch_fn` (default `data.underlying_closes.fetch_underlying_eod_yahoo`,
   :265-291, which overwrites the parquet in place and already excludes
   same-day partial rows internally via `drop_same_day_rows` :108-113 and its
   own `_now_ny_iso()` — do not re-implement that exclusion, and do not use
   `today` for row filtering: `today` reaches only the fact text
   (`recent_topup.py:88`), it is cosmetic).
3. Guard: read the refreshed frame; on the intersection of dates, any close
   differing by relative tolerance > 1e-4 means the history changed
   retroactively (unregistered-split signature — `SPLITS` at
   `data/underlying_closes.py:208-214` ends 2025-12-18). For that symbol:
   restore the pre-fetch frame via `store_closes` and record the symbol +
   first differing date in the returned summary. Continue with the other
   symbols. Consequence to state in the function docstring: a restored
   symbol stays stale until the owner amends `SPLITS` — that is the designed
   fail-visible outcome, surfaced by the closes freshness chip
   (`options_researcher/attractiveness_dashboard.py:1106-1126`).
4. Append EXACTLY ONE ledger fact per invocation via the same
   `research.facts.append_fact` pattern `refresh_closes` uses at
   `data/recent_topup.py:87-91`, extending the message with the guard outcome
   (e.g. "guard: N ok, M restored"). Do NOT call plain `refresh_closes` from
   the guarded function (double-fetch + double-append) and do NOT add any
   second fact call site.
5. Docstring conflict resolution (required, or Codex must stop per
   `.cursorrules`): `data/recent_topup.py:16-18` says "ORCHESTRATOR-ONLY
   network path… executed by the controlling session after review" and
   `refresh_closes`'s docstring (:74-79) says "owner-run cancellation
   workflow". Amend BOTH docstrings to additionally record: "Scheduled
   guarded path authorized by owner in-session 2026-08-20 (Decision 2 =
   yes: automate the Yahoo closes refresh as a guarded daily ritual step);
   see docs/superpowers/plans/2026-08-20-18-ok-starved-and-closes-cadence-codex-brief.md."
6. Return a dict summary: per-symbol max stored date, restored symbols,
   fetch errors. A fetch error for one symbol is recorded and skipped, not
   raised; the function itself should not raise on per-symbol problems.

Ritual step placement — **at the TOP of the data-tier island**: after the
comment block ending at `tools/daily_ritual.sh:279` and BEFORE the QM OHLCV
step at :286, because the attractiveness feature rebuild at :300-306 consumes
closes (`options_researcher/features.py:114-121` calls `load_closes`);
refreshing after it would rebuild features from yesterday's closes — the
exact consumer-before-refresh defect class the script header documents at
:6-10 (H10_RITUAL_ORDER_FIX). Mirror the `python -c` idiom at :301 and the
fail-SOFT `&& note ... || note ...` pattern of the QM step at :286-292 —
never `crit`. Pass `today='$RUN_DATE'` (`RUN_DATE` is the NY wall-clock date,
:114; `AS_OF` is the previous completed session and would mislabel the fact).
Suggested shape (adjust wording, keep the idiom):

```
"$UV" run python -c "from data.recent_topup import refresh_closes_guarded; import json; print(json.dumps(refresh_closes_guarded(today='$RUN_DATE'), default=str))" \
  && note "underlying closes: guarded refresh ran" \
  || note "underlying closes: refresh FAILED — closes chip will show stale"
```

**DATA_TIER_PATHS:** the new step appends a `DATA_PULL` fact to
`ledger/facts.log` on every run, but `DATA_TIER_PATHS` (:454) excludes it —
facts.log is committed only under full authority (:462-467), which is
currently never true, so the file would stay dirty and eventually break the
evidence merge/push (:487-497 — a merge with a locally-modified tracked file
fails, `crit "evidence: PUSH FAILED"`). Add `ledger/facts.log` to
`DATA_TIER_PATHS` at :454, amend the tier-scoping comment at :451-452 to say
the data tier now produces one descriptive DATA_PULL fact per day, and update
`tests/test_daily_ritual_provenance.py::test_durability_allow_list_is_tier_scoped`
(:492) to match.

### WP-D — Tests (offline, `unittest`, no network)

1. `tests/test_daily_ritual_provenance.py` — extend the existing starvation
   tests (`test_starved_label_requires_single_capture_critical` :563,
   `test_starved_title_flips_to_broken_on_a_second_critical` :587):
   - The :587 test executes the extracted block under real `zsh`; mirror that
     pattern to verify the NEW three-way terminal block behaviorally: the
     three counter combinations yield `OK` / `OK_STARVED` / `BROKEN`.
   - Keep `test...:475-486` green: both original literals present, ordering
     unchanged.
   - Source-text assertions: the closes step is inside the data-tier island,
     BEFORE the attractiveness feature rebuild
     (`source.index(closes_step) < source.index(features_step)`), and uses
     `note` (never `crit`) on failure.
   - Update `test_durability_allow_list_is_tier_scoped` (:492) for the
     facts.log addition.
2. `tests/test_ritual_status.py` — `OK_STARVED` accepted by `build_status`
   and publishable; an invalid status still raises.
3. `tests/test_research_context_assemble.py` — build fixtures with
   `_write_successful_ritual(root)` (:163-180, writes all five hypotheses
   `NO_SIGNAL` + evidence), then mutate
   `reports/ritual/capture_receipt_<AS_OF>.json`, then re-call
   `_write_run_status(root, status="OK_STARVED")` so the receipt sha matches
   — the exact three-step pattern of `test_broken_hypothesis_blocks`
   (:222-233). (`_write_run_status` alone writes only the status file and
   hashes an already-existing receipt; the sha check runs BEFORE the
   hypothesis loop, so mutating the receipt without re-writing the status
   file fails on sha, not on the lane rule.) Assert on the specific message
   (`assertRaisesRegex(UpstreamBlocked, "H10 status")`), never a bare
   `UpstreamBlocked`, so a sha-mismatch failure can never masquerade as a
   lane-rule pass. Both directions: H6/H7/H8 → `MISSING` with `OK_STARVED`
   must PASS; H5 or H10 → `MISSING` with `OK_STARVED` must BLOCK; H6
   `MISSING` with plain `OK` must still BLOCK (regression pin). Still blocks
   with `"BROKEN"` and `"RUNNING"`
   (`test_blocked_preflight_never_invokes_llm` :751 shows the blocking
   pattern).
4. New tests for `refresh_closes_guarded` with an injected `fetch_fn` and a
   monkeypatched `underlying_closes.CACHE_DIR` (tmp dir): clean refresh
   advances max date; a retroactive change is restored and reported while
   other symbols still refresh; a fetch exception for one symbol skips it
   without aborting; exactly one fact line appended per invocation (tmp
   `ledger_dir`). `fetch_underlying_eod_yahoo` is never called by any test.

## Acceptance

All of, by exit code:

```
uv run python -m unittest discover -s tests
uv run ruff check .
uv run pyright
```

Plus: `git grep -n "OK_STARVED"` output must list ONLY: the Scope IN files,
the three documents named in WP-B.4, tests, and this brief — proof of no
scope creep.

## Explicitly forbidden

- No new fact types, no second `append_fact` call site, no hand-edits to
  `ledger/**`.
- No changes to `ritual_receipt.py`, to the CONTENTS of
  `SUCCESSFUL_RITUAL_STATUSES` (`attractiveness_research_v2.py:27`), to
  `SCHEMA_VERSION`, `config.py`, any plist, any frozen value, or to
  `tools/daily_ritual.sh:532-537`.
- No network in tests.
- No new module, CLI, class hierarchy, retry logic, or config surface beyond
  the one function, one shell step, and one frozenset above. If a capability
  seems missing, STOP and report — do not build infrastructure
  (`.cursorrules` engineering rules).
- No tightening or loosening of any other gate while in the files (brief-17
  precedent: an executor tightened a spread gate without authorization and it
  was reverted).
