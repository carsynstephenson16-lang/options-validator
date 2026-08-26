# Domain 6 — Obsidian and knowledge-management audit

**Verdict:** NOT READY as a current-state knowledge layer.  The repository-local
Obsidian contract and the small, indexed graph are structurally sound, but the
derived summaries have not been reconciled since the material 2026-08-17 to
2026-08-23 authority, provider, and lane-status changes.  The most harmful
drift is in `wiki/hypotheses.md`, where retired H5 entry rules, paused H7, and
closed H10a are still presented as live.

## Boundary and method

- Audited checkout: `/Users/carsynstephenson/options-validator/.tmp/worktrees/2026-08-25-1403-options-validator-audit`
  at `c9e74ccd05e4ecdd0de8de6f35bef714bc6f1771`.
- Read `AGENTS.md`, `wiki/CLAUDE.md`, `wiki/index.md`, and `wiki/log.md`; read
  only the five derived pages named in the index.  `wiki/raw/` was not read.
- Canonical comparisons used `PROJECT_STATE.md`, README **Scope status**,
  registrations/facts, dated reports/docs, and current implementation.  No
  daily/personal notes, attachments, cache data, providers, or operational
  state were accessed.
- `reports/repository-audits/2026-08-25-options-validator/00-preflight-and-wip.md`
  was treated as a protected-WIP manifest.  This audit makes no implementation
  recommendation that authorizes a protected-path edit.

## Structural health

| Check | Result | Evidence |
|---|---|---|
| Vault contract | Source-backed | `wiki/CLAUDE.md:1-9` correctly makes `wiki/` derived and canonical sources controlling. |
| Index coverage | Source-backed | `wiki/index.md:12-17` lists all five derived pages; the only raw link is the deliberately indexed source-pattern file. |
| Orphan derived pages | None found | The indexed derived pages are exactly `hypotheses`, `data-layer`, `automation`, `dashboards`, and `decisions`; each is reachable from the index and cross-linked. |
| Broken links | One low-severity candidate | `wiki/log.md:36` contains `[[wikilinks]]` as prose, but Obsidian will parse it as a link to a nonexistent page.  Use inline code or plain text in a future log-only correction. |
| Duplicate authority | Material | Every page says it is derived, but `wiki/hypotheses.md:16-63` and `wiki/automation.md:9-63` contain operationally decisive status prose.  This duplicates the canonical registry/roadmap without an as-of stamp and has drifted. |
| Maintenance cadence | Stale | `wiki/log.md:8-68` records the five-page ingest on 2026-07-25 and then only RAG-health entries; it contains no semantic lint after the subsequent scope/authority changes. |

## Claim reconciliation

### `wiki/hypotheses.md`

| Derived claim | Classification | Canonical comparison and safe candidate |
|---|---|---|
| H5 fires when frozen price/IV triggers align and awaits a fired entry (`:16-23`) | **Contradicted** | `options_researcher/entry_watch.py:1-11` retires both historical trigger rules and makes this a descriptive, non-verdict-bearing Schwab observer; `README.md:250-253` records the seq-29 OBSERVE status.  Replace the section with the observer status, verified-session dependency, and no-FIRE/no-paper-entry boundary. |
| H6 one open NVDA position, zero completed, insufficient sample (`:25-31`) | **Source-backed, but incomplete** | Current README scope registry confirms one open H6 call and insufficient sample (`README.md:253-256`); retain but link the current registration/status source rather than a dated snapshot. |
| H7 forward window is LIVE through 2026-10-26 and scores at end (`:33-44`) | **Contradicted** | `PROJECT_STATE.md:1-13` and `data/ritual_authority.py:38-49,69-84` state `h7_active=False`; `README.md:254-256` calls it PAUSED and requires a new registration/namespace. `tools/daily_ritual.sh:260-267` skips H7 full-tier lanes.  Replace with “old namespace paused; prepared Schwab lane not registered/activated; no active H7 namespace.” |
| H8 structure/status (`:46-53`) | **Source-backed, status may age** | README scope records H8 zero positions (`README.md:256`); the terms should remain pointers to its registration and current book, not stand-alone authority. |
| H10a/H10b presented as a single continuing lane, H10a ending 2026-10-06 (`:55-63`) | **Contradicted** | `README.md:256-261` and `PROJECT_STATE.md:1-13` record H10a CLOSED 2026-08-15, INSUFFICIENT_SAMPLE—STARVED; only H10b resumes on the guarded Schwab preclose lane. `tools/daily_ritual.sh:431-465` explicitly excludes adjudicated H10a and writes H10b to the namespaced `reports/h10/h10b_observations.jsonl`. Split the section into closed H10a history and current H10b only. |
| H9/RQ1 spent studies (`:65-74`) | **Source-backed** | README registry retains RQ1 as spent/no verdict (`README.md:262-263`). |

