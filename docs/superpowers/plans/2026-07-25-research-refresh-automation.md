# Scheduled Research Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automate the attractiveness board's LLM research refresh (currently owner-triggered) on a schedule — Mon–Fri 07:40 & 16:45 ET plus Sat 09:00 ET — so the board never shows stale research without anyone asking.

**Architecture:** A LaunchAgent runs `tools/research_refresh.sh` (zsh, modeled on `tools/daily_ritual.sh`). The script: (1) converges data freshness (topup → attractiveness features → QM OHLCV — all no-ops when already current), (2) invokes a headless `claude -p` Sonnet session that follows the repo skill `research-refresh` to web-research today's hero cards and write `reports/attractiveness_context/<data-as-of>.json` through the existing `top3_context` validator, (3) rebuilds the dashboard and verifies the stale-research banners are gone. A new module `tools/research_context_assemble.py` owns ID derivation, assembly, validation, and HTML verification, with offline unittest coverage. Governing spec: `docs/superpowers/specs/2026-07-16-attractiveness-v2-technicals-context-design.md`, amendment *2026-07-25 (owner-directed): scheduled research refresh* — read it before starting.

**Tech Stack:** Python 3.12 via `uv run`, `unittest` (offline — never network in tests), zsh, launchd, Claude Code CLI 2.1.143 (verified installed at `~/.local/bin/claude`; supports `-p/--print`, `--model`, `--allowedTools`, `--max-budget-usd`).

**Non-negotiable constraints (from CLAUDE.md / .cursorrules — violations are plan failures):**
- NEVER touch the H7 receipt/gate/ledger machinery (`h7_source_health`, `h7_data_gate`, `h7_event_ledger`, `ledger/`). This automation is display-layer only.
- The research layer is advisory-only: it cannot add, remove, or reorder board candidates. `top3_context.normalize_research_annotations` stays the sole annotation gate — do not modify it or `options_researcher/attractiveness_dashboard.py`.
- Tests stay offline (no network, no `claude` invocation, no `assemble()` over live data inside unittest).
- No runtime auto-commit and no push from the scheduled run.
- Register the LaunchAgent LAST, only after tests pass and one manual end-to-end run succeeds (2026-07-15 hook-lockout lesson: script exists and works FIRST, registration LAST).
- Existing repo hooks (ledger guard, project boundary) remain active in the headless session — do not disable or work around them.

**File map:**

| File | Responsibility |
|---|---|
| `tools/research_context_assemble.py` (create) | Pure-core assembly/validation/verification + CLI (`--print-ids`, `--assemble`, `--verify`) |
| `tests/test_research_context_assemble.py` (create) | Offline unittest for the pure core |
| `tools/research_refresh.sh` (create) | LaunchAgent entry: guards, data convergence, headless claude, verify, receipts |
| `.claude/skills/research-refresh/SKILL.md` (create) | Procedure the headless Sonnet session follows |
| `tools/launchd/com.carsyn.options-validator.research-refresh.plist` (create) | Checked-in schedule template (installed by copy) |
| `.gitignore` (modify) | Add `.research-refresh-off` kill-switch |
| `docs/research-context-refresh-runbook.md` (modify) | Point the runbook at the automation; keep manual procedure as fallback |

---

### Task 1: Assembler pure core + tests (TDD)

**Files:**
- Create: `tools/research_context_assemble.py`
- Test: `tests/test_research_context_assemble.py`

The pure core takes plain dicts (no filesystem/network) so tests stay offline. The reference implementation for behavior is the session assembler that produced `reports/attractiveness_context/2026-07-24.json` (committed `c742cf1`) — this task productionizes it.

- [ ] **Step 1: Write the failing tests**

