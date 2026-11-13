# D — Repo efficiency & instruction-effectiveness audit (2026-09-15)

Read-only; no tracked file modified. **Session load:** `CLAUDE.md` 8,913 B/154 L **+** `@.cursorrules`
8,365 B/141 L = **17,278 B unconditional**, plus `.claude/rules/` (1,786+2,463+1,429 B) by path.
`AGENTS.md` 18,691 B/338 L (Codex). `PROJECT_STATE.md` 100,150 B/1,043 L.

## §1 Findings

| id | area | file:line | problem | evidence |
|---|---|---|---|---|
| **A1** | stale | `.cursorrules:79`, `AGENTS.md:184` | "H5, H6, H7, and H8 are registered forward-paper hypotheses" — live set adds H10a (CLOSED), H10b, RQ1 (SPENT), RQ2-v1, A2-v1 | `README.md:250-284`; **both files self-contradict 50 lines later** at `.cursorrules:130`/`AGENTS.md:231`, which list all eight |
| **A2** | contradiction | `CLAUDE.md:6-9`, `:25-26` | points at two gates that no longer exist: `.cursorrules`' Scope guard and PROJECT_STATE's "P0 gate wins" | `.cursorrules:102-103` "no longer blocks building"; `PROJECT_STATE.md:203` closes those P0s; blocker retired at `.cursorrules:100-118` |
| **A3** | drift | `.cursorrules` → **absent from** `AGENTS.md` | Codex never loads `:15-43` — no-look-ahead; mid-or-worse + SLIPPAGE_HAIRCUT; COMMISSION_PER_CONTRACT both legs + half-spread; MIN_OPEN_INTEREST/MAX_SPREAD_PCT both legs; EOD-gap skip-the-day; parquet cache; no-custom-engine; verify-API-against-installed-lib; numbers-from-`config.py`; expectancy+bootstrap-CI headline; `MIN_LOSSES_FOR_VERDICT` gate | `AGENTS.md:170-183` has only a generic "lookahead / bad fills / spread costs" line — no constant, no mid-or-worse rule, no loss gate |
| **A4** | drift | `AGENTS.md` → **absent from** `.cursorrules` **and** `CLAUDE.md` | Claude never loads: **Draft-PR authority hold** `:98-104`; **Catalyst-Calendar Rule** `:266-274` (PJM BRA); Data Rules `:250-264`; Security Rules `:308-316`; `ruff format --check` `:150` | `CLAUDE.md:18-19` mandates co-update; `git log -1` shows `.cursorrules` 08-10 vs `AGENTS.md` 08-25 — the 08-25 hold landed in one file only |
| **A5** | bloat | `.cursorrules:87-141` ≡ `AGENTS.md:191-242` | ~2.4 KB of 08-03/08-09 authorization narrative duplicated verbatim; one copy loads every session | operative content ≈ 3 sentences |
| **A6** | redundant | `CLAUDE.md:76`; `.cursorrules:52` | ledger hand-edit ban stated 3×; "validator only, no live orders" 4× | also `.claude/rules/ledger.md:12-16` + hook; `.cursorrules:12`, `CLAUDE.md:5,116`, `AGENTS.md:182` |
| **A7** | stale-soon | `README.md:54` | "Current holdings" hard-codes live book state into a doc | true today (39 VST; h8 empty; H6-0001 open) — H6-0001 **expires 09-18** |
| **A8** | gap | `CLAUDE.md:54-68` | omits `ruff format --check` and `tools/h7_activation_day.sh` (landed #161, 09-08) | `grep -c h7_activation_day CLAUDE.md AGENTS.md README.md` → 0/0/0 |
| **B1** | findability | `PROJECT_STATE.md:1-181` | **34,200 B — 34% of the file — of refresh log before the first heading**; 9 paragraphs, largest 5,430 B (`:11`), 3,761 (`:13`), 3,657 (`:9`) | the current next task and live blocker exist only as prose inside `:9`/`:11` — no heading, list, or anchor |
| **B2** | stale / misleading | `:3,:7`; `:209` §2 "P0 in plain language"; `:677` §12 "execution queue" | header says "Audit date 2026-08-02", "branch `sfix`"; the only two headings a reader would search are historical | committed 09-09, **no branch `sfix` exists**; `:203` closes those P0s, Q0–Q15 mostly COMPLETE. **Verdict: the current P0/next task is not findable in under a minute** |
| **B3** | links | — | **140** `PROJECT_STATE` refs across `*.md/py/sh/json/toml`; **zero in `.py`/`.sh`** → restructure is docs-only | 7 anchored refs listed in P3 |
| **C1** | ops SPOF | `daily_ritual.sh:102-107` | the gate compares HEAD to `origin/main` **with no `git fetch`** — a stale ref PASSES while the checkout runs behind reviewed code | the 15:45 wrapper fetches first: `schwab_chain_capture.sh:44-49` |
| **C2** | ops SPOF | `daily_ritual.sh:102-107` vs `:601,:612-623` | **Deadlock.** Step 8 commits (`:601`) → `push_evidence_once` fails (`:622`) → next morning dies at `:106` *before* reaching Step 8's push. The only self-heal sits downstream of the gate its own failure trips; `:604` still promises "retries next run" | the wrappers got evidence-only tolerance for exactly this on 08-14 (D-3); rationale at `schwab_chain_capture.sh:58-60`: *"A strict SHA equality also refused when the only divergence was the daily ritual's own evidence commit whose fail-soft push had failed -- turning a transient push failure into a PERMANENTLY lost irreplaceable capture."* The ritual never got it |
| **C3** | ops SPOF | `daily_ritual.sh:562-563` | `DATA_TIER_PATHS` stages `reports/pick_tracker` + `reports/closes_receipts`, in **no** `EVIDENCE_ALLOW` list; `closes_receipts` gains a dated dir every morning (8 present, newest 09-09) | **defeats D-3** — on a failed push the divergence holds non-allow-listed paths, so the 15:45 capture cannot be rescued. Brief-40 r2 finding 3 was applied to `h7_activation_day.sh`, not Step 8 |
| **C4** | ops gap | `daily_ritual.sh:572-574` | `FULL_TIER_PATHS` omits `reports/h7_data_gate_schwab`, `reports/h7_forward_schwab` | both allow-listed; both written by the activation-day chain |
| **C5** | ops SPOF | `daily_ritual.sh:134-139`, `:628-637` | `CHAIN_EDGE` derives the cache edge by `ls`+`sed` on filenames — a convention or v2-namespace change yields empty, STARVED never fires, the board looks healthy over a frozen cache; separately, restic failure is a `note`, not a `crit` | no test pins the filename convention against the sed; `:636` never raises `CRIT_COUNT` |
| **C6** | ops SPOF | launchd | installed-but-not-loaded has no runtime check; `research-refresh` is in that state now and two agents silently dropped out (one cost 5 weeks of a stale board) | `PROJECT_STATE.md:9`; brief 41 written, branches exist, **unlanded** |
| **D1** | enforcement | `.gitignore:22` vs `CLAUDE.md:109-114` | 2 of 3 "hard enforcement" hooks (`block_live_trading`, `session_note_guard`) live at `.claude/hooks/*.py`, **untracked** — absent from a fresh clone, both ops checkouts, every worktree | `git check-ignore -v` → `.gitignore:22 .claude/*`; only `.agents/hooks/block_ledger_edits.py` is tracked. `:114` discloses local *registration*, not untracked **bodies** |
| **D2** | ok | `.agents/skills/` | 15 skills, all symlinked into `.claude/skills/` plus real `research-refresh`; `CLAUDE.md:101-107` lists exactly those. **No drift; no skill contradicts CLAUDE.md.** All 3 hooks registered; all `.agents/hooks/*.py` referenced | sizes below |
| **E1** | tests | `.tmp/audit-2026-09-15-testrun.log` | **exists but is 0 bytes** — no wall-clock. Published figures stale: `PROJECT_STATE.md:274` "2,284/2,284 passed in 333.781s" (144 modules); `docs/evidence-upgrade/codex-sol-high-execution-plan.md:53` "2109 tests OK (~4min)" | tree is now **218 modules / 3,905 `def test_` / 3.33 MB / 704 TestCases** |
| **E2** | tests | — | driver is **tempfile + subprocess**, not sleeps: tempfile 141/218, parquet 63/218, subprocess 39/218; sleeps 45 ms total; freezegun zero; hypothesis in one module. No markers, `-k`, Makefile, `tests/__init__.py`, or conftest | `test_black_scholes_properties.py:13` `max_examples=100, deadline=None, derandomize=True`, 8 `@given`. CI's `macos-shell-contracts` subset (19 modules) is topic-scoped and holds 5 of the 10 heaviest |
| **F1** | dead | `crawler.js`, `package.json`, `package-lock.json` (**tracked**, 136 KB); `node_modules/` 120 MB + `storage/` 136 KB (ignored) | Node **100% dead** — `crawler.js` is the verbatim Crawlee tutorial crawling `crawlee.dev`; no `setup-node`, no Node in pre-commit, no `npm/npx/node ` anywhere | queued `PL471-C7b`, `reports/2026-08-09-parking-lot-471-idea-ledger.json:439`, **`"blocker": ""`** — gate now satisfied |
| **F2** | **NOT dead** | `REVIEW.md` | load-bearing CI — the PR-review charter | `claude-review.yml:116` `git show "origin/${base_ref}:REVIEW.md"`, `:127` "Follow ./REVIEW.md exactly". **Deleting breaks every PR**; the base-branch overwrite is a deliberate injection defense |
| **F3** | dead / orphan | `.coverage` 1.2 MB; `Untitled*` ×4; `docs/branch-disposition-2026-08-03.md` | first two untracked+ignored, never committed, zero consumers; the doc is tracked with **zero** inbound refs | `.gitignore:6,47-48`; 66 other unreferenced `docs/**.md` are write-once SDD artifacts (benign) |
| **F4** | stale-but-linked | `docs/monday-runbook.md` (8 refs), `docs/options-validator-readiness.md` (4), `docs/codex-implementation-plan.md` (1) | mutually-reinforcing 2026-07-25 ThetaData-premised cluster; `wiki/` is the only consumer | `reports/2026-09-09-pm-sweep-and-pattern-findings.md:98` and `wiki/automation.md:15` already call the runbook stale; bare deletion dangles 13 `wiki/` links |

**10 heaviest test modules** (bytes; composite of size, test count, tempfile/parquet/subprocess use;
all `tests/`): `test_attractiveness_dashboard.py` 192,825 (4,177 L, 223 tests, 45 tempfile — 5.8% of
suite bytes) · `test_intraday_capture.py` 80,971 · `test_daily_ritual_provenance.py` 63,274 ·
`test_research_integrity.py` 59,128 · `test_job_health_digest.py` 49,189 ·
`test_schwab_chain_intraday.py` 27,840 · `test_h7_entry_variant_menu.py` 27,773 · `test_h8_watch.py`
24,386 · `test_job_health_digest_schedule.py` 17,184 · `test_anti_stranding_remote_owner.py` 12,803.

**Skills** (`.agents/skills/*/SKILL.md`, bytes/lines/mtime): independent-research-critic
6,479/148/08-20 · daily-ritual 4,986/101/08-16 · ledger-discipline 4,286/48/08-16 · web-fetch-order
3,826/57/08-04 · codex-brief-writing 3,610/61/09-09 · results-red-team 3,568/37/07-29 ·
executor-handback-verification 3,322/54/09-09 · obsidian-vault 3,039/77/08-16 · options-data-audit
2,989/46/08-16 · backtest-realism-audit 2,902/39/07-07 · session-synthesis 2,592/50/08-16 ·
options-beginner-explainer 2,585/31/08-16 · repo-health-review 2,357/27/07-29 · verdict-interpreter
2,333/34/08-16 · grilling 1,008/10/07-29.

## §2 Proposed changes, ranked by value ÷ risk

**P1 — Give the ritual the alignment tolerance the wrappers already have** *(ops-script)*. Replace
`daily_ritual.sh:102-107`'s un-fetched strict SHA equality with the wrappers' predicate: (1) fetch
first, bounded and prompt-free — copy `schwab_chain_capture.sh:44-49` verbatim, refuse on fetch
failure (**C1**); (2) if `git rev-list --count HEAD..origin/main` ≠ 0 → refuse exactly as today;
(3) if ahead-only **and** `git diff --name-only --no-renames origin/main HEAD` touches only
`EVIDENCE_ALLOW` paths → `git push origin main` once, re-resolve, proceed; else → today's message (**C2**).
*Is a start-of-run bounded push safe? Yes, with one modification.* It grants **no new authority** —
`push_evidence_once()` (`:612-616`) already pushes ops main to origin/main every run. But do not
reuse that function: it runs `merge -q --no-edit origin/main` first, which could create a merge
commit and change the tree the ritual is about to execute (fine at end-of-run, not at start). Use a
bare push reachable only on the ahead-only + evidence-only branch. The residual risk — a human
evidence-path commit on ops main gets auto-pushed — already exists at `:617` and is allow-list
bounded. **Worst case on misfire: the ritual refuses, i.e. today's behaviour.** *Could break:* a
predicate permissive in the wrong direction lets unreviewed **code** run unattended against the real
H7 ledger — mitigate by reusing the wrapper's reviewed `alignment_divergence_is_evidence_only()`
body unchanged (`:78-86` documents the merge-commit and rename blind spots it defends).
*Test that pins it:* `tests/test_schwab_chain_capture.py:320-395` is the ready-made harness (temp
repo, fake `git`/`uv`/`date` shims on `PATH`, real wrapper under `zsh` via `subprocess`). Clone to
`tests/test_daily_ritual_alignment.py` with four cases — aligned, behind, ahead+evidence-only+push
OK, ahead+evidence-only+push fails — and have the fake `git` assert `fetch` ran *before*
`rev-parse origin/main`. Extend the byte-order fence `tests/test_daily_ritual_provenance.py:715-723`
with the new fetch index.
**Verify:** `PYTHONPATH=tests uv run python -m unittest test_daily_ritual_alignment test_daily_ritual_provenance test_schwab_chain_capture`

**P2 — Close the `DATA_TIER_PATHS ∖ EVIDENCE_ALLOW` hole** *(ops-script)*. `daily_ritual.sh:562-564`:
stage only the **intersection** of the two; any dirty path outside it is a refusal — the disposition
brief-40 r2 already ratified for `h7_activation_day.sh`. Add the two missing `reports/h7_*_schwab`
paths to `FULL_TIER_PATHS` (**C4**). Without P2, P1's tolerance is worthless on any morning
`closes_receipts` gains a directory, i.e. every morning. *Could break:* `pick_tracker`/
`closes_receipts` stop being auto-committed — decide explicitly (add them to all four allow-lists,
preferred, or accept non-persistence). *Verify:* assert the intersection in the shell test,
mirroring `tests/test_h7_activation_day.py:298-306`, which already reads `DATA_TIER_PATHS`.

**P3 — Restructure `PROJECT_STATE.md`, preserving every byte** *(docs-only)*. Move `:1-181` verbatim
→ `docs/status-history/2026-08-02--2026-09-09-status-refresh-log.md` and `:182-1043` verbatim →
`docs/status-history/2026-08-02-audit-body.md`, `§1`–`§15` numbering untouched. Leave a ≤150-line
head: title, **As of**, **Next 3 actions**, **Live blockers**, **Owner decisions pending**, index of
the two history files. Docs-only because **zero `.py`/`.sh` read it**. Keep these 7 anchored links
resolvable by listing them in that index —
`docs/superpowers/plans/2026-08-09-h7-schwab-restart-codex-brief.md:249` (§13);
`docs/superpowers/specs/2026-08-03-cross-project-research-source-standard-design.md:16` (§6);
`reports/2026-08-15-branch-cleanup-batch.md:79` (§3.1);
`reports/provider-transition/2026-07-31-q4-exact-asof-proof.md:5` (Q4);
`reports/provider-transition/2026-08-04-scanner-staleness-diagnosis.md:225` (§6);
`reports/strategy-evaluations/14_governance_rebuild_2026-07-31.md:115` (§4–§5);
`reports/strategy-evaluations/15_owner_summary_2026-07-31.md:78` (§9). Also fix **B2**. *Verify:* the two new files' line counts sum to
1,043; `diff` the moved ranges.

**P4 — Reconcile `.cursorrules` ↔ `AGENTS.md`** *(docs-only, governed wording)* — one pass, both
files, as `CLAUDE.md:18-19` requires. **A1:** `.cursorrules:79`/`AGENTS.md:184`, old
`H5, H6, H7, and H8 are registered forward-paper hypotheses;` → new `the registered set is
maintained in README.md "Scope status" — do not restate it here;`. **A3:** port `.cursorrules:15-43`
verbatim into `AGENTS.md`'s "Quant, Trading, and Market Rules". **A4:** port the Draft-PR authority
hold and Catalyst-Calendar Rule into `.cursorrules` so both agents inherit them via `@`. **A5:**
collapse the duplicated authorization narrative to one operative sentence each plus the dated-report
pointers it already cites. *Could break:* dropping a binding rule by accident — diff rule-by-rule
against A3/A4 above. *Verify:* `grep -n "H5, H6, H7" .cursorrules AGENTS.md` → none;
`grep -c "Draft-PR\|Catalyst-Calendar" .cursorrules` → 2.

**P5 — Track the two untracked hooks** *(ops-script/config)*. **D1:** move `block_live_trading.py`
and `session_note_guard.py` into the already-tracked `.agents/hooks/` and update the two `command`
strings in `.claude/settings.local.json`. Registration stays local; the **bodies** become
reproducible. *Could break:* both hooks stop firing if the settings edit is not made in the same
change — do them together and confirm with one deliberate trigger each.

**P6 — Measure before optimizing tests** *(tests)*. **E1:** the log is empty and every published
figure is stale, so ranking by file size is a guess. Run once:
`uv run python -m unittest discover -s tests -v 2>&1 | tee .tmp/testrun-$(date +%F).log`. Do **not**
add pytest markers — `CLAUDE.md:79` and `AGENTS.md:148` pin `unittest`, and forking the runner for
speed weakens what CI asserts. Free win today: document CI's own module-selection loop in the
Commands block, `PYTHONPATH=tests uv run python -m unittest <module>…` (needed because there is no
`tests/__init__.py`). `pytest-xdist -n auto` is viable in principle (100% `TestCase`, no conftest,
`pytest 9.1.1` already in `.venv`/`uv.lock:3558`) but 141 modules touch `tempfile`; fixed-path
collisions must be **proven** absent, so rank it below the measurement step.

**P7 — Dead weight.** *Delete (untracked + ignored, zero consumers; docs-only):* `node_modules/`
120 MB, `storage/` 136 KB, `.coverage` 1.2 MB, `Untitled*` 6 B. *Delete with a commit (ops-script,
low):* `crawler.js`, `package.json`, `package-lock.json` — `PL471-C7b`'s gate is satisfied by F1.
**Do NOT delete `REVIEW.md`** (F2). *Refresh, do not bare-`rm`* (F4): add a one-line `> SUPERSEDED —
see docs/provider-transition.md and PROJECT_STATE.md` banner atop the 2026-07-25 trio, leaving the
13 `wiki/` links intact. `docs/branch-disposition-2026-08-03.md` is an owner call. **Never** proposed
for deletion: `.cache/`, `data/`, `ledger/`, `reports/`, any worktree.

**P8 — Land brief 41** *(ops-script)*. **C6:** implemented on
`codex/brief-41-launchagent-loaded-check`, unlanded, while `research-refresh` sits in exactly the
state it detects. The highest-value already-paid-for fix in the queue.

## §3 Proposed `CLAUDE.md` (full text, 5.4 KB)

```markdown
# options-validator — Claude Code instructions

Research platform anchored to four AI-infrastructure core names (VST, CEG,
MSFT, AMZN), plus the owner-authorized H7 story-name watchlist. **Research
only — this is NOT a live bot and places no orders.** A "no edge after costs"
finding is a success, not a failure to fix.

## Non-negotiable research guardrails

@.cursorrules

The import above is the authoritative wording (hard guardrails, engineering
rules, verdict rule, claim discipline, vocabulary discipline, feasibility gate,
web-fetcher limits, draft-PR authority hold, catalyst-calendar rule, scope
guard). If sources conflict, say so instead of picking one silently.
`AGENTS.md` is the Codex-facing twin. When a guardrail changes, update
`.cursorrules` and `AGENTS.md` in the same commit so they cannot drift.

## Start here (single-source index)

Do not restate live state in this file — a copy here goes stale silently.

- **Status, next task, live blockers:** `PROJECT_STATE.md` (canonical).
- **Which hypotheses are registered:** `README.md` "Scope status" (the registry).
- **Provider transition (ThetaData exit, Schwab lane):** `docs/provider-transition.md`.
- **H7 day-to-day operations:** `docs/h7-forward-operations.md`.
- **Ops checkouts + scheduled jobs:** `tools/launchagents/README.md` and
  `docs/superpowers/plans/2026-08-13-08-fork-healing-ops-sync-canary-runbook.md`.
- **Parked ideas:** `ideas-parking-lot.md` — parked is not rejected; it's just not now.
- **Path-scoped rules** load automatically from `.claude/rules/` (ledger,
  data/providers, backtest engine).

## Division of labor (owner directive 2026-07-22)

Claude sessions ORCHESTRATE: research, specs, Codex briefs, review,
verification, owner decision packages. Codex implements from briefs. The owner
types every frozen number, new registration, and verdict ratification.
Amendments to already-registered specs may be drafted and recorded by the
implementing agent only after independent adversarial review and Fable's
sign-off, labelled "owner-delegated standing 2026-07-25"; the owner retains
veto, exercised by a further append-only amendment.
Delegate heavy reading and routine lifting to subagents (Sonnet for research
and scouting, Opus for adversarial review); reserve the main session for
judgment, synthesis, and integrity checks. Claude writes code directly only
for docs, briefs, and trivial mechanical fixes — not strategy or ledger code.

## Commands

```bash
uv sync --frozen                                 # Python 3.12; uv.lock is source of truth
uv run python -m unittest discover -s tests      # full suite, OFFLINE; exit code is the verdict
PYTHONPATH=tests uv run python -m unittest <mod> # fast loop: named modules (no tests/__init__.py)
uv run ruff check . && uv run ruff format --check . && uv run pyright
uv run python tools/irreplaceable_data_guard.py verify  # REQUIRED before deleting any worktree/branch/dir
uv run python -m options_researcher.h7_source_health    # exit 1 = refresh needed
uv run python -m options_researcher.h7_data_gate --source-health-receipt <path>
uv run python -m options_researcher.h7_entry_preflight  # read-only; writes nothing
tools/h7_activation_day.sh                       # one-shot activation-day receipt chain
uv run python -m options_researcher.dashboard    # writes .tmp/dashboard/index.html
uv run python -m options_researcher.live_dashboard --serve  # display-only live lane
uv run python -m options_researcher.live_quotes --probe     # regular-session schema probe
uv run python -m options_researcher.attractiveness_dashboard
uv run python -m tools.research_context_assemble --verify
uv run python -m options_researcher.robustness --help
```

H7 safety clauses that are easy to forget: `--source-health-receipt` is
REQUIRED on the data gate (a receipt written without it is immutable and
permanently revokes that session's real-entry authority); operator order is
source health → data gate exit 0 → watcher; source-unhealthy names are
entry-banned per-name by the watcher's fail-closed gate but a data-gate NO_GO
still blocks the run (amendment v1.4, 2026-07-14). The daily procedure is the
`daily-ritual` skill.

Tests are `unittest` (not pytest) and must stay runnable offline against the
local parquet cache — no network, no paid API calls. Anything that would hit a
provider endpoint needs owner sign-off first (`.claude/rules/data-and-providers.md`).

## Layout

- `ledger/` — append-only research ledger. Never rewrite or delete entries.
- `data/`, `.cache/chains/` — parquet chain cache (v1, immutable); `data/positions/` drives the paper book.
- `reports/`, `docs/superpowers/` — dated findings, frozen specs, pre-registrations.

## Research integrity (always on)

- Hypotheses are pre-registered in the ledger before results exist: parameters
  frozen first, run once, result recorded whatever it shows.
- The legacy holdout is sealed (OOS reveal budget 0/3 spent). Never read past
  `IN_SAMPLE_END` without the reveal gate. 2023+ is not a credible blind
  holdout for these names; new hypotheses pre-declare their own validation design.

## Procedures (read the SKILL.md before performing)

Repeatable procedures live in `.agents/skills/<name>/SKILL.md` (tracked) and
are symlinked into `.claude/skills/`. `.claude/skills/research-refresh` is the
scheduled research-context refresh. `ls .agents/skills` is the current list —
do not maintain a second copy here.

## Hard enforcement (hooks — treat a block as correct)

- `block_live_trading` (PreToolUse): no live order paths; validator only.
- `block_ledger_edits` (PreToolUse): ledger writes only via typed APIs.
- `session_note_guard` (Stop): work days need a session note (`session-synthesis`).
Hook bodies are tracked in `.agents/hooks/`; registration is local in
`.claude/settings.local.json` (gitignored by policy). Do not work around a
hook. This repo is a validator: it never places orders, never connects to a
live brokerage endpoint, and never disables paper mode.

## Worktree location rule (owner-directed 2026-08-03)

Worktrees live under `.tmp/worktrees/<short-name>` and **nowhere else** — never
in `/tmp` or `/private/tmp`, never in `~/Downloads`, never as a bare sibling
directory, so `git worktree list` stays the single honest inventory.

Two sanctioned exceptions, load-bearing for scheduled jobs — **do not remove or
relocate them**: `~/options-validator-ops` (LaunchAgent `WorkingDirectory` for
`daily-ritual` and `live-dashboard`) and `~/options-validator-research`
(`tools/research_refresh.sh` for `research-refresh`).

To move a misplaced worktree use `git worktree move`; never `rm -rf` one.
Before removing any worktree, branch, or directory, run
`uv run python tools/irreplaceable_data_guard.py verify` AND
`git -C <path> status --short --ignored=matching --untracked-files=all`.
Rationale and the 2026-08-03 od1-v2 incident: `.claude/rules/data-and-providers.md`.

## Conventions

- Root dated notes (`/2026-*.md`, `Untitled*`) are gitignored Obsidian scratch — never commit them.
- Secrets live in `.env` / macOS Keychain (`.env.example` is the template).
- `.claude/rules/` and `.claude/skills/` are tracked; the rest of `.claude/` stays local-only.
- `wiki/` is derived operator memory, never source of truth (`wiki/CLAUDE.md`).
```

**Removed sentences → where the content now lives** (`:N` = old CLAUDE.md line)

- `:6-9` binding-scope-test / no-scanner-retirement → `.cursorrules:78-118` (guard **and** its retirement). Fixes **A2**
- `:23-26` "older plans superseded… its P0 gate wins" → `PROJECT_STATE.md` head (P3). Fixes **A3**
- `:31-32` engine-defect history + report-12 path → `PROJECT_STATE.md` §5, `.claude/rules/backtest-engine.md:14-19`
- `:42-46` amendment-delegation rationale → one operative sentence; full text in the 2026-07-25 ledger amendment
- `:76-77` "NEVER hand-edit `ledger/h7_forward/*`" → `.claude/rules/ledger.md:12-16` + `block_ledger_edits`. Fixes **A7**
- `:101-106` the 15-name skill list → `ls .agents/skills` (a hand-kept list only drifts)
- `:124-125` stray-checkout narrative → folded into the rule's clause
- `:130-135` plist / `.cache`-symlink detail → `tools/launchagents/README.md`
- `:141-146` 110 MB od1-v2 incident + `LOCATION ERROR` note → `.claude/rules/data-and-providers.md:36-45` (**already a verbatim duplicate today**)
- **Added:** draft-PR hold + catalyst rule via `@.cursorrules` (**A5**); `ruff format --check`, `h7_activation_day.sh`, fast-loop command (**A10**); `docs/h7-forward-operations.md`; tracked hook bodies (**D1**)

5,431 B vs 8,913 B — **39% smaller**; with P4's `.cursorrules` collapse the session load falls from
~17.3 KB to ~12.7 KB.

## §4 The `EVIDENCE_ALLOW` lists, verbatim

**Four** copies exist today, not three — `h7_activation_day.sh` added a fourth when Brief 40
landed (#161, 2026-09-08) — plus the ritual's two staging arrays.

```
tools/schwab_chain_capture.sh:65-71
  65  EVIDENCE_ALLOW=(ledger/facts.log ledger/h7_forward ledger/h7_forward_schwab
  66                  reports/h7_receipts reports/h7_data_gate
  67                  reports/h7_data_gate_schwab reports/h7_forward_schwab reports/h5
  68                  reports/h6_forward reports/h8_forward reports/h10
  69                  reports/ritual reports/intraday_capture reports/live_probe
  70                  reports/cache_runs reports/schwab_chains
  71                  reports/schwab_chains_intraday)

tools/schwab_chain_intraday_capture.sh:73-79
  73  EVIDENCE_ALLOW=(ledger/facts.log ledger/h7_forward ledger/h7_forward_schwab
  74                  reports/h7_receipts reports/h7_data_gate
  75                  reports/h7_data_gate_schwab reports/h7_forward_schwab reports/h5
  76                  reports/h6_forward reports/h8_forward reports/h10
  77                  reports/ritual reports/intraday_capture reports/live_probe
  78                  reports/cache_runs reports/schwab_chains
  79                  reports/schwab_chains_intraday)

tools/ops_alignment_check.sh:62-68
  62  EVIDENCE_ALLOW=(ledger/facts.log ledger/h7_forward ledger/h7_forward_schwab
  63                  reports/h7_receipts reports/h7_data_gate
  64                  reports/h7_data_gate_schwab reports/h7_forward_schwab reports/h5
  65                  reports/h6_forward reports/h8_forward reports/h10
  66                  reports/ritual reports/intraday_capture reports/live_probe
  67                  reports/cache_runs reports/schwab_chains
  68                  reports/schwab_chains_intraday)

tools/h7_activation_day.sh:22-28
  22  EVIDENCE_ALLOW=(ledger/facts.log ledger/h7_forward ledger/h7_forward_schwab
  23                  reports/h7_receipts reports/h7_data_gate
  24                  reports/h7_data_gate_schwab reports/h7_forward_schwab reports/h5
  25                  reports/h6_forward reports/h8_forward reports/h10
  26                  reports/ritual reports/intraday_capture reports/live_probe
  27                  reports/cache_runs reports/schwab_chains
  28                  reports/schwab_chains_intraday)

tools/daily_ritual.sh:562-563   (staging, data tier)
 562  DATA_TIER_PATHS=(reports/ritual reports/intraday_capture reports/live_probe reports/cache_runs
 563                   reports/h5 reports/h10 reports/schwab_chains reports/schwab_chains_intraday reports/pick_tracker reports/closes_receipts ledger/facts.log)

tools/daily_ritual.sh:572-574   (staging, full tier — added only when FULL_AUTHORITY_RC == 0)
 572    FULL_TIER_PATHS=(ledger/facts.log ledger/h7_forward ledger/h7_forward_schwab
 573                     reports/h7_receipts reports/h7_data_gate
 574                     reports/h6_forward reports/h8_forward)
```

**Diff.**
1. The four `EVIDENCE_ALLOW` copies are **byte-identical** — same 17 paths, same order, same
   wrapping. Pinned equal by a star topology around `schwab_chain_capture.sh`:
   `tests/test_ops_alignment_check.py:310-320`, `tests/test_schwab_chain_intraday.py:440,523`,
   `tests/test_h7_activation_day.py:303-306`. A fifth copy (P1) must join that star, or all five
   should be replaced by one sourced file.
2. **`DATA_TIER_PATHS` ⊄ `EVIDENCE_ALLOW`:** `reports/pick_tracker` and `reports/closes_receipts`
   are in **no** allow-list; `closes_receipts` gains a dated directory every ritual morning (8
   present, newest `2026-09-09`). Finding **C3** — this silently defeats owner decision D-3.
3. **`FULL_TIER_PATHS` ⊂ `EVIDENCE_ALLOW`** (all 7 present) but **omits**
   `reports/h7_data_gate_schwab` and `reports/h7_forward_schwab`, both allow-listed and both
   written by the activation-day chain. Finding **C4**.
4. No allow-list entry is over-broad relative to staging; the asymmetry runs only in the
   direction of (2) and (3).
