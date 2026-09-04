# Codex brief 37 — Dashboard presentation fixes from the 2026-09-04 review

**Date:** 2026-09-04 (rev 2; rev 1 reviewed FAIL — `reports/2026-09-04-brief-37-adversarial-review-round1.md`, all 22 findings applied)
**Author:** Claude (orchestrating session; options-validator status + dashboard review, 2026-09-04)
**Executor:** Codex (Sol, high reasoning — the executor tier used for brief 07; owner may substitute at dispatch)
**Status:** DRAFT — pending independent adversarial review (round 2) before hand-off
**Provenance:** file:line constraints below are Repo-verified against origin/main
@039d76e unless a sentence carries its own label. "Test-verified" observations
were taken read-only from the ops execution checkout's 2026-09-04 09:12 ET build
(`~/options-validator-ops/.tmp/dashboard/{index,attractiveness}.html`) and its
ritual log `.tmp/daily_ritual/2026-09-04_0909.log`. Sentences labelled
**Inference** are the author's reading of the code, not a file fact.

## Why this exists (plain language)

The 2026-09-04 review opened both dashboards the morning after the 2026-09-03
intraday-capture fix (`reports/2026-09-03-attractiveness-scanner-pm-evaluation.md`
§3) and found the board FRESH for the first time since July: 13 of 18 names on
the 2026-09-03 Schwab 15:45 chains, top-5 shortlist filled. Reading the two
pages as a portfolio manager surfaced nine defects that make the pages say
things that are false, stale, or repeated. This brief is the finding record
(there is no earlier receipt for these items) and the hand-off in one document.
Every work package is presentation or plumbing; the one item that would touch
the ranking (DR-5, and the badge half of DR-6) is withheld for an owner ruling.

| ID | Page | What the page says today (Test-verified 2026-09-04) | Why it is wrong |
|---|---|---|---|
| DR-1 | Mission Control | "VST — Held — 38 shares, no options" | `data/positions/holdings.csv:2` says 39; the text is a constant at `options_researcher/dashboard.py:223` |
| DR-2 | Mission Control | banner "DATA AS-OF 2026-06-30 CLOSE" | the as-of lookup is capped at `config.BACKTEST_END` (`config.py:81`, "2026-06-30"); closes run through 2026-09-03 (ritual log `max_dates`, same morning) |
| DR-3 | Mission Control | "H7 FORWARD WINDOW (live, scores once 2026-10-26)" | that window (`h7-forward-15-v1`) is PAUSED per OD-3 (`PROJECT_STATE.md:38-39`, 2026-08-02 close-out: "H7 will not restart now; any later restart requires a new registration and namespace"); the ritual prints "H7 lanes: PAUSED" the same morning (`tools/daily_ritual.sh:266`) |
| DR-4 | Mission Control | Achievements: "Study Hall: A" ×8, B ×8, C ×18, D ×8, E ×16 | one tile is appended per matching `ledger/facts.log` line (`dashboard.py:192-197`) |
| DR-6 | Attractiveness board | every Schwab-sourced name: "Unavailable for this session — rv21: underlying closes end 2026-09-03, before this 2026-09-03 session" (174 copies) | the sentence is self-contradictory. The Schwab branch sets `rv21`/`iv_minus_rv` to NaN unconditionally (`attractiveness_dashboard.py:1965-1966`). **Inference:** the branch comment ("the closes store ends earlier") describes a state that no longer holds — the ritual refreshes closes (`daily_ritual.sh:290`) before the dashboards build (`:483`). Effect: the price ladder and move bands are empty on all 13 fresh names, and the cushion and vol-premium badges read UNKNOWN |
| DR-7 | Attractiveness board | Registered-bets tracker cites `reports/ritual/capture_receipt_2026-09-02.json` (50 citations) on the 2026-09-04 build | `tools/daily_ritual.sh` builds both dashboards (`:483-484`) BEFORE it writes the capture receipt (`:492-507`), and the tracker takes the newest receipt on disk (`hypothesis_evidence.py:1133` glob, max-by-date at `:227`) |
| DR-8a | Attractiveness board | two red notices "Schwab capture session 2026-08-31 / 2026-09-01 FAILED verification" | `schwab_chain_view.verified_sessions` (`:170-195`) returns every failed receipt on disk with no age limit and `_schwab_state_html` (`:1050-1095`) prints each one forever |
| DR-8b | Attractiveness board | the identical "EVENT · CAL · fomc meeting · FOMC decision · 2026-09-16 …" chip on all 5 picks, all 5 context picks and both core cards (12 copies above the fold) | `_event_chips_html` (`:3014-3028`) is called per card (`:3227`, `:3908`, `:4463`, `:4647`) with no section-level dedupe |
| DR-9 | Job-health digest | "Schwab preclose — FAILED — receipt path escapes root — .cache/schwab_chains" for the 2026-09-03 capture that verified 15/15 (reproduced by the round-1 reviewer) | `_contained_path` (`tools/job_health_digest.py:91-99`) resolves symlinks; the ops checkout's `.cache` is a SANCTIONED symlink to the main checkout's `.cache` (CLAUDE.md "Worktree location rule"; `ls -la ~/options-validator-ops/.cache` Test-verified) |