```python
"""tests/test_research_context_assemble.py — offline; no network, no live data."""
import unittest

from tools.research_context_assemble import (
    AssemblyError,
    build_context,
    check_dashboard_html,
    clean_claims,
    clean_symbol_blurb,
)


def _claim(**over):
    base = {
        "id": "c1", "text": "t", "classification": "fact",
        "source_url": "https://investor.nvidia.com/x", "unknown_rationale": None,
        "source_tier": "issuer_ir", "fact_date": "2026-07-24",
        "date_certainty": "confirmed", "countercase": "could fail",
    }
    base.update(over)
    return base


class CleanClaimsTest(unittest.TestCase):
    def test_banned_host_is_hard_error(self):
        bad = _claim(source_url="https://www.reddit.com/r/options/x",
                     source_tier="secondary", date_certainty="estimated")
        with self.assertRaises(AssemblyError):
            clean_claims("NVDA", [bad])

    def test_confirmed_without_primary_tier_is_hard_error(self):
        bad = _claim(source_tier="secondary")
        with self.assertRaises(AssemblyError):
            clean_claims("NVDA", [bad])

    def test_extra_fields_are_dropped_not_fatal(self):
        messy = _claim(confidence="high")  # agents sometimes add extras
        cleaned = clean_claims("NVDA", [messy])
        self.assertNotIn("confidence", cleaned[0])
        self.assertEqual(cleaned[0]["id"], "c1")

    def test_good_claim_passes_through(self):
        cleaned = clean_claims("NVDA", [_claim()])
        self.assertEqual(cleaned[0]["source_tier"], "issuer_ir")


class CleanBlurbTest(unittest.TestCase):
    def test_banned_catalyst_source_is_hard_error(self):
        blurb = {"news_summary": "x", "catalysts": [
            {"date": None, "what": "w", "source": "https://www.fool.com/a",
             "confirmed": False}], "sources": []}
        with self.assertRaises(AssemblyError):
            clean_symbol_blurb("VST", blurb)

    def test_keeps_only_known_keys(self):
        blurb = {"news_summary": "x", "sentiment": "bull", "extra": 1,
                 "sources": ["https://insidelines.pjm.com/a"]}
        cleaned = clean_symbol_blurb("VST", blurb)
        self.assertNotIn("extra", cleaned)
        self.assertEqual(cleaned["sentiment"], "bull")


class BuildContextTest(unittest.TestCase):
    def _inputs(self):
        return {
            "market": {"market": {"summary": "s. more.", "regime": "mixed",
                                  "notes": ["n1"]},
                       "symbols": {}, "market_sources": []},
            "symbol_research": {
                "NVDA": {"symbol": "NVDA", "news_summary": "x",
                         "sentiment": "bull", "catalysts": [],
                         "move_thesis": "y", "sources": [],
                         "claims": [_claim()]},
            },
        }

    def test_builds_validated_context(self):
        ctx = build_context(
            as_of="2026-07-24", researched_on="2026-07-25",
            candidate_ids=["NVDA:long_call:2026-08-07:212.50"],
            inputs=self._inputs(),
        )
        self.assertEqual(ctx["as_of"], "2026-07-24")
        ann = ctx["annotations"]["NVDA:long_call:2026-08-07:212.50"]
        self.assertEqual(ann["market_as_of_date"], "2026-07-24")
        self.assertTrue(ann["claims"])
        self.assertIn("LLM-asserted", ctx["provenance"])

    def test_candidate_without_research_is_omitted_not_invented(self):
        ctx = build_context(
            as_of="2026-07-24", researched_on="2026-07-25",
            candidate_ids=["NVDA:long_call:2026-08-07:212.50",
                           "NOW:long_call:2026-08-07:103.00"],
            inputs=self._inputs(),
        )
        self.assertNotIn("NOW:long_call:2026-08-07:103.00", ctx["annotations"])

    def test_never_emits_legacy_top_picks(self):
        ctx = build_context(
            as_of="2026-07-24", researched_on="2026-07-25",
            candidate_ids=["NVDA:long_call:2026-08-07:212.50"],
            inputs=self._inputs(),
        )
        self.assertNotIn("top_picks", ctx)
        self.assertNotIn("legacy_top_picks_unusable", ctx)

    def test_schema_violation_surfaces_as_assembly_error(self):
        inputs = self._inputs()
        inputs["symbol_research"]["NVDA"]["claims"][0]["countercase"] = ""
        with self.assertRaises(AssemblyError):
            build_context(as_of="2026-07-24", researched_on="2026-07-25",
                          candidate_ids=["NVDA:long_call:2026-08-07:212.50"],
                          inputs=inputs)


class CheckHtmlTest(unittest.TestCase):
    def test_flags_every_stale_marker(self):
        html = ("annotations are from 2026-07-15 ... do not match any card "
                "... Research evidence incomplete ... Research evidence stale")
        problems = check_dashboard_html(html)
        self.assertEqual(len(problems), 4)

    def test_clean_html_passes(self):
        self.assertEqual(check_dashboard_html("all good ✓ Research evidence · complete"), [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m unittest tests.test_research_context_assemble -v`
