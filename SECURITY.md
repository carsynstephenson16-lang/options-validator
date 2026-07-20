# Security boundary

## Scope

The project root is `/Users/carsynstephenson/options-validator`. The requested
Downloads path is a symlink to that Git root. Filesystem MCP is registered with
the resolved Git root only; it must not be broadened to the home directory,
Desktop, Documents, Downloads, SSH files, cloud credentials, browser profiles,
or system keychains.

The project remains scanner/research-only. No live trade is submitted, and no
brokerage order endpoint is implemented or tested.

## Credentials

- `.env.example` contains variable names only. Put real values in an ignored
  local `.env` or in the process environment.
- Never place API keys, PATs, app secrets, OAuth codes, access tokens, refresh
  tokens, account identifiers, or passwords in source, Git history, MCP args,
  Codex config, logs, reports, or documentation.
- GitHub MCP uses `GITHUB_PAT_TOKEN` through Codex's bearer-token environment
  binding. Start with a fine-grained, read-only repository token.
- Tavily's local MCP command is registered without an `env` value so the
  process can inherit `TAVILY_API_KEY`; the current Codex CLI does not expose
  the requested `env_vars` list through `codex mcp add`. The official hosted
  OAuth endpoint is the alternative when process-environment inheritance is
  unavailable.
- Alpha Vantage's hosted MCP uses its OAuth page. The direct adapter reads
  `ALPHAVANTAGE_API_KEY` from the process environment.

## OAuth and tokens

Schwab OAuth is scaffolded but not authorized. The callback URL must exactly
match the developer application. `FileTokenStore` rejects paths outside the
project root, writes tokens with mode `0600`, and is covered by `.gitignore`.
The provider has only read methods for account data, positions, quotes, and
option chains.

Exa's Codex OAuth setup completed during this setup through the hosted endpoint;
no API key was written to the project. Any future OAuth cleanup must target the
provider's own credential store, not project files.

## Logging and caching

The HTTP transport never logs request query strings. Cache keys remove known
sensitive parameter names such as `apiKey`, `apikey`, `token`, and
`access_token`; cached raw responses contain provider data and retrieval time,
not credentials. Provider errors contain status and endpoint path only.

Do not commit `.cache/market_data/`, `.secrets/`, token/session/OAuth JSON, or
any populated environment file.

## Browser automation

Playwright is headless and is for local interface tests, public documentation,
and public pages whose terms permit automation. Do not use it for Schwab login,
credential capture, bypassing authentication protections, or scraping broker
pages. The Codex registration invokes the repo-local
`tools/playwright_mcp_readonly_proxy.mjs`, which launches the official server
with `--headless --isolated` and filters/rejects the upstream
`browser_evaluate` and `browser_run_code_unsafe` tools. Do not bypass the proxy
by registering the raw upstream server.

## Verification

The setup tests mock all external APIs. Live-provider tests are intentionally
skipped until credentials and account approvals exist. Before any future
provider use, run the relevant health check, inspect timing/entitlement, and
run `market_data.validation` before allowing data into research code.
