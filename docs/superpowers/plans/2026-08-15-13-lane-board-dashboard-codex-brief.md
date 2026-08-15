# Brief 13 — Lane Board: attractiveness dashboard reorganized into honest, self-contained lanes

**Date:** 2026-08-15
**Status:** READY FOR IMPLEMENTATION (Codex)
**Authority:** owner-directed in-session 2026-08-15 (Carsyn): "I want the QM and
mechanical movement to be its own pick, not just the top mechanical picks …
I want all my different lanes and signals on there … I want all the lanes up
and running." Display-only presentation work; the 2026-08-03 ship-blocker
retirement applies. No registered hypothesis, ranking recipe, frozen number,
ledger path, or FIRE authority is touched.
**Target:** `main` (base ≥ `b68363f`, which includes brief 12 Schwab pre-close
freshness and PR #48 research-views ops lane).
**Author:** Claude (Fable session). Implementing agent: Codex.

## 1. Objective (plain English)

Today the attractiveness page is one merged story: a mechanical Top-3 hero,
with QM movement context shackled to those same three picks, other lanes
scattered below, and staleness reported as warning banners. The owner wants a
**Lane Board**: every lane is its own clearly-labeled section with its own
pick(s), its own freshness stamp, and a badge saying what it is allowed to
mean. Stale data becomes a visible state, not a surprise.

## 2. Page layout after this brief (top to bottom)

1. **Freshness strip** (new, replaces nothing — banners stay until §3.1)
2. **Rule-based top 3** (existing hero, relabeled; selection code untouched)
3. **Movement lane (QM)** (new standalone section with its own membership)
4. **Composite four-angle lane** (existing, gains a "highest agreement" row)
5. **Research desk** (new coverage panel for the written research bundle)
6. **Registered-bets tracker** (new strip from `hypothesis_evidence`)
7. **Experiments shelf** (new link-card; no `exp_*` imports — see §3.7)
8. **Core names strip, market context, per-symbol panels** (unchanged)

## 3. Sections in detail

### 3.1 Freshness strip

One row of chips at the top, each chip = one data source with its as-of date
and age in trading sessions, colored OK / WARN / BLOCKED using the existing
`CHAIN_STALE_WARN_SESSIONS` / `CHAIN_STALE_BLOCK_SESSIONS` thresholds where
they apply:

- Option chains — show BOTH stores when split: frozen EOD store edge
  (`.cache/chains`) and Schwab pre-close edge (`.cache/schwab_chains`), with
  the per-symbol split count (e.g. "13 fresh / 5 frozen") derived from the
  brief-12 `chain_source` plumbing already in `_gather_symbol`.
- Underlying closes — max session in `data/underlying_closes`.
- Research bundle — `as_of` + `researched_on` of the newest
  `reports/attractiveness_context/*.json` (via `load_context`).
- QM — frozen study vintage (2026-07-14 sidecar) AND the exact-session QM
  computation date (two-date label already exists on main:
  `_qm_two_date_label_html`).
- Composite lane — its max as-of.
- Experiments views — timestamp parsed from
  `.tmp/dashboard/research-views-status.txt` if present, else "not published".

The existing stale-board warning banners MAY be slimmed once the strip exists,
but never removed entirely: the hard BLOCK banner (chain age ≥ block
threshold) must survive as-is. No threshold values change.

### 3.2 Rule-based top 3 (relabel only)

Heading becomes: "Rule-based top 3 — best policy-and-liquidity fit today".
Sub-line: "Chosen by fixed rules (green-check fraction, one pick per stock).
This is a fit ranking, not a prediction; whether it predicts anything is
exactly what the registered RQ2/A2 studies will measure."
`select_top_picks`, `_admissible_pick_pool`, `_display_quality_key`,
`pinned_picks` are **byte-untouched**. A test must assert the rendered Top-3
membership and order are identical before/after this brief on a fixture board
(extend the existing byte-identity pattern from the experiments split).

### 3.3 Movement lane (QM) — its own pick

New section, rendered AFTER the mechanical hero (subordination preserved),
with its OWN membership: every symbol in the QM display scope whose
exact-session `signal_status` is `BREAKOUT`, `PARABOLIC WARNING`, or both
(from `qm_dashboard`'s existing per-session computation). Not limited to,
and never influencing, the mechanical Top-3.

- Empty state (the normal state): "No movement fires today. Expected — these
  patterns fired ~46 times in nine years across twelve names." Never render
  placeholder picks.
- Per-name coverage: names added after the frozen 2026-07-14 study (IREN,
  USAR, ET) show their LIVE signal state labeled "not covered by the frozen
  study" and NEVER display frozen-study statistics (`NOT_IN_FROZEN_STUDY`
  handling already exists at qm_dashboard's evidence layer — keep that
  boundary; a live state may show, frozen stats may not).
- The mandatory banner stays verbatim: "DESCRIPTIVE ONLY — NOT A TRADE
  RANKING" plus the existing UNVALIDATED SIGNAL language from `qm_watch`.
- The existing "QM context for mechanical top 3" comparison panel is RETAINED
  below this new lane (it answers a different question). Its per-name
  block-reason behavior from main (one uncovered name no longer blanks the
  panel) is kept.
- **Prerequisite amendment (§5)** must land in the same PR.
- Tests: (a) QM lane membership derives only from signal state, with a
  fixture forcing a fire; (b) a fire changes NOTHING in `select_top_picks`
  output (adversarial fixture); (c) uncovered-name cards contain the
  not-covered label and no frozen-study fire counts; (d) empty state renders
  when no fires.

### 3.4 Composite lane

Keep the existing cards. Add one summary row above them: "Highest agreement
today: <grade-A names, comma-separated, or 'none at grade A'>". No scoring
change; grades stay the lexicographic angle count. Label stays
"display-only, not verdict-bearing".

### 3.5 Research desk

Replaces the buried mismatch warnings with a visible coverage panel:

- Bundle identity: `as_of`, `researched_on`, provenance line, and whether it
  exactly matches the board session (exact / stale-by-N-sessions / none).
- Coverage grid: for each of the 18 board names, covered (has a symbol
  packet) vs not covered. Covered names keep their per-symbol accordions
  exactly as today.
- Candidate annotations: unchanged logic (`_research_annotation_map`,
  `_research_html`); the unmatched-annotation notice moves inside this panel.
- No new research fetching, no producer changes. Pure re-presentation of
  `load_context` output.

### 3.6 Registered-bets tracker

One strip built ONLY from `options_researcher/hypothesis_evidence.py` (the
documented aggregator; "the dashboard is a consumer of this module, never an
authority source"). One line per family — H5, H6, H7, H8, H10a, H10b — each
with a plain-language state derived from existing receipts/evidence, e.g.:
"H5 entry watch — halted: needs an exact-session chain (last: 2026-07-27)",
"H6 post-earnings calls — 1 open position", "H7 — paused; Schwab restart in
progress", "H10a/b movement bets — recording paused by ritual authority;
window ends 2026-10-06 / 2027-01-06". Wording must be honest about PAUSED
states — never render a paused lane as if it observed today. If
`hypothesis_evidence` lacks a needed field, extend it read-only (no watcher
execution, no receipt writes — preserve its read-only contract and add tests).

### 3.7 Experiments shelf

A link card, NOT an embed. Constraint that binds: the 2026-08-10 experiments
split removed all `exp_*` imports from `attractiveness_dashboard.py` and an
AST test enforces it — that test must remain green. The shelf shows: the five
experiment lane names (beta-to-QQQ, tail shape, spread stability, T-bill
carry, short-interest context), the research-views status-file contents
(timestamp + OK/FAILED per builder) when present, and links to
`experiments.html` / `wasserstein-regime.txt` on the local research-views
server (relative links; the page must render fine when the files are absent).

## 4. Hard constraints (all test-enforced where marked)

- Frozen GREEN-fraction recipe byte-untouched; Top-3 membership/order
  identical on fixture (TEST).
- QM never selects, reorders, or gates the mechanical shortlist (TEST).
- No `exp_*` imports in `attractiveness_dashboard.py` (existing AST TEST).
- No network calls anywhere in the render path (existing hermetic-suite
  discipline; offline test run is the verdict).
- No ledger writes; no watcher execution during render (hypothesis_evidence
  read-only contract, TEST if extended).
- Any new presentation constant goes in `config.py` with an
  "LLM-proposed 2026-08-15 (presentation only)" provenance comment; no
  strategy-adjacent numbers are introduced.
- Plain-language headings: every section carries a one-line "what this can
  and cannot mean" sub-line, per the owner's standing no-jargon directive.

## 5. Prerequisite amendment (same PR)

`docs/superpowers/2026-07-17-qm-dashboard-remediation-addendum.md` ruled QM
"never a selector, action ranking, edge estimate, or verdict input" and bound
its display to the mechanical shortlist. Giving QM its own membership requires
a recorded amendment, NOT silence. Append (do not rewrite) to that file:

> **Amendment 2026-08-15 (owner-directed in-session; provenance:
> owner-delegated standing 2026-07-25):** the QM lane may render its own
> standalone section whose membership is the set of names with a current-
> session mechanical fire. The 2026-07-17 prohibitions are unchanged where
> they matter: QM remains descriptive-only, renders below the mechanical
> shortlist, never selects/orders/gates any mechanical pick, and frozen-study
> statistics still never attach to names outside the frozen study's coverage.
> Recorded by the implementing agent after independent adversarial review and
> Fable sign-off (review receipt: PR review thread of this brief's PR).

The PR description must request an explicit adversarial-review pass on this
amendment text; Fable (orchestrating session) signs off at merge review.

## 6. Acceptance

- Full offline suite green (exit 0), ruff + pyright clean.
- Rendered page (fixture and live-cache smoke render) shows all eight §2
  sections in order; empty states render honestly with zero candidates.
- Byte-identity: Top-3 selection unchanged on fixture.
- No new imports in the dashboard module beyond stdlib + existing
  options_researcher modules named here.
- Screenshot or html artifact attached to the PR for owner review.

## 7. Rollback

Each new section is one render helper behind `render()` composition; a revert
of the single PR restores today's page. No data, config threshold, or ledger
state changes to unwind.

## 8. Out of scope

RQ2 badge implementation (EX4/EX5 briefs), A2 battery (EX8), any
`entry_watch`/FIRE-path change, wiring Schwab pre-close into any registered
hypothesis input, universe changes, QM study re-runs, research bundle
production (separate lane), LaunchAgent installs.
