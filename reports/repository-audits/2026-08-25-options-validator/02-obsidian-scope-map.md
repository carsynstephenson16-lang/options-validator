# Obsidian scope map — options-validator

**Audit date:** 2026-08-25
**Mode:** read-only discovery; derived notes are untrusted until checked against
canonical repository evidence.
**Protected-overlap ruling:** `00-preflight-and-wip.md:15-19` protects active
branches, ledgers, provider work, and operational receipts. This report makes
no implementation recommendation for a protected path.

## Verdict

The five indexed derived project pages are a useful July-25 historical map,
but they are **not current operational status**. They have not had a
substantive content update since their 2026-07-25 ingest (`wiki/log.md:22-44`).
The largest drift is the treatment of H7 as live: the current canonical policy
has `h7_active=False` and no active H7 namespace.

## Coverage and boundary

- Read all five indexed derived pages: `wiki/hypotheses.md`, `data-layer.md`,
  `automation.md`, `dashboards.md`, and `decisions.md` (5 notes; below the
  200-note cap).
- Expanded their wikilinks one hop only. All resolve within that same five-note
  set; no additional project-relevant note was reached.
- Excluded `wiki/raw/llm-wiki.md` (pattern source only), the dated root daily
  notes, personal/journal material, and attachments. No personal content was
  read or extracted.
- Checked the cited canonical sources on the canonical checkout, currently
  `claude/codex-handoff-plan-2026-08-22` at `915e303`; its current status
  authority remains `PROJECT_STATE.md:1-9`. The audit worktree is a separate
  `main`-based snapshot, so line citations below identify evidence rather than
  merge readiness.

## Claim map

