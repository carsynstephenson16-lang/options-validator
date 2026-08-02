---
name: web-fetch-order
description: Choose the right web-fetch tool for a URL you already have — WebFetch vs Trafilatura vs Crawl4AI vs Scrapling — using this repo's measured 2026-07-17 findings, including that WebFetch gets HTTP 403 from SEC EDGAR. Use when quoting a filing, IR page, earnings date, or any table verbatim, or when a fetch came back empty or truncated. Not for discovering an unknown URL (that is WebSearch).
---

# Which fetch tool, in order (measured 2026-07-17, not assumed)

The binding rules for these fetchers live in `.cursorrules` (always loaded):
manual research utilities only, never called from tests, strategy code, or a
trigger path; never used to bypass source terms, rate limits, logins,
paywalls, or bot walls; retain the source URL and capture time; and they
cannot change a hypothesis verdict.

These fetchers are **not** a substitute for WebSearch: neither can discover an
unknown URL from a question. They replace WebFetch once a URL is known.

1. **WebSearch** — discovery only (you don't have the URL yet). No substitute.
2. **WebFetch** — default once the URL is known and a short answer suffices.
   It fetches *and summarizes*: it returned one sentence for a page whose body
   is ~10.5k chars. Never treat its output as verbatim source text.
3. **Trafilatura** — use when WebFetch is not good enough, which for this repo
   is often: **WebFetch gets HTTP 403 from SEC EDGAR** (SEC requires a
   descriptive User-Agent and WebFetch cannot set one), while Trafilatura with
   a UA configured via `use_config()` returns 200. Earnings-date discipline
   runs on SEC/IR primary sources, so this is the tool for quoting a filing,
   an IR page, or any table verbatim (`include_tables=True` recovered a full
   8-K list cleanly). Set a real identifying UA — spoofing a browser UA to
   evade a block is the banned behavior above, not this.
4. **Crawl4AI** — last resort, only after confirming the content is absent from
   the raw HTML (i.e. genuinely JS-rendered). Costs a ~171 MB browser download
   on first use (`crawl4ai-setup`) plus ~3 s/page, and its default
   `PruningContentFilter` silently reduced a real page to 9 characters — check
   output length before trusting it.
5. **Scrapling** — untested here; per above, last-resort static fetching.

Install with `uv sync --extra web-fetchers`.

Firecrawl is out of credits — do not reach for it. First recorded 2026-07-09,
still out on 2026-07-23 (equity-research session note: "Firecrawl out of
credits this session (same as 07-06); all market/peer/SPY data via
`scripts/crawlee_fetch.py` fallback per doctrine"). The `firecrawl-*` skills
still carry recent invocation timestamps — that records the skill being
dispatched, not a successful fetch. Don't read those timestamps as evidence
that credits came back.
