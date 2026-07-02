# rg silently honors .gitignore even for explicit directory arguments — absence claims from a .venv walk are void

**Lesson:** `rg <pattern> /path/to/.venv/...` returns nothing when `.venv` is
gitignored — ripgrep applies the project's ignore chain to directory walks even
when the directory is named explicitly (explicit FILE arguments are exempt).
Use `rg --no-ignore` (or `-uu`) for installed-package searches, and prove API
existence/absence with a runtime probe (`python -c "hasattr(...)"`), never with
a text search alone.

**What happened (2026-07-02):** During Phase-0 verification of installed
lumibot 4.5.63, `rg -ln "def get_greeks" <venv>/lumibot` returned empty, which
became the finding "no greeks anywhere in installed lumibot." A prior session's
memory note ("get_chain_full_info may compute greeks locally") prompted a
`hasattr` probe: `Strategy.get_greeks` and `Strategy.get_chain_full_info` both
exist. In backtesting they delegate to `data_source.calculate_greeks`
(data_source.py:664), which computes MODEL greeks locally. The false negative:
`.venv` is gitignored, so every rg that walked the package directory silently
matched nothing, while every rg that named a specific file worked — which made
the tool look reliable exactly when it wasn't.

**Why it mattered:** The wrong claim ("no greeks at all") was about to go into
the Phase-0 verification doc as a load-bearing design justification. The
corrected claim ("greeks exist but are locally computed model values, not
ThetaData's exchange-derived historical greeks") justifies the same design —
fetch greeks/IV/OI via the adapter — on honest grounds: data over model, not
capability absence. File-scoped findings (no greeks/OI endpoints in
thetadata_helper.py) were unaffected and still stand. Cross-check every
package-wide ABSENCE claim with `--no-ignore` plus a runtime probe before it
becomes a design premise. Related: [[2026-07-01-concurrent-actor-vs-tool-corruption]]
— that lesson said "don't blame tools prematurely"; this one is the flip side:
characterize the tool's actual failure mode before trusting its silence.
