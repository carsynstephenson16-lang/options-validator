# 2026-07-23 — Ritual repair: H8 artifact contract + H7 identity aftermath — Codex brief

**Executor:** Codex implements Plans A and B only; Plan C is an operator runbook (owner/ops
session — NOT Codex). Claude Code orchestrated, verified root causes against primary evidence,
and reviews the result. The owner ratifies every gated choice. If a cited interface, path, or
line does not match the installed code, STOP and report — do not improvise.

**Branch discipline:** implement on a fresh branch cut from `main` (the ritual's ops worktree
runs `main` only, branch-guarded). The relevant code landed on `main` via PR #14 merge
`b305000`. Deadline that matters: **merged to `main` before the next scheduled ritual run
(07:10 ET weekdays)** so the next session's capture is clean end-to-end. Owner merges.

---

## Verified root cause (do not re-diagnose; evidence cited)

Timeline for 2026-07-23 (ET), all verified from `.tmp/daily_ritual/2026-07-23_0805.log`,
`.tmp/daily_ritual/2026-07-23_1137.log`, receipt file mtimes, and `git` on the ops checkout:

1. **08:05–08:11** — scheduled ritual ran PRE-merge code for session 2026-07-22. Old-style
   chain: preflight REACHABLE, no exit-fill/monitor steps, no capture receipt, and `h8_watch`
   ran display-only (no `--json`, no redirect — verified against
   `b305000^1:tools/daily_ritual.sh:175`). Immutable source-health + data-gate receipts for
   session 07-22 were cut 08:07 under config identity `ae5de583…`.
2. **11:31** — PR #14 (`b305000`) merged to `main`, bringing BOTH the new ritual machinery
   (exit fill/monitor, capture receipt, H8 JSON artifact) AND +18 lines to `config.py`
   (new identity `0aa16b6a…`).
3. **11:37** — manual re-run, the new machinery's FIRST flight, still session 07-22. It reused
   the immutable 08:07 receipts → `ExitSessionRefused: data-gate config identity is stale`
   (`ae5de583` ≠ `0aa16b6a`) → exit fill/monitor REFUSED → entry path SKIPPED → no preflight
   artifact → capture receipt `H7: MISSING`. Separately, the new ritual line
   `tools/daily_ritual.sh:238-239` shell-redirects `h8_watch --json` stdout into
   `reports/h8_forward/<as_of>.json`; LumiBot v4.5.63 and dotenv emit import-time INFO banner
   lines on stdout, so the artifact begins with two log lines before the JSON → the strict
   parser (`options_researcher/ritual_receipt.py::_h8`) correctly reports
   `MISSING - unparseable JSON`.

**Consequences that gate the plans:**
- Both failures were introduced/exposed by the same merge. Nothing previously working broke.
- The H7 refusal is DESIGNED fail-closed behavior. Receipts are session-keyed and immutable
  (`FileExistsError: refusing to overwrite`); there is NO valid way to cut "fresh receipts"
  for session 07-22. Session 07-22's `H7: MISSING` stands as the honest transitional record.
  The unit of repair is the NEXT session, which re-keys automatically.
- H8's substantive day was clean: payload shows PLTR entry BLOCKED (IV-rank gate), AMZN
  OUT_OF_WINDOW, no exits, no errors → classifies NO_SIGNAL under `_h8`'s contract
  (`errors == []`, no BLOCKED exits, zero ENTRY-OK/EXIT count). Only the byte-zero JSON
  contract failed.
- `reports/h8_forward/` contains only the one (polluted) artifact — no historical residue.
- The preflight artifact path also uses shell capture, but its parser is a tolerant
  line-anchored text regex (`exit_code=(\d+)`) — banner-safe by construction. No change.

---

## Plan A (Codex, do first — deadline-bound): H8 writes its own artifact

**Scope guard:** H8 is a live forward-paper hypothesis; without this fix every future ritual
day records `H8: MISSING` and those capture days are unrecoverable by construction.

**Files:** Modify `options_researcher/h8_watch.py`, Modify `tools/daily_ritual.sh:236-239`,
Test `tests/test_h8_watch.py` (extend) and/or `tests/test_ritual_receipt.py` (extend).

**Chosen design — program-written artifact (matches H6/H10 precedent):** `h6_watch` and the
H10 watcher write their own receipt files; H8 becomes consistent with them instead of relying
on shell stream capture.

**Behavioral contract:**
1. Add `--out PATH` (default `reports/h8_forward/<as_of>.json` when `--json` is given) to
   `h8_watch`. The payload is written by the program: serialize to a temp file in the same
   directory, `os.replace` into place (atomic; no partial artifact can exist).
2. The payload keeps every field `ritual_receipt._h8` reads: `evaluation_session`, `entries`,
   `exits`, `errors` — byte-zero-parseable JSON, nothing else in the file.
3. stdout/stderr become irrelevant to the artifact: human-readable output may keep going to
   stdout; error/BLOCKER lines stay on stderr (h8_watch.py:901 already does this).
4. `tools/daily_ritual.sh` drops the `>` redirection and invokes `--json --out …`; the
   `mkdir -p reports/h8_forward` stays (or moves into the writer).
5. Do NOT "fix" this by scanning past garbage in the parser (fail-visible discipline: a
   half-written or polluted artifact must keep failing loudly), and do NOT try to silence
   LumiBot/dotenv stdout — third-party import-time output is not a stable contract to fight.

**Acceptance tests (named):**
- Subprocess test: run `python -m options_researcher.h8_watch --as-of <fixture> --json --out
  <tmp>` with the offline fixtures; assert `json.loads(open(out).read())` succeeds (byte
  zero), and assert the parsed payload carries `evaluation_session == as_of`.