Expected: FAIL/ERROR with `ModuleNotFoundError: No module named 'tools.research_context_assemble'` (confirm `tools/` has an `__init__.py`; if it does not, create an empty one and note it in the commit).

- [ ] **Step 3: Write the implementation**

```python
"""tools/research_context_assemble.py — assemble/validate/verify the
attractiveness research context.

Pure core (no I/O): clean_claims, clean_symbol_blurb, build_context,
check_dashboard_html. CLI wires the core to live repo data:

  uv run python -m tools.research_context_assemble --print-ids
  uv run python -m tools.research_context_assemble --assemble --inputs DIR
  uv run python -m tools.research_context_assemble --verify

Advisory-only by construction: annotations pass through
options_researcher.top3_context.normalize_research_annotations (the same
gate the dashboard uses) and are keyed to candidates the deterministic
board already selected. This module can never add, remove, or reorder a
candidate.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from urllib.parse import urlparse

BANNED_HOSTS = ("reddit.", "youtube.", "youtu.be", "seekingalpha.",
                "medium.", "substack.", "wordpress.", "blogspot.",
                "stocktwits.", "fool.")
PRIMARY_TIERS = frozenset({"issuer_ir", "sec_filing", "regulator",
                           "market_operator"})
CLAIM_FIELDS = ("id", "text", "classification", "source_url",
                "unknown_rationale", "source_tier", "fact_date",
                "date_certainty", "countercase")
BLURB_FIELDS = ("news_summary", "sentiment", "catalysts", "move_thesis",
                "sources")
STALE_MARKERS = ("annotations are from", "do not match any card",
                 "Research evidence incomplete", "Research evidence stale")


class AssemblyError(ValueError):
    """A refusal: malformed or policy-violating research input."""


def _host(url: str) -> str:
    return (urlparse(url).netloc or "").lower()


def _check_url(url, *, where: str) -> None:
    if url is None:
        return
    if any(b in _host(url) for b in BANNED_HOSTS):
        raise AssemblyError(f"{where}: banned source host {_host(url)}")


def clean_claims(symbol: str, claims: list) -> list[dict]:
    out = []
    for i, raw in enumerate(claims):
        where = f"{symbol}.claims[{i}]"
        claim = {k: raw.get(k) for k in CLAIM_FIELDS}
        if (claim.get("date_certainty") == "confirmed"
                and claim.get("source_tier") not in PRIMARY_TIERS):
            raise AssemblyError(
                f"{where}: confirmed date without primary tier")
        _check_url(claim.get("source_url"), where=where)
        out.append(claim)
    return out


def clean_symbol_blurb(symbol: str, blurb: dict) -> dict:
    keep = {k: blurb.get(k) for k in BLURB_FIELDS
            if blurb.get(k) is not None}
    for i, cat in enumerate(keep.get("catalysts") or []):
        _check_url(cat.get("source"), where=f"{symbol}.catalysts[{i}]")
    for i, url in enumerate(keep.get("sources") or []):
        _check_url(url, where=f"{symbol}.sources[{i}]")
    return keep


def build_context(*, as_of: str, researched_on: str,
                  candidate_ids: list[str], inputs: dict) -> dict:
    """Build the context dict from researcher output; validate through the
    dashboard's own annotation gate. inputs = {"market": {...},
    "symbol_research": {SYMBOL: {...incl. claims...}}}."""
    from options_researcher.top3_context import (
        AnnotationValidationError, normalize_research_annotations)

    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    annotations: dict[str, dict] = {}
    for cid in candidate_ids:
        symbol = cid.split(":", 1)[0]
        agent = (inputs.get("symbol_research") or {}).get(symbol)
        if agent is None:
            continue  # honest omission renders "evidence incomplete"
        annotations[cid] = {
            "research_as_of_utc": ts,
            "market_as_of_date": as_of,
            "claims": clean_claims(symbol, agent.get("claims") or []),
        }
    try:
        normalize_research_annotations(candidate_ids, annotations)
    except AnnotationValidationError as e:
        raise AssemblyError(f"annotation schema rejection: {e}") from e

    symbols: dict[str, dict] = {}
    for symbol, agent in (inputs.get("symbol_research") or {}).items():
        symbols[symbol] = clean_symbol_blurb(symbol, agent)
    market_block = (inputs.get("market") or {})
    for symbol, blurb in (market_block.get("symbols") or {}).items():
        symbols.setdefault(symbol, clean_symbol_blurb(symbol, blurb))

    market = market_block.get("market") or {}
    return {
        "as_of": as_of,
        "provenance": ("LLM-asserted (Claude subagents, web research "
                       f"{researched_on})"),
        "researched_on": researched_on,
        "market": {k: market.get(k) for k in ("summary", "regime", "notes")},
        "market_sources": market_block.get("market_sources") or [],
        "symbols": symbols,
        "annotations": annotations,
    }


def check_dashboard_html(html: str) -> list[str]:
    """Return the stale-research markers present in rendered HTML."""
    return [m for m in STALE_MARKERS if m in html]


# ---------------------------------------------------------------- CLI --

def _live_board():
    from options_researcher.attractiveness_dashboard import (
        assemble, select_qm_top_picks, select_top_picks)
    from options_researcher.qm_dashboard import load_qm_context

    data = assemble()
    as_of = data.get("data_as_of")
    if not as_of:
        raise SystemExit("no data_as_of on the assembled board -- refusing")
    qm = load_qm_context(as_of)
    ids: list[str] = []
    for p in select_top_picks(data, include_csp_watch=True):
        ids.append(p["card"]["top3_snapshot"]["candidate_id"])
    for p in select_qm_top_picks(data, qm, include_csp_watch=True):
        cid = p["card"]["top3_snapshot"]["candidate_id"]
        if cid not in ids:
            ids.append(cid)
    return data, as_of, ids


def _cmd_print_ids() -> None:
    from options_researcher.attractiveness_dashboard import pinned_picks

    data, as_of, ids = _live_board()
    pinned = [p["symbol"] for p in pinned_picks(data)]
    print(json.dumps({"data_as_of": as_of, "candidate_ids": ids,
                      "pinned_symbols": pinned}))


def _cmd_assemble(inputs_dir: str) -> None:
    _data, as_of, ids = _live_board()
    with open(os.path.join(inputs_dir, "market.json")) as f:
        market = json.load(f)
    symbol_research = {}
    for name in sorted(os.listdir(inputs_dir)):
        if name == "market.json" or not name.endswith(".json"):
            continue
        with open(os.path.join(inputs_dir, name)) as f:
            blob = json.load(f)
        if blob.get("symbol"):
            symbol_research[blob["symbol"]] = blob
    ctx = build_context(
        as_of=as_of,
        researched_on=datetime.now(timezone.utc).date().isoformat(),
        candidate_ids=ids,
        inputs={"market": market, "symbol_research": symbol_research},
    )
    out = os.path.join("reports", "attractiveness_context", f"{as_of}.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    tmp = f"{out}.{os.getpid()}.tmp"
    with open(tmp, "w") as f:
        json.dump(ctx, f, indent=1)
        f.write("\n")
    os.replace(tmp, out)
    covered = len(ctx["annotations"])
    print(f"wrote {out} (annotations {covered}/{len(ids)})")


def _cmd_verify() -> None:
    _data, as_of, _ids = _live_board()
    ctx_path = os.path.join("reports", "attractiveness_context",
                            f"{as_of}.json")
    if not os.path.exists(ctx_path):
        raise SystemExit(f"missing {ctx_path}")
    html_path = os.path.join(".tmp", "dashboard", "attractiveness.html")
    with open(html_path) as f:
        problems = check_dashboard_html(f.read())
    if problems:
        raise SystemExit("stale markers still present: " + "; ".join(problems))
    print(f"verify OK: {ctx_path} matches board and no stale markers remain")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--print-ids", action="store_true")
    group.add_argument("--assemble", action="store_true")
    group.add_argument("--verify", action="store_true")
    parser.add_argument("--inputs", help="directory of researcher JSON files")
    args = parser.parse_args()
    if args.print_ids:
        _cmd_print_ids()
    elif args.assemble:
        if not args.inputs:
            parser.error("--assemble requires --inputs DIR")
        _cmd_assemble(args.inputs)
    else:
        _cmd_verify()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m unittest tests.test_research_context_assemble -v`
