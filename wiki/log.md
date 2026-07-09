# Options Validator Wiki Log

Chronological, append-only record of wiki operations. Each entry starts with
`## [YYYY-MM-DD] <op> | <summary>` so it is greppable with
`grep "^## \\[" wiki/log.md`.

## [2026-07-08] setup | Add LLM Wiki pattern source and wiki scaffold

Added `wiki/raw/llm-wiki.md` as the immutable source pattern and created the
initial `wiki/index.md` / `wiki/log.md` scaffold for future derived pages.