**Held for an owner ruling, NOT in this brief (recorded so it is not lost):**

- **DR-5** — the GREEN-fraction ranking divides by the number of checks per
  lane (`options_researcher/display_rank.py:18-19`), so a 4-check long call
  beats an 8-check put with one AMBER. Changing that is a change to the
  frozen baseline recipe.
- **DR-5b** — on Schwab-sourced cards the `cushion` badge (from `rv21`,
  `attractiveness.py:189-201`) and the `vrp_for_seller` badge (from
  `iv_minus_rv`, `:203`) are UNKNOWN because the inputs are NaN. Both badges
  are members of `grades`, which is what `display_rank.py:18-19` ranks on, so
  restoring them reorders the top 5 and the pick-tracker arms. Whether Schwab
  cards may grade those two badges is therefore the same class of decision as
  DR-5 and is left to the owner. WP-E below restores the display fields only.

## Scope

**IN:** `options_researcher/dashboard.py`,
`options_researcher/attractiveness_dashboard.py`, `tools/daily_ritual.sh`,
`tools/job_health_digest.py`, and their tests (`tests/test_dashboard.py`,
`tests/test_attractiveness_dashboard.py`, `tests/test_attractiveness_layout.py`,
`tests/test_daily_ritual_provenance.py`, `tests/test_job_health_digest.py`).

**OUT (hard):**
- No edit to any member of `FEASIBILITY_SOURCE_PATHS` (frozen literal tuple,
  `options_researcher/h7_schwab_window_registration.py:143-194`, 50 files;
  owner ruling 1 of `reports/2026-09-03-brief-36-owner-rulings.md`).
  Test-verified 2026-09-04 (and re-verified by the round-1 reviewer): the four
  IN files and `options_researcher/{portfolio,hypothesis_evidence,schwab_chain_view,top3_snapshot}.py`
  and `data/ritual_authority.py` are OUTSIDE the closure;
  `options_researcher/features.py` and `data/underlying_closes.py` are INSIDE
  it and may only be imported, never modified. Do not add an import of any
  H7/activation module into the IN files.
- No change to `options_researcher/display_rank.py`, to any badge grade, to
  the `grades` inputs of any card, or to any ranking, signal, or constant
  with owner provenance (DR-5 / DR-5b are owner rulings).
- No ledger write, no registration, no authority flip, no live-order path, no
  paper-book mutation, no change to `config.py`.
- No launchd / plist change (the unloaded `research-refresh` LaunchAgent is an
  ops action for the owner, not code).
- No visual redesign (theme, KPI tiles, name table, charts) — a separate brief
  once the owner picks a direction.
- In `tools/daily_ritual.sh`: no change to the pick tracker's fail-soft
  isolation (`:486-487`), to the `RITUAL_TERMINAL_STATUS` block and its
  `ritual_status` call (they stay after the capture receipt and before Step 8
  DURABILITY, `:528+`; pinned at `tests/test_daily_ritual_provenance.py:588-591`),
  or to any `note`/`crit` string (tests pin them).
- No change to the ThetaData-sourced branch of the board.

## Work packages

### WP-A — Mission Control as-of banner and sparklines follow the real closes (DR-2)

1. `dashboard.py:124-145` `_default_data_as_of` and `:112-122`
   `_default_closes` both call `load_closes(sym, config.BACKTEST_START,
   config.BACKTEST_END, allow_oos=True)`. `load_closes` slices
   `.loc[start:end]` (`data/underlying_closes.py:57-59`) and gates only on
   `end > IN_SAMPLE_END` without `allow_oos` (`:53-56`). **Inference:** an
   END bound past the store's last row is therefore safe and returns what
   exists — prove it with the test in step 3.
