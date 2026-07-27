---
name: research-refresh
description: Produce an advisory attractiveness-research v2 bundle only after an exact-session daily-ritual preflight succeeds.
---

# Research refresh (attractiveness board)

This workflow annotates a deterministic board. It does not fetch market data,
run topups, build features, refresh QM, change candidate membership, or change
any hypothesis receipt, threshold, gate, ranking, or verdict.

`RESEARCH_RITUAL_ROOT` must identify the authoritative checkout that ran the
daily ritual. `RESEARCH_RUN_DATE` is interpreted in `America/New_York`.

## Procedure

1. Read the immutable board identity:

   `uv run python -m tools.research_context_assemble --print-ids`

   Record `data_as_of`, every exact `candidate_id`, and every `pinned_symbol`.
   Never guess or rewrite strikes, expirations, or membership.

2. Repeat the fail-closed ritual preflight inside this session:

   `uv run python -m tools.research_context_assemble --preflight --as-of <data_as_of>`

   If it returns `UPSTREAM_BLOCKED`, stop. Do not research and do not invoke
   another agent. The outer runner performs this check before launching Claude;
   this repeat prevents a time-of-check/time-of-use gap. The gate requires both
   the per-hypothesis capture receipt and
   `reports/ritual/run_status_<data_as_of>.json` with
   `schema_version: daily_ritual/run_status/v1`, `status: OK`, a full ritual
   `code_sha`, and the matching capture-receipt path and SHA. Successful
   per-hypothesis statuses alone are insufficient.

3. Create a new run directory without deleting prior evidence:

   `mkdir -p .tmp/research_refresh/work/<data_as_of>`

   `mktemp -d .tmp/research_refresh/work/<data_as_of>/run.XXXXXX`

4. Research the market and every required symbol. Required symbols are the
   unique hero symbols from `candidate_ids`, all `pinned_symbols`, plus `VST`
   and `CEG`. Use parallel Task subagents when available. Every factual source
   must be fetched during this run; never cite training memory or an unfetched
   URL.

   Write one lowercase `<symbol>.json` packet for every required symbol and one
   `market.json` packet into the new run directory.

   Symbol packet:

   `{"symbol", "news_summary", "sentiment", "catalysts", "move_thesis", "sources", "claims"}`

   Claim:

   `{"id", "text", "classification", "source_url", "unknown_rationale", "source_tier", "fact_date", "date_certainty", "countercase"}`

   Every candidate packet needs at least one claim backed by a primary tier:
   `issuer_ir`, `sec_filing`, `regulator`, or `market_operator`. Every claim and
   catalyst URL must also appear in that symbol packet's `sources` list.

   Market packet:

   `{"market": {"summary", "regime", "notes"}, "symbols": {}, "market_sources": [urls]}`

5. Apply these source and calendar rules without exception:

   - No blogs, Reddit, YouTube, Seeking Alpha, Motley Fool, forums, or social
     posts.
   - `date_certainty: confirmed` requires a fetched primary source URL.
   - `confirmed: true` catalysts require an ISO date and a fetched primary
     source.
   - If a fact is unverifiable, omit it or mark it `unknown` with a concise
     `unknown_rationale`; never fill a gap from memory.
   - VST and CEG must each include exactly one next-auction catalyst with
     `"id": "PJM_BRA_NEXT"`, `"confirmed": false`, and a direct official
     `pjm.com` source URL. Keep the date null until PJM publishes the exact
     schedule.
   - Match catalyst timing to the exact option expiration in each candidate ID.
     Treat theta, IV, liquidity, and spread effects as risks unless the packet
     contains measured canonical evidence.

6. Assemble and validate the bundle:

   `uv run python -m tools.research_context_assemble --assemble --inputs <run_dir>`

   The producer copies the exact packets into the durable lineage directory,
   renders `reports/<data_as_of>-attractiveness-research-context.md` from JSON,
   and publishes
   `reports/attractiveness_research/<data_as_of>/manifest.json` last. A repeated
   byte-identical input identity returns `NO_NEW_INPUT` without rewriting
   timestamps or artifacts.

7. Rebuild and verify:

   `uv run python -m tools.research_context_assemble --verify --bundle-only`

   `uv run python -m options_researcher.attractiveness_dashboard`

   `uv run python -m tools.research_context_assemble --verify`

   Verification re-hashes the ritual receipt, underlying ritual evidence,
   mutable latest ritual-run status, copied source packets, machine context,
   and Markdown; checks exact live candidate coverage, ET/UTC temporal parity,
   source linkage, and both `PJM_BRA_NEXT` entries.

8. Final output is exactly one line:

   `RESEARCH_REFRESH RESULT: OK as_of=<date> annotations=<n>/<n>`

   or

   `RESEARCH_REFRESH RESULT: FAILED <one-line reason>`

Do not commit, push, enable a schedule, or mutate the authoritative ritual
checkout.