- Pollution-proof test: simulate a banner print to stdout before/around the write (e.g.
  wrapper script or monkeypatched print at import in a subprocess); artifact still parses.
- Classification pin: a payload with one BLOCKED entry, one OUT_OF_WINDOW entry, empty
  `exits`/`errors` classifies `NO_SIGNAL` through `ritual_receipt._h8` (this pins today's
  substantive day as the regression fixture).
- Ritual-line check: assert `tools/daily_ritual.sh` no longer contains a `>`-redirect into
  `reports/h8_forward/` (cheap grep-style test, mirrors existing script-content tests if any;
  if none exist, a unit test on the new `--out` path suffices — do not build a bash test
  harness for this).

**Out of scope:** the existing polluted `reports/h8_forward/2026-07-22.json` is evidence —
leave it untouched. The capture receipt for 07-22 already recorded the failure honestly.

## Plan B (Codex, small): refusal diagnostics + capture-receipt overwrite semantics

### B1 — Stale-identity refusal message (unblocked now)

**Scope guard:** the next config-touching merge will reproduce today's refusal; the operator
should be able to read cause and remedy off the log line instead of re-deriving it.

**Files:** Modify the module raising `ExitSessionRefused: data-gate config identity is stale`
(locate it under `options_researcher/` — expected `h7_session` / exit-session code; STOP and
report if the raise site differs from expectation), extend its tests.

**Behavioral contract:** the refusal message (and ritual log line) must name: the receipt's
`config_hash`, the current config hash, and the remedy sentence "expected after a
config-touching merge landed after this session's receipts were cut; the next session's
receipts re-key automatically; do not attempt to rewrite receipts." REFUSAL BEHAVIOR ITSELF
DOES NOT CHANGE — message only. Test pins both hashes appearing in the message.

### B2 — Capture-receipt overwrite semantics (owner-gated design choice)

**Scope guard:** today the 11:37 run wrote the first capture receipt for 07-22, so nothing was
clobbered — but `ritual_receipt` currently has no refuse-overwrite, so a future broken re-run
could overwrite a good day's capture receipt with `MISSING`, violating the receipt-immutability
doctrine every other receipt in the chain follows.

**Files:** Modify `options_researcher/ritual_receipt.py` (write path), extend
`tests/test_ritual_receipt.py`.

**Recommended contract (owner ratifies before implementation `[OWNER: yes/no + choice]`):**
first-write-wins — if `capture_receipt_<as_of>.json` exists, refuse to overwrite; a re-run
whose computed result DIFFERS writes `capture_receipt_<as_of>.rerun-<HHMMSS>.json` beside it
and exits nonzero so the divergence is loud; identical result → benign no-op exit 0 (mirrors
the source-health "benign re-run" pattern). Alternative (rejected, recorded): last-write-wins
with history — weaker than the chain's own doctrine. Do not implement until the owner picks.

## Plan C (operator runbook — NOT Codex; no code, no receipt edits)

1. **Accept session 07-22 as recorded.** `H7: MISSING` and `H8: MISSING` are the honest
   transitional record of the merge day. Rewriting or deleting any 07-22 receipt/artifact is
   prohibited (immutability doctrine; 07-20 precedent).
2. **Next clean capture:** the next ritual run evaluating session 2026-07-23 (tonight after
   close, or the 07:10 scheduled run) cuts fresh receipts under `0aa16b6a…` and should go
   clean. Verify in the log, in order: source-health receipt written → data gate GO → exit
   fill OK → exit monitor OK → watcher receipt → preflight artifact `exit_code=0` → capture
   receipt `H7 ∈ {NO_SIGNAL, CAPTURED}` and (post-Plan-A) `H8 ∈ {NO_SIGNAL, CAPTURED}`.
   If Plan A hasn't merged yet, expect `H8: MISSING` again — known, not new.
3. **Standing process rule (owner to adopt):** merge `config.py`-touching PRs only AFTER the
   day's ritual chain has completed (or before the first run of a session). Each violation
   costs one session of H7 capture by construction — that is the designed price of the
   fail-closed identity check, not a bug.
4. **Optional, low urgency:** source health exited 2 with 6+ names showing "NO GATING
   ASSERTIONS" (CRWV, SMCI, NVDA, AVGO, IREN, USAR) — all OUTSIDE the registered 9-name
   cohort, so the live window is unaffected; run the owner-run earnings refresher
   (`tools/h7_refresh_earnings.py`) when convenient to clear the exit-2 noise.

## Non-goals (recorded so they aren't rebuilt by accident)

- No gate-logic changes anywhere in the H7 chain (B1 is message-only).
- No narrowing of the config-identity hash to an "H7-relevant subset" — considered and
  rejected: conservatism wins on a verdict-bearing path; the Plan C merge-timing rule removes
  the recurrence at zero code cost.
- No parser leniency for any JSON artifact, ever (fail-visible discipline).
- No rewriting of any immutable receipt or evidence file for 2026-07-22.

## Plan self-review (done at write time)

- Every claim above was verified this session against the two ritual logs, receipt mtimes and
  `config_hash` field, `b305000^1` script content, the polluted artifact bytes, and
  `ritual_receipt.py` source — not taken from the prior summary.
- Corrections vs the prior (Codex) summary, recorded for the reviewer: "generate fresh H7
  receipts and rerun" is impossible for 07-22 (session-keyed immutable receipts — repair unit
  is the next session); the identity change was attributed (PR #14 itself); the polluter is
  third-party import-time stdout, which is why the fix is a program-written artifact rather
  than stream redirection; the capture-receipt overwrite hazard and the source-health exit-2
  context were missing entirely; recommended order inverted — H8 is the only code fix with a
  deadline, H7 needs no code at all.
- Owner blanks: B2 semantics choice; Plan C rule adoption; merge timing of the Plan A PR.