### `wiki/data-layer.md`

| Derived claim | Classification | Canonical comparison and safe candidate |
|---|---|---|
| Chain cache “only ever adds” days through blind-fetching `recent_topup` (`:7-14`) | **Contradicted** | `data/recent_topup.py:20-30` says non-dry-run ThetaData top-up is operator-disabled as of 2026-07-31; `PROJECT_STATE.md:15-31` preserves the cache as frozen and blocks richer-data integration.  State that historical cache reads remain available, ThetaData acquisition is disabled, and only the separately authorized guarded closes refresh runs. |
| Closes, earnings, rates, split/parity and legacy holdout sections (`:16-47`) | **Mostly source-backed** | Code confirms the parity helper; config confirms the dates.  The word “current” for `gating_v3.csv` should be guarded by an as-of stamp, because freshness is a data-quality question rather than a structural fact. |
| ThetaData adapter called the “live data path,” with active subscription (`:49-55`) | **Stale/misleading** | Adapter still documents remote MDDS/no terminal, but the provider is not a permitted current acquisition path; `data/recent_topup.py:29-30` and `PROJECT_STATE.md:15-31` control.  Reframe as a legacy direct-MDDS implementation retained for immutable cache reads; do not repeat subscription/credential status in derived wiki. |

### `wiki/automation.md`

| Derived claim | Classification | Canonical comparison and safe candidate |
|---|---|---|
| 07:10 ops-checkout ritual and branch guard (`:9-15,30-38,55-63`) | **Source-backed, history-heavy** | `tools/daily_ritual.sh:55-106` retains tracked data-phase authority and main/origin-main guard.  The page needs authority-tier language and an as-of label. |
| H7 data gate blocks “every watcher below” and the full H7/H6/H8 chain proceeds (`:16-28`) | **Contradicted** | Full tier is presently unavailable because `h7_active=False` (`data/ritual_authority.py:38-49,69-84`); H7 is paused (`tools/daily_ritual.sh:260-267`).  H5/H10b are a separate data-tier island guarded by verified Schwab sessions (`tools/daily_ritual.sh:383-465`), so the old linear chain is no longer a faithful model. |
| Durability always commits/pushes/restic (`:27-28`) | **Source-backed with missing condition** | Script retains it, but it is tier-scoped: data tier persists only listed paths and explicitly says no H7 evidence (`tools/daily_ritual.sh:523-556`).  Record the condition. |
| Intraday “5x/day” only (`:40-44`) | **Incomplete** | Current durable Schwab preclose is a separately installed 15:45 job (`tools/launchagents/README.md:94-99`); link it so users do not infer the old intraday schedule is the sole capture authority. |
| Repo-RAG advisory-only (`:46-53`) | **Source-backed, operational status unknown** | The script/plist exists; whether it is installed/running is host state and was deliberately not checked.  Replace “installed” with “repository template/script” unless a future host-state audit supplies evidence. |

### `wiki/dashboards.md`

