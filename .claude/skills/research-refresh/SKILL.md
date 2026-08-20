---
name: research-refresh
description: Produce an advisory attractiveness-research v2 bundle only after an exact-session daily-ritual preflight succeeds.
disable-model-invocation: true
---

# Research refresh (attractiveness board)

This workflow annotates a deterministic board. It does not fetch market data,
run topups, build features, refresh QM, change candidate membership, or change
any hypothesis receipt, threshold, gate, ranking, or verdict.

`RESEARCH_RITUAL_ROOT` must identify the authoritative checkout that ran the
daily ritual. `RESEARCH_RUN_DATE` is interpreted in `America/New_York`.
`RESEARCH_STARTED_AT` is supplied by the outer producer before this session
starts. `RESEARCH_REFRESH_ATTEMPT_ID` identifies its reserved paid attempt.
Both are required durable lineage.

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
   `schema_version: daily_ritual/run_status/v1`, `status: OK` or `OK_STARVED`, a full ritual
   `code_sha`, and the matching capture-receipt path and SHA. Successful
   per-hypothesis statuses alone are insufficient.

3. Create a new run directory without deleting prior evidence:

   `mkdir -p .tmp/research_refresh/work/<data_as_of>`

   `mktemp -d .tmp/research_refresh/work/<data_as_of>/run.XXXXXX`

4. Research the market and every required symbol. Required symbols are the
   unique hero symbols from `candidate_ids`, all `pinned_symbols`, plus `VST`
   and `CEG`. Use parallel subagents (Claude Code's Agent tool, formerly named
   Task) when available. Every factual source
   must be fetched during this run; never cite training memory or an unfetched
   URL.

   Write one lowercase `<symbol>.json` packet for every required symbol and one
   `market.json` packet into the new run directory.

   Symbol packet:

   `{"symbol", "news_summary", "sentiment", "catalysts", "move_thesis", "sources", "claims"}`

   Claim:

   `{"id", "text", "classification", "source_url", "unknown_rationale", "source_tier", "fact_date", "date_certainty", "countercase"}`

   Source metadata object:

   `{"url", "source_tier", "published_at", "publication_time_unknown_rationale", "retrieved_at_utc"}`

   `published_at` must be a timezone-aware source publication timestamp. If the
   canonical page exposes no timestamp, use null and provide a specific
   `publication_time_unknown_rationale`. `retrieved_at_utc` must be the actual
   UTC fetch time during this research run. Do not backfill either field.

   Every candidate packet needs at least one claim backed by a primary tier:
   `issuer_ir`, `sec_filing`, `regulator`, or `market_operator`. Every claim and
   catalyst URL must have one matching metadata object in that symbol's
   `sources`, with the same `source_tier`.

   Market packet:

   `{"market": {"summary", "regime", "notes"}, "symbols": {}, "market_sources": [source_metadata_objects]}`

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
     `pjm.com` source whose tier is `market_operator`. Keep the date null until
     PJM publishes the exact schedule.
   - Match catalyst timing to the exact option expiration in each candidate ID.
     Treat theta, IV, liquidity, and spread effects as risks unless the packet
     contains measured canonical evidence.

6. Assemble the untrusted pending bundle:

   `uv run python -m tools.research_context_assemble --assemble --inputs <run_dir>`

   The producer copies the exact packets into the durable run directory, binds
   `uv.lock` and the reserved producer attempt ID, records distinct UTC/ET
   research start and finish timestamps, renders
   `reports/<data_as_of>-attractiveness-research-context.md` from JSON, and
   writes only
   `reports/attractiveness_research/<data_as_of>/manifest.pending.json`.
   `manifest.json` is not published here. A repeated byte-identical finalized
   input identity returns `NO_NEW_INPUT` without rewriting timestamps or
   artifacts.

7. Verify the pending bundle, render, finalize, and verify the final marker:

   `uv run python -m tools.research_context_assemble --verify --pending --bundle-only`

   `uv run python -m options_researcher.attractiveness_dashboard`

   `uv run python -m tools.research_context_assemble --finalize`

   `uv run python -m tools.research_context_assemble --verify`

   Finalization refuses stale/incomplete dashboard markers. Only a clean render
   may atomically publish `manifest.json` with `publication_status: FINAL` and
   dashboard verification evidence. Verification re-hashes the ritual receipt,
   underlying ritual evidence, mutable latest ritual-run status, `uv.lock`,
   copied packets, machine context, and Markdown; checks exact live candidate
   coverage, ET/UTC temporal parity, source metadata/linkage, and both
   `PJM_BRA_NEXT` entries.

8. Final output is exactly one line:

   `RESEARCH_REFRESH RESULT: OK as_of=<date> annotations=<n>/<n>`

   or

   `RESEARCH_REFRESH RESULT: FAILED <one-line reason>`

Do not commit, push, enable a schedule, or mutate the authoritative ritual
checkout.
