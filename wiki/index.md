# Options Validator Wiki Index

This is the navigation page for the LLM-maintained Obsidian wiki layer.
Canonical project truth still lives in `ledger/`, `data/`, `reports/`,
`docs/superpowers/`, tests, and committed source files.

## Operating Pattern

- [LLM Wiki source pattern](raw/llm-wiki.md) - abstract pattern for maintaining a persistent LLM-written wiki over immutable raw sources.

## Project Pages

- [Hypotheses](hypotheses.md) - the live hypothesis map: H5/H6/H7/H8/H10 (registered forward-paper) plus H9/RQ1 (spent one-run studies), each with registration/receipt/verdict pointers.
- [Data layer](data-layer.md) - chain cache, closes stores, earnings gating store, rates CSVs, the sealed blind/in-sample split, and the remote-MDDS keyed data path.
- [Automation](automation.md) - the 07:10 daily ritual's step order and fail-closed gates, 5x/day intraday capture, the repo-RAG health agent, and why it all runs from the ops checkout.
- [Dashboards](dashboards.md) - the two static dashboard pages, the manual live-preview server, and the bookmark-and-refresh architecture decision.
- [Decisions](decisions.md) - index of standing decisions: the four-name pivot, the H7 scope freeze, OI-line v1/v2, RQ2 delegated values, and the 2026-07-25 readiness verdict.

## Maintenance Notes

- Read this index before answering wiki-oriented questions.
- Keep raw inputs under `wiki/raw/` immutable.
- Add or revise derived wiki pages only when they synthesize project evidence.
- Log every ingest, query result filed as a page, and lint pass in `wiki/log.md`.
