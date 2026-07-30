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

When this refresh completes, offer to run independent-research-critic on the new report.