2. Replace the END bound in BOTH helpers with the build date in the repo's
   NY-date convention (an `America/New_York`-zoned `date`, or an injected
   `today` parameter for tests — never bare `date.today()`, which is local).
   The banner VALUE must remain the series index (earliest last-cached date
   across `config.UNIVERSE`, docstring `:125-131`), never the clock —
   `tests/test_dashboard.py:131-176` stay green unchanged (they patch the
   loader by module attribute and ignore call arguments).
3. Add tests: a series whose last index is after `BACKTEST_END` reports that
   later date; sparklines take the last 60 rows of the same extended range.

### WP-B — VST share count comes from the holdings file (DR-1)

1. `dashboard.py:219-225` `_PARTY` carries the role text as a constant
   (`"Held — 38 shares, no options"` at `:223`). Keep `_PARTY` for symbol and
   accent colour only; derive the role line for held names inside
   `assemble()` so `render()` stays pure.
2. Read shares through the existing fail-loud loader
   `options_researcher.portfolio.load_holdings()` (`portfolio.py:77-96`,
   `HOLDINGS_PATH` at `:25`; already the board's reader at
   `attractiveness_dashboard.py:1788-1794`). Role text: `Held — {shares}
   shares` plus `, no options` when the book (`assemble()`'s `book["marks"]`)
   has no open mark for that symbol, else `, {n} open option mark(s)`.
3. Fail-visible, never the old constant: catch exactly `(OSError,
   ValueError)` — the loader raises `FileNotFoundError` and `ValueError`
   (`portfolio.py:79-94`) and the house pattern is a named tuple with
   everything else crashing loudly (`dashboard.py:173-176`); a bare `except
   Exception` is a review reject. On those two, render `Held — shares UNKNOWN
   (holdings.csv unreadable)` and print the error to stderr like the
   entry-watch path does (`:176-177`).
4. Tests: 39 from a temp holdings file; unreadable file → the UNKNOWN text;
   an assertion that the literal `38 shares` no longer exists in the module.

### WP-C — The H7 panel may only say "live" when H7 authority is granted (DR-3)

1. `dashboard.py:398-425` `_h7_window_panel` prints `(live, scores once …)`
   (`:413`) from `h7_window_status.window_status()`
   (`h7_window_status.py:21-70`), which reads the append-only store
   `REAL_FORWARD_STORE` (`:14-18`) and knows nothing about authority.
2. Authority truth is `data/ritual_authority.py`: `CURRENT_AUTHORITY`
   (`:38-46`) with `h7_active=False` at `:39`, and `evaluate_full_ritual()`
   (`:69-84`) which aggregates THREE flags and appends the H7 blocker "H7
   forward-paper authority is paused; no active namespace exists." at `:83`.
   Because it aggregates, do NOT key the H7 wording on its `ready` field.
   `assemble()` attaches `h7_authority = {"h7_active":
   CURRENT_AUTHORITY.h7_active, "blockers": [b for b in
   evaluate_full_ritual().blockers if "H7" in b]}` (**Inference:** both
   calls are pure dataclass evaluation with no I/O — the round-1 reviewer
   confirmed no side effects) and `render()` passes it to the panel.
3. Panel behaviour: when `h7_active` is False, the heading is
   `H7 FORWARD WINDOW — PAUSED (H7 authority not granted)` followed by the
   H7 blocker sentence verbatim; the counts line (`dashboard.py:414-422`,
   including `entries taken: {n}`) is emitted byte-identical, prefixed by
   the label `registered window (paused; scores nothing while paused)`; the
   word "live" must not appear anywhere in the panel. When `h7_active` is
   True, the current wording is kept unchanged. If the store is unavailable
   the existing UNAVAILABLE branch (`:400-405`) still wins.
4. Tests, both directions: inject `h7_active=False` with the blocker →
   PAUSED text and `entries taken: 0` present, `live` absent; inject
   `h7_active=True` → `live` present. Update `tests/test_dashboard.py:38-77`
   to pass `h7_authority=` explicitly so neither existing test depends on the
   live `CURRENT_AUTHORITY` value (`:65` asserts `entries taken: 0`).

### WP-D — One achievement tile per tag (DR-4)

1. `dashboard.py:192-197` appends a tile for every `facts.log` line whose tag
   is in `ACHIEVEMENTS` (`:46-82`; the per-symbol study tags `STUDY_A..E` at
   `:77-81` match dozens of lines — 18 `STUDY_C` lines today).
2. Collapse to one tile per tag, first-occurrence order preserved, with a
   `×N` count suffix in the title when N > 1 (`_achievements_grid`,
   `:373-390`). The Graveyard list is untouched.
3. Tests: the existing fixture (`tests/test_dashboard.py:8-22`, one `STUDY_C`
   line) stays valid; three `STUDY_C` lines → exactly one tile whose title
   ends in `×3`.

### WP-E — Realized volatility for the DISPLAY fields of Schwab-sourced sections (DR-6, display half only)

1. `attractiveness_dashboard.py:1964-1975`: the Schwab branch sets
   `rv21 = nan`, `iv_minus_rv = nan` and records the gap sentence at
   `:1972-1973` unconditionally. The branch already holds `adjusted_closes`
   through `day` (`:1943-1944`) and computes `atm_iv` from the fresh chain
   (`:1971`). `rv21` feeds the price ladder and move bands
   (`_price_ladder`, `:120-124`; `:237-247`), which are display-only, AND the
   `cushion` / `vrp_for_seller` badges (`attractiveness.py:189-203`), which
   are ranking inputs (DR-5b).
2. Timing (**Inference**, disclosed): the chain is a 15:45 ET snapshot
   (docstring `:1931-1936`); the session's official close prints at 16:00,
   after the capture instant. To keep every input at or before the capture
   instant (`.cursorrules` NO LOOK-AHEAD), compute `rv21` from
   `adjusted_closes` restricted to index STRICTLY BEFORE `day` — the last
   close before the capture — never the session's own close.
3. Formula, byte-for-byte the feature builder's: `np.log(closes).diff()
   .rolling(features.RV_WINDOW).std(ddof=1) * np.sqrt(252.0)`
   (`options_researcher/features.py:23`, `:50-51`), taking the last value.
   Import `RV_WINDOW` from `features.py`; do NOT modify that file (closure
   member). Use `adjusted_closes` — the only series a trailing signal may
   consume (`data/underlying_closes.py:49-52`, `:86-93`).
   `iv_minus_rv = atm_iv - rv21` exactly as `features.py:70`, for DISPLAY
   provenance only (see step 5).
4. Availability rule, fail-closed: compute only when the strictly-before
   series has at least `RV_WINDOW + 1` rows AND its last index is no more
   than `config.CHAIN_STALE_BLOCK_SESSIONS` (`config.py:690`, = 3;
   LLM-asserted per the PM evaluation §1) sessions before `day`, counted with
   `options_researcher.top3_snapshot.trading_sessions_between`
   (`top3_snapshot.py:83-92`; weekday count, holidays counted as sessions —
   the helper the page already uses at `attractiveness_dashboard.py:1246`).
   Otherwise keep NaN and record a gap sentence that is TRUE, naming the
   actual last close date and the session (e.g. `underlying closes end
   2026-08-28; the last close before this 2026-09-03 session is 4 sessions
   old`). The current sentence must never be emitted when the two dates are
   equal.
5. **The badges do not change.** The `grades` dict passed to the card
   builders for Schwab-sourced cards must continue to receive NaN for
   `rv21` and `iv_minus_rv` (so `cushion` and `vrp_for_seller` stay UNKNOWN
   exactly as today) until the owner rules DR-5b. Only the display consumers
   (`_price_ladder` and the provenance/"Unavailable" sentences) receive the
   computed value. Add a provenance sentence on the card: `realized vol
   (rv21) through {last_close_date}, the last close before the 15:45
   capture; not used for grading on this data source`.
6. Keep `iv_rank` / `iv_rank_preview` handling (`:1967-1970`) unchanged; set
   `features_source` to `schwab_preclose_session+closes_through_<last_close_date>`
   when rv21 is computed.
7. Tests: (a) parity — on a split-free synthetic close series the branch's
   rv21 equals `features.build_daily_features(...)["rv21"]` at the same date
   (import only); (b) closes 4 sessions old → NaN and the new true sentence;
   (c) closes reaching the prior session → finite rv21 for the ladder and no
   self-contradictory sentence; (d) **ranking pin:** on a fresh-chain fixture
   the `frozen_baseline` candidate ordering and the `grades` of every card
   are byte-identical before and after this WP; (e) the two badges still
   read UNKNOWN on a Schwab-sourced card.
8. Report, do not fix (closure file; **Inference**): `features.py:121` passes
   RAW `load_closes` into the rv21 computation, which
   `data/underlying_closes.py:49-52` forbids for trailing signals. Impact is
   confined to rows within `RV_WINDOW` sessions of a split boundary
   (`SPLITS`, `data/underlying_closes.py:208-214`, latest 2025-12-18), so no
   current board session is affected. Record it in the PR body for the owner;
   the parity test in (7a) must use a split-free series.

### WP-F — Write the capture receipt before the dashboards are built (DR-7)

1. `tools/daily_ritual.sh:481-484` rebuilds both dashboards, `:485-490` runs
   the pick tracker, `:492-507` writes the per-hypothesis capture receipt
   (`options_researcher.ritual_receipt`, output
   `reports/ritual/capture_receipt_<as_of>.json`, `ritual_receipt.py:448`;
   the closing `fi` of the block is `:507`), and the `RITUAL_TERMINAL_STATUS`
   block follows.
2. `ritual_receipt` reads only lane artifacts written earlier in the script
   (`ritual_receipt.py:117-300`: `reports/h5`, `reports/h6_forward`,
   `reports/h7_*`, `reports/h8_forward`, `reports/h10`). **Inference:**
   nothing produced by the dashboards or the pick tracker is read by it, and
   nothing between `:483` and `:492` sets a variable the receipt block reads
   (both confirmed by the round-1 reviewer). Move the whole capture-receipt
   block (`:492-507`, including the `STARVED_CRIT=1` line and both `crit`
   strings) to immediately BEFORE the dashboards comment at `:481`. Every
   `note`/`crit` string stays byte-identical; the block moves as one unit.
3. **Net-zero line count is mandatory.**
   `tests/test_daily_ritual_provenance.py:131-142` pins the ABSOLUTE line
   numbers of every mutation verb (asserted at `:370`) and
   `PYTHON_DASH_C_CLASSIFICATION` is line-number-keyed (`:390`); all of those
   sites are after `:507`, so a pure relocation preserves them. Do not add,
   remove, or reflow any line while relocating the block. Do not touch the
   pick tracker's isolation (`:486-487`) or the terminal status block.
   `bash -n tools/daily_ritual.sh` must pass.
4. Update the pinned order in `tests/test_daily_ritual_provenance.py:233-241`
   (`test_pick_tracker_is_fail_soft_between_board_and_capture_receipt`): the
   assertions become receipt < dashboard < record < evaluate, the fail-soft
   assertions stay, and the test name says "…between board and ritual
   status". `:583-591` (RUNNING < capture < terminal < durability) and
   `:745-757` (`STARVED_CRIT=1` sits after the capture call and before the
   `REFUSED` crit) must pass unchanged — the block moves as a unit, so they do.
5. Proof: on a fixture root with lane artifacts for session S, running the
   moved block then `attractiveness_dashboard` yields a tracker line citing
   `capture_receipt_S.json` (the newest-on-disk selection at
   `hypothesis_evidence.py:1133` / `:227` needs no change). The pick-tracker
   snapshot binds `reports/schwab_chains/<as_of>/preclose.json`
   (`attractiveness_dashboard.py:5766`; `pick_tracker.py:151-152`), not the
   ritual receipt, so the reorder does not change that binding.

### WP-G — Capture-failure notices age out; one event chip per section (DR-8)

1. (a) Leave `schwab_chain_view.verified_sessions` (`:170-195`) and its
   return shape alone. In `_schwab_state_html`
   (`attractiveness_dashboard.py:1050-1095`) partition `failures` by age
   against the board's evaluation session using
   `top3_snapshot.trading_sessions_between` (`:83-92`, the helper used at
   `:1246`) and the existing constant `config.CHAIN_STALE_BLOCK_SESSIONS`
   (`config.py:690`, = 3). Failures within that window keep today's red
   notice byte-for-byte (`tests/test_attractiveness_dashboard.py:3571-3584`
   uses age 0 and must pass unchanged). Older failures collapse into ONE
   info notice — `N earlier capture session(s) failed verification
   (2026-08-31, 2026-09-01; older than 3 sessions); their chains were never
   used` — rendered inside the Diagnostics & provenance drawer, never
   silently dropped. **Fail-visible rule:** when the evaluation session is
   missing or unparseable (`:1739` can hand `None`), EVERY failure keeps the
   full red notice; the collapse path is taken only on a successfully
   computed age. `CHAINS_ABSENT` handling (`:1069-1080`) is unchanged.
   Disclosure: this narrows the loudness guarantee stated at `:1051-1056`
   (a non-verifying capture "must never degrade quietly") from "forever" to
   "for `CHAIN_STALE_BLOCK_SESSIONS` sessions, then one named line" — say so
   in the PR body; no existing test forbids it (round-1 reviewer checked).
2. (b) In the rule-based shortlist (`_original_hero_html`, `:4099-4174`,
   which calls `_hero_pick_html`, `:3877-3928`, at `:4140`) and the
   context-lane section (`_context_lane_html`, `:4417+`), compute every
   card's event chips first. If all cards in the section produce an
   identical chip list, emit that list ONCE as a section-level
   `.event-chips` line directly under the section header and pass a flag
   into `_hero_pick_html` (and the context-lane card builder) to omit the
   per-card copies; otherwise keep per-card chips exactly as today. Chip
   text is unchanged. Symbol panels (`:3227`) and core cards (`:4647`) are
   untouched. Note for the reader: the dedupe fires only when every card's
   chip list matches — true on the 09-04 build (5/5 identical in both
   sections) and inert on a mixed-expiry day; that is by design, not a
   regression.
3. Tests (all new — no existing test asserts on `.event-chips`): (a)
   failures at 1 and 5 sessions old → one red notice and one collapsed info
   line naming the old session; (b) missing evaluation session → both stay
   red; (c) five picks sharing one FOMC chip → the chip text occurs once
   inside the shortlist section; (d) two picks with different chips →
   per-card chips.

### WP-H — Job-health digest accepts the sanctioned cache symlink (DR-9)

1. `tools/job_health_digest.py:91-99` `_contained_path` resolves the
   candidate and rejects it unless it sits under `root`; `:524-531` applies
   that to `.cache/schwab_chains` (the only `.cache` reference in the file),
   and `:533-541` to each chain parquet. In the ops checkout `.cache` →
   `~/options-validator/.cache` (sanctioned, load-bearing; CLAUDE.md
   "Worktree location rule").
2. Contain CHAIN files within the RESOLVED cache root: `cache_root = (root /
   ".cache").resolve()`, then `_contained_path(cache_root,
   f"schwab_chains/{symbol}_{as_of}.parquet")`. The universe is already
   pinned against `_EXPECTED_SCHWAB_UNIVERSE` before the loop (`:508`), so no
   new traversal is introduced (**Inference**, reviewer-confirmed). Receipts
   and manifests under `reports/` keep strict root containment — the
   existing symlink tests (`tests/test_job_health_digest.py:377-389` manifest,
   `:492-534` fixed receipts, `:604-635` intraday receipt/directory) stay
   green unchanged.
3. Visibility: the `Schwab preclose` HealthRow must report the resolved cache
   root in its reason or receipt-path field (e.g. `chains: /Users/…/options-validator/.cache/schwab_chains`),
   so a `.cache` redirected somewhere unexpected is visible in the digest
   rather than silently trusted.
4. Tests: (a) root whose `.cache` is a symlink to an external directory
   holding valid chains → `Schwab preclose` OK and the row names the resolved
   root; (b) a chain parquet inside that cache directory which is itself a
   symlink to outside the resolved cache root → FAILED with `escapes root`.
5. Manual proof (orchestrator/owner, needs the ops checkout):
   `uv run python -m tools.job_health_digest --as-of 2026-09-03 --root
   ~/options-validator-ops --out-dir /tmp/jhd` → the Schwab preclose row reads
   OK for the 15/15 capture (today it reads FAILED; reproduced by the round-1
   reviewer).

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
`attractiveness_dashboard` built on a fresh-chain fixture shows a populated
price ladder, no self-contradictory "Unavailable" sentence, UNCHANGED grades
and top-5 order (WP-E), and one FOMC chip in the shortlist section (WP-G).

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
