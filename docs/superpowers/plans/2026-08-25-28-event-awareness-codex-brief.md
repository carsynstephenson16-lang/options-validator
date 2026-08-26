# Codex brief 28 — event awareness: macro calendar, non-grading event chips, complex-event tagging, derived implied move

**Date:** 2026-08-26 (rev 6, final-review correction)
**Author:** Claude orchestrating session (Fable), 2026-08-25
**Executor:** Codex (GPT-5-class), high reasoning tier
**Status:** CORRECTION CANDIDATE — final-head independent review pending. The prior correction review passed `bc760a2`, but the subsequent final-head review found a stale Brief 25 order passage and an incomplete hashing citation; rev 6 repairs those findings without changing Brief 28's event contract. The prior adversarial review round 3 verdict was **PASS** (rounds 1–2 PASS WITH FIXES, all applied; round-3 NEW-8 sentence added). Rev 5 rebased the contract after Brief 25, moved Brief 28 ahead of Brief 27, and pinned event-chip coverage for the landed context cards. Receipt: `reports/2026-08-25-briefs-28-30-adversarial-review-receipt.md`.
**Provenance:** Repo-verified against post-Brief-25 `origin/main@8a6920a2449094f4e5db5ad6ff00741f2d388023` unless labeled otherwise. Design pre-audited 2026-08-25 (analyst-note audit findings 17–21 baked in); rev-5 ordering, current line references, and context-card coverage were re-verified 2026-08-26 against that base. Owner directive: Carsyn in-session 2026-08-25 ("nvidia reports earnings tmrw … the fed speaks friday … these are things i want this options validator to be aware of"; hand-off directive same day).
**Landing order (binding):** 26 → 25 → 28 → 27 → 30. Briefs 26 and 25 are already canonical on the provenance base. Event chips render on the post-26 card surfaces and on Brief 25's landed context-card renderer (`options_researcher/attractiveness_dashboard.py:3841-3923`); a context pick receives the SAME chips as its underlying `pick["card"]` (`:3868-3870`) and empty context slots receive none. NOTE: this brief adds modules under `options_researcher/`, which is included in and therefore shifts `diagnostic_source_hash` (`research/hashing.py:132-154`) — batch its landing with the other briefs in this train per standing guidance; no `config.py` constant is added, so `config_hash` is untouched.

## Why this exists (plain language)

On 2026-08-25 the board's three hero cards were 11-day calls crossing, invisibly: July core-PCE + Q2-GDP data (Wed 8:30am), NVDA earnings (Wed after close, ~5.3% implied move), a correlated name's own earnings (IREN, Thu), and the new Fed Chair's first Jackson Hole keynote (Fri). The board knew none of it, for a structural reason (Repo-verified): `earnings` and `fomc` exist as GRADING badges on sell lanes only (`options_researcher/attractiveness.py:202-206`); buy lanes carry exactly `fits_bucket|fits_cap`, `iv_for_buyer`, `liquidity` (`:364-371`, `:406-412`) — no event awareness at all. And the only calendar the platform has is per-name earnings + FOMC meeting dates; no data releases, no speeches, no cross-name event contagion.

## Hard constraint that shapes everything (audit finding 17 — BLOCKER class)

The frozen GREEN-fraction ranking computes `greens / len(grades)` (`options_researcher/display_rank.py:17-20` on the provenance base). Adding ANY key to a buy lane's `grades` dict changes numerator and denominator, changes cross-lane ordering, changes Top-N membership — i.e. edits the frozen recipe that A2-v1's OPEN 12-month forward window (ledger seq 19/27, opened 2026-08-17) is scoring. Therefore: **everything this brief adds is a NON-GRADING annotation. Nothing enters any `grades` dict. Ever.** Proof-test in WP-E.

## Scope

**IN**
- WP-A: cached macro-event calendar with per-entry source + capture time.
- WP-B: event chips on ALL lanes (buy included), non-grading, life-window matched.
- WP-C: complex-event tagging via a frozen, owner-approved relatedness map.
- WP-D: implied-move column DERIVED from the already-captured chain (no new acquisition).
- WP-E: experiment envelope — acceptance metrics, tests, failure behavior, rollback.

