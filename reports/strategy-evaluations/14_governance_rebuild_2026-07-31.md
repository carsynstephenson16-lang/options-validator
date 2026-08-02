# 14 — Repository-state verification and governance rebuild

**Date:** 2026-07-31 (session began 2026-07-30 evening).
**Scope:** documentation, governance, and Claude Code instruction files only.
No production code, no tests, no ledger writes, no provider calls, no git
branch/commit/push operations, no cache mutation.
**Checkout inspected:** `sfix` @ `40a6b21`; `main` @ `ecdaeb9` (via git
objects; ops worktree at `/Users/carsynstephenson/options-validator-ops`).

Labels: **VERIFIED** (current-session command or file evidence),
**DOC-VERIFIED** (confirmed against a repo report whose code refs were spot-
checked but not fully retraced), **CONTRADICTED**, **STALE**, **UNRESOLVED**.

---

## 1. Handoff claim register

| # | Handoff claim | Status | Evidence |
|---|---|---|---|
| 1 | `ecdaeb9` docs-only, no ledger write, no network | VERIFIED | `git show --stat ecdaeb9`: 7 files, all reports/specs; `facts.log` last entry 2026-07-27 |
| 2a | Work occurred on `main`; `5165144` pushed; `88ffbb6`, `ecdaeb9` local-only | VERIFIED | `git log origin/main..main` = `ecdaeb9`, `88ffbb6`; `git branch --contains 5165144` incl. `main` (and `origin/main` per report 12 §0) |
| 2b | "`sfix` remained untouched" | **CONTRADICTED / STALE** | `sfix` is the checked-out branch, 43 commits past merge-base `3f2d19f`, 9 unpushed, incl. Schwab provider `54b0e76` and evidence-upgrade docs through D40 — none mentioned in the handoff |
| 2c | Reports 08–11 copied so `main` held the full set | VERIFIED | `ecdaeb9` contains 08–13; on `sfix` they existed only as untracked 08–11 (12, 13, NAV spec restored to this worktree from `main` this session, byte-identical via `git show`) |
| 3 | Two wrong ratios per record; H1 −4,442.93%→−19.66%; H2 −1,823.97%→−9.31%; H9 drawdown $718.50 chronological vs $361.30 recorded; verdicts stand; verdict reads neither ratio | VERIFIED (values) + DOC-VERIFIED (recomputation) | Raw values read this session from `ledger/experiments.jsonl` seq 0 (−44.4293…), seq 3 (−18.2397…), `reports/h9/receipt.json` (`max_drawdown` 361.3); twin bug live in `main:metrics.py` (`economic_max_loss.mean()`); verdict block seen gating only losses/cohorts/CI; ÷n recomputation from report 13 |
| 4 | 1pm entry: endpoint exists on installed client, cache EOD-only, Greeks PERMISSION_DENIED on Standard $80/mo (probe 2026-07-24), ~62,700 refetch, D+1 recommended, midday 13:00 owner-typed, live module display-only, retrofit would void H7 window | VERIFIED (config; `option_at_time_quote` absent from repo code, i.e. installed-client claim) + DOC-VERIFIED (probe, tier) | `config.py:731` `"midday": "13:00"  # owner-typed 2026-07-24`; report 09: 31,367 files, ≈62,734 calls (handoff's 31,366/62,700 slightly off); report 12 §4 |
| 5 | NAV drawdown option 3, design at `2026-07-30-daily-nav-drawdown.md` | VERIFIED | File in `ecdaeb9`, restored to worktree; states PARKED, option 3, stitching options + proof test |
| 6 | $600 cap unenforceable; Thursday-size/Friday-fill; test holds quotes constant; `entry_date` redefinition feeds verdict; last-session exit crash; Session-3 $6.40 precedent | DOC-VERIFIED | Report 12 F1–F3 with code line refs (`put_credit_spread.py:111,277,296,456,551-556`; `test_canonical_pricing.py:98`; `harness/run_backtest.py:105-113`); `MAX_LOSS_PER_TRADE = 600` VERIFIED in `config.py:42`. The mechanisms were not independently re-executed |
| 7 | No backtest after changes; Pyright not run; H7/H8 not retraced; commits local | VERIFIED | Report 12 §0/§3 states it; nothing in this session ran them either (out of scope); locality per 2a |
| 8 | Session 4 / Session 7 are proposals, not decisions | VERIFIED | Report 10 D4/D7 present options tables with recommendations; no ledger registration; "0 of 310" measurement in report 12 §5 |
| 9a | 31,366 v1 partitions; v2 needs side-by-side namespace | VERIFIED (count is 31,367) | `find .cache/chains -name "*.parquet" | wc -l` = 31,367; no v2 namespace exists |
| 9b | "The code gate is ready" | **UNRESOLVED (nuance)** | v2 gate code exists ONLY on unmerged branch `codex/cache-schema-v2` (`8fa0637`, touches `h7_data_gate`, `h9_census`, +tests). Not on `main` or `sfix` — "ready" ≠ "landed" |
| 9c | H7 window holds only its registration; registration used a v1 gate receipt | VERIFIED (first half) / UNRESOLVED (receipt provenance not re-traced) | `ledger/h7_forward/events.jsonl` = 1 line, `window_registration`, 2026-07-20 |
| 9d | H9 one run spent; direct-v2 bypass checks belong in the four named files | VERIFIED (spent — PROJECT_STATE + receipt) / UNRESOLVED (file list not re-verified; roadmap P2.2 requires re-verification before work) | |
| 10 | Owner direction: ThetaData ends, Schwab stays, Schwab data delayed, no new paid data | VERIFIED as direction; **"delayed" is nuanced** | `data/schwab_adapter.py:260-265` raises on `isDelayed` chains, and the 2026-07-29/30 probe succeeded — the configured account returned non-delayed data. The adapter fails closed if that ever changes |

Conflicts recorded (not silently resolved): cancel-date records disagree
(07-07 checklist "ends 2026-07-29" vs PROJECT_STATE-07-23 "confirmed to
2026-11-30" vs owner 07-30 "will end") → owner decision OD-4.

## 2. Issue triage

- **Blocks all further research:** branch divergence with local-only fixes
  (P0.1); F1 cap; F3 crash; F2/F6 unregistered semantics. No backtest,
  promotion, or registration until closed.
- **Blocks one hypothesis/phase:** OD-1 v2 backfill (Phase B, H6/H8);
  OD-3 (H7 future sessions); review-lane absence (evidence-upgrade).
- **Changes reporting, not verdicts:** F4 twin ratio; F5 drawdown ordering;
  correction-facts append (P0.6).
- **Documentation-only debt:** instruction/plan sprawl (addressed this pass);
  skill triplication; untracked hook logic.
- **Safe to defer:** Session 4 feed inclusion (0/310); NAV build; 1pm
  hypothesis; ov/ dedup.

## 3. P0 change specifications (for later implementation — no code touched)

- **P0.2 metrics twin + ordering.** `metrics.py`: `economic_return =
  pnls.sum() / economic_max_loss.sum()` (guard zero); `scoreboard` sorts
  trades chronologically by entry date before `_max_drawdown`, or
  `_max_drawdown` asserts a monotonic date column. Acceptance: a test with
  n>1 identical trades where mean≠sum denominators diverge (red on current
  code); a two-orderings drawdown test asserting the chronological value;
  update `tests/test_core.py:297` (27.27% → 13.64%). Suite green.
- **P0.3 cap.** Per owner mechanism (default: cancel-if-worse-than-tolerance
  at fill). Acceptance: test where decision credit $0.50 → fill credit $0.35
  at 4×$2-wide must NOT produce >$600 recorded risk; dataset-wide breach scan
  reported once.
- **P0.4 chunk-end exit.** Acceptance: harness test with an exit trigger on
  the final session of a chunk completes without the year-end guard raising,
  and a dropped-at-seam trade is recorded, not silent.
- **P0.5 registration.** Owner-typed chained-ledger entry for
  `BACKTEST_EXECUTION_CONVENTION` and `entry_date` semantics; config comments
  point at the entry. Acceptance: `research.cli verify` green; grep shows no
  "owner-typed" label without a ledger backing.
- **P0.6 correction facts.** Procedure in `13_correction_facts_draft.md`
  checklist; hook-prefix dry run BEFORE the real append.

## 4. Instruction-system rebuild: rule-migration map

Anthropic sources reviewed 2026-07-31 (fetched this session):
“How Claude remembers your project” (code.claude.com/docs/en/memory) and
“Extend Claude with skills” (code.claude.com/docs/en/skills). Applied: root
CLAUDE.md < 200 lines; stable facts only; path-scoped `.claude/rules/` with
`paths` frontmatter; procedures stay in skills; imports load at launch (used
only for the authoritative `.cursorrules`); hooks remain the enforcement
layer; status/history moved out of always-loaded files.

| Rule / content | Old location | New location | Disposition |
|---|---|---|---|
| Hard guardrails, claim discipline, vocabulary, scope guard, feasibility gate, web-fetcher limits | `.cursorrules` + restated in CLAUDE.md | `.cursorrules` (imported; one surgical scope-guard edit, mirrored in AGENTS.md — see §6) | Single authoritative copy; CLAUDE.md duplicates removed; "if sources conflict, say so" line kept in CLAUDE.md (it was never in `.cursorrules`) |
| Identity, scope-loosening 2026-07-22 | CLAUDE.md §1 | CLAUDE.md (compressed) | Kept |
| Division of labor + 2026-07-25 amendment delegation + provenance label | CLAUDE.md | CLAUDE.md (compressed, label preserved verbatim) | Kept |
| Command list | CLAUDE.md | CLAUDE.md (trimmed); H7 safety clauses kept inline; daily procedure → `daily-ritual` skill pointer | Kept + pointer |
| H7 receipt-immutability / operator-order warnings | CLAUDE.md line 53 | CLAUDE.md "H7 safety clauses" | Kept (safety-critical) |
| Ledger append-only, facts.log non-chained, correction procedure, spent runs, H7 no-retrofit | scattered (CLAUDE.md, ledger/README, reports) | `.claude/rules/ledger.md` (paths: ledger/**) | Consolidated |
| v1 immutability, v2 side-by-side, no unapproved provider calls, fail-closed, Schwab boundary, provenance | scattered (handoff, reports 09/12, setup doc) | `.claude/rules/data-and-providers.md` | Consolidated; newly written as binding rule |
| Engine guardrail pointers, P0 do-not-build warning, frozen-number provenance, offline tests, verdict-gates-on-losses | CLAUDE.md + reports | `.claude/rules/backtest-engine.md` | Consolidated |
| Live-hypothesis status, data state, EX-queue status | CLAUDE.md / old PROJECT_STATE | `PROJECT_STATE.md` (rewritten, canonical) | Moved out of always-loaded prose where stale |
| Registration feasibility gate text | CLAUDE.md + `.cursorrules` | `.cursorrules` only | Duplicate removed |
| Claim-discipline block | CLAUDE.md + `.cursorrules` | `.cursorrules` only | Duplicate removed |
| Lumibot/ThetaData signature verification | CLAUDE.md + `.cursorrules` | `.cursorrules` only | Duplicate removed |
| "`.claude/` is gitignored" statement | CLAUDE.md | CLAUDE.md Conventions (updated: rules/ and skills/ un-ignored and meant to be committed at the next landing — nothing was committed this pass; `.gitignore` restructured `.claude/` → `.claude/*` + negations) | Amended |
| Obsidian scratch, secrets | CLAUDE.md | CLAUDE.md Conventions | Kept |
| Wiki-not-truth rule | `wiki/CLAUDE.md` + AGENTS.md | unchanged (nested file loads on demand); 1-line pointer in root | Kept in place |
| Codex work style, toolchain, catalyst-calendar rule, security rules | AGENTS.md | AGENTS.md (untouched — Codex-facing by declared design) | Kept; drift risk noted |
| PR-review charter | REVIEW.md | REVIEW.md (untouched; consumed by CI) | Kept |
| Hooks (3) + registration | `.claude/hooks/`, `.agents/hooks/`, settings.local.json | unchanged; documented in CLAUDE.md "Hard enforcement" | No new hooks added: ledger and live-order protections already exist and are tested; a paid-call hook was considered and rejected as not safely testable in this pass → advisory rule instead |

AGENTS.md/`.cursorrules` mirroring is deliberate (AGENTS.md header) — the one
remaining sanctioned duplication. An earlier draft of this table claimed no
rule was lost; the independent verifier disproved that (§7) and the losses
were repaired before completion.

## 5. Superseded / parked / duplicated work list

See PROJECT_STATE §4–§5 and §8 (single home). Notables: twelve-month
EX-queue paused wholesale; 07-07 cancel checklist superseded by
`docs/provider-transition.md`; evidence-upgrade paused at 5B; skills
triplication and untracked hook logic queued at P3.

## 6. Independent fresh-context verifier — findings and dispositions

A read-only fresh-context subagent audited the changes against the task
prompt. Confirmed issues, all fixed before completion:

- **Five dropped rules** restored: the "if sources conflict, say so" line, the
  subagent-delegation directive, "Fable's sign-off" in the amendment gate, the
  "never connects to a live brokerage endpoint / never disables paper mode"
  boundary, and the H7 per-name entry-ban / NO_GO semantics (all back in
  CLAUDE.md); the `live_quotes --probe` precondition moved into
  `.claude/rules/data-and-providers.md`.
- **Authority conflict**: `.cursorrules` (and AGENTS.md) called H7's roadmap
  "the active build arc," contradicting the P0 freeze. Both files received the
  same surgical edit pointing sequencing at `PROJECT_STATE.md`; README's
  status-table function added to the supersession table (its stale figures —
  cache edge "2026-06-30", "suite green" — are flagged for the next landing;
  README was not edited this pass).
- **Factual fixes**: cache symbol count corrected (26 prefixes on disk, 22
  active per report 09; stray `.cache/chains/dolthub/` subdir documented);
  broken concatenated path in the supersession table fixed; `test_core.py`
  line ref branch-qualified (297 on `main`, 293 on `sfix`); "ledgers verify"
  softened (verify was not re-run); "are tracked" corrected to "meant to be
  committed".
- **Missing `daily-ritual` symlink** in `.claude/skills/` created (the other
  12 pre-existed; without it the daily procedure never loaded as a skill).

Verifier findings assessed and NOT adopted: its claim that only two records
carry inflated percentages — H9's `capital_efficiency` (+1,387.30% recorded,
+86.71% honest) is a third, per report 13's table read directly from
`reports/h9/receipt.json` this session.

## 7. What this session did NOT do

No Pyright run, no test-suite run, no backtest, no H7/H8 retrace, no
re-execution of report 12's F1/F3 mechanisms, no provider call, no ledger
write, no commit/push/branch/merge, no v1 cache byte touched. Claims relying
on reports 08–13 are labeled DOC-VERIFIED above accordingly.
