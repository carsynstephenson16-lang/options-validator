# M7 — Game-Style Dashboard Implementation Plan (for a future session)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax. This plan is SELF-CONTAINED for a cold-start session (any capable model): every interface it consumes is named exactly; verify each import exists before coding and STOP/report if one doesn't.

**Goal:** One command renders a single static HTML "mission control" — dark, game-styled, zero servers, zero external JS — showing the H4 paper book, per-ticker "party cards", the quest log, and an achievement wall built from the project's real history.

**Architecture:** Pure data-assembly function (tested) → HTML template string (tested for section presence) → CLI writes `.tmp/dashboard/index.html`. Inputs are read-only: `options_researcher.portfolio.analyze()` (marks + bucket issues), `options_researcher.features.load_features(sym)` (close/atm_iv history for inline-SVG sparklines), `ledger/facts.log` (achievements), `reports/` filenames (library shelf), `config` (universe, buckets). No new dependencies — stdlib + pandas only. `.tmp/` is gitignored; the generator is committed, its output is not.

**Owner context:** coding beginner; wants "attractive, easy on the eye, like a video game". Dark background, neon accents, big numbers, no jargon on the surface (tooltips can carry detail).

**Tech Stack:** Python 3.12/uv, unittest (`uv run python -m unittest discover -s tests`; per-file form: `discover -s tests -p "test_<name>.py"` — dotted module form does NOT work in this repo). Repo quirk: set `LUMIBOT_LOG_LEVEL=WARNING` for clean stdout.

---

### Task 1: Data assembly (`options_researcher/dashboard.py::assemble`)

**Files:** Create `options_researcher/dashboard.py`; Test `tests/test_dashboard.py`.

- [ ] Step 1 — failing test:

```python
"""tests/test_dashboard.py"""
import unittest

from options_researcher.dashboard import assemble


class AssembleTests(unittest.TestCase):
    def test_assemble_from_injected_parts(self):
        book = {"marks": [{"id": "p1", "structure": "leaps_call",
                           "symbol": "MSFT", "strike": 340.0,
                           "expiration": "2027-06-17", "contracts": 1,
                           "dte": 300, "mark": 80.0, "pnl": -461.0,
                           "flags": []}],
                "bucket_issues": []}
        facts = ["2026-07-04T00:00:00+00:00\tCEG_CACHE_COMPLETE ...",
                 "2026-07-04T00:00:00+00:00\tSTUDY_C VST d=0.20: ..."]
        d = assemble(book=book, facts=facts,
                     reports=["reports/2026-07-04-study-a.md"],
                     closes={"MSFT": [430.0, 431.5, 429.0]})
        self.assertEqual(d["book"][0]["symbol"], "MSFT")
        self.assertTrue(any(a["key"] == "CEG_CACHE_COMPLETE"
                            for a in d["achievements"]))
        self.assertIn("MSFT", d["sparklines"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] Step 2 — run, expect `ModuleNotFoundError`.
- [ ] Step 3 — implement: `assemble(*, book=None, facts=None, reports=None, closes=None)` where every arg defaults to loading the real thing (`portfolio.analyze()`, `research.facts.read_facts()`, `sorted(glob("reports/*.md"))`, last ~60 closes per `config.UNIVERSE` symbol via `data.underlying_closes.load_closes(sym, start, end, allow_oos=True)`). Achievements = facts lines whose tag (text before the first space after the tab) is in a curated map, e.g. `{"CEG_CACHE_COMPLETE": ("Data Hoarder", "Cached every CEG chain since listing"), "PIVOT_4NAME_SCOPE": ("New Game+", "Re-scoped to the 4-name thesis"), "UNDERLYING_CLOSES_YAHOO": ("Free Data Achieved", "$0.0000 vs official closes"), "H4_PAPER_WINDOW_SEEDED": ("Party Assembled", "The book went live"), ...}` — include one entry per major fact tag visible in `grep -o "\t[A-Z_0-9]*" ledger/facts.log | sort -u`. Sparklines = raw close lists (rendering happens in Task 2).
- [ ] Step 4 — tests pass; full suite unchanged+new.
- [ ] Step 5 — commit `feat(dashboard): data assembly layer`.

### Task 2: HTML renderer

- [ ] Step 1 — failing test (append):

```python
class RenderTests(unittest.TestCase):
    def test_render_contains_sections_and_no_external_assets(self):
        from options_researcher.dashboard import render
        html = render(assemble(book={"marks": [], "bucket_issues": []},
                               facts=[], reports=[], closes={}))
        for token in ("MISSION CONTROL", "PARTY", "QUEST LOG",
                      "ACHIEVEMENTS", "<style>"):
            self.assertIn(token, html)
        self.assertNotIn("http://", html)
        self.assertNotIn("https://cdn", html)
```

- [ ] Step 2 — expect ImportError. Step 3 — implement `render(data) -> str`: one f-string template. Design spec (follow, don't reinvent): background `#0b0e17`; panel cards `#141a2a` with 1px `#2a3350` border, 12px radius; accent neon per symbol (MSFT `#4da3ff`, AMZN `#ff9900`, VST `#ffd23f`, CEG `#7CFC9B`); headline font-stack `ui-monospace, Menlo, monospace`. Sections in order: (1) header `MISSION CONTROL — H4 FORWARD WINDOW` + as-of date; (2) **PARTY** — one card per universe symbol: name, role line (MSFT "The Tank — LEAPS core", VST "Dual-class — CSP + tactical", CEG "Reserve — LEAPS slot 2", AMZN "Bench — returns with covered calls"), inline SVG sparkline (`<polyline>` from the 60 closes normalized to a 120×28 viewBox, stroke = symbol accent), open-position P&L badges (green `#2fd27d` / red `#ff5470`); (3) **BOOK** — table of marks with flags rendered as pill badges (ROLL_DUE amber, ASSIGNMENT_WATCH red, EARNINGS purple, QUOTE_MISSING grey); bucket issues as a red banner, else "ALL BUCKETS GREEN"; (4) **QUEST LOG** — hardcoded ordered list with states from data: completed quests (struck through, ✓) M1..M6 + seeded window; active quest "Survive 2 quarters of forward window"; locked quest "Dashboard v2 (live sparkline history)"; (5) **ACHIEVEMENTS** — grid of unlocked achievement tiles (title + one-liner) from Task 1's map, plus a "graveyard" row listing the measured kills verbatim: "H1 $2-wide (FAIL)", "H2 $5-wide (FAIL)", "IV-rank premium selling (Study A)", "$5 bull put spreads (Study E, 8/8 ~$0)". Escape all dynamic strings with `html.escape`.
- [ ] Step 4 — tests pass. Step 5 — commit `feat(dashboard): game-styled static renderer`.

### Task 3: CLI + docs

- [ ] `main()` writes `.tmp/dashboard/index.html` (mkdirs), prints the absolute path and "open it in your browser". `if __name__ == "__main__": main()`. Manual check: `LUMIBOT_LOG_LEVEL=WARNING uv run python -m options_researcher.dashboard` then open the file — verify the three seeded positions render with badges.
- [ ] README: add a Quickstart line `uv run python -m options_researcher.dashboard   # mission control`.
- [ ] Full suite green; commit `feat(dashboard): CLI + README (M7 complete)`.

### Guardrails for the executor

Read-only over research data (never mutate positions/ledger/reports); no network; no JS frameworks (inline `<script>` allowed only if trivial and offline); if `portfolio.analyze()`'s shape differs from Task 1's fixture, STOP and report (the fixture mirrors `mark_position`'s dict as of 2026-07-04). Do not editorialize numbers — the dashboard renders what the tools computed, including losses.
