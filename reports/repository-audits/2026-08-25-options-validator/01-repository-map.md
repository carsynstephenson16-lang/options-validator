# Repository map — options-validator

**Audit scope:** read-only structural map of `c9e74ccd05e4ecdd0de8de6f35bef714bc6f1771` in the dedicated audit worktree. No commands that execute a strategy, access a provider, or mutate an operational store were run. This is an architecture/inventory report, not a correctness verdict or a re-test of protected WIP.

## Evidence and coverage limits

- The project declares itself a Python 3.12 non-package (`package = false`) with the locked `uv` environment, Lumibot/Pandas/PyArrow, Schwab, and ThetaData dependencies; lint is intentionally narrow (`E4,E7,E9,F,I`) and coverage excludes all `tools/` code ([pyproject.toml](../../../pyproject.toml#L1-L16), [pyproject.toml](../../../pyproject.toml#L25-L67)).
- The root README defines research-only/no-order scope and separates the conservative simulation/ledger discipline layer from descriptive/scanner research ([README.md](../../../README.md#L16-L39)). `PROJECT_STATE.md` declares itself the current queue; README calls it canonical ([PROJECT_STATE.md](../../../PROJECT_STATE.md#L1-L6), [README.md](../../../README.md#L41-L45)).
- This pass inspected top-level configuration, package/module inventories, command/LaunchAgent documents, named data/authority paths, strategy/harness boundaries, and test filenames. It did not enumerate parquet/ignored-cache contents, read every report/ledger record, construct an import graph, or execute tests/lint/types/backtests. Claims about runtime reachability beyond direct calls are therefore **inferred**, not test-verified.
- Provider/network and write surfaces were deliberately not invoked. Existing raw data, caches, ledgers, receipts, manifests, and operational reports are out of scope for mutation.

## System map

### Subsystems and public entry points

| Area | Main modules / interfaces | Boundary mapped |
|---|---|---|
| Configuration and legacy simulation | `config.py` (913 lines), `strategies/{base,put_credit_spread,h7_backtest,h7_lanes}.py`, `harness/run_backtest.py`, `tools/score_backtest.py` | Offline harness refuses an OOS end unless its reveal path authorizes it, and derives OOS scope from a registered ledger record rather than caller/config input ([harness/run_backtest.py](../../../harness/run_backtest.py#L117-L175)). |
| Cached data / provider adapters | `data/{cache_schema,cache_provenance,cache_runner,chain_policy,underlying_closes,underlying_ohlcv,rates}.py`; `data/thetadata_adapter.py`; `data/schwab_adapter.py`; `data/options_flow/*`; `data/short_positioning/*` | Schwab adapter is explicitly market-data-only (no account/order/transaction/position endpoints) ([data/schwab_adapter.py](../../../data/schwab_adapter.py#L1-L5)). ThetaData acquisition is owner-disabled; construction must refuse while cache reads remain supported ([data/thetadata_adapter.py](../../../data/thetadata_adapter.py#L24-L29)). |
| Descriptive/scanner layers | `options_researcher/{attractiveness,attractiveness_dashboard,composite_signals,market_context,qm_*,regime*,ownership_context,flow/*,studies/*}.py` | Scanner candidates are display-only and do not add trades or mutate positions ([README.md](../../../README.md#L49-L56)); four experimental overlays remain off by default and isolated from frozen baseline ranking ([README.md](../../../README.md#L285-L287)). |
| Registered forward-paper lanes | `h5`/`entry_watch`, `h6_features` + `h6_watch`, `h7_*`, `h8_watch`, `h10_*`, `rq1_runner`, `a2_*` | H6 has its own read-only evaluator, exact-session artifacts/manifests, and manual receipt-bound book action; it has no live-order path ([README.md](../../../README.md#L303-L335)). H7 is a distinct real-forward/paper namespace, not an order route ([options_researcher/h7_real_scoring.py](../../../options_researcher/h7_real_scoring.py#L1981-L2028)). |
| Governance, evidence, and stores | `ledger/`, `research/`, `options_researcher/{hypothesis_evidence,h7_event_ledger,h7_window_registration,h7_forward_book,h7_paper_lifecycle,h7_real_scoring}.py`, report/receipt namespaces | H7 scoring exposes read-only `preview` versus owner-required `finalize`, and fails with a non-zero refusal exit ([options_researcher/h7_real_scoring.py](../../../options_researcher/h7_real_scoring.py#L1981-L2024)). |
| Operations / scheduled jobs | `tools/daily_ritual.sh`, `tools/launchagents/*.plist`, `tools/launchagents/README.md`, `options_researcher/{ritual_status,ritual_receipt,intraday_capture,schwab_chain_capture}.py`, `tools/job_health_digest.py` | The ritual verifies tracked authority before creating its log, checks it runs precisely on `main`/`origin/main`, then sets a publisher role only after those checks ([tools/daily_ritual.sh](../../../tools/daily_ritual.sh#L53-L65), [tools/daily_ritual.sh](../../../tools/daily_ritual.sh#L90-L112)). LaunchAgent documentation identifies scheduled preclose capture and display jobs ([tools/launchagents/README.md](../../../tools/launchagents/README.md#L94-L122), [tools/launchagents/README.md](../../../tools/launchagents/README.md#L260-L334)). |
| Audits and ancillary tools | `tools/{chain_consistency_audit,fill_haircut_calibration,future_ticker_data_audit,h7_*,thetadata_*,strategy_a_cap_audit,irreplaceable_data_guard,research_refresh_guard}.py`; `tools/repo_rag/` | These are mostly direct Python CLIs rather than package console scripts; the bundled RAG utility has its own `status/ingest/query/eval/search/health` CLI ([tools/repo_rag/repo_rag/cli.py](../../../tools/repo_rag/repo_rag/cli.py#L42-L100)). |

### Data and decision flow

```text
Provider payloads (Schwab read-only; ThetaData disabled) / existing raw caches
  -> adapter + schema/provenance + chain policy
  -> normalized local parquet / underlying closes / earnings and event facts
  -> features (attractiveness, H6/H7/QM, flow, regime, composite experiments)
  -> display-only boards and candidate/watch outputs
  -> registered-lane gates (scope + source-health + data-gate + frozen identity)
  -> immutable receipts / append-only event ledger / manual paper-book action
  -> exit monitor/fill records and separately gated final scoring
```

The critical H7 fork is visible in the ritual: `require-data` authorizes only non-verdict data/display work; `require-full` fences H7 regions ([tools/daily_ritual.sh](../../../tools/daily_ritual.sh#L16-L23), [tools/daily_ritual.sh](../../../tools/daily_ritual.sh#L147-L155)). In the full tier it chains source-health receipt into the whole-universe data gate ([tools/daily_ritual.sh](../../../tools/daily_ritual.sh#L156-L215)), then runs exit fill/monitor even when `NO_GO` so existing paper positions are not silently unmanaged ([tools/daily_ritual.sh](../../../tools/daily_ritual.sh#L219-L258)).

The data gate itself requires a same-session source-health receipt and refuses future/missing inputs ([options_researcher/h7_data_gate.py](../../../options_researcher/h7_data_gate.py#L809-L867)); after evaluation it writes an artifact and immutable receipt ([options_researcher/h7_data_gate.py](../../../options_researcher/h7_data_gate.py#L870-L893)). This is evidence-gated paper-research plumbing, not live execution.

### Strategies, variants, registries, and status

- Legacy H1/H2 are recorded in-sample failures and H3R is archived/un-run; H4 is superseded at zero cycles ([README.md](../../../README.md#L55-L57), [README.md](../../../README.md#L297-L302)).
- Current registered/forward surfaces include H5 (observe only), H6, H7 (paused current namespace), H8, H10a (closed/starved), H10b, RQ1/RQ2, and A2-v1. The README also records prepared-but-not-registered H7 Schwab restart work ([README.md](../../../README.md#L246-L285)). Treat this as status documentation, not a replacement for ledger inspection.
- H7 has lane-specific strategy code in `strategies/h7_lanes.py`; historical evaluation has both `harness/run_h7_backtest.py` and `strategies/h7_backtest.py`. The forward path instead fans through the dedicated `h7_*` modules, especially scope, source health, gate, registration, scoring identity, lifecycle, book, exit, and final score.
- The robustness package is a separate registry/runner/reporting/walk-forward layer; its stated contract is that return-matrix robustness does not propagate to registered runs/reports ([options_researcher/robustness/return_matrix.py](../../../options_researcher/robustness/return_matrix.py#L57-L76)).

### Build, validation, integrity, and operational commands

- Project-declared baseline: `uv sync --frozen`; `uv run python -m unittest discover -s tests`; `uv run ruff check .`; `uv run ruff format --check .`; `uv run pyright` ([AGENTS.md](../../../AGENTS.md#L134-L153), [README.md](../../../README.md#L78-L101)). None were run in this read-only mapping pass.
- Test inventory is broad: unit tests span cache/provenance/schema, strategy fills, H5–H10, H7 registration/lifecycle/gates, A2, dashboards, data adapters, operational scripts, research integrity, and tool-specific audit commands. `tools/` are excluded from the configured coverage source, so script/LaunchAgent behavior needs direct tests or integration checks even if global coverage clears ([pyproject.toml](../../../pyproject.toml#L52-L67)).
- Operational invocation is materially different from safe read-only commands: the daily ritual creates logs and may advance receipts/books; its own comments identify these stateful surfaces ([tools/daily_ritual.sh](../../../tools/daily_ritual.sh#L16-L18), [tools/daily_ritual.sh](../../../tools/daily_ritual.sh#L67-L71)). `tools/irreplaceable_data_guard.py verify` is the required precondition for any later worktree removal per AGENTS ([AGENTS.md](../../../AGENTS.md#L82-L104)).

## Findings, ordered by project value

1. **[High] Operational authority is concentrated in a long, stateful shell orchestrator, while its component commands span both read-only and write-once semantics.** `tools/daily_ritual.sh` is 619 lines and combines authority checks, branch/publisher identity, receipt discovery/reuse, source health, data gating, exit lifecycle, display refresh, and notifications. Its protections are explicit, but a change to ordering or a misclassified command has an unusually wide decision surface. The first review target should be an executable command-to-effect contract (read-only / artifact write / ledger append / paper-book mutation) rather than a rewrite. Evidence: authority/fencing ([tools/daily_ritual.sh](../../../tools/daily_ritual.sh#L16-L23), [tools/daily_ritual.sh](../../../tools/daily_ritual.sh#L147-L155)); branch/publisher guard ([tools/daily_ritual.sh](../../../tools/daily_ritual.sh#L90-L112)); gate-to-exit sequence ([tools/daily_ritual.sh](../../../tools/daily_ritual.sh#L156-L258)).

2. **[High] “Read-only” language is not uniform with filesystem effect, creating a documentation/API-contract audit lead.** The H7 data-gate summary labels itself “read-only; BUILD-ONLY” ([options_researcher/h7_data_gate.py](../../../options_researcher/h7_data_gate.py#L786-L792)), but the same CLI writes a gate artifact and immutable receipt ([options_researcher/h7_data_gate.py](../../../options_researcher/h7_data_gate.py#L870-L893)). That is intentional evidence persistence, not a live-order issue, but tools and operators need a three-way vocabulary: computation-only, artifact-writing, and ledger/book-mutating. This lead overlaps protected `options_researcher/h7_activation_guard.py`, `h7_schwab_window_registration.py`, and operational receipt paths, so any remediation is plan-only in this audit.

3. **[Medium] The highest-risk domain logic is concentrated in several oversized modules with overlapping H7 responsibilities.** `h7_real_scoring.py` is 2,028 lines, `h7_paper_lifecycle.py` 1,907, `h6_watch.py` 1,375, and `hypothesis_evidence.py` 1,320; `config.py` is 913. The direct boundaries remain strong (e.g., scoring preview/finalize), but these sizes make independent review and causal-change isolation costly. Map-before-refactor candidates are `h7_real_scoring` (input opening, calculation, artifact write, event append) and `h7_paper_lifecycle` (entry/exit state transitions), with regression fixtures keyed to immutable receipt hashes. No cyclic-import claim is made: no import-graph analysis was executed.

4. **[Medium] Tooling assurance has an intentional gap: coverage omits `tools/*` and ruff enables only import/syntax-class checks.** This is a lead, not evidence that a defect exists. The tool surface includes data acquisition guards, audit CLIs, LaunchAgent orchestration, backup/guard utilities, and the standalone RAG package; direct test inventory exists for many, but reporting should distinguish package coverage from end-to-end scheduled-job validation ([pyproject.toml](../../../pyproject.toml#L37-L67), [tools/launchagents/README.md](../../../tools/launchagents/README.md#L94-L122)).

5. **[Medium] Status is distributed across canonical state, README history/corrections, ledger, reports, and protected active plans.** README tells operators `PROJECT_STATE.md` is canonical ([README.md](../../../README.md#L41-L45)), then retains historical registry prose with corrective updates ([README.md](../../../README.md#L246-L295)). This is appropriately transparent but creates a reconciliation risk if a command consumes one source while an operator reads another. Review all command status consumers against the ledger/event store before changing policy or dashboard claims.

## Protected-WIP overlap

The preflight identifies 136 protected paths and prohibits mutation; its protected list includes `config.py`, `ledger/facts.log`, active H7/A2/attractiveness source and tests, data/earnings/rates inputs, current plans, and runtime receipts ([00-preflight-and-wip.md](00-preflight-and-wip.md#L43-L69), [00-preflight-and-wip.md](00-preflight-and-wip.md#L123-L150)). The map’s first two findings directly overlap protected daily-ritual/H7 operational flows and protected receipt namespaces; the third overlaps protected H7/A2 sources. All are discovery-only and require later owner-scoped planning outside this audit.

## Diminishing-returns stop

Stopped after the main data, research, forward-paper, governance, and operational boundaries were independently mapped. Further per-function expansion would repeat the module/test inventory without adding a new material category. Remaining unreviewed depth: full import graph/cycle detection, individual data schema semantics, every test’s asserted behavior, report/ledger content reconciliation, and actual runtime/LaunchAgent state.