**OUT (hard stops)**
- No modification of any `grades` dict, badge set, `select_top_picks`,
  `_admissible_pick_pool`, `_display_quality_key`, or any `PICK_*` constant.
- No network calls at render or in tests; no new provider endpoints, no new
  acquisition (OD-4 stands). WP-D computes from cached parquet ONLY.
- No coupling into H5/H6/H7/H8/H10b/RQ2/A2, the paper books, FIRE paths, or
  the (future) pick-tracker's scored records; no ledger writes.
- No `exp_*` imports into `attractiveness_dashboard.py` (AST test
  `tests/test_experiments_baseline.py:92-93`).
- Promotion of any of this into ranking/selection/signal authority requires
  a separate owner decision + registration + the 2026-07-24 feasibility
  gate — state this in every module docstring.

## Work packages

### WP-A — macro-event calendar

1. New data file `data/events/macro_calendar.jsonl`, append-preferred, one
   event per line: `{"event_id", "date" (ET), "time_et" (nullable, "UNKNOWN"
   allowed and rendered as such), "kind" ("data_release"|"fed_speech"|
   "fomc_meeting"|"symposium"|"other"), "title", "source_url",
   "source_kind" ("official_gov"|"official_exchange"|"company_ir"),
   "verification" ("fetched"|"asserted"), "source_quote" (REQUIRED when
   verification=="fetched": the sentence from the fetched page — round-2
   finding NEW-4, so the claim is checkable in-repo, not only in a PR
   body), "captured_at", "added_by"}`.
   Source discipline is a DENYLIST plus a typed claim, not an allowlist
   (rev-1 finding 1 — "company IR" has no bounded host set, so an
   allowlist cannot be built): the loader REJECTS any `source_url` whose
   host matches `BANNED_HOST_FRAGMENTS`, and requires `source_kind`; the
   owner eyeballs source quality in the diff. The constant moves to a new
   tiny shared module `options_researcher/source_policy.py` imported by
   BOTH the calendar loader and `attractiveness_research_v2.py`
   (currently defined at `attractiveness_research_v2.py:61-72` — rev-1
   finding 2 corrected the line; do not import the research module itself,
   it drags in the research-artifact pipeline). Entries with
   `verification: "asserted"` render visibly weaker ("source not yet
   fetched — verify before relying").
2. Loader module `options_researcher/event_calendar.py`: validates schema,
   refuses duplicate `event_id`, sorts by date. Staleness rule (audit
   finding 20): an entry whose `date` is in the past relative to the
   board's evaluation date renders only in an "elapsed events" details
   block, never as an active chip; an entry with `captured_at` older than
   30 days renders with a "re-verify source" flag. No silent persistence.
3. Population is MANUAL (CLI `python -m options_researcher.event_calendar
   add ...`) or by a future research-refresh step — this brief ships the
   file seeded with the 2026-08-25 research entries (NVDA earnings 08-26
   AMC; PCE/GDP 08-26 08:30 ET; Jackson Hole 08-27..29; Warsh keynote
   08-28 time UNKNOWN; AVGO earnings 09-02; IREN earnings 08-27).
   Seed-data discipline (rev-1 finding 3 — LLM-transcribed facts must not
   wear an Official-source label unearned): every seed entry's
   `source_url` must be FETCHED by Codex at implementation time with a
   quoted line from the fetched page pasted into the PR body; entries
   whose page cannot be fetched or does not state the claim ship with
   `verification: "asserted"` (rendered weaker) or are dropped;
   `added_by: "LLM-seeded-2026-08-25"` on all of them. The Warsh-keynote
   entry in particular requires a federalreserve.gov or kansascityfed.org
   page, not press. Seed entries are data, reviewable by the owner in the
   PR diff.
4. FOMC meeting dates: the platform already carries them for the sell-lane
   `fomc` badge — WP-A's loader must read the SAME underlying source (find
   it; do not create a second FOMC source of truth that can drift).

