# Options Validator Wiki Log

Chronological, append-only record of wiki operations. Each entry starts with
`## [YYYY-MM-DD] <op> | <summary>` so it is greppable with
`grep "^## \\[" wiki/log.md`.

## [2026-07-08] setup | Add LLM Wiki pattern source and wiki scaffold

Added `wiki/raw/llm-wiki.md` as the immutable source pattern and created the
initial `wiki/index.md` / `wiki/log.md` scaffold for future derived pages.


## [2026-07-25] ingest | RAG health

RAG health indexed 409 sources and 8831 chunks; 0 source failures were reported.


## [2026-07-25] ingest | RAG health

RAG health indexed 409 sources and 8831 chunks; 0 source failures were reported.

## [2026-07-25] ingest | First five derived pages: hypotheses, data-layer, automation, dashboards, decisions

Created the first real derived wiki pages (scaffold-only since 2026-07-08):
`hypotheses.md` (H5/H6/H7/H8/H10 registered forward-paper hypotheses plus
H9/RQ1 spent one-run studies, plain-English for an options-beginner owner),
`data-layer.md` (chain cache, closes stores incl. QQQ/SPY, earnings gating
store, rates CSVs, the sealed blind/in-sample split, the remote-MDDS keyed
adapter path per `tools/daily_ritual.sh:56-61`), `automation.md` (07:10
daily ritual step order + fail-closed semantics, 5x/day intraday capture,
the 2026-07-25 repo-RAG health agent, ops-checkout branch guard),
`dashboards.md` (the two static pages, the live-preview server, the
bookmark-and-refresh decision per `docs/dashboard-architecture.md`), and
`decisions.md` (four-name pivot, H7 15-name scope / 9-name immutable
cohort, OI-line v1/v2, RQ2 delegated values, the 2026-07-25 readiness
verdict). All five cross-link via `[[wikilinks]]` and cite canonical paths
rather than restate them as authority. Updated `wiki/index.md`'s Project
Pages list. No contradictions found against `docs/options-validator-readiness.md`
during sourcing; sources used: `README.md`, `docs/options-validator-readiness.md`,
`docs/monday-runbook.md`, `docs/dashboard-architecture.md`,
`docs/codex-implementation-plan.md`, `config.py`, `ledger/facts.log`
(grepped for registrations), `ledger/h7_forward/events.jsonl`,
`ledger/experiments.jsonl`, `reports/` (h9, rq1), `tools/daily_ritual.sh`,
`ideas-parking-lot.md`.


## [2026-07-25] ingest | RAG health

RAG health indexed 413 sources and 8910 chunks; 0 source failures were reported.


## [2026-07-29] ingest | RAG health

RAG health indexed 427 sources and 9119 chunks; 0 source failures were reported.

## [2026-08-01] lint | Align the Obsidian skill with the repo-local LLM wiki

Replaced the obsolete Windows vault path and flat-note rules in the shared
`obsidian-vault` skill with the repo-local `wiki/` contract, immutable
`wiki/raw/` boundary, index/log workflows, worktree-aware vault resolution,
and validation against Obsidian's registered macOS vault path.


## [2026-08-02] ingest | RAG health

RAG health indexed 549 sources and 13137 chunks; 0 source failures were reported.


## [2026-08-05] ingest | RAG health

RAG health indexed 594 sources and 14879 chunks; 0 source failures were reported.


## [2026-08-09] ingest | RAG health

RAG health indexed 594 sources and 14879 chunks; 0 source failures were reported.
