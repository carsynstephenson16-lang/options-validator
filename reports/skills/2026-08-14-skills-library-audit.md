# Skills-library audit — 2026-08-14

**Author:** Claude (Fable 5 orchestrating session, worktree
`financial-analysis-skill-audit-3f5c84`, base commit 58b1fd9).
**Method:** three parallel Sonnet scans (per-skill drift audit; architecture/
ops gap scan; financial-analysis/sourcing gap scan) followed by an independent
Opus adversarial review instructed to refute findings and kill weak proposals.
Every change below survived that review; several Sonnet findings did not.
**Provenance:** all file:line claims below were re-verified either by the Opus
reviewer or by the orchestrating session against this checkout unless labeled
otherwise. Predecessor: `reports/skills/2026-08-08-fable-5-skill-audit.md`.

## Headline

The library is structurally healthy (registry consistent, symlinks valid, no
retired doctrine lingering) but had a factual-currency gap the 2026-08-08
audit's method could not catch: it validated references and frontmatter, not
claims against current repo state. This audit adds that pass.

## Changes landed (this branch)

| # | File | Change | Basis |
|---|---|---|---|
| 1 | `.agents/skills/options-beginner-explainer/SKILL.md` | Example rewritten: names the registered structure families (H5 CSP+CC; H6/H8 long calls; H7 long lanes routing single long call vs call debit spread on IV-vs-RV; H7c put credit spreads) and points to README "Scope status" for what is active. | Sonnet claimed the put-credit-spread example was legacy-only drift; Opus REFUTED that (H7c is a registered put credit spread — `config.py:456-462`, `strategies/h7_lanes.py:182-192`, `options_researcher/h7_signals.py:148`; Fable re-verified). Real defect was present-tense "trades" while H7 is PAUSED per OD-3. |
| 2 | `.agents/skills/options-data-audit/SKILL.md` | Description made provider-accurate (immutable ThetaData cache OR Schwab-lane capture); body gains a provider note: Schwab has no historical chains/OI/Greeks, never enters `.cache/chains`, N/A checks must be reported as N/A. | `.claude/rules/data-and-providers.md` ("Schwab is the live-preview lane only"); ThetaData kept by name — it remains the historical corpus and a `.cursorrules` hard guardrail cites it. |
| 3 | `.agents/skills/daily-ritual/SKILL.md` | One paragraph naming the merged Schwab lane, bound to the mechanism (`data/ritual_authority.py` flags + the PREPARED authority-flip patch), not to a status that flips. | Grep: zero "Schwab" mentions across all 14 skills pre-change, post PR #35. |
| 4 | `.agents/skills/ledger-discipline/SKILL.md` | Item 1 generalized (IS/OOS split = legacy shape; forward-paper window + loss bar = current norm). New section "Before registering a new hypothesis or forward window": feasibility gate as precondition, provenance labels, owner-typed rule, blank owner fields, review-before-hand-off. | Ledger seq 6–25 carry no window/OOS fields (Opus-verified); `.cursorrules` feasibility gate; absorbs the "registration-packet" skill candidate (see kill list) as a fold-in rather than a new slot. |
| 5 | `.agents/skills/verdict-interpreter/SKILL.md` | "guaranteed" added to the banned-vocabulary list. | Now matches `.cursorrules` Vocabulary discipline verbatim (5 words). Cosmetic. |
| 6 | `.agents/skills/session-synthesis/SKILL.md` | New "Where the note goes" section: exact path, and the worktree trap — the Stop hook (`session_note_guard.py:50-57`) anchors on the CURRENT checkout root, so a gitignored note written in a worktree is destroyed with the worktree. Procedure: write at worktree root for the hook, copy to the main checkout, append (not overwrite) if today's note exists. | Opus finding; Fable re-verified the hook source. Neither Sonnet scan caught it. |
| 7 | `.agents/skills/obsidian-vault/SKILL.md` | One-line exception noting gitignored root daily notes never land with any branch. | Same trap, vault-side wording ("visible after it is landed" was silently false for gitignored notes). |
| 8 | `.claude/skills/research-refresh/SKILL.md` | `disable-model-invocation: true` added. | Open recommendation from the 2026-08-08 audit §8.1, conditioned on the LaunchAgent path being unaffected. Verified this session: `~/options-validator-research/tools/research_refresh.sh` invokes `claude -p "/research-refresh"` — an explicit slash invocation, unaffected by the flag (same pattern daily-ritual already uses). Highest-risk skill in the library (scheduled, networked, budgeted) can no longer be model-auto-invoked in an interactive session. |
| 9 | `.agents/skills/codex-brief-writing/SKILL.md` (**NEW**) + `.claude/skills/` symlink + CLAUDE.md Procedures list | The one new skill. Canonical brief shape: file/naming convention, header block (Date/Author/Executor/Status/Provenance), body order (plain-language why → Scope IN/OUT → work packages → verification), claim-discipline labels, review-before-hand-off, delegates-implementation-never-authority. | 14 briefs since 2026-07-22 with three incompatible body shapes and divergent headers (Opus-verified); recurrence guaranteed by CLAUDE.md division-of-labor policy, near-zero staleness surface. Only candidate of nine to survive adversarial review. |
| 10 | `CLAUDE.md` "Start here" | Index line added pointing at the ops-sync runbook + `tools/launchagents/README.md`. | The ops-sync/LaunchAgent docs had ZERO inbound links from any always-loaded file (Opus measurement); the recurring failure was discoverability, not missing content — a 2-line index entry, not two new skills. |
| 11 | `CLAUDE.md` Conventions; `AGENTS.md` Skills | Stale "commit them with the next landing" (already done) fixed; "`.claude/skills/` holds local copies" corrected to symlinks + the real `research-refresh` dir. | Opus Part-3 findings; `git ls-files` verified. |

