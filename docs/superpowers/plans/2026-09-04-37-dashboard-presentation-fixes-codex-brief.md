# Codex brief 37 — Dashboard presentation fixes from the 2026-09-04 review

**Date:** 2026-09-04 (rev 4; revs 1–3 reviewed FAIL — receipts
`reports/2026-09-04-brief-37-adversarial-review-round{1,2,3}.md`; every
finding applied or dispositioned in those receipts)
**Author:** Claude (orchestrating session; options-validator status + dashboard review, 2026-09-04)
**Executor:** Codex (Sol, high reasoning — the executor tier used for brief 07; owner may substitute at dispatch)
**Status:** DRAFT — pending independent adversarial review (round 4) before hand-off
**Provenance:** file:line constraints below are Repo-verified against origin/main
@039d76e unless a sentence carries its own label. "Test-verified" observations
were taken read-only from the ops execution checkout's 2026-09-04 09:12 ET build
(`~/options-validator-ops/.tmp/dashboard/{index,attractiveness}.html`) and its
ritual log `.tmp/daily_ritual/2026-09-04_0909.log`; counts marked "measured"
were re-counted by the round-2 and round-3 reviewers. Sentences labelled
**Inference** are the author's reading of the code, not a file fact.

## Why this exists (plain language)

The 2026-09-04 review opened both dashboards the morning after the 2026-09-03
intraday-capture fix (`reports/2026-09-03-attractiveness-scanner-pm-evaluation.md`
§3) and found the board FRESH for the first time since July: 13 of 18 names on
the 2026-09-03 Schwab 15:45 chains, top-5 shortlist filled. Reading the two
pages as a portfolio manager surfaced nine defects that make the pages say
things that are false, stale, or repeated. This brief is the finding record
(there is no earlier receipt for these items) and the hand-off in one document.
Every work package is presentation or plumbing. Three review rounds moved two
items OUT of this brief: the realized-volatility half of DR-6 (inseparable from
the badge decision — held with DR-5 for the owner) and the event-chip dedupe
DR-8b (it would silently retire a parity contract brief 28 authored on purpose
— held for the visual-redesign brief). What remains is seven fixes.

| ID | Page | What the page says today (Test-verified 2026-09-04) | Why it is wrong |
|---|---|---|---|
| DR-1 | Mission Control | "VST — Held — 38 shares, no options" | `data/positions/holdings.csv:2` says 39; the text is a constant at `options_researcher/dashboard.py:223` |
| DR-2 | Mission Control | banner "DATA AS-OF 2026-06-30 CLOSE" | the as-of lookup is capped at `config.BACKTEST_END` (`config.py:81`, "2026-06-30"); closes run through 2026-09-03 (ritual log `max_dates`, same morning) |
| DR-3 | Mission Control | "H7 FORWARD WINDOW (live, scores once 2026-10-26)" | that window (`h7-forward-15-v1`) is PAUSED per OD-3 (`PROJECT_STATE.md:38-39`, 2026-08-02 close-out: "H7 will not restart now; any later restart requires a new registration and namespace"); the ritual prints "H7 lanes: PAUSED" the same morning (`tools/daily_ritual.sh:266`) |
| DR-4 | Mission Control | Achievements: "Study Hall: A" ×8, B ×8, C ×18, D ×8, E ×16 (measured on `ledger/facts.log` and the build) | one tile is appended per matching `ledger/facts.log` line (`dashboard.py:192-197`) |
| DR-6 | Attractiveness board | on every Schwab-sourced name the sentence "underlying closes end 2026-09-03, before this 2026-09-03 session" — 174 copies, measured: 26 across the 13 "! Unavailable for this session" lines (each line carries the reason twice, for the `rv21` entry `:1974` and the `iv_minus_rv` entry `:1975`, joined at `attractiveness_dashboard.py:5073`) plus 148 repeated per card by `bbb_absent` (`:1619-1625`) | the sentence is self-contradictory. The Schwab branch sets `rv21`/`iv_minus_rv` to NaN unconditionally (`:1965-1966`) and writes the gap text at `:1972-1973`. **Inference:** the branch comment ("the closes store ends earlier") describes a state that no longer holds — the ritual refreshes closes (`daily_ritual.sh:290`) before the dashboards build (`:483`). The NaN itself is a policy question (DR-5b below); the sentence is simply false |
| DR-7 | Attractiveness board | Registered-bets tracker cites `reports/ritual/capture_receipt_2026-09-02.json` (50 citations) on the 2026-09-04 build | `tools/daily_ritual.sh` builds both dashboards (`:483-484`) BEFORE it writes the capture receipt (`:492-507`), and the tracker takes the newest receipt on disk (`hypothesis_evidence.py:1133` glob, max-by-date at `:227`) |
| DR-8a | Attractiveness board | two red notices "Schwab capture session 2026-08-31 / 2026-09-01 FAILED verification" | `schwab_chain_view.verified_sessions` (`:170-195`) returns every failed receipt on disk with no age limit and `_schwab_state_html` (`:1050-1093`) prints each one forever |
| DR-9 | Job-health digest | "Schwab preclose — FAILED — receipt path escapes root — .cache/schwab_chains" for the 2026-09-03 capture that verified 15/15 (reproduced by all three reviewers) | the chain-directory containment check at `tools/job_health_digest.py:525-532` resolves symlinks and returns FAILED before the per-symbol loop; the ops checkout's `.cache` is a SANCTIONED symlink to the main checkout's `.cache` (CLAUDE.md "Worktree location rule"; `ls -la ~/options-validator-ops/.cache` Test-verified) |

