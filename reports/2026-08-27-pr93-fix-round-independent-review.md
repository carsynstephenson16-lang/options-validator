# PR #93 fix-round independent adversarial review — 2026-08-27

- **Reviewed head (exact):** `36a167e6bf2942ea54a993790acc692f0b288a3f` (branch `codex/brief27-implementation`, draft PR #93)
- **Reviewer:** independent Opus subagent commissioned by the orchestrating Claude session, adversarial framing ("assume the receipt could be lying"), read/run-only in a detached review worktree (`.tmp/worktrees/pr93-review-0827`)
- **Inputs:** fix-round receipt `reports/2026-08-27-pr93-fix-round-receipt.md` (committed at the reviewed head); prior FAIL findings at `58779390528719ed6c8447c9b8f1aad0ede741ce` (SDD ledger `.superpowers/sdd/2026-08-26-audit-closeout-handoff-package/progress.md`, A6 entry)
- **Method:** diff audit, per-finding revert probes (delete the claimed fix, observe whether a test goes RED), behavioral probes, receipt line-cite/count reproduction
- **Out of scope by prior ruling:** the two schedule-test failures inherited from main (fixed separately in PR #116); confirmed the ONLY full-suite failures at this head and untouched by this PR

## OVERALL: FAIL for head `36a167e`

Three of five findings survive scrutiny (P1-c, P2-a, P2-b). **P1-b is not closed** — the named mechanism is intact and was reproduced. **P1-a is partial** — the final source-row hash comparison is not load-bearing in any test (the earlier field-set/identity guards were not separately probed and may have incidental coverage), and the divergence class it names is still accepted. Two Important new defects were introduced by the P1-c fix. The receipt is substantially honest on counts and lint/type gates but overclaims RED-first evidence for P1-a and has imprecise line cites.

## Scope audit — clean

Fix-round-only diff (`cc580ba..36a167e`), exactly as claimed:

```
options_researcher/attractiveness_dashboard.py |   8 +-
options_researcher/pick_tracker.py             | 321 ++++++++++---
reports/2026-08-27-pr93-fix-round-receipt.md   |  54 +++
tests/test_attractiveness_dashboard.py         |  16 +-
tests/test_pick_tracker.py                     | 294 ++++++++++-
```

- Governed paths touched: NONE (`ledger/`, `config.py`, `docs/superpowers/`, `AGENTS.md`, `CLAUDE.md`, `.cursorrules`, `.github/` all clean).
- No pre-existing test deleted, renamed, or loosened (`git diff cc580ba 36a167e -- tests/ | grep -E "^-.*def test_|^-.*assert"` → empty). Test count 30 → 36.
- Fixture helpers were made stricter (real SHA-256s replacing `"a"*64`/`"c"*64`), not weaker.
- Whole-PR-vs-main context: adds `docs/superpowers/plans/2026-08-25-pick-tracker-registration-packet-DRAFT.md` (correctly labeled "Status: DRAFT — NOT REGISTERED"), modifies `tools/daily_ritual.sh` and `tests/test_daily_ritual_provenance.py`.

## Per-finding verdicts

### P1-a — snapshot source-row/render divergence → PARTIAL

- (a) Changes exist as cited. Repo-verified: `pick_tracker.py:132-169` adds exact-field-set check, candidate/leg identity match, and source-row hash recomputation; `:173-187` recomputes `render_id`; producer `attractiveness_dashboard.py:4840-4847` now embeds all 7 hashed source-row fields.
- (b) **The final source-row hash comparison is not load-bearing in any test.** REVERT-PROBE R1: deleting the `SNAPSHOT_SOURCE_ROW_MISMATCH` guard (`:168-169`) leaves the snapshot suite GREEN (12 tests, exit 0). `grep -rn "SNAPSHOT_SOURCE_ROW_MISMATCH" tests/` → zero hits. Scope of this evidence: R1 establishes the hash-recomputation comparison specifically is untested; the earlier field-set and identity guards (`:132-167`) were not separately revert-probed and may have incidental coverage. R2 (remove only the render_id check) → RED, so the render_id half is covered. *(Amended 2026-08-27 after PR #117 review comment 3875097927 — the original "does NOT exercise the source-row work" claim was broader than the R1 evidence supports.)*
- (c) **The fix is bypassable for the class the finding names.** Probe A: mutate `raw_quote["bid"] 1.0 → 1.1`, re-derive `source_row_hash`, `source_row_hashes`, and `render_id`, leave the HTML bytes untouched → **ACCEPTED** — snapshot claims bid=1.1 while the rendered HTML says 1.00. `render_id` binds the snapshot to the HTML bytes, not to the values rendered. The fix genuinely adds detection of partial post-hoc snapshot edits; that is narrower than "source-row/render divergence is rejected."
- Positive control: `tests/test_attractiveness_dashboard.py:2378-2433` is a genuine producer→validator round trip and survives; only a `put`-lane card is driven through the strict identity match.

### P1-b — mutable portfolio retroactively rewrites CC/PMCC history → NOT-CLOSED

- The named mechanism is untouched: `pick_tracker.py:599-609` `_current_coverage_validator` ignores its session argument and reads `load_holdings()`/`load_positions()` (today's state); `evaluate_cli` (`:1474-1491`) rebuilds the entire journal every run with exactly this validator. Every historical CC/PMCC decision is re-adjudicated against today's portfolio.
- **Reproduced (Probe B, exit 0):** day-1 evaluation records `frozen_baseline OPEN` for decision_session 2026-08-25; mutate holdings 100 → 0 shares; day-2 evaluation (new dated directory) records `CANCELLED_COVERAGE_CHANGED` for the SAME historical decision, **written with no conflict**. Same-day rerun after mutation correctly raises `IMMUTABLE_HISTORY_CONFLICT` — the immutability fix protects one dated directory from overwrite, not history from rewrite. The cumulative scoreboard the dashboard reads is always the newest dated artifact.
- The cited test (`tests/test_pick_tracker.py:688-776`) asserts only byte-stability of the already-written directory; it never asserts the outcomes are unchanged in later artifacts. R5 confirms the test discriminates for the narrow property it tests.
- Applying today's portfolio to a historical decision timestamp is also a live **NO LOOK-AHEAD** hard-guardrail violation (`.cursorrules`), not merely a bookkeeping issue.

### P1-c — daily marking absent; drawdown ignores zero-return entry → CONFIRMED-CLOSED (introduces N1/N2)

- Zero-return entry mark `:933-942`; daily series `:928-984`; drawdown over the daily series unconditionally `:1055-1060`.
- Causality holds for the price path: each mark reads only `chain_loader(symbol, mark_session)`; `daily_end` clamped by `as_of`. Off-by-one clean at both ends (entry excluded from the series, expiry appended as the terminal mark).
- R4 (delete the ENTRY mark) → RED. The zero entry point is load-bearing.

### P2-a — FAILED/DISABLED arms synthesize exits/re-entries → CONFIRMED-CLOSED (narrow; see N4)

`pick_tracker.py:376-388` carries prior slots forward with empty entries/restrikes/exits. R3 → RED (2 failures). Three-session lifecycle covered for both states.

### P2-b — WP-D reports omit cohort/cancellation/scoreboard content → CONFIRMED-CLOSED

Checked against the brief itself (`docs/superpowers/plans/2026-08-25-27-pick-tracker-scoreboard-codex-brief.md:400-425`, WP-D.1), not just the receipt. Every WP-D.1 element present in a live-rendered `scoreboard.md`; raw dollars never pooled across lanes. R6 → RED.

## New findings

- **N1 — Important — the P1-c fix amplifies the P1-b look-ahead.** `pick_tracker.py:945-948`: the coverage validator was previously called at ~3 scheduled offsets; it now runs on every trading session, so a portfolio change retroactively cancels a historical CC/PMCC position at `elapsed_sessions=1` instead of at the first scheduled mark. Blast radius strictly larger.
- **N2 — Important — chain-load volume explosion inside the daily ritual.** `schwab_chain_view.py:213-231` `load_chain` is an uncached `pd.read_parquet` per call. Measured: one position, lane=leaps → 188 chain_loader calls (pre-fix bound ≈ 8); lane=long_call → 42. `evaluate_records` now scales O(records × candidates × sessions-since-fill) and runs inside `tools/daily_ritual.sh:475`. No caching, no memoization, no bound.
- **N3 — Important — first write of a date is permanent, and a later conflict is indistinguishable from any other isolated failure.** The `|| note` fail-soft wrapper at `daily_ritual.sh:475` is CONTRACTUAL (brief WP-E.1: a tracker failure must be incapable of changing the ritual's exit status or lane state) and `note()` does echo the failure into `SUMMARY` and the ritual log — the wrapper itself is not the defect and must be retained. The defect: this PR adds `reports/pick_tracker` to the ritual auto-commit allow-list (`:550`), so the first successful evaluate for date D is committed and pushed; any later, more complete rerun for D raises `IMMUTABLE_HISTORY_CONFLICT`, which surfaces only as the generic "pick tracker evaluator: FAILED (isolated)" note — indistinguishable from a transient error — and the stale artifact stands. No supersede path, no documented recovery, no test for operator recovery. The concrete legitimate same-date scenario: the morning ritual (09:09 ET) evaluates before the 15:45 ET chain capture, so a post-capture rerun for the SAME as_of can be genuinely more complete — first-write-wins permanently keeps the less-complete artifact. The required fix must work WITHIN the fail-soft contract (distinct conflict messaging + an explicit append-only supersede/recovery mechanism), not by letting the evaluator alter ritual status, and must PRESERVE the fail-closed default: automatic paths (the ritual) never supersede; only a manual, reason-bearing, prior-bytes-preserving operator action does. This complements, not weakens, the recorder journal's same-session different-hash fail-closed contract (brief `:344-348`). *(Amended 2026-08-27 after PR #117 review comments 3874438063 and 3875097901 — the original wording called the failure "silent" and did not name the authorizing workflow.)*
- **N4 — Minor — unrecognized arm states route through the entry-synthesis path.** `:377` guards `{"FAILED", "DISABLED"}` while `evaluate_records:875` treats anything `!= "READY"` as unavailable. A missing/empty state safely defaults to `"FAILED"` (`:376`), but an unrecognized non-empty state falls through to `_arm_record(...)` — the normal READY path — and synthesizes entries into the append-only journal, the exact behavior P2-a forbids for non-ready arms. Latent today (producer emits only READY/FAILED/DISABLED, and the brief's contract at `2026-08-25-27-pick-tracker-scoreboard-codex-brief.md:289-291` names only those), but the correct remedy is FAIL-CLOSED: raise a `TrackerError` on an unrecognized state, keeping FAILED/DISABLED carry-forward and READY normal. Blanket `!= "READY"` → unavailable would be wrong in the other direction — it would convert malformed/corrupted state into an ordinary unavailable arm. *(Amended 2026-08-27 after PR #117 review comment 3874438077 — remedy changed from denylist-broadening to fail-closed.)*
- **N5 — Minor — `_immutable_write` leaks an unhandled `FileExistsError`** from `tmp.open("xb")` on a leftover same-PID tmp file (`:1275-1287`); only the `os.link` `FileExistsError` is caught.
- **N6 — Minor — `_write_evaluation_reports` bypasses the dry-run write boundary** (`:1396-1421`, no `_enforce_write_path`); safe today only because the caller hardcodes `DRYRUN_ROOT`.
- **N7 — Minor — a scheduled checkpoint miss appends nothing and does not increment `unreachable_marks`** (`:998-1003`); no live construction found, but the previously-guaranteed mark is now conditional with no loud path.
- **Order/authority-path check — clean; NO-LOOK-AHEAD guardrail — VIOLATED.** Narrow scope of the clean part: no live-order path, no brokerage endpoint, no paper-book mutation, no ledger write; both new payloads carry `"authority": "NONE — descriptive tracking, dry-run"`; nothing verdict-bearing or FIRE-capable. This does NOT mean the hard guardrails pass: P1-b is a live NO LOOK-AHEAD violation (today's portfolio state adjudicates historical decision timestamps), and per `.cursorrules` a leak of this class invalidates its downstream results — here, the CC/PMCC lane outcomes plus any aggregate, contrast, or scoreboard summary that consumes them. Independently computed lanes (long_call, LEAPS, put) are not invalidated by this mechanism, though any cross-lane artifact containing corrupted CC/PMCC inputs is. *(Amended 2026-08-27 after PR #117 review comment 3874438091 — the original "Guardrail check — clean" heading contradicted the P1-b finding.)*

## Receipt audit

- Focused-suite counts (36 / 198, exit 0) and full-suite result (3,412 tests, 2 inherited failures, exit 1), ruff 0, pyright 0: **reproduced exactly** (via `unittest discover`; the dotted and path invocation forms in the receipt are broken in fresh venvs because `schwab-py` and `lumiwealth_tradier` install a top-level `tests` package that shadows the repo's — use `discover`).
- "Each testable finding was observed RED before its implementation": **overclaimed for P1-a** — R1 shows the source-row guard can be deleted with the suite green; whatever went RED exercised only the render_id half.
- Line cites: mostly accurate; four cites off by small margins (`1396-1438` → actual 1396-1421; `815-906` → 823-906; `1158` → 1156; `128-185` → 128-187).
- The receipt does not disclose (a) the untested P1-a source-row guard, (b) that the P1-b rewrite mechanism remains live in every newly-dated artifact, (c) the N1/N2 side effects. Framing all five findings as flat "Fixed" is the receipt's main overstatement. Otherwise honest, including its explicit non-claim of A6 readiness.

## Controller disposition

- P1-a adjudicated against the original A6 wording: Probe A reproduces the named divergence class verbatim → not closed as worded.
- Verdict for the A6 gate: **HOLD** — PR #93 is not ready. A bounded round-4 fix is required for: P1-a (full closure + missing test), P1-b (causal/frozen history redesign; also resolves N1), N2 (bounded chain loads), and N3 (distinct conflict surfacing + append-only supersede/recovery, implemented WITHIN the WP-E.1 fail-soft contract, fail-closed default preserved). The four minors (N4 as fail-closed on unrecognized states, N5, N6, N7) are recommended hardening, NOT readiness gates: N6 and N7 in particular have no live triggering path today and must not by themselves hold the A6 decision. *(Amended 2026-08-27 after PR #117 review comments 3875097909 and 3875097920.)*
- P1-c, P2-a, P2-b are closed and must not regress in round 4.
