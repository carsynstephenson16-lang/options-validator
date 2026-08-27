# PR #93 round-4 (second fix round) independent adversarial review — 2026-08-27

- **Reviewed head (exact):** `fd38aa22e21b9bd680d37b984730c23ec622ec1d` (branch `codex/brief27-implementation`, draft PR #93); implementation commit `0de1457d8cb760952da01009fb9ed50ee941faa0`
- **Reviewer:** independent Opus subagent commissioned by the orchestrating Claude session; adversarial framing; read/run-only in detached worktree `.tmp/worktrees/pr93-review2-0827`; all temporary probe edits restored (final `git status --short` empty, HEAD re-verified)
- **Controlling artifact:** `reports/2026-08-27-pr93-fix-round-independent-review.md` @`95bdfd4` (amended). Codex implemented from the pre-amendment version and never received the round-4 addendum — divergences adjudicated on merits per the dispatch.
- **Receipt under audit:** `reports/2026-08-27-pr93-fix-round-2-receipt.md` (committed at the reviewed head)

## OVERALL: FAIL for head `fd38aa2`

Every commissioned item closed: P1-a and P1-b are closed for the mechanisms their probes name (Probe A → rejected with `SNAPSHOT_HTML_SOURCE_MISMATCH`; Probe B extended to 3 days → day-1 bytes byte-stable, cancellation dated to its observed session; R1 revert now RED), N2/N3/N5/N6/N7 closed with discriminating tests, the N4 divergence is ACCEPTED (see below), and no prior closure (P1-c/P2-a/P2-b) regressed. **But the round introduces one Critical and three Important new defects**, one of which makes the evaluator inoperable in production for the non-covered lanes.

## Key adjudications

- **P1-a: post-hoc tampering closed; REOPENED narrowly for producer divergence (A3).** Residual probes: A2 (rewrite the digest inside the HTML too, update `html_sha256` + `render_id`) and A3 (producer renders one dataset, snapshots another) are still ACCEPTED. A2 is outside any detectable model (an attacker rewriting published HTML can rewrite the visible table; byte-level detection cannot distinguish) and is accepted as a permanent boundary. A3 is NOT accepted: the controlling dispatch requires failure on ANY source-row/render divergence, and a producer that renders one dataset while snapshotting another is a plausible implementation failure, not attacker-only. Because the embedded digest is currently computed from the snapshot side (`attractiveness_dashboard.py:5276-5277`), a diverging producer stays self-consistent. Round 5 must derive the embedded digest from the RENDER-side data path (the values actually rendered), so snapshot-vs-render divergence yields a digest mismatch at validation. Duplicate digest-marker injection fails closed. *(Amended 2026-08-27 after PR #117 review comment 3875261975 — the original "closed with a documented boundary" adjudication conceded A3, contradicting the dispatch's any-divergence wording.)*
- **P1-b: closed for the named mechanism.** Validator causality sound: live holdings read only at `session == as_of`; earlier sessions consume only persisted observations dated `<= session`; future sessions raise. But see NEW-1 and NEW-4.
- **N3: closed; wording divergence, contract preserved.** The `|| note` wrapper was replaced by `if/elif/else`, but Test-verified fail-soft: conflict and generic failure both leave ritual exit 0 and CRITICAL unchanged, even under injected `set -e`. Supersede attacks all refused (no-canonical-date, empty reason, second distinct supersede, path traversal, tampered replacement bytes); repeat of the same supersede idempotent; ritual never passes the flag.
- **N2: closed.** 254 → 127 loads for 127 distinct pairs, reproduced at both heads. Cached loader errors surface as fail-visible `MARK_GAP`, per-run only.
- **N4 divergence: ACCEPTED.** Blanket non-READY carry-forward eliminates entry synthesis for ALL states (strictly better than the denylist); the literal state string is preserved in the journal (forensically recoverable); a corrupted state surfaces as `LANE_FAILED` — loud, but indistinguishable from a genuine producer FAILED at the report layer. Diagnostic-precision loss, not corruption laundered. Non-blocking follow-up: set `"reason": arm_state` (one line) so the literal state reaches the report.

## New findings

- **NEW-1 — CRITICAL — evaluator crashes for `long_call`/`leaps`; the lane is dead in production.** `resolve_fill` calls the coverage validator unconditionally BEFORE consulting `needs_coverage_check` (`pick_tracker.py:835-836`); `_coverage_key` (`:646-650`) hard-raises when `coverage_context` is absent — the normal case for non-covered lanes (`attractiveness_dashboard.py:4771` sets `coverage = None`). Measured through the real `evaluate_cli`: `long_call` and `leaps` CRASH with `PositionSchemaError` at `fd38aa2`; both ACCEPTED at `36a167e`. The exception is uncaught end-to-end, so the ENTIRE book rebuild aborts — under the fail-soft ritual wrapper this prints the generic failure note every day and never writes a scoreboard. No test catches it (the only `evaluate_cli` tests use `cc`; `evaluate_records` tests with these lanes pass `coverage_validator=None`). Fix: gate on `needs_coverage_check` or return a sentinel key; regression test must drive `evaluate_cli` with a real `_CausalCoverageValidator` and a non-covered lane.
- **NEW-2 — IMPORTANT — `SNAPSHOT_RENDER_ID_MISMATCH` has no discriminating test.** Disabling the render_id check leaves 44/44 + 198/198 OK. The only isolating test was repurposed this round to assert `SNAPSHOT_HTML_SOURCE_MISMATCH`; nothing replaced it. Round 4 closed the R1 gap and opened an R2 gap (R2 was RED at `36a167e`).
- **NEW-3 — IMPORTANT — the ritual's fail-soft contract is no longer pinned by any test.** The `|| note` structural assertion was loosened (the `||` dropped) and the new execution test never checks `returncode`. A fail-HARD variant (`exit 9` on both failure branches) passes all 41 ritual-provenance tests. Behavior at this head is correct; the guard against future regression was removed — exactly what the addendum's clause (a) required be retained.
- **NEW-4 — IMPORTANT — backdated `evaluate --as-of <past>` reintroduces look-ahead.** `evaluate_cli` validates nothing about `as_of` (unlike `record_cli`'s `SESSION_UNVERIFIED`). Measured: a backdated run observes TODAY's portfolio, persists it as an observation dated in the past, and writes a new immutable dated artifact — which then binds every future evaluation. Not reachable from the LaunchAgent (always today's `AS_OF`); reachable by the exact manual-rerun shape the N3 recovery guidance suggests. Guard: refuse `as_of` earlier than the newest persisted dated artifact/observation.
- **NEW-5 — MINOR** — the same backdated input class inconsistently hard-aborts the whole rebuild when it predates a cc/pmcc fill (fail-closed vs NEW-4's silent acceptance).
- **NEW-6 — MINOR** — dashboard reports a supersede-suffixed directory name as `as_of` (`attractiveness_dashboard.py:5335-5341`); display-only.
- **NEW-7 — MINOR** — coverage cancellation inflates the `unreachable_marks` column (deliberate per test, but conflates "cancelled" with "data unreachable").
- **NEW-8 — MINOR** — a superseded date can never be re-evaluated (canonical-bytes-only comparison + one-active-supersede); partially disclosed by receipt boundary #4.
- **NEW-9 — INFORMATIONAL** — with an unwritable `LOGDIR` a real conflict is misreported as the generic failure note; remote path, still fail-soft.

## Order/authority/guardrail check

No live-order path, brokerage endpoint, paper-book mutation, or ledger write in the round-4 diff; all payloads and the supersede receipt carry `"authority": "NONE — descriptive tracking, dry-run"`. NO LOOK-AHEAD is no longer violated by the mechanism P1-b named; NEW-4 opens a narrower operator-triggered route of the same class.

## Receipt audit

Reproduced exactly: focused counts 44/198/41/4 (exit 0); full suite 3,421 with exactly the two inherited schedule failures (exit 1); ruff 0; pyright 0; the N2 flip; Probe A rejection; R1 RED; N3 conflict naming. Two line cites imprecise (`128-229` → spans to 246; N7 assertion at 1374 not 1303-1367). "Remaining boundaries and gaps": accurate on what it states, **materially incomplete** — NEW-1/2/3/4 undisclosed (NEW-1 most likely an unknown-unknown, not concealment) and NEW-8 only partial. Explicit non-claims (no review PASS, no A6, no landing authority) correct. Net: substantially honest with four material omissions.

## A6 evidence

Full suite on a local throwaway merge of the head with green main (`5652c04`, post-#116): **3,421 tests, OK, 5 skipped, exit 0** — plus ruff 0, pyright 0. The throwaway merge branch was deleted after guard verification; nothing pushed.

## Required for a round-5 PASS

1. **NEW-1 (blocking):** gate the coverage validator on `needs_coverage_check` (or sentinel key for missing coverage context); regression test driving `evaluate_cli` with a real `_CausalCoverageValidator` and a `long_call`/`leaps` record.
2. **NEW-2:** restore a test that isolates `SNAPSHOT_RENDER_ID_MISMATCH` (render-id revert probe must go RED).
3. **NEW-3:** re-pin the fail-soft contract — the execution test asserts `returncode == 0`, plus a structural assertion that the failure note sits on a non-propagating branch.
4. **NEW-4:** whenever live holdings are observed, `evaluate_cli` must require `as_of` to equal the CURRENT New York session (or consume genuinely point-in-time portfolio data). Merely refusing dates older than the newest artifact is insufficient — a fresh tracker has no newest record, and gap dates (newest = Aug 25, run on Aug 27 with `--as-of` Aug 26) would still stamp today's portfolio into the past. Fail closed, distinct error, tested; no override flag this round. *(Amended 2026-08-27 after PR #117 review comment 3875261967, which showed the original newest-artifact guard was bypassable.)*
5. **P1-a/A3:** the embedded source-row digest is computed from the render-side data path so producer divergence fails closed; RED-first test: producer renders dataset X while the snapshot carries dataset Y → validation rejects.
6. Non-blocking: NEW-5 through NEW-9 and the N4 `reason` one-liner.

P1-a/P1-b/N2/N3/N5/N6/N7 closures and the accepted N4 divergence must not regress.
