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


## [2026-08-16] ingest | RAG health

RAG health indexed 690 sources and 16355 chunks; 0 source failures were reported.


## [2026-08-19] ingest | RAG health

RAG health indexed 786 sources and 17607 chunks; 0 source failures were reported.


## [2026-08-23] ingest | RAG health

RAG health indexed 829 sources and 28365 chunks; 0 source failures were reported.

## [2026-08-26] lint | WIKI-01 stale-status reconciliation (owner-authorized)

Owner authorized the vault refresh 2026-08-26 in-session. Corrected against
canonical sources (README "Scope status", ledger registry, PR #76/#82 history):
hypotheses.md — H5 trigger RETIRED/observe-only (seq 29), H7 forward window
PAUSED per OD-3 with the Schwab restart lane PREPARED/NOT REGISTERED, H10a
CLOSED STARVED (2026-08-15), H10b resumed on the Schwab preclose lane
(seq 28); data-layer.md — ThetaData retired ~2026-07-29 (stale
"subscription through 2026-11-30" claim removed), Schwab 15:45 preclose
lane documented as the capture path; automation.md — ThetaData key check
marked historical, Schwab preclose + 15:30 alignment-check noted;
decisions.md — "live forward window" and ThetaData-dependency claims
stamped historical. All corrections carry as-of 2026-08-26 stamps. Evidence
trail: audit finding WIKI-01
(reports/repository-audits/2026-08-25-options-validator/, lands with PR #82)
and reports/2026-08-25-codex-audit-verification-owner-package.md.


## [2026-08-26] ingest | RAG health

RAG health indexed 848 sources and 32824 chunks; 0 source failures were reported.

## [2026-08-26] lint | merge-resolution correction

data-layer.md: the brief-29 protection claim for `.cache/schwab_chains`
corrected to reflect that brief 29 is BLOCKED pending re-review (receipt:
`reports/2026-08-26-brief-29-independent-review-receipt.md`); the gap is
still open.

## [2026-08-26] lint | PR #90 review: token-lifetime claim labeled

data-layer.md: the 7-day Schwab refresh-token claim now carries its
mandatory claim labels (Official-source + Test-verified), per the Codex
review of PR #90 and AGENTS.md claim discipline.


## [2026-08-30] ingest | RAG health

RAG health indexed 1072 sources and 35065 chunks; 0 source failures were reported.


## [2026-09-02] ingest | RAG health

RAG health indexed 1129 sources and 35626 chunks; 0 source failures were reported.


## [2026-09-09] ingest | RAG health

RAG health indexed 1233 sources and 37004 chunks; 0 source failures were reported.

## [2026-09-09] lint | 2026-09-09 stale-status reconciliation (owner-directed PM sweep)

Owner directed a full vault refresh in-session ("ensure it's up to date to
where we are"). A Sonnet audit (raw output not persisted; the corrections
below are its findings after re-verification) was checked against
canonical sources, then applied here; an Opus adversarial audit of the
result caught two errors in the first pass (brief 29 status, leftover
07:10 mentions), fixed before commit. hypotheses.md — H7 as-of bumped to 2026-09-09
with Brief 36 door (#147) + Brief 40 activation-day chain (#161 @ d95a5a1)
landed, source health 7/15 with AMZN/MSFT/NOW/TEM UNHEALTHY, activation
realistically early-to-mid October; H6-0001 recorded as open past its
21-DTE rule with the H6/H8 evaluators PAUSED (ritual line; newest receipt
2026-07-27) — owner item; H10b observed cadence (10 receipts, 0 fires,
ET/IREN/USAR DATA-skipped) added as description only. data-layer.md — the
"protection GAP" wording corrected (namespace guarded since d987c1f
2026-08-09; brief 29 implemented and merged via PR #96 @ 42f6a1b 2026-08-27
— the registry row and the brief header still disagree on its status, noted);
holiday refusal (Brief 40 WP-C) and the isolated 10:00/13:00 intraday lane
(#150) added. automation.md, dashboards.md, index.md — every current-tense 07:10 mention
corrected to 09:09 (retimed 2026-08-26; monday-runbook flagged stale;
decisions.md's 07:10 lines are historical and left as-is); Step 8 durability regression
09-03→09-06 + Brief 38 fix (#158) recorded; new "Installed is not loaded"
section from a live launchctl comparison (research-refresh installed but
NOT loaded; job-health-digest + schwab-chain-intraday tracked but not
installed, owner-gated). dashboards.md — banner pin marked FIXED (#156,
dashboard.py:123-141); live-dashboard LaunchAgent recorded; Brief 39 board
redesign noted on the Top-3 row. decisions.md — H7 freeze stamp bumped.
Evidence trail: PROJECT_STATE.md 2026-09-08 refresh, README "Scope status",
tools/launchagents/README.md:3-14, PRs #147/#150/#156/#158/#159/#161,
ops checkout ritual log 2026-09-09_0909. index.md unchanged (all five
pages listed; every wiki link resolves).