### WP-B — event chips on all lanes (non-grading)

1. Pure function `event_chips(card, section, calendar, complex_map)` →
   list of chips for every event whose date falls inside the card's LIFE
   WINDOW (evaluation date → expiry). Chip text: kind + title + date +
   (time or "time TBD") + provenance marker ("cal" vs "complex" per WP-C).
2. Rendered on EVERY lane's cards — buy lanes included — visually distinct
   from grading badges (different CSS class, no GREEN/AMBER/RED colors; a
   neutral "EVENT" chip style), so a beginner cannot read them as scores.
3. The chips NEVER enter `card["grades"]`, never affect ordering, and are
   attached at render time only (assemble() output unchanged — keeps
   `sections_json()` consumers and the brief-27 picks artifact byte-stable).
4. Rule-based hero/top-pick cards get the same chips (today's gap was
   precisely the hero cards).
5. Brief 25 context cards are an explicit, required consumer. In
   `_context_lane_html`, pass each non-empty row's underlying
   `pick["card"]` (`attractiveness_dashboard.py:3865-3870`) through the SAME
   `event_chips` function used by the rule-based hero and per-lane renderers.
   Render identical neutral chip markup for the same candidate in either
   shortlist; empty context slots (`:3894-3901`) render no chips. This remains
   a render-only join: no context row, candidate card, `grades` dict, or
   `sections_json()` payload is mutated.

### WP-C — complex-event tagging (audit finding 18)

1. New data file `data/events/complex_map.json`:
   `{"as_of": "YYYY-MM-DD", "clusters": {"ai_infra": {"members": [...],
   "events_propagate_from": ["NVDA", "AVGO", "IREN", ...]}}}` — a name's
   OWN calendar/earnings event propagates a "COMPLEX EVENT" chip to every
   other member of its cluster.
2. Causality discipline: the map is frozen with its `as_of`; the loader
   REFUSES a map whose `as_of` is later than any event date it is being
   applied to (no post-event membership edits — hindsight ban, test
   required). Changing membership = a new dated map version; old versions
   stay in git history.
3. Seed map: the 18-name `ATTRACTIVENESS_UNIVERSE` as one `ai_infra`
   cluster (LLM-proposed seed, labeled; the owner may veto members in the
   PR). Docstring states: this map asserts co-movement and is therefore a
   SIGNAL-shaped object; it stays display-only, and any ranking-bearing
   use requires registration + the 2026-07-24 gate.

### WP-D — derived implied-move column (audit finding 19, resolved by derivation)