### Held for an owner ruling or a later brief — NOT in this brief (recorded so it is not lost)

- **DR-5** — the GREEN-fraction ranking divides by the number of checks per
  lane (`options_researcher/display_rank.py:18-19`), so a 4-check long call
  beats an 8-check put with one AMBER. Changing that is a change to the
  frozen baseline recipe.
- **DR-5b (the computation half of DR-6). Codex must NOT implement any part
  of this bullet.** It is a record for the owner's ruling; the imperative
  wording describes what a future brief would specify, not work authorized
  here. On Schwab-sourced cards the `cushion` badge (from `rv21`,
  `attractiveness.py:189-201`) and the `vrp_for_seller` badge (from
  `iv_minus_rv`, `:203`) are UNKNOWN because the inputs are NaN, and the
  price ladder / bull-base-bear table are empty for the same reason. Both
  badges are members of `grades`, which `display_rank.py:18-19` ranks on, so
  restoring the inputs reorders the top 5 and the pick-tracker arms. Two
  review rounds established that a display-only restoration (ladder yes,
  badges no) leaves every put card contradicting itself
  (`attractiveness.py:211-215` prints "typical monthly wiggle is
  UNAVAILABLE" while the same card's table would be built from a finite
  value) and cannot be fixed without editing `attractiveness.py`. It is
  therefore one decision, the owner's. Pre-drafted design for whichever way
  the ruling goes (**Inference** throughout; citations verified): compute
  from `adjusted_closes` (`attractiveness_dashboard.py:1943-1944`; the only
  series a trailing signal may consume, `data/underlying_closes.py:49-52`)
  restricted to index STRICTLY BEFORE `day` so every input predates the
  15:45 capture (docstring `:1931-1936`); formula byte-for-byte
  `features.py:23`, `:50-51`, `:70` (import `RV_WINDOW`, never edit the file
  — closure member); availability `1 <= trading_sessions_between(last_close_date,
  day) <= config.CHAIN_STALE_BLOCK_SESSIONS` (`top3_snapshot.py:83-92` is
  `np.busday_count`, half-open `[start, end)`; `config.py:690` = 3), with any
  exception or count < 1 keeping NaN; wire through `ladder_cards` at `:2032`
  (grades) and the `_gather_symbol` return at `:2213` → `rv21_by_symbol:1912`
  → `scenario_rows:1612` / `bbb_rows:1614` (display); parity test against
  `features.build_daily_features(...)["rv21"]` at `last_close_date`, not
  `day` (the store's value at D includes D's own return, `features.py:68`);
  tests in `tests/test_schwab_freshness_gather.py` (`:174`, `:188`,
  `:197-199`); because the ranking changes, the pick-tracker arms change and
  the first post-landing ritual raises `IMMUTABLE_HISTORY_CONFLICT` by
  design. Latent defect for the same ruling: `features.py:121` feeds RAW
  closes to rv21, which `data/underlying_closes.py:49-52` forbids; impact
  confined to rows within `RV_WINDOW` of a split (`SPLITS` `:208-214`, latest
  2025-12-18), so no current board session is affected.
