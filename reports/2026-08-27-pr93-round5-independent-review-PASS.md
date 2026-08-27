# PR #93 round-5 independent adversarial review — PASS — 2026-08-27

- **Reviewed head (exact):** `d8304c6e5c403aea8550db3256e04c75ba7d26a1` (branch `codex/brief27-implementation`, draft PR #93); round-5 commits `542c13f` + `d8304c6` over merge `d43221e` (`origin/main@5652c04` incorporated — full-suite bar exit 0, no tolerated failures)
- **Reviewer:** independent Opus subagent, adversarial framing, read/run-only in detached worktree `.tmp/worktrees/pr93-review3-0827`; all temporary probe edits restored (final `git status --short` empty; touched-file blob hashes re-verified against the head)
- **Controlling artifact:** `reports/2026-08-27-pr93-round4-independent-review.md` @`77ff464` (amended "Required for a round-5 PASS" list, incl. NEW-4 final form and P1-a/A3)
- **Receipt under audit:** `reports/2026-08-27-pr93-round5-receipt.md` (committed at head)

## OVERALL: PASS for head `d8304c6`

All five round-5 gate items survived independent revert/mutation probing; no prior closure regressed; no new Critical or Important-correctness defect. The undisclosed governed-path file (below) is a process/disclosure violation, not a technical blocker.

## Gate-item verdicts (all Test-verified by independent probes, not receipt-reading)

1. **NEW-1 (evaluator crash) — CLOSED.** Real `evaluate_cli` + real `_CausalCoverageValidator`: `long_call` and `leaps` publish OPEN, no crash. Revert probe (restore the unconditional validator call) → suite RED with the exact `PositionSchemaError`. The lane gate does not over-skip: a coverage-changed `cc` position still cancels prospectively (`pmcc` Repo-verified in the literal set).
2. **NEW-2/R2 — CLOSED.** Disabling only the render_id check → 1 test RED (`test_snapshot_render_id_mismatch_fails_closed_independently`). R1 spot-revert RED; Probe A present and green.
3. **NEW-3 (ritual fail-soft) — CLOSED.** The fail-hard mutation Codex's environment refused was performed by the reviewer: `exit 9` on both failure branches → 2 tests RED (structural + `returncode == 0` execution); else-branch-only → 1 RED. `tools/daily_ritual.sh` bytes unchanged this round (sha256-stable). Gap NEW-A below.
4. **NEW-4 final form — CLOSED.** `_current_new_york_session()` = `datetime.now(ZoneInfo("America/New_York")).date()`; two production call sites; **no env var, no CLI parameter, no override flag** — not caller-controllable. Scheduled shape (as_of = prior completed session) publishes with the observation dated the MACHINE date, never as_of. Fresh-tracker and gap-date backdate shapes cannot create past-dated observations (field is unconditionally the machine session). Forged past AND future observation dates raise `LIVE_HOLDINGS_OBSERVATION_SESSION_MISMATCH` BEFORE any write (zero partial artifacts confirmed). Both persisted and newly-observed rows filtered to `observed_session <= session`.
5. **P1-a/A3 — CLOSED.** Revert to snapshot-side binding → 1 dashboard test RED. Digest is over a sorted de-duplicated set symmetrically on both sides (no order/multiplicity asymmetry to exploit); subset divergence detected; duplicate-marker refusal holds; qualified + watch-inclusive + context lanes all flow through the render-side capture; render hashes feed only the HTML marker while the snapshot digest stays independently derived.

**Regression spot-checks:** P2-a revert → 3 RED; N2 reproduced (127 loads / 127 distinct pairs); N3 second-distinct-supersede refused (`SUPERSEDE_ALREADY_RECORDED`; note: this guard has no unit test — pre-existing, not a round-5 regression); Probe B day-1 byte-stability and day-2-dated cancellation intact (its only change was a date-source mock; zero test deletions repo-wide).

**Full suite at the head: 3,428 tests, OK, 5 skipped, exit 0. ruff 0. pyright 0.** Reproduced exactly.

## Governed-path file adjudication

`docs/superpowers/plans/2026-08-27-pr93-round5-fixes.md` (Codex-authored, undisclosed in the receipt). Content audited: an executor work plan — **no frozen values, no thresholds, no registration or pre-registration language, no owner-typed numbers**; it points at the round-4 review as its spec and restates the no-authority posture. Zero inbound references. Sharpest concern: it opens with an instruction addressed to future agents, which is the wrong shape for an undisclosed artifact in the owner-governed path. **Disposition recommended: RELOCATE to `reports/` (or delete — the receipt supersedes it) before landing; owner rules on the boundary breach.** Does not alone block the technical gate.

## New findings

- **NEW-C — Important (disclosure, not correctness).** Machine-date binding makes the same-day live coverage check inert under the only shape the LaunchAgent produces: a coverage change is observed dated today, today's run evaluates yesterday's session, so cancellation lands ONE RITUAL RUN LATE. This is the causally honest cost of removing the look-ahead (applying today's holdings to yesterday's session was exactly the defect), on a display-only lane with no authority — but it is undisclosed in the receipt, the `raise TrackerError("coverage observation was not available…")` is now unreachable dead code, and no test exercises cancellation under production timing. Remedy: disclose the lag as a boundary, delete or re-reach the dead raise, add a production-timing cancellation test.
- **NEW-A — Minor.** The ritual structural guard asserts `assertNotIn("exit ", …)`; a bare `exit` evades it (41/41 stayed green). One-line fix: `\bexit\b` regex.
- **NEW-B — Minor.** A run crossing New York midnight aborts the rebuild fail-closed via the mismatch error (validator and writer derive the date independently); not practically reachable at the scheduled cadence; costs that day's scoreboard if ever hit.
- **NEW-D/NEW-E — Informational.** `id(card)` keying without strong refs (pre-existing pattern); a `create=True` mock that would mask a rename, with one asserted date coinciding with the real date at review time.
- No verdict-bearing, FIRE-capable, paper-book-mutating, or ledger-touching surface in the round-5 diff. One `block_live_trading` hook fire on a grep pattern was honored, not worked around.

## Receipt audit

Substantially honest: every cheaply testable claim reproduced exactly (focused counts 50/199/41/4; full suite 3,428/5/exit 0; ruff/pyright/`git diff --check` 0; shell bytes unchanged; Probe B assertions unchanged; A3/R2 revert behavior; no-override-flag claim; three-lane render capture). Omissions: the governed-path file (most material), the NEW-C lag, the dead raise, the midnight straddle.

## A6 evidence summary (reviewer's words, for the owner)

At head `d8304c6` — which already contains `origin/main@5652c04` — the full offline suite is 3,428 tests, OK, 5 skipped, exit 0, with ruff and pyright clean and no tolerated failures. All five round-5 gate items survived independent adversarial probing rather than receipt-reading. Nothing in this round touches orders, brokers, the network, the paper book, or the ledger. Residual known boundaries for the owner to carry forward: coverage-change cancellation lands one ritual run after the change is first observed; the ritual's structural guard would miss a bare `exit`; a midnight-crossing run fails closed and loses that day's scoreboard; and the executor's implementation-plan file sits undisclosed in the owner-governed path pending relocation.
