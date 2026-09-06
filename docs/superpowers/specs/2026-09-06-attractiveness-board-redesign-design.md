# Attractiveness board redesign — design spec

**Date:** 2026-09-06
**Status:** APPROVED AS WRITTEN — owner review 2026-09-06 (in chat, after the spec was read); implementation plan and Codex brief 39 follow
**Author:** Claude (orchestrating session), from a brainstorming dialogue with the
owner on 2026-09-06 (every design decision below cites the owner's answer).
**Baseline:** origin/main @f83428d (PR #156 landed; brief 37's fixes are in).
**Mockup of the approved first screen:**
`docs/superpowers/specs/assets/2026-09-06-board-redesign-option-a-v2.html`
(zero-JS static page built from the real Friday 2026-09-04 board data; open it in
a browser). Throwaway generator lives in gitignored `.tmp/redesign-mockups/`.

## 1. Purpose and the decisions that shape it

The attractiveness board (`options_researcher/attractiveness_dashboard.py`,
771 KB / 30 headings / 362 fold-outs / ~19 screens on 2026-09-04) is honest
but not usable in one sitting. The owner's brief, verbatim intent: "less long
and easier to read"; "I want the top picks always displayed at the top";
"if several factors share a pick in common … could prove it could be best";
"I only want the 5 best picks out of each experiment — don't show the other
names if they aren't better than another".

Owner decisions taken 2026-09-06 (in chat, one at a time):

| # | Question | Decision |
|---|---|---|
| D1 | One question the first screen must answer | "Is there a trade worth taking today?" — shortlist-first; design and test against a populated board (Friday 2026-09-04, five qualifying picks) |
| D2 | JavaScript policy | Keep zero-JS (tested contract `tests/test_attractiveness_layout.py:497`) |
| D3 | Scope | The attractiveness board only; Mission Control untouched |
| D4 | Keep on page | Context lane; diagnostics drawer. Remove: 18-row composite table (becomes a top-5 column), per-name panels for all 18 names (details only for names on the table) |
| D5 | Which lanes get a top-5 slot | Rule-based baseline (registered, always), context lane, composite, QM movement, and the four parking-lot experiments (beta-to-QQQ, tail shape, spread stability, T-bill carry) |
| D6 | Lanes without a natural "best" | Show the names each lane FLAGS, capped at 5 — membership, not an invented ranking |
| D7 | First-screen direction | Option A: one agreement table (names × lanes) |
| D8 | Agreement count | Favourable lanes only; cautions shown separately and never counted |
| D9 | Pick-tracker scoreboard | Moves into the diagnostics drawer (owner chose "continue" over keeping it in the main flow) |

Design classification: architectural (restructures how the page's components
fit together and re-pins two test contracts). Implementation is delegated to
Codex through a brief (CLAUDE.md division of labor); this spec is the owner's
review artifact.

## 2. Page structure (top to bottom)

1. **Status strip** — one line, five facts, each a coloured dot plus a word:
   option-quote source and session; closes date; fresh vs stale names (stale
   named); research-annotation age; capture failures in the retention window.
   Same facts as today's freshness block, one line instead of eight plus six
   notices; the per-notice detail moves into the diagnostics drawer.
2. **Position tiles** — four stat tiles: open option (H6-0001), last mark
   (red when older than the registered exit rule allows), shares, the one
   event ahead. Same sources as today's registered-bets tracker
   (`load_open_positions`, the H6 receipt date). The per-hypothesis tracker
   lines move into the drawer.
3. **Agreement table** — the decision area (§3).
4. **One event line** — the union of upcoming calendar events for the names
   on the table, printed once (today the identical FOMC chip prints twelve
   times above the fold).
5. **Pick details on demand** — one closed `<details>` per name on the
   table, holding what today's per-name panel holds (gate checks, ladder,
   bull/base/bear table, event chips). Nothing is rendered for names not on
   the table.
6. **Diagnostics & provenance drawer** — unchanged six sections
   (`_diagnostics_drawer_html`, pinned by `tests/test_attractiveness_layout.py:405`)
   plus the relocated freshness notices, the per-hypothesis tracker lines and
   the pick-tracker scoreboard (D9), closed by default.
7. **Disclaimers and footer** — every existing disclaimer string verbatim
   (`test_disclaimers_are_present_verbatim`), including the sentence that
   this page and Mission Control date independently.

Removed from the page (content, not data): the 18-row composite table, the
18 per-name panels, the five context-lane cards and their comparison table,
the QM hero cards, the core-names VST/AMZN strip (pinned names become table
rows marked "pinned"), the repeated event chips, and the sticky symbol nav
(the table is the index).

## 3. The agreement table

**Rows.** Every symbol that appears in any lane's capped list, plus the
owner-pinned names (VST, AMZN — always shown, 2026-07-16 ruling). Order: the
five registered picks in their registered order first; then the remaining
names by favourable count descending, then symbol. On Friday's data that is
14 rows.

**Columns.**

| Group | Column | Kind | What the cell shows | Cap |
|---|---|---|---|---|
| — | Name | — | symbol, `pinned` mark when owner-pinned | — |
| — | Registered pick | — | the baseline headline + cost, worst case, breakeven, expiry (DTE), `details` link; or "not in the registered top 5"; a DATA_BLOCKED name shows its block reason here | — |
| Favourable | Rule-based | ranking | `#rank` | `PICK_TOP_N` |
| Favourable | Context | ranking | `#rank`, or `veto` when the lane vetoed the baseline pick | `PICK_TOP_N` |
| Favourable | Composite | ranking (by aligned-angle count) | `grade · n/4` | `PICK_TOP_N` |
| Favourable | QM movement | ranking (mechanical picks, existing selector) | `#rank` | `PICK_TOP_N` |
| Favourable | T-bill carry | describing (`ABOVE_TBILL`) | `✓ carry_spread` | `PICK_TOP_N` |
| — | Agree | — | `k/m` favourable lanes agreeing, with a thin bar; m = READY favourable lanes | — |
| Caution | Spread stability | describing (`ELEVATED`) | `! ratio` | `PICK_TOP_N` |
| Caution | Tail shape | describing (`UNSTABLE`) | `! jump_count` | `PICK_TOP_N` |
| Caution | Beta to QQQ | describing (`UNSTABLE`) | `!` | `PICK_TOP_N` |

Every column header carries: lane title, lane kind (registered baseline /
display-only / gated study / experiment), as-of session, state.

**Rules.**
- The registered baseline (`select_top_picks`, `display_rank.py`) decides row
  order and is never re-ordered by any other lane. Its grades and its
  candidates are byte-identical before and after this change (tested, §8).
- "Agree" counts favourable lanes only (D8). It is a description of
  membership, never a score, never a signal, never an input to any ranking,
  registration, verdict, FIRE path, or the paper book. The RQ2/A2 studies
  remain the only path to a scored combination.
- Ranking lanes are capped at `config.PICK_TOP_N` (owner-directed 2026-08-25).
  Composite's top 5 is by `aligned_count` descending; ties are broken by
  baseline row order, then symbol (deterministic).
- Describing lanes list the names in their flag state (D6). When more than
  `PICK_TOP_N` names are flagged, the five shown are those with the largest
  value of the lane's own metric (`carry_spread`, `ratio`, `jump_count`);
  beta has no ordering metric and shows the first five by symbol. This
  direction is an LLM-proposed display rule (2026-09-06), stated in the
  column header, and carries no other meaning.
- Caution flags are shown but never counted (D8): spread `ELEVATED`, tail
  `UNSTABLE`, beta `UNSTABLE`.
- The context lane's `VETOED` mark is a caution on the favourable side: it
  shows in the Context column as `veto` and does not count as agreement.

## 4. Architecture

**New pure module `options_researcher/board_lanes.py`.** No file, network or
clock access; every input is passed in. It exposes:

```
LaneMember(symbol, label, value, rank)
LaneColumn(key, title, kind, favourable, state, as_of, members, note)
BoardRow(symbol, pinned, baseline_pick, marks: dict[key, LaneMember], fav_count, fav_ready)
LaneBoard(columns, rows, event_line, notes)
build_lane_board(*, baseline_picks, context_rows, composite_cards, qm_picks,
                 experiment_lanes, pinned, cap, board_as_of) -> LaneBoard
```

`build_lane_board` never raises on a bad lane: a lane whose input is `None`
or carries `state != READY` becomes a column with that state, no members, and
is excluded from `fav_ready`.

**Data flow.** All inputs exist today:

| Input | Source (unchanged) |
|---|---|
| baseline picks | `select_top_picks(data)` |
| context rows | `_context_lane_selection(data)["rows"]` |
| composite cards | `data["composite_signals"]` |
| QM picks | `select_qm_top_picks(data, qm_context, include_csp_watch=True)` |
| experiment lanes | `experiments_dashboard.build_experiment_lanes(symbols, asof=data_as_of)` — computed in the board's gather step from cached data with the board's own as-of (the research-display-refresh job publishes the standalone experiments page at 09:50 ET, after the 09:09 board build, and only as HTML; the board therefore computes rather than reads). Injectable through `assemble(experiment_lanes=…)` so tests stay hermetic. |
| positions, freshness, events | as today |

**Renderer.** `attractiveness_dashboard.render` gains `_status_strip_html`,
`_position_tiles_html`, `_agreement_table_html(board)`,
`_event_line_html(board)`, and `_pick_details_html(rows)` (which calls the
existing per-symbol panel builder only for names on the table), and stops
calling the removed section builders. The picks snapshot writer
(`_selection_snapshot`, schema `picks_snapshot/v1`), the source-row hashes,
and the HTML digest comment are untouched; the pick tracker keeps recording
the baseline and context arms exactly as today.

**Constants** (both LLM-proposed 2026-09-06, labelled as such in `config.py`,
no numeric value new — the cap reuses `PICK_TOP_N`):
- `BOARD_LANES_ENABLED: bool = True` — switch for the lane board layout;
  `False` renders today's layout byte-for-byte (rollback path).
- `BOARD_FAVOURABLE_LANES = ("baseline", "context", "composite", "qm", "tbill")`
  and `BOARD_CAUTION_LANES = ("spread", "tail", "beta")` — the D8
  classification. Changing the set is an owner decision.

The four experiments' own flags stay disabled for the standalone experiments
page; the board's use of their lane builders is an owner-directed display
decision (D5, 2026-09-06) and does not promote any experiment beyond
experimental status (2026-08-09 authorization: promotion needs a separate
owner decision — none is implied here).

**Zero JavaScript (D2).** Folding is native `<details>`; the agreement bar is
an inline `<span>` width; the optional payoff sketch inside a pick's details
is inline SVG. No script tags, no external assets.

## 5. Fail-visible rules

- Every lane has a state (`READY`, `FAILED:<ExceptionName>`, `DISABLED`,
  `UNAVAILABLE:<reason>`). A non-READY lane keeps its column, its header
  prints the state, its cells are blank, and it leaves the denominator: a row
  then reads e.g. `3/4` with the header explaining why m is 4, never a
  silently smaller count.
- Baseline open slots keep today's consolidated "intentional open slot"
  notice (`_open_slots_html`) directly above the table; rows show only real
  picks.
- A DATA_BLOCKED or stale name is never promoted by another lane: its pick
  cell shows the block reason; other lanes' marks still render.
- Composite ties and describing-lane overflow are deterministic (§3).
- Every column carries its as-of; a lane whose as-of differs from the board's
  chain session is marked in the header, as the page does today.
- If `build_lane_board` itself raises (a bug), the page renders a loud
  `LANE BOARD FAILED — <ExceptionName>` notice in place of the table and
  falls back to the baseline pick cards, so a defect can never blank the
  decision area.

## 6. Invariants that must survive (tested)

1. `select_top_picks(data)` output and `picks_snapshot.json` are
   byte-identical before and after (ranking untouched; DR-5/DR-5b stay held).
2. Every card's `grades` unchanged; no badge, signal, or constant with owner
   provenance changes.
3. The HTML digest comment and `source_row_hashes` round-trip as today.
4. Every disclaimer string verbatim; the "two dashboards date independently"
   sentence verbatim.
5. Diagnostics drawer keeps its six sections in order (new items append).
6. Owner-pinned VST/AMZN always visible.
7. DATA_BLOCKED / stale names remain fail-visible.
8. No ledger write, no registration, no authority flip, no live-order path,
   no paper-book mutation, no network or provider call, no `config.py` value
   with owner provenance touched.

## 7. Contracts that change (and why)

- **Layout contract** (`tests/test_attractiveness_layout.py`): section
  order, one-line panel summaries, sticky nav, composite-as-one-table, core
  names in main flow. Re-pinned to §2. The drawer, disclaimer, digest and
  zero-JS tests stay.
- **Event-chip parity** (`tests/test_event_awareness.py:311`
  `test_populated_hero_lane_context_and_pinned_surfaces_share_exact_chip_list`):
  the hero, context and pinned card surfaces no longer exist. New contract:
  every per-name details fold-out renders the same chip list the symbol panel
  did, and the single event line is exactly the sorted union of the table
  names' chips. This is the DR-8b renegotiation brief 37 deferred.

## 8. Testing and acceptance

- **Unit (pure module):** caps; favourable-only counting; cautions never
  counted; veto not counted; composite tie order; describing-lane overflow
  order; failed lane keeps its column and leaves the denominator; pinned rows
  always present; baseline order preserved; DATA_BLOCKED pick cell.
- **Render:** section order; removed sections absent; details rendered only
  for table names; one event line; zero `<script`; disclaimers verbatim;
  digest round trip; six drawer sections; `BOARD_LANES_ENABLED=False`
  reproduces today's output byte-for-byte on the layout fixture.
- **Parity:** invariants 1–3 on a fresh-chain fixture and on the Friday
  2026-09-04 ops data (manual proof in the PR body).
- **Acceptance targets** (LLM-proposed 2026-09-06, measured on Friday's data;
  targets, not frozen numbers): ≤ 8 `<h2>`; HTML under 150 KB (771 KB today);
  ≤ 20 `<details>` open or closed above the drawer (362 today).
- Suite, ruff, pyright exit 0; `bash -n` not applicable (Python only).

## 9. Out of scope / held

- DR-5 (GREEN-fraction denominator tilt) and DR-5b (rv21 / vol-premium badges
  on Schwab-sourced cards): owner rulings; the pre-drafted design sits in
  brief 37's "Held" section. This redesign changes no ranking input.
- Mission Control (D3); any JavaScript (D2); the standalone experiments page;
  the live dashboard; the pick tracker's arms and scoring.
- Enabling any experiment beyond display on this board.

## 10. Mockup reference

`assets/2026-09-06-board-redesign-option-a-v2.html` shows the approved first
screen on Friday's data: status strip, four tiles, the 14-row agreement table
with the favourable/caution split (NVDA, AMZN, SMCI, PLTR, CRWV at 4/5; CEG
at 1/5 with two cautions), one event line, details fold-outs, drawer. Two
rejected directions (B lane columns, C pick cards with badges) are in the
gitignored mockup folder for the record.