- **DR-8b (event-chip repetition). Codex must NOT implement any part of this
  bullet.** The identical "EVENT · CAL · fomc meeting · FOMC decision ·
  2026-09-16 …" chip appears on all 5 picks, all 5 context picks and both
  core cards (12 copies above the fold). Measured on the whole page: 295
  `event-chip` spans, every one an FOMC chip (180 for the 2026-09-16
  decision, 65 for 2026-10-28, 32 for 2026-12-09, 18 across six 2027 dates),
  in 180 `event-chips` containers. `_event_chips_html` (`:3014-3028`) is
  called per card (`:3227`, `:3908`, `:4463`, `:4647`). A section-level
  dedupe was drafted and withdrawn in round 3 because
  `tests/test_event_awareness.py:311`
  (`test_populated_hero_lane_context_and_pinned_surfaces_share_exact_chip_list`,
  comment `:312` "Catches a consumer drifting from the single event-chip
  join contract"; assertions `:441-449`; second exposure `:258`) pins that
  every surface shows the same per-card chips — an invariant brief 28
  authored on purpose. Removing repetition therefore means renegotiating
  that contract, which belongs in the visual-redesign brief, not here.

## Scope

**IN:** `options_researcher/dashboard.py`,
`options_researcher/attractiveness_dashboard.py`, `tools/daily_ritual.sh`,
`tools/job_health_digest.py`, and their tests (`tests/test_dashboard.py`,
`tests/test_attractiveness_dashboard.py`, `tests/test_attractiveness_layout.py`,
`tests/test_schwab_freshness_gather.py` — the only test that drives
`_gather_symbol`'s Schwab branch end-to-end; its assertions at `:188` and
`:197-199` must stay green — `tests/test_daily_ritual_provenance.py`,
`tests/test_job_health_digest.py`).

**OUT (hard):**
- No edit to any member of `FEASIBILITY_SOURCE_PATHS` (frozen literal tuple,
  `options_researcher/h7_schwab_window_registration.py:143-194`, 50 files;
  owner ruling 1 of `reports/2026-09-03-brief-36-owner-rulings.md`).
  Test-verified 2026-09-04 and re-verified by all three reviewers: the four
  IN files and `options_researcher/{portfolio,hypothesis_evidence,schwab_chain_view,top3_snapshot}.py`
  and `data/ritual_authority.py` are OUTSIDE the closure;
  `options_researcher/features.py` (`:162` of the tuple) and
  `data/underlying_closes.py` (`:157`) are INSIDE it and may only be
  imported, never modified. Do not add an import of any H7/activation module
  into the IN files (`h7_window_status` is already imported at
  `dashboard.py:181`).
- No change to `options_researcher/attractiveness.py`,
  `options_researcher/display_rank.py`, any badge grade, the `grades` inputs
  of any card (`rv21` and `iv_minus_rv` stay NaN on Schwab-sourced cards
  until DR-5b is ruled), or any ranking, signal, or constant with owner
  provenance.
- No change to event-chip rendering (`_event_chips_html`, `:3014-3028`, or
  any of its four call sites) and no edit to `tests/test_event_awareness.py`
  (DR-8b is held).
- No ledger write, no registration, no authority flip, no live-order path, no
  paper-book mutation, no change to `config.py`.
- No launchd / plist change (the unloaded `research-refresh` LaunchAgent is an
  ops action for the owner, not code).
- No visual redesign (theme, KPI tiles, name table, charts) — a separate brief
  once the owner picks a direction. No change to `_diagnostics_drawer_html`
  (`attractiveness_dashboard.py:5435-5452`) or its fixed six-section list
  (`:5660-5669`; pinned by `tests/test_attractiveness_layout.py:405`).
- In `tools/daily_ritual.sh`: no change to the pick tracker's fail-soft
  isolation (`:486-487`), to the `RITUAL_TERMINAL_STATUS` block and its
  `ritual_status` call (they stay after the capture receipt and before Step 8
  DURABILITY, `:528+`; pinned at `tests/test_daily_ritual_provenance.py:588-591`),
  or to any `note`/`crit` string (tests pin them).
- No change to the ThetaData-sourced branch of the board.

## Work packages

### WP-A — Mission Control as-of banner and sparklines follow the real closes (DR-2)

1. `dashboard.py:124-144` `_default_data_as_of` and `:112-121`
   `_default_closes` both call `load_closes(sym, config.BACKTEST_START,
   config.BACKTEST_END, allow_oos=True)`. `load_closes` slices
   `.loc[start:end]` on a plain-string index (`data/underlying_closes.py:57-59`;
   measured: the `date` column is dtype `object`) and gates only on
   `end > IN_SAMPLE_END` without `allow_oos` (`:53-56`). **Inference:** an
   END bound past the store's last row is therefore safe and returns what
   exists — prove it with the test in step 3.
2. Replace the END bound in BOTH helpers with the `.isoformat()` STRING of
   the `America/New_York` build date (or an injected `today: str` for tests
   — never bare `date.today()`, which is local, and never a `date` object,
   which is a slice error against the string index). The banner VALUE must
   remain the series index (earliest last-cached date across
   `config.UNIVERSE`, docstring `:125-131`), never the clock —
   `tests/test_dashboard.py:131-176` stay green unchanged (they patch the
   loader by module attribute and ignore call arguments).
3. Add tests: a series whose last index is after `BACKTEST_END` reports that
   later date; sparklines take the last 60 rows of the same extended range.

### WP-B — VST share count comes from the holdings file (DR-1)

1. `dashboard.py:219-225` `_PARTY` carries the role text as a constant
   (`"Held — 38 shares, no options"` at `:223`); its single consumer is the
   loop at `:450` (`for symbol, color, role in _PARTY`). Keep `_PARTY` for
   symbol and accent colour only; derive the role line for held names inside
   `assemble()` and re-point `:450` at the derived role, so `render()` stays
   pure.
2. Read shares through the existing fail-loud loader
   `options_researcher.portfolio.load_holdings()` (`portfolio.py:77-96`,
   `HOLDINGS_PATH` at `:25`; already the board's reader at
   `attractiveness_dashboard.py:1788-1794`). Add a keyword-only `holdings:
   pd.DataFrame | None = None` parameter to `assemble()` following the house
   injection pattern (`dashboard.py:155-157`: every argument defaults to the
   real project state and a test passes it explicitly); tests pass a frame
   rather than changing directory. Role text: `Held — {shares} shares` plus
   `, no options` when the book (`assemble()`'s `book["marks"]`) has no open
   mark for that symbol, else `, {n} open option mark(s)`.
3. Fail-visible, never the old constant, three cases: (a) loader failure —
   catch exactly `(OSError, TypeError, ValueError)`: the loader raises
   `FileNotFoundError` and `ValueError` explicitly (`portfolio.py:79-95`)
   and `TypeError` on a short CSV row (`:90` and `:93` receive `None` from
   `csv.DictReader`); the house pattern is a named tuple with everything
   else crashing loudly (`dashboard.py:173-176`) and a bare `except
   Exception` is a review reject → `Held — shares UNKNOWN (holdings.csv
   unreadable)`; (b) file loads but has no row for the held symbol → `Held —
   shares UNKNOWN (no holdings.csv row for VST)` — never `.iloc[0]` on an
   empty frame, never 0; (c) more than one row for the symbol → sum the
   lots. In (a) and (b) print the cause to stderr like the entry-watch path
   does (`:176-177`).
4. Tests: 39 from an injected frame; unreadable file → the UNKNOWN text; a
   frame without a VST row → the no-row text; a short-row CSV → the UNKNOWN
   text (not a crash); an assertion that the literal `38 shares` no longer
   exists in the module.

### WP-C — The H7 panel may only say "live" when H7 authority is granted (DR-3)

1. `dashboard.py:398-424` `_h7_window_panel` prints `(live, scores once …)`
   (`:413`) from `h7_window_status.window_status()`
   (`h7_window_status.py:21-70`), which reads the append-only store
   `REAL_FORWARD_STORE` (`:14-18`) and knows nothing about authority.
2. Authority truth is `data/ritual_authority.py`: the frozen dataclass
   `RitualAuthority` (`:31-35`, fields `h7_active`,
   `exact_session_source_active`, `ritual_data_phase_active`), the
   `CURRENT_AUTHORITY` literal (`:38-50`) with `h7_active=False` at `:39`,
   and `evaluate_full_ritual()` (`:69-84`), which aggregates the three flags
   and appends the H7 blocker "H7 forward-paper authority is paused; no
   active namespace exists." at `:83`. Do not key on its aggregate `ready`
   and do not substring-match the blocker text. Instead `assemble()` calls
   `evaluate_full_ritual(RitualAuthority(h7_active=CURRENT_AUTHORITY.h7_active,
   exact_session_source_active=True, ritual_data_phase_active=True))` so the
   H7 sentence at `:83` is the ONLY blocker that can be produced (`:65`,
   `:79`, `:81` unreachable; `THETADATA_ACQUISITION_DISABLED` is nested under
   `:78-81` — confirmed by the round-3 reviewer). **Inference:** both
   functions are pure dataclass evaluation with no I/O; the module's only
   first-party import, `THETADATA_ACQUISITION_DISABLED` from
   `data/provider_policy.py`, is a constant. `assemble()` attaches
   `h7_authority = {"h7_active": …, "blockers": [...]}`; `render()` passes
   it to the panel.
3. Panel behaviour: when `h7_active` is False, the heading is
   `H7 FORWARD WINDOW — PAUSED (H7 authority not granted)` followed by the
   blocker sentence verbatim; if the blocker list does not contain exactly
   one entry while `h7_active` is False, render `H7 BLOCKER TEXT UNAVAILABLE
   (ritual_authority contract changed)` rather than nothing or an unrelated
   sentence. The counts line (`dashboard.py:414-422`, including `entries
   taken: {n}`) is emitted byte-identical, prefixed by the label `registered
   window (paused; scores nothing while paused)`; the word "live" must not
   appear anywhere in the panel. When `h7_active` is True, the current
   wording is kept unchanged. If the store is unavailable the existing
   UNAVAILABLE branch (`:400-405`) still wins.
4. Tests, both directions plus the contract guard: inject
   `h7_active=False` with the blocker → PAUSED text and `entries taken: 0`
   present, `live` absent; inject `h7_active=True` → `live` present; inject
   `h7_active=False` with an empty blocker list, and separately with two
   blockers → the UNAVAILABLE-text sentinel in both. Update
   `tests/test_dashboard.py:38-77` to pass `h7_authority=` explicitly so
   neither existing test depends on the live `CURRENT_AUTHORITY` value
   (`:65` asserts `entries taken: 0`).

### WP-D — One achievement tile per tag (DR-4)

1. `dashboard.py:192-197` (inside `assemble()`) appends a tile for every
   `facts.log` line whose tag is in `ACHIEVEMENTS` (`:46-82`; the per-symbol
   study tags `STUDY_A..E` at `:77-81` match dozens of lines — 18 `STUDY_C`
   lines today).
2. Collapse in `assemble()` — so `data["achievements"]` itself is deduplicated
   — to one entry per tag, first-occurrence order preserved, carrying a
   `count` field. The `render()` function body is unchanged; only its helper
   `_achievements_grid` (`:373-388`) gains the `×N` title suffix when N > 1.
   The Graveyard list is untouched.
3. Tests: the existing fixture (`tests/test_dashboard.py:8-22`, one `STUDY_C`
   line) stays valid; three `STUDY_C` lines → `data["achievements"]` holds
   exactly one `STUDY_C` entry with `count == 3` and the rendered title ends
   in `×3`.

### WP-E — Make the Schwab-branch gap sentence true (DR-6, sentence only)

1. `attractiveness_dashboard.py:1972-1973` builds `gap = "underlying closes
   end {closes_as_of}, before this {day} session"` and feeds it to the
   `feature_unavailable` entries for `rv21` and `iv_minus_rv` (`:1974-1975`),
   which render as the "! Unavailable for this session — …" line
   (`:5056-5075`, one call site at `:5609`) and are repeated per card by
   `bbb_absent` (`:1619-1625`, which filters for `field == "rv21"` and takes
   `reasons[0]`). `closes_as_of` is a plain ISO string (`:1945`,
   `str(raw_closes.index[-1])`) and `raw_closes` is loaded with `end=day`
   (`:1942`), so `closes_as_of > day` is impossible. When `closes_as_of ==
   day` the sentence is false.
2. Compute NOTHING new. Replace the sentence with one that names the real
   cause, is true in both states, and carries no expiry date:
   - when `closes_as_of == day`: `rv21 and iv_minus_rv are not computed on
     the 15:45 capture lane (this lane has no realized-volatility input; see
     brief 37 DR-5b); closes are current through {day}`;
   - when `closes_as_of < day`: `rv21 and iv_minus_rv are not computed on
     the 15:45 capture lane (this lane has no realized-volatility input; see
     brief 37 DR-5b); closes end {closes_as_of}, {n} session{s} before this
     {day} session`, pluralized properly like `:1128` (`1 session` / `2
     sessions`), with `n` from `trading_sessions_between(closes_as_of, day)`
     (`top3_snapshot.py:83-92`, `np.busday_count`, half-open; the helper the
     page already calls at `:1248`). Import it locally inside
     `_gather_symbol`, mirroring the local import at `:1938` — do not add it
     to the injected-dependency parameter list (docstring `:1927-1929`). On
     any exception from it, print the two dates without a count.
   The NaN assignments at `:1965-1966`, `iv_rank` handling (`:1967-1970`),
   `features_source` (`:1964`) and every `grades` input (`:2030-2035`) are
   unchanged; the ThetaData branch (`:1980-2017`) is untouched.
3. Tests: in `tests/test_schwab_freshness_gather.py` (drives
   `_gather_symbol` directly, `:174`, and never renders a page): closes
   ending on `day` → the "current through" sentence and no occurrence of
   `, before this `; closes ending 8 sessions earlier (the file's existing
   fixture, `DAY = "2026-08-14"` at `:24`, closes end `2026-08-04`,
   `:122-124`; `busday_count == 8` measured) → the "end … 8 sessions before"
   sentence; `:188` and `:197-199` remain green. In
   `tests/test_attractiveness_dashboard.py`: a rendered-page assertion that
   the literal `, before this ` never appears when the two dates are equal.

### WP-F — Write the capture receipt before the dashboards are built (DR-7)

1. `tools/daily_ritual.sh:481-484` rebuilds both dashboards, `:485-490` runs
   the pick tracker, `:492-507` writes the per-hypothesis capture receipt
   (`options_researcher.ritual_receipt`, output
   `reports/ritual/capture_receipt_<as_of>.json`, `ritual_receipt.py:448`;
   the block's shell structure is outer `if` `:494` / inner `if` `:495` /
   inner `else` `:498` / inner `fi` `:504` / outer `else` `:505` / outer
   `fi` `:507` — balanced), and the `RITUAL_TERMINAL_STATUS` block follows.
2. `ritual_receipt` reads only lane artifacts written earlier in the script
   (`ritual_receipt.py:117-300`: `reports/h5`, `reports/h6_forward`,
   `reports/h7_*`, `reports/h8_forward`, `reports/h10`). **Inference:**
   nothing produced by the dashboards or the pick tracker is read by it, and
   nothing between `:483` and `:492` sets a variable the receipt block reads
   (confirmed by all three reviewers). Move the whole capture-receipt block
   (`:492-507`, including the `STARVED_CRIT=1` line and both `crit` strings)
   to immediately BEFORE the dashboards comment at `:481`. Every
   `note`/`crit` string stays byte-identical; the block moves as one unit.
3. **Net-zero line count is mandatory.**
   `tests/test_daily_ritual_provenance.py:131-142` pins the ABSOLUTE line
   numbers of every mutation verb (asserted at `:370`) and
   `PYTHON_DASH_C_CLASSIFICATION` is line-number-keyed (`:390`); all of those
   sites are after `:507`, so a pure relocation preserves them (the round-2
   and round-3 reviewers executed the move in memory and confirmed both sets
   unchanged and `bash -n` clean). Do not add, remove, or reflow any line
   while relocating the block. Do not touch the pick tracker's isolation
   (`:486-487`) or the terminal status block. `bash -n
   tools/daily_ritual.sh` must pass.
4. Update the pinned order in `tests/test_daily_ritual_provenance.py:233-241`
   (`test_pick_tracker_is_fail_soft_between_board_and_capture_receipt`): the
   assertions become receipt < dashboard < record < evaluate, the fail-soft
   assertions stay, and the test name says "…between board and ritual
   status". `:583-591` (RUNNING at `:143` < capture < terminal < durability)
   and `:745-757` (`STARVED_CRIT=1` sits after the capture call and before
   the `REFUSED` crit) must pass unchanged — the block moves as a unit, so
   they do.
5. Proof: on a fixture root with lane artifacts for session S, running the
   moved block then `attractiveness_dashboard` yields a tracker line citing
   `capture_receipt_S.json` (the newest-on-disk selection at
   `hypothesis_evidence.py:1133` / `:227` needs no change). The pick-tracker
   snapshot binds `reports/schwab_chains/<as_of>/preclose.json`
   (`attractiveness_dashboard.py:5766`; `pick_tracker.py:151-152`), not the
   ritual receipt, so the reorder does not change that binding.

### WP-G — Capture-failure notices age out (DR-8a)

1. Leave `schwab_chain_view.verified_sessions` (`:170-195`) and its return
   shape alone. Inside `_schwab_state_html`
   (`attractiveness_dashboard.py:1050-1093`; sole caller `_chain_age_html` at
   `:1122`, which passes the whole page mapping; spliced near the top of the
   page at `:5651`) compute each failure's age as
   `trading_sessions_between(failure_session, evaluation_session)`
   (`top3_snapshot.py:83-92`; the helper the page already calls at `:1248`;
   `evaluation_date` is set at `:1739`). Predicate: `age >
   config.CHAIN_STALE_BLOCK_SESSIONS` (`config.py:690`, = 3) collapses;
   everything else — including a negative count for a failure dated after
   the evaluation session — keeps the full red notice byte-for-byte
   (`tests/test_attractiveness_dashboard.py:3571-3584` uses age 0 and must
   pass unchanged). Collapsed failures become ONE `notice info` div,
   rendered IN PLACE by the same function (not in the diagnostics drawer —
   the drawer's list is fixed and pinned, see OUT) — `N earlier capture
   session{s} failed verification (2026-08-31, 2026-09-01; older than 3
   sessions); their chains were never used`, pluralized properly like
   `:1128`. **Fail-visible rule:** when the evaluation session is missing or
   unparseable (`:1739` can hand `None`), or `trading_sessions_between`
   raises, EVERY failure keeps the full red notice; the collapse path is
   taken only on a successfully computed age. `CHAINS_ABSENT` handling
   (`:1069-1080`) is unchanged.
2. Disclosure: this narrows the loudness guarantee stated at `:1051-1056` (a
   non-verifying capture "must never degrade quietly") from "forever" to
   "for `CHAIN_STALE_BLOCK_SESSIONS` sessions, then one named line" — say so
   in the PR body; no existing test forbids it (all three reviewers checked).
3. Tests (new): (a) failures at 1 and 5 sessions old → one red notice and
   one collapsed info line naming the old session; (b) missing evaluation
   session → both stay red; (c) a failure dated after the evaluation session
   → stays red.

### WP-H — Job-health digest accepts the sanctioned cache symlink (DR-9)

1. `tools/job_health_digest.py:91-99` `_contained_path` resolves the
   candidate and rejects it unless it sits under `root`. The chain-directory
   block `:524-532` applies it to `.cache/schwab_chains` (the only `.cache`
   reference in the file) and returns the FAILED row DR-9 quotes BEFORE the
   per-symbol loop `:533-542`; the `chain_dir` it produces at `:525` is also
   the third positional argument to `schwab_chain_manifest.verify_session(as_of,
   universe, chain_dir, manifest_path, path)` at `:550`. In the ops checkout
   `.cache` → `~/options-validator/.cache` (sanctioned, load-bearing;
   CLAUDE.md "Worktree location rule").
2. Delete the `_contained_path(root, chain_dir_relative)` call and its
   FAILED row (`:525-532`). In their place compute `cache_root = (root /
   ".cache").resolve()` and `chain_dir = cache_root / "schwab_chains"`. If
   `cache_root` is not an existing directory (dangling symlink, or a symlink
   to a file — both resolve without error and would otherwise surface later
   as the misleading `manifest verification failed: …` built at `:560`),
   return `HealthRow("Schwab preclose", FAILED, f"cache root is not a
   directory: {cache_root}", chain_dir_relative)` before the per-symbol
   loop. Inside the loop use `_contained_path(cache_root,
   f"schwab_chains/{symbol}_{as_of}.parquet")`. `chain_dir` as computed
   above is what continues to be passed to `verify_session(...)` at `:550`;
   that call site is otherwise unchanged. The universe is already pinned
   against `_EXPECTED_SCHWAB_UNIVERSE` before the loop (`:508`), so no new
   traversal is introduced (**Inference**, reviewer-confirmed). Receipts and
   manifests under `reports/` keep strict root containment — the existing
   symlink tests (`tests/test_job_health_digest.py:377-389` manifest,
   `:492-534` fixed receipts, `:604-635` intraday receipt/directory) stay
   green unchanged.
3. Visibility: the `Schwab preclose` HealthRow must report the resolved cache
   root in its reason or receipt-path field (e.g. `chains:
   /Users/…/options-validator/.cache/schwab_chains`), so a `.cache`
   redirected somewhere unexpected is visible in the digest rather than
   silently trusted (no existing test pins the OK reason string).
4. Tests: (a) root whose `.cache` is a symlink to an external directory
   holding valid chains → `Schwab preclose` OK and the row names the resolved
   root; (b) a chain parquet inside that cache directory which is itself a
   symlink to outside the resolved cache root → FAILED with `escapes root`;
   (c) `.cache` dangling → FAILED `cache root is not a directory`; (d)
   `.cache` → a regular file → same.
5. Manual proof (orchestrator/owner, needs the ops checkout):
   `uv run python -m tools.job_health_digest --as-of 2026-09-03 --root
   ~/options-validator-ops --out-dir /tmp/jhd` → the Schwab preclose row reads
   OK for the 15/15 capture (today it reads FAILED; reproduced by all three
   reviewers).

## Acceptance / verification

Done means all of the following, in the implementation worktree
(`.tmp/worktrees/<name>`, never elsewhere):

```bash
uv run python -m unittest discover -s tests                 # offline; exit code is the verdict
uv run ruff check . && uv run pyright                       # both exit 0
bash -n tools/daily_ritual.sh                               # syntax
uv run python -m options_researcher.dashboard               # then inspect .tmp/dashboard/index.html
uv run python -m options_researcher.attractiveness_dashboard  # then inspect .tmp/dashboard/attractiveness.html
```

Post-build assertions on `index.html` (add as tests where marked, otherwise
the PR body quotes the grep): the banner date equals the earliest last-cached
close across `config.UNIVERSE` (WP-A); no `38 shares` (WP-B); no `live,` while
`h7_active` is False (WP-C); one `Study Hall: C` tile (WP-D).
`attractiveness_dashboard` built on a fresh-chain fixture contains zero
occurrences of `, before this ` when closes reach the session, UNCHANGED
`grades` and top-5 order (WP-E), and unchanged event chips on every card
(DR-8b held).

Closure re-verification after implementation: run
`tests/test_h7_schwab_window_registration.py::…::test_feasibility_source_paths_equal_the_recomputed_import_closure`
(`:510-519`; it recomputes the closure from source — importing the frozen
tuple proves nothing) and confirm `git diff --name-only` shares no path with
the tuple. Because no IN file is inside the closure, landing this brief does
not by itself invalidate a qualifying H7 feasibility receipt; landing order
relative to the H7 activation stays the owner's call.

Expected on the first ritual after landing: WP-A/E/F/G change the rendered
board bytes for a session already recorded, so the pick tracker may report
`IMMUTABLE_HISTORY_CONFLICT` (`pick_tracker.py:1470-1476`; handled fail-soft
at `daily_ritual.sh:487`). That is expected and is resolved only by an
owner-directed `--supersede-reason` rerun; the executor must not pass that
flag.

Every constraint above is labelled; anything Codex finds that contradicts a
citation is a STOP-and-report, not a workaround. The implementation PR starts
as a GitHub draft; the executor may not make it ready, merge, sync
`~/options-validator-ops` or `~/options-validator-research`, or touch
`ledger/`. Green checks are review evidence for the owner, not landing
authority.