Deliberately NOT changed: `results-red-team` and `backtest-realism-audit`
(their put-credit-spread references are accurate — H7c is live and the
survivorship point is timeless); `grilling` one-question-at-a-time in
non-interactive contexts (minor, noted below).

## New-skill candidates killed (do not re-propose without new evidence)

Nine candidates came out of the two gap scans; eight died under adversarial
review. Recorded so the next audit doesn't pay to rediscover them.

| Candidate | Kill reason (Opus-verified) |
|---|---|
| ops-checkout-sync | Content exists at command level in 3 docs; measured defect was zero inbound links. Fixed by the CLAUDE.md index line (#10) at ~1/20th the cost. Closest call of the eight. |
| merge-train-and-review-fix-cycle | "Convention" doesn't exist: the six cited `wt/*` branches are deleted; the two waves used two different shapes. Also collides with owner-reserved merge timing. |
| worktree-and-branch-lifecycle | 4 of 6 elements already load every session from CLAUDE.md verbatim; the guard tool prints its own docs. Textbook restating-CLAUDE.md skill. |
| launchagent-deploy-and-debug | Pure duplication of `tools/launchagents/README.md` §Install/Verify/Uninstall; same indexing fix applies. |
| schwab-data-lane-triage | "Four incidents" = three root causes, two of them one continuous incident; the layer checklist already exists verbatim in `reports/2026-08-12-schwab-auth-diagnosis.md`; capture scripts now print their own reauth remedy; reauth is owner-only (browser + Keychain on the production Mac) so an agent skill would imply the wrong actor. |
| research-lane-registration-packet | "≥6 structurally identical packets" refuted (four documents, four genres, zero shared headings). The real, live need folded into ledger-discipline (#4). |
| earnings-source-refresh | Recurrence evidence did not exist: zero `REFRESH` facts; the 10 "EARNINGS" grep hits are substring matches in other fact types, all ≥3 weeks old. Tool docstring + `--help` already carry the procedure; refresh is owner-in-the-loop by design. |
| data-provider-capability-evaluation | No shared template across the cited reports; the provider question is settled and mechanically enforced (OD-4, provider_policy, "no new paid subscription enters the plan"); routinizing evaluation normalizes the on-ramp to owner-only spend. |

## Open items (not actioned, owner-visible)

1. **Utilization mismatch (structural observation):** three skills trigger on
   "before any backtest run" while no backtest has run since 2026-07-18 and
   engine-building is forbidden; the live activity (forward-paper ops,
   registration drafting) was thinly covered. #4 and #9 address part of this;
   worth rechecking at the next audit.
2. **`grilling` in non-interactive contexts:** its one-question-at-a-time
   contract degenerates when fired inside a subagent. All 25 routing tests
   (2026-07-29) were interactive. Low priority.
3. **Next audit must keep the factual-currency pass:** validate skill CLAIMS
   against current repo state, not just references and frontmatter — that gap
   is how "trades put credit spreads" survived the 2026-08-08 audit while
   being status-stale.

## Verification

- Routing trigger tests (repo standard, 2026-07-29 precedent): 5/5 — three
  positive scenarios route to `codex-brief-writing`; two negatives correctly
  do not (owner decision package → NONE; session wrap-up → `session-synthesis`).
  The NONE result also exposed that ledger-discipline's description didn't
  advertise its new registration-packet section; its description was extended.
- Independent Opus adversarial review of the full diff: **PASS WITH FIXES**.
  All three must-fix findings were applied before commit: (1) H7 lanes a/b
  wrongly described as fixed call debit spreads — they route long call vs
  debit spread on IV-vs-RV (`strategies/h7_lanes.py:80-158`); (2) brief `NN`
  is a plans-directory-wide running sequence, not per-day; (3) this report
  originally overclaimed that the suite enforces registry/symlink invariants.
  Optional fixes applied: reference-brief section naming, H7 restart wording,
  owner-delegated amendment path added to ledger-discipline.
- Full offline suite on this tree: exit 0. **No test enforces skill-registry/
  symlink consistency** — that consistency was verified manually this session
  and remains unenforced.
- `ruff check` + `pyright`: exit codes recorded in the landing commit.