| Derived claim | Classification | Canonical comparison and safe candidate |
|---|---|---|
| Four surfaces, static outputs, atomic writes (`:7-21`) | **Source-backed as a 2026-07-25 architecture record** | It accurately attributes the dated decision record.  Add its decision date/as-of rather than imply present runtime freshness. |
| Bookmark and known banner quirk (`:23-35`) | **Source-backed as historical guidance; host freshness unknown** | The paths are an ops-checkout convention, but the actual bookmarked/served file was not inspected under this audit boundary.  Label as recommended path, not confirmed live display state. |
| Preview cannot show FIRE because `entry_watch` owns it (`:37-41`) | **Contradicted** | `entry_watch` has no FIRE path after seq 29 (`options_researcher/entry_watch.py:1-11`).  Replace with the current non-verdict observer boundary and retain any separate preview-signal rule only if source-backed. |
| Framework rejection because it fails the live-hypothesis scope guard (`:43-53`) | **Stale policy rationale** | `PROJECT_STATE.md:32-51` records retirement of the global pre-verdict ship-blocker.  The dependency/offline-surface rationale may remain, but remove the retired rationale. |

### `wiki/decisions.md`

| Derived claim | Classification | Canonical comparison and safe candidate |
|---|---|---|
| Four-name pivot (`:7-12`) | **Source-backed** | Config still names the four-name universe; preserve as a dated decision. |
| H7 15-name scope and nine-name cohort “for the life of the live forward window” (`:14-26`) | **Partly source-backed, materially stale status** | Current code still enforces 15 names (`options_researcher/h7_scope.py:19-25`) and historical ledger cohort remains immutable, but it is not a live window: H7 is paused and needs new registration (`README.md:254-256`, `data/ritual_authority.py:38-49`). Reword the nine-name cohort as immutable historical registration evidence, not current active scope. |
| OI v1 active/v2 gated (`:28-34`) | **Source-backed** | Config values match (`config.py:132-136`). |
| RQ2 delegated-value framing (`:36-44`) | **Stale/incomplete** | README records K=3 and seq-26 statistic pinning (`README.md:274-279`); new RQ2/composite status deserves its own source-backed entry rather than an old brief-only synopsis. |
| 2026-07-25 readiness verdict (`:46-54`) | **Source-backed historical record, unsafe as present readiness** | It is explicitly dated and should be labeled historical. Current authority/provider status is controlled by `PROJECT_STATE.md:1-13`. |
| Capital/risk ceiling (`:56-60`) | **Source-backed** | Config values remain present; retain. |

## Safe update candidates (plan only)

1. Run a derived-wiki lint that refreshes `hypotheses.md` first: H5 observer,
   H7 paused/new-namespace requirement, H10a closed, and H10b namespaced
   Schwab-resume status.  Cite `README.md` **Scope status**, `PROJECT_STATE.md`
   2026-08-23 refresh, and the current authority/ritual code; add an explicit
   “checked as of commit/date” line.
2. Refresh `automation.md` and `data-layer.md` around authority tiers and
   provider status: separate full H7 authority from the H5/H10b data tier,
   state ThetaData acquisition is disabled, and distinguish guarded closes
   refresh from historical options-cache acquisition.
3. Refresh `dashboards.md` and `decisions.md` only where current claims are
   contradicted; preserve dated decision history.  Replace the prose
   `[[wikilinks]]` in `wiki/log.md:36` with code/plain text in the same future
   lint.  Update `wiki/index.md` and append one `lint` entry to `wiki/log.md`
   only when those derived-note edits are actually authorized.

## Risks and unsupported assumptions

- No assertion is made that any LaunchAgent is currently loaded, that a
  dashboard file is fresh, or that a credential/subscription works; those are
  host/operational facts outside this audit.
- Dated reports and the 2026-07-25 readiness record are retained as historical
  evidence, not treated as current authority.
- Protected WIP and all canonical sources remain unmodified.  The only file
  written by this domain audit is this report.

## Final decision

**Not ready for current-status use; ready for a narrow, derived-notes-only
lint/update once separately authorized.**  Structural repair is low risk, but
the semantic corrections need a current-as-of pass and must not rewrite
historical evidence or protected operational material.