| Classification | Note and section | Claim | Canonical support / contradiction | Linked repo area | Next action |
|---|---|---|---|---|---|
| **CONTRADICTED** | `wiki/hypotheses.md:33-44`, H7 | H7 forward paper window is live from 2026-07-20 through 2026-10-26 and is the sole verdict path. | The historical ledger registration exists (`ledger/h7_forward/events.jsonl:1`), but current authority says `h7_active=False` and “no active namespace exists” (`data/ritual_authority.py:38-49, 69-84`). Canonical current status calls old H7 paused and the Schwab successor PREPARED / NOT REGISTERED / NOT ACTIVATED (`PROJECT_STATE.md:72-87`; `README.md:254-255,279-284`). | H7 ledger, ritual authority, Schwab restart | Refresh the wiki only after owner-authorized, separately reviewed change; do not infer activation from historical receipts. |
| **CONTRADICTED** | `wiki/hypotheses.md:16-23`, H5 | Frozen price/IV-rank triggers await their first fired entry. | H5 is now Schwab-ramp **OBSERVE** mode; the old trigger is RETIRED and no paper entry may occur until an owner-typed new rule (`README.md:250-253`). Constants remain in `config.py:310-322`, but that is retained configuration, not current authority. | H5 observer and registry | Mark the trigger description superseded; point readers to seq 29 / current README scope-status. |
| **CONTRADICTED** | `wiki/hypotheses.md:55-63`, H10a/H10b | Both H10 variants are active continuation windows. | H10a was owner-ratified closed on 2026-08-15, INSUFFICIENT_SAMPLE — STARVED (`README.md:256-262`; `ledger/facts.log:19412`). H10b remains the only resumable lane, with a 2026-08-19 no-backfill floor (`config.py:613-617`). | H10 evidence and watcher | Split the note’s combined section: H10a closed; H10b active only under its amended Schwab/preclose conditions. |
| **CURRENT DECISION** | `wiki/hypotheses.md:25-31,46-53` | H6 has one open NVDA call and H8 has no positions. | Supported by the current books: H6 has the single `H6-0001` row and H8 has header only; README also says one H6 open position and H8 zero (`README.md:253-256`). | `data/positions/` | Retain, but date-stamp any position summary at refresh time. |
| **CONTRADICTED** | `wiki/data-layer.md:7-14,49-55` | Daily top-up uses ThetaData and a subscription is confirmed through 2026-11-30. | The historical registration records an owner commitment, not a current availability proof (`ledger/h7_forward/events.jsonl:1`). Current provider policy disables all ThetaData acquisition without an environment override (`data/provider_policy.py:1-25`); cached reads remain enabled. The adapter’s remote-MDDS architecture remains historically/source supported (`data/thetadata_adapter.py:1-24,202-229`). | Provider policy, chain cache | Preserve the architecture explanation but label acquisition/subscription status stale; link to provider-policy and current roadmap. |
| **EVIDENCE** | `wiki/data-layer.md:24-31,57-62` | Earnings assertions are point-in-time and source health makes unhealthy names entry-banned; manifests/provenance bind inputs. | Supported by cited data-layer code and by H7 operations: receipt order and rechecking are documented at `docs/h7-forward-operations.md:7-21`; current full H7 execution is nevertheless paused. | Earnings provenance, receipt/manifest code | Retain as data-contract description; add the distinction between capability and current activation. |
| **CONTRADICTED** | `wiki/automation.md:9-38` | The 07:10 ritual runs the H7 source-health/data-gate/watcher sequence as its active routine. | The ordering and branch/data-gate fail-closed logic are implemented (`tools/daily_ritual.sh:90-107,177-215`), but it first requires full authority. With `h7_active=False`, it logs H7 lanes PAUSED (`tools/daily_ritual.sh:147-167,260-267`; `data/ritual_authority.py:82-84`). | Daily ritual, H7 authority | Reframe H7 steps as conditional full-tier behavior; keep branch-guard and NO_GO behavior as current implementation evidence. |
| **CURRENT DECISION** | `wiki/automation.md:40-44` | Intraday capture writes receipts five times daily and is committed by the following ritual. | The preflight captured current protected receipt files for 2026-08-25 under `reports/intraday_capture/` (`00-preflight-and-wip.md:27-36`). This confirms a current operational evidence namespace, not that every scheduled run succeeded. | Intraday receipts, ops checkout | Retain with the narrower “scheduled/receipt namespace” wording; consult individual receipts for run outcome. |
| **CONTRADICTED** | `wiki/dashboards.md:31-35` | Mission-control’s data-as-of banner is pinned to `config.BACKTEST_END`. | Current implementation derives the earliest available cached close date, not the constant (`options_researcher/dashboard.py:124-144`); the tests explicitly cover this behavior (`tests/test_dashboard.py:131-175`). | Mission-control dashboard | Remove the obsolete P1 quirk; retain the cache-freshness semantics. |
| **STALE** | `wiki/decisions.md:49-58` | The 2026-07-25 readiness verdict is the operative status. | It is a historical, commit-specific readiness statement. `PROJECT_STATE.md:5,9` says the roadmap is the single current status authority, and its H7 state has since changed. | Readiness docs, roadmap | Keep as dated evidence only; direct current-status readers to `PROJECT_STATE.md`. |
| **EVIDENCE** | `wiki/decisions.md:7-26,28-47,60-64` | Four-name pivot, legacy holdout boundary, H7 historic diagnostic withdrawal, OI v1 display-only/v2 gated, and risk ceiling are standing governance decisions. | The pivot and risk constants remain source-supported (`config.py:30-42,51-78`); the H7 historical record exists but must not be confused with live authority. OI/RQ2 claims were not independently re-run in this bounded note audit. | Config, legacy research, governance | Retain supported decision history; label unverified subclaims as historical pointers until a dedicated governance refresh. |

## Top findings

1. **H7 is the critical contradiction.** The wiki presents an active
   ThetaData-based forward window, while current authority pauses H7 and says
   no active namespace exists.
2. **The hypothesis map overstates live lanes.** H5’s frozen trigger is
   retired; H10a is closed; H10b has a narrower amended observation path.
3. **The automation/dashboard pages mix durable design facts with obsolete
   operating status.** Branch guards, receipt-chain checks, and cached
   freshness logic are supported; “what runs now” needs refresh.

## Blockers and limitations

- No wiki file was changed: the parent audit authorization permits only this
  report, and derived-page repair would touch the canonical vault rather than
  the isolated audit worktree.
- The audit did not inspect individual operational receipts or invoke any
  provider, watcher, backtest, broker, or mutation command. Their outcomes are
  therefore **UNKNOWN** unless explicitly cited above.
- `PROJECT_STATE.md` itself contains historical layers; this report relied on
  its declared current-status sections and on current source authority rather
  than treating every older roadmap line as active.

## Ready decision

**NOT READY** to use the wiki as a current operational scope map. It is ready
only as a historical navigation layer after each affected claim is revalidated
and the H7/H5/H10a/automation/dashboard corrections are separately authorized.