1. NO new acquisition: implied move is computed OFFLINE from the
   already-captured verified chain parquet — nearest-expiry ATM straddle
   mid (call mid + put mid at the strike nearest spot) divided by spot,
   from the SAME 15:45 capture the board renders. Rev-1 finding 4
   verified the parquet carries both legs and all quote columns (no
   entitlement gap) but NO underlying/spot column. **Spot source, named
   (round-2 finding NEW-1 corrected rev 2 — the parity spot I named is
   the one the boundary explicitly forbids, `schwab_chain_view.py:285-286`
   "never a parity fallback"):** use
   `schwab_chain_view.load_preclose_spot(symbol, session)` — the 15:45
   intraday-capture receipt's `spot_mid` with `spot_source ==
   "stock_snapshot"`, the one internally-consistent same-instant pairing
   (`:278-282`). It returns `None` fail-closed, wiring straight into the
   UNAVAILABLE path. DISCLOSED DEPENDENCY: WP-D therefore requires the
   intraday capture lane healthy for that session, not just the chain
   lane — and (round-3 NEW-8) a PERSISTENT "implied move UNAVAILABLE" is
   an intraday-lane health signal, not an event-layer bug; it must never
   be "fixed" by loosening the spot rule. If spot is unavailable, do NOT substitute `underlying_closes`
   (a prior-session close under a same-session IV is a units mismatch)
   — render UNAVAILABLE. Method name
   `atm_straddle_mid/v1`, stamped on every value with session, capture
   convention, expiry used, strike used, spot source
   (`stock_snapshot`), AND the intraday receipt's session (the
   2026-08-25 research pass showed providers disagree by 150bp+
   depending on convention — the stamp is the point).
2. Fail-visible: missing put or call quote at the ATM strike, missing
   spot, or no expiry within 1–21 calendar days, renders "implied move
   UNAVAILABLE — <reason>" (never a default, never a silently different
   expiry).
3. Display-only, computed at RENDER time only (rev-1 finding 5 — WP-B.3's
   constraint applies verbatim): the value never enters the assembled
   section dict, so `sections_json()` output and the brief-27 picks
   artifact stay byte-stable. Rendered on the symbol panel header area;
   feeds nothing.

### WP-E — envelope (audit finding 21; `.cursorrules:133-135` artifacts)

1. Named acceptance metrics: (a) `select_top_picks` output, every
   `card["grades"]` dict, AND full `sections_json()` output byte-identical
   before/after on a full fixture board WITH the calendar populated (the
   non-grading proof, extended per rev-1 finding 5); additionally assert
   the KEY SET of every lane's `grades` dict equals the exact pre-brief
   set (rev-1 finding 6 — so a future edit cannot add a key that happens
   not to reorder the fixture); (b) on a fixture reproducing 2026-08-25
   (three 11-day hero calls + seeded calendar), every hero card renders
   ≥3 event chips; (c) with `CONTEXT_LANE_ENABLED`, a non-empty context pick
   and the same underlying candidate in another card surface render an
   identical event-chip list, while an empty context slot renders none;
   (d) full suite + ruff + pyright exit 0.
2. Tests: loader validation (banned host rejected, duplicate id rejected,
   post-event map rejected); staleness rendering; chips life-window edges
   (event on expiry day = in; day after = out); implied-move fail-visible
   cases; byte-identity of (a).
3. Failure behavior: any exception in calendar load, chip computation, or
   implied-move derivation renders a loud per-section "EVENT LAYER FAILED —
   <class>" notice; the board otherwise renders normally (event layer must
   be incapable of taking the board down).
4. Rollback (round-2 finding NEW-3 — unconditional CSS would falsify the
   claim): the EVENT-chip style block is emitted ONLY when at least one
   chip renders on the page. Then: delete the two data files → loader
   reports "no calendar", chips absent, style block absent, board
   byte-identical to pre-brief output (test this exact chain).

## Acceptance / verification

```bash
uv run python -m unittest discover -s tests    # exit 0, offline
uv run ruff check . && uv run pyright          # exit 0
```
Plus WP-E.1's named metrics.

## Claim-discipline register

- Buy lanes carry no event badges; sell-lane grades include earnings/fomc:
  Repo-verified `attractiveness.py:202-206,364-371,406-412` on
  `origin/main@8a6920a`.
- GREEN-fraction denominator sensitivity: Repo-verified
  `display_rank.py:17-20`.
- Brief 25 context-card rendering and underlying-card binding: Repo-verified
  `attractiveness_dashboard.py:3841-3923` (especially `:3865-3870`) on
  `origin/main@8a6920a`.
- A2-v1 forward window open since 2026-08-17: Repo-verified ledger seq 19/27.
- Banned-host fragments constant: Repo-verified
  `attractiveness_research_v2.py:61-72` (rev-1 finding 2 corrected the
  line; moves to `options_researcher/source_policy.py` in WP-A).
- 2026-08-25 seed event dates/sources: Official-source URLs captured in the
  session's research pass (NVIDIA IR, BEA schedule, KC Fed, Fed Board page);
  re-verify each URL when seeding.
- Provider implied-move divergence (150bp+ by convention): research-pass
  observation 2026-08-25, Inference for the general claim; the stamp
  requirement does not depend on its exact size.
- Cluster seed membership, 30-day re-verify window, 1–21-day expiry band
  for the straddle: LLM-proposed 2026-08-25, labeled in code.
