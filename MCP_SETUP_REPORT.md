# MCP and market-data setup report

Status date: 2026-07-20  
Operating system: macOS 14.6.1, Apple Silicon arm64  
Shell: zsh  
Project root: `/Users/carsynstephenson/options-validator`  
Project language/package manager: Python 3.12 project managed by uv; Node/npm/npx are present for MCP packages.

## Prerequisites

| Check | Result |
|---|---|
| Git | present at `/usr/bin/git` |
| Codex CLI | present at `/Applications/ChatGPT.app/Contents/Resources/codex` |
| Node/npm/npx | Node 22.23.1, npm 10.9.8, npx present |
| Python | Python 3.14.4 system interpreter; project declares `>=3.12,<3.13` and uv resolves the project environment |
| uv | uv 0.11.29 |
| Serena | serena-agent 1.6.0 |
| Playwright | project package 1.61.1; Chromium binary already installed |

## MCP servers

`codex mcp list` shows all requested servers as enabled. Local stdio packages
were launched for an 8-second startup smoke test and stayed alive; no tool call
was made with a credential or live trade capability.

| Server | Configuration | Result |
|---|---|---|
| context7 | `npx -y @upstash/context7-mcp` | registered; startup smoke test passed; no key required |
| github | official `https://api.githubcopilot.com/mcp/` | registered; bearer binding present; credential-gated test pending |
| filesystem | official filesystem package scoped to PROJECT_ROOT | registered; startup smoke test passed; direct boundary read test remains a Codex-client operation |
| playwright | repo-local guarded proxy -> official `npx -y @playwright/mcp@latest --headless --isolated` | registered; MCP handshake passed; 22 safe tools exposed; `browser_evaluate` and `browser_run_code_unsafe` filtered and rejected |
| sequential-thinking | official sequential-thinking package | registered; startup smoke test passed |
| serena | official `serena-agent` MCP server | registered; 222 Python files indexed; health check passed |
| tavily | `npx -y tavily-mcp@latest` | registered; startup smoke test passed; API/OAuth credential pending |
| exa | official hosted `https://mcp.exa.ai/mcp` | registered; Codex reported OAuth login successful |
| alphavantage | official hosted `https://mcp.alphavantage.co/mcp` | registered; OAuth URL emitted but authorization is pending |

The current Codex CLI does not provide a standalone `tools/list`/`tools/call`
subcommand for arbitrary configured servers. Therefore “enabled” is not being
reported as a successful authenticated tool call. Re-run in a fresh Codex
session after credentials are supplied.

## Configuration backup

Original Codex configuration backup:

`/Users/carsynstephenson/.codex/config.toml.backup-20260719-215655`

No secret values were added to `config.toml`. The registered GitHub server uses
`GITHUB_PAT_TOKEN`; hosted OAuth servers use their client-managed auth stores.

## Project changes

- Added `market_data/` read-only normalized models, provider interface, cache,
  retry/rate-limit transport, and Massive, Alpha Vantage, ThetaData, and
  Schwab adapters.
- Added `market_data/validation.py` for quote, freshness, liquidity, event,
  duplicate, timestamp, and cross-provider checks.
- Added `tests/test_market_data_stack.py` with 11 mocked tests.
- Added `tools/playwright_mcp_readonly_proxy.mjs`, which launches the official
  Playwright MCP server in headless/in-memory mode and blocks arbitrary code
  execution tools at the stdio boundary.
- Added `.env.example` with variable names only.
- Extended `.gitignore` for local secrets, tokens, sessions, and OAuth files.
- Added `MARKET_DATA_PROVIDERS.md` and `SECURITY.md`.

## Missing credentials and approvals

- `GITHUB_PAT_TOKEN`: create a fine-grained GitHub PAT with read-only access to
  only the repository/repositories used by this project. Do not grant write,
  issues, pull-request, or administration permissions unless separately needed.
- `TAVILY_API_KEY`: create/approve a Tavily account key, or complete the
  official hosted OAuth flow. Basic search is the default.
- `ALPHAVANTAGE_API_KEY`: create/approve a free Alpha Vantage key. The official
  MCP authorization page still needs to be completed.
- `MASSIVE_API_KEY`: create/approve a Massive Options Basic account/key;
  `POLYGON_API_KEY` is supported only as a compatibility fallback.
- ThetaData: provide an entitled account credential. The existing repo adapter
  prefers `THETADATA_API_KEY`; `THETADATA_USERNAME`/`THETADATA_PASSWORD` are
  placeholders only until the official account path is selected.
- Schwab: create a Schwab Developer application, obtain app key and secret,
  configure an exact callback URL, and approve read-only account/market-data
  access. No interactive Schwab sign-in was started.

## Exact next commands

From the project root, after filling a local ignored `.env` or exporting the
variables in the process environment:

```bash
cp .env.example .env
# Edit .env locally; do not paste populated contents into chat or Git.

codex mcp list
uv run python -m unittest discover -s tests -p 'test_market_data_stack.py' -v
uv run ruff check market_data tests/test_market_data_stack.py
uv run pyright market_data
```

For GitHub, restart Codex after exporting `GITHUB_PAT_TOKEN`, then perform only
read-only repository identification, branch, commits, issues, and pull-request
checks.

For Alpha Vantage, run `codex mcp login alphavantage` and enter the key only in
the official browser authorization page. For Exa, no further key is required
after the successful OAuth flow.

For Schwab, after the developer app is approved, set the four `SCHWAB_*`
variables, generate an unpredictable local OAuth `state`, call
`SchwabReadOnlyProvider.authorization_url(state)`, complete the owner login at
Schwab, exchange the returned code with
`exchange_authorization_code(code)`, and then run account/quote/chain reads.
Never add order endpoints to this project.

## Verification completed

- `uv run python -m unittest discover -s tests -p 'test_market_data_stack.py' -q`:
  11 tests passed.
- `uv run python -m unittest discover -s tests -q`: 1,592 tests passed in
  253.226 seconds. The suite exercised its existing offline/network-retry and
  H7 fail-closed paths; no test failed.
- `uv run ruff check .`: passed.
- `uv run pyright`: 0 errors, 0 warnings, 0 informations.
- `node --check tools/playwright_mcp_readonly_proxy.mjs`: passed.
- Playwright proxy MCP handshake: 22 safe tools exposed; both arbitrary-code
  tool names absent and direct calls rejected.
- `git diff --check`: passed.

## Existing project issue found

The Downloads checkout is a symlink to the real Git root, so the MCP filesystem
scope must use the resolved path above. Serena's first index attempt hit the
managed global uv-cache restriction; rerunning with
`UV_CACHE_DIR=/private/tmp/options-validator-uv-cache` succeeded. Existing
untracked repository files were preserved and not modified.