Expected: all tests PASS.

- [ ] **Step 5: Lint + types, then commit**

Run: `uv run ruff check tools/research_context_assemble.py tests/test_research_context_assemble.py` (fix anything it reports; double quotes, 100 cols).

```bash
git add tools/research_context_assemble.py tests/test_research_context_assemble.py
git commit -m "feat(research-refresh): context assembler with offline tests"
```

### Task 2: Live-CLI smoke check (manual, not a unittest)

**Files:** none (verification only)

- [ ] **Step 1: Print IDs against the live board**

Run: `uv run python -m tools.research_context_assemble --print-ids 2>/dev/null | tail -1`
Expected: one JSON line with `data_as_of` `2026-07-24` (until the next ritual advances it) and 3 candidate ids.

- [ ] **Step 2: Verify current state passes**

Run: `uv run python -m tools.research_context_assemble --verify 2>/dev/null | tail -1`
Expected: `verify OK: ...` (the 2026-07-24 context and clean board exist from commit `c742cf1`'s session). If this fails, STOP and report — do not proceed to Task 3 with a broken baseline.

### Task 3: Headless-agent skill

**Files:**
- Create: `.claude/skills/research-refresh/SKILL.md`

- [ ] **Step 1: Write the skill**

````markdown
---
name: research-refresh
description: Scheduled/manual refresh of the attractiveness board's research layer — derive today's hero candidates, web-research them, assemble and validate reports/attractiveness_context/<as-of>.json, rebuild the dashboard, verify. Runs headless from tools/research_refresh.sh; also usable interactively.
---

# Research refresh (attractiveness board)

You are refreshing the ADVISORY research layer. You cannot and must not
change which candidates the board shows — only annotate them. All output
is provenance-labeled LLM-asserted. Work from the repo root.

## Procedure

1. **Derive the board state** (never guess strikes/expiries):
   `uv run python -m tools.research_context_assemble --print-ids`
   → gives `data_as_of`, `candidate_ids`, `pinned_symbols`.

2. **Prepare a work dir**: `.tmp/research_refresh/work/<data_as_of>/`
   (create it; clear any older files inside it).

3. **Research each unique hero symbol** (from candidate_ids) and each
   pinned symbol, plus the market backdrop. Use parallel Task subagents
   when available, otherwise do it sequentially yourself with WebSearch +
   WebFetch. For each hero symbol write `<symbol>.json` (lowercase) in
   the work dir; write `market.json` for the backdrop + pinned blurbs.
   Every fact must come from a live fetch THIS session — never from
   training memory. File shapes:

   `<symbol>.json`: {"symbol", "news_summary", "sentiment"
   (bull|bear|neutral), "catalysts": [{"date"|null, "what", "source",
   "confirmed": bool}], "move_thesis", "sources": [urls],
   "claims": [2-3 claim objects]}

   claim: {"id", "text", "classification": fact|derived_calculation|
   inference|unknown, "source_url"|null, "unknown_rationale"|null
   (EXACTLY one of the two non-null), "source_tier": issuer_ir|
   sec_filing|regulator|market_operator|secondary|unknown, "fact_date"
   (null only when date_certainty=unknown), "date_certainty":
   confirmed|estimated|unknown, "countercase" (required)}.

   `market.json`: {"market": {"summary", "regime": risk_on|risk_off|
   mixed, "notes": [..]}, "symbols": {PINNED: blurb-shape-without-
   claims}, "market_sources": [urls]}

   Source rules (hard): no blogs/Reddit/YouTube/Seeking Alpha/Motley
   Fool/forums. "confirmed" date_certainty ONLY with a primary tier
   (issuer_ir/sec_filing/regulator/market_operator) AND a URL you
   fetched. Financial press = "secondary" + "estimated". Cite only URLs
   actually fetched. If unverifiable: omit it, or classification
   "unknown" with unknown_rationale and NO source_url. The single
   highest-value claim per card is earnings timing vs the card's expiry.
   Catalyst "confirmed": true only when its source URL is primary.

4. **Assemble + validate**:
   `uv run python -m tools.research_context_assemble --assemble --inputs .tmp/research_refresh/work/<data_as_of>`
   If it refuses (AssemblyError), fix the offending researcher JSON
   honestly (downgrade certainty, remove banned source, drop the claim)
   and re-run. Never weaken a rule to make it pass.

5. **Rebuild + verify**:
   `uv run python -m options_researcher.attractiveness_dashboard`
   `uv run python -m tools.research_context_assemble --verify`

6. **Report**: final message is exactly one line —
   `RESEARCH_REFRESH RESULT: OK as_of=<date> annotations=<n>/<n>` or
   `RESEARCH_REFRESH RESULT: FAILED <one-line reason>`. Do not commit;
   the context file is committed by humans/sessions.
````

- [ ] **Step 2: Sanity-check the skill loads**

Run: `ls .claude/skills/research-refresh/SKILL.md && head -5 .claude/skills/research-refresh/SKILL.md`
Expected: file exists with frontmatter.

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/research-refresh/SKILL.md
git commit -m "feat(research-refresh): headless refresh skill"
```

### Task 4: Refresh entry script

**Files:**
- Create: `tools/research_refresh.sh` (mode 755)
- Modify: `.gitignore` (add `.research-refresh-off` under the session-scratch section)

- [ ] **Step 1: Write the script**

```zsh
#!/bin/zsh
# Scheduled research refresh — spec amendment "2026-07-25 (owner-directed):
# scheduled research refresh" in docs/superpowers/specs/2026-07-16-
# attractiveness-v2-technicals-context-design.md. Display-layer ONLY: it
# converges chain/feature freshness, runs a headless Sonnet session to
# rebuild reports/attractiveness_context/<as-of>.json, rebuilds the
# dashboard, verifies. It NEVER touches H7 receipts/gates/ledger, never
# commits, never pushes. Kill-switch: .research-refresh-off at repo root.
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
REPO="${0:A:h:h}"
UV="$HOME/.local/bin/uv"
CLAUDE="$HOME/.local/bin/claude"
cd "$REPO" || exit 2

LOGDIR="$REPO/.tmp/research_refresh"
mkdir -p "$LOGDIR"
STAMP="$(date +%Y-%m-%d_%H%M)"
LOG="$LOGDIR/${STAMP}.log"
exec > "$LOG" 2>&1
echo "=== research refresh ${STAMP} ==="

if [ -f "$REPO/.research-refresh-off" ]; then
  echo "DISABLED by .research-refresh-off — exiting 0"; exit 0
fi

HOUR="$(TZ=America/New_York date +%H)"
if [ "$HOUR" -lt 12 ]; then SLOT="premarket"; else SLOT="postclose"; fi
[ "$(TZ=America/New_York date +%u)" = 6 ] && SLOT="weekend"

# --- Stage 1: converge data freshness (no-ops when already current) ---
"$UV" run python data/recent_topup.py --scope h7 --refresh-closes \
  || echo "WARN: h7 topup failed — continuing on cached data"
"$UV" run python data/recent_topup.py --scope display-extra --refresh-closes \
  || echo "WARN: display-extra topup failed — continuing"
AS_OF="$("$UV" run python -m tools.research_context_assemble --print-ids 2>/dev/null \
  | tail -1 | "$UV" run python -c 'import json,sys; print(json.load(sys.stdin)["data_as_of"])')"
if [ -z "$AS_OF" ]; then
  echo "CRITICAL: could not resolve board data_as_of"; exit 1
fi
RECEIPT="$LOGDIR/receipt_${AS_OF}_${SLOT}.json"
if [ -f "$RECEIPT" ]; then
  echo "SKIP: ${SLOT} refresh for ${AS_OF} already succeeded (${RECEIPT})"; exit 0
fi
"$UV" run python -c "from options_researcher.features import build_all; from options_researcher.h7_scope import watch_universe; build_all('$AS_OF', symbols=watch_universe())" \
  || { echo "CRITICAL: watch feature rebuild failed"; exit 1; }
"$UV" run python -c "from config import ATTRACTIVENESS_EXTRA_NAMES; from options_researcher.features import build_all; build_all('$AS_OF', symbols=ATTRACTIVENESS_EXTRA_NAMES)" \
  || echo "WARN: display-extra features failed (non-blocking)"
"$UV" run python -m options_researcher.qm_dashboard --refresh-ohlcv --as-of "$AS_OF" \
  || echo "WARN: QM OHLCV refresh failed (QM cards will show DATA BLOCKED)"

# --- Stage 2: headless research session (Sonnet, hard dollar cap) ---
"$CLAUDE" -p "/research-refresh" \
  --model sonnet \
  --max-budget-usd 8 \
  --allowedTools "Bash Read Write Edit Grep Glob WebSearch WebFetch Task TodoWrite Skill" \
  > "$LOGDIR/claude_${STAMP}.out" 2>&1
CLAUDE_RC=$?
tail -3 "$LOGDIR/claude_${STAMP}.out"
if [ "$CLAUDE_RC" -ne 0 ]; then
  echo "CRITICAL: headless research session exit ${CLAUDE_RC}"; exit 1
fi

# --- Stage 3: independent verification (never trust the agent's own OK) ---
"$UV" run python -m options_researcher.attractiveness_dashboard \
  || { echo "CRITICAL: dashboard rebuild failed"; exit 1; }
if "$UV" run python -m tools.research_context_assemble --verify; then
  echo "{\"as_of\": \"${AS_OF}\", \"slot\": \"${SLOT}\", \"stamp\": \"${STAMP}\", \"status\": \"ok\"}" > "$RECEIPT"
  echo "RESULT: OK ${AS_OF} ${SLOT}"
  echo "NOTE: context file left uncommitted by design; commit it in a session"
else
  echo "CRITICAL: verification failed — board keeps honest stale banners"; exit 1
fi
```

- [ ] **Step 2: Make it executable and add the kill-switch to .gitignore**

Run: `chmod +x tools/research_refresh.sh`
In `.gitignore`, next to the existing session-scratch entries, add a line: `.research-refresh-off`

- [ ] **Step 3: Dry-run the guards (no claude invocation)**

Run: `touch .research-refresh-off && zsh tools/research_refresh.sh; echo "exit=$?"; cat .tmp/research_refresh/*.log | tail -3; rm .research-refresh-off`
Expected: `exit=0` and the newest log ends with `DISABLED by .research-refresh-off — exiting 0`.

- [ ] **Step 4: Commit**

```bash
git add tools/research_refresh.sh .gitignore
git commit -m "feat(research-refresh): scheduled refresh entry script"
```

### Task 5: LaunchAgent template

**Files:**
- Create: `tools/launchd/com.carsyn.options-validator.research-refresh.plist`

- [ ] **Step 1: Write the plist** (paths reference the MAIN checkout — the copy the owner reads; the ops worktree keeps only the deterministic ritual)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.carsyn.options-validator.research-refresh</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/zsh</string>
    <string>/Users/carsynstephenson/options-validator/tools/research_refresh.sh</string>
  </array>
  <key>StandardOutPath</key>
  <string>/Users/carsynstephenson/options-validator/.tmp/research_refresh/launchd.out</string>
  <key>StandardErrorPath</key>
  <string>/Users/carsynstephenson/options-validator/.tmp/research_refresh/launchd.err</string>
  <key>StartCalendarInterval</key>
  <array>
    <dict><key>Weekday</key><integer>1</integer><key>Hour</key><integer>7</integer><key>Minute</key><integer>40</integer></dict>
    <dict><key>Weekday</key><integer>2</integer><key>Hour</key><integer>7</integer><key>Minute</key><integer>40</integer></dict>
    <dict><key>Weekday</key><integer>3</integer><key>Hour</key><integer>7</integer><key>Minute</key><integer>40</integer></dict>
    <dict><key>Weekday</key><integer>4</integer><key>Hour</key><integer>7</integer><key>Minute</key><integer>40</integer></dict>
    <dict><key>Weekday</key><integer>5</integer><key>Hour</key><integer>7</integer><key>Minute</key><integer>40</integer></dict>
    <dict><key>Weekday</key><integer>1</integer><key>Hour</key><integer>16</integer><key>Minute</key><integer>45</integer></dict>
    <dict><key>Weekday</key><integer>2</integer><key>Hour</key><integer>16</integer><key>Minute</key><integer>45</integer></dict>
    <dict><key>Weekday</key><integer>3</integer><key>Hour</key><integer>16</integer><key>Minute</key><integer>45</integer></dict>
    <dict><key>Weekday</key><integer>4</integer><key>Hour</key><integer>16</integer><key>Minute</key><integer>45</integer></dict>
    <dict><key>Weekday</key><integer>5</integer><key>Hour</key><integer>16</integer><key>Minute</key><integer>45</integer></dict>
    <dict><key>Weekday</key><integer>6</integer><key>Hour</key><integer>9</integer><key>Minute</key><integer>0</integer></dict>
  </array>
</dict>
</plist>
```

- [ ] **Step 2: Validate the XML**

Run: `plutil -lint tools/launchd/com.carsyn.options-validator.research-refresh.plist`
Expected: `OK`.

- [ ] **Step 3: Commit** (do NOT install/register in this task)

```bash
git add tools/launchd/com.carsyn.options-validator.research-refresh.plist
git commit -m "feat(research-refresh): launchd schedule template (not yet registered)"
```

### Task 6: Docs sync

**Files:**
- Modify: `docs/research-context-refresh-runbook.md` (Cadence section)
- Modify: `CLAUDE.md` (Commands section — one line)

- [ ] **Step 1: Update the runbook's Cadence section** — replace the "If the owner ever wants this automated…" paragraph with the actual automation: schedule (Mon–Fri 07:40 & 16:45 ET, Sat 09:00 ET), LaunchAgent label, kill-switch (`touch .research-refresh-off`), receipts/logs location (`.tmp/research_refresh/`), and the note that the manual procedure above remains the fallback when the automation is off or red. Cite the spec amendment (owner-directed 2026-07-25).

- [ ] **Step 2: Add one line to CLAUDE.md's Commands block** after the attractiveness_dashboard line:

```
uv run python -m tools.research_context_assemble --verify  # research-context freshness check; tools/research_refresh.sh runs the scheduled LLM refresh (kill-switch: .research-refresh-off)
```

- [ ] **Step 3: Commit**

```bash
git add docs/research-context-refresh-runbook.md CLAUDE.md
git commit -m "docs(research-refresh): runbook + commands for scheduled refresh"
```

### Task 7: Full-suite gate (before any registration)

- [ ] **Step 1: Run the full test suite**

Run: `uv run python -m unittest discover -s tests` — exit code is the verdict.
Expected: OK. If anything fails that you did not cause, STOP and report; do not "fix" unrelated tests.

- [ ] **Step 2: Lint gate**

Run: `uv run ruff check .`
Expected: clean.

### Task 8: HELD FOR ORCHESTRATOR — live E2E + registration

Do NOT perform this task in a subagent. The orchestrating session (Fable) runs it after adversarial review passes: one manual `zsh tools/research_refresh.sh` live run (proves headless auth + web research + verify end-to-end, ~$3–8), then `cp` the plist to `~/Library/LaunchAgents/` and `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.carsyn.options-validator.research-refresh.plist`, then `launchctl list | grep research-refresh`. Registration is LAST, after everything else is green (2026-07-15 hook-lockout lesson).
