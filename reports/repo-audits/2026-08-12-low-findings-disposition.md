# LOW findings disposition — 2026-08-12

Bounded resolution of the LOW findings (L1–L10) from
`reports/repo-audits/2026-08-11-three-day-state-audit.md` §4/§7, per the
owner's approved scope: smallest safe change (docs-only) or a written
disposition for each. This report was produced in worktree `docs-batch`
(branch `wt/docs-batch`). Code-owned findings, PROJECT_STATE.md, README.md,
`reports/h7_forward_schwab/*`, and `ledger/` were out of scope for this pass
and are untouched here.

## Disposition table

| Finding | Disposition | Where |
|---|---|---|
| L1 | **Documented carve-out.** `_JUMP_MIN_PERIODS`/`_FAT_TAIL_EXCESS_KURTOSIS` stay module-level in `exp_tail_shape.py` rather than moving to `config.py`; moving frozen, already-provenance-labeled, test-covered experiment constants was judged riskier than documenting the exception. | Comment added `options_researcher/exp_tail_shape.py:38-44` (comment-only, verified by `git diff`); one sentence added to `docs/superpowers/specs/2026-08-09-attractiveness-experiment-program-design.md` item 3 (constants/provenance section). |
| L2 | **CLOSED.** Brief 06 (`docs/superpowers/plans/2026-08-10-06-experiments-dashboard-split-codex-brief.md`) is present at this worktree's HEAD (`ff2e709`) — landed via the H1 merge. Verified with `ls -la`; no edit needed. | n/a |
| L3 | **Fixed.** Inline dated correction on the false "NOT yet implemented" line. | `ideas-parking-lot.md:1213-1216` |
| L4 | **Fixed.** Reworded the "Start here" index bullet to mark the report historical, pointing to PROJECT_STATE.md for the current P0 closures. | `CLAUDE.md` "Start here" section, one bullet |
| L5 | **Delegated (code fix), not actioned here.** Eager `getattr` default evaluation at `live_quotes.py:348` makes 54 tests depend on `.env`'s `LIVE_MARKET_DATA_PROVIDER=schwab`. This is a code change (test hermeticity), out of scope for a docs-only worker — delegated to a follow-up code worker this session. CLAUDE.md's "OFFLINE" test framing is NOT edited here; if the code fix does not land, that framing needs an env-var caveat as a separate follow-up (not done in this pass, to avoid describing a fix that may not exist yet). | Not edited |
| L6 | **Delegated (code fix), not actioned here.** Test-isolation leak writes a stray `reports/live_probe/2026-07-15.json` into the real repo tree when the suite runs without the env var; candidate origin among five test modules sharing that fixture date. Same delegation as L5 — a code/test-isolation fix, out of scope for this docs-only pass. | Not edited |
| L7 | **DEFERRED-BY-DESIGN.** `h7_schwab_data_gate.evaluate()` fails package-tamper cases via an uncaught `SchwabChainManifestError` rather than the module's NO_GO-code contract. Audit calls this intentional and crash-visible, not silently wrong, and flags it for normalization "before CLI wiring." No CLI wiring exists yet (H7 Schwab lane is still PREPARED/NOT ACTIVATED per the audit's fresh-evidence matrix), so this is tracked as an H7 activation prerequisite rather than fixed now — normalizing an error contract ahead of its consumer risks guessing the consumer's needs. No change made. | Not edited |
| L8 | **Fixed (doc note).** `--allow-absent` only skips a namespace whose directory is wholly absent; a directory that exists but is empty (e.g. auto-mkdir'd by an importing module, no bytes ever written) still alarms as LOST FILES if the inventory recorded files there. Confirmed by reading `scan()`/`verify()`: `scan()` returns `present: True` for any existing directory regardless of contents, so the empty-but-present case falls through the `allow_absent` skip and into the file-count comparison. This is working as documented — the tool cannot distinguish "never populated" from "silently emptied" once the directory exists, and catching silent emptying is the tool's whole purpose. Documented in place; no functional change. | Comment added `tools/irreplaceable_data_guard.py:151-162` (comment-only, verified by `git diff`), immediately above the `allow_absent` handling in `verify()`. |
| L9 | **HISTORICAL.** H7 Schwab lane code commits carry no implementer attribution (no `Co-Authored-By:` / "Implemented by" trailers), unlike `50af90f` and the Codex experiment commits. The audit is explicit this is "a division-of-labor auditability gap, not a demonstrated violation" — the brief names Codex as implementer but git cannot corroborate it. Retrofitting attribution onto already-landed commits would mean inventing a trailer after the fact, which this worker is expressly forbidden from doing (no invented attribution). Left as historical fact. Discipline note going forward: commits implementing from a Codex brief should carry an implementer trailer at commit time, matching the convention `50af90f` and the four `codex/attractive-exp-*` commits already follow. | Not edited (no retroactive attribution added) |
| L10 | **OWNER-OPTIONAL / UNVERIFIABLE-HERE (two parts).** (a) `claude/schwab-api-setup-cleanup-79f827` holds an unadopted 2026-08-04 CLAUDE.md "branch hygiene" rule absent from main — an adopt-or-reject decision for the owner; not actioned by this worker (CLAUDE.md is edited above only for L4's single unrelated bullet, per the assignment's explicit scope). (b) `wiki/log.md`'s 2026-08-05 and 2026-08-09 RAG-health entries reporting byte-identical stats (594 sources / 14879 chunks) are plausible but this worker has no independent way to re-run or corroborate that RAG index from a docs-only worktree pass — left unverifiable, not disputed. | Not edited |

## Verification

- `git diff --check` clean (no whitespace-conflict markers) across all edited files.
- `options_researcher/exp_tail_shape.py` and `tools/irreplaceable_data_guard.py`
  diffs are comment-only — no statements, no logic, no test-visible behavior
  changed (see commit diff hunks).
- `ideas-parking-lot.md`, `CLAUDE.md`, and the experiment-program-design spec
  edits are additive/reworded prose only; no frozen research meaning changed,
  no attribution invented.
- Out of scope, untouched: `PROJECT_STATE.md`, `README.md`,
  `reports/h7_forward_schwab/*`, `ledger/`, all test files, all other code files.

## Cross-references

- `reports/repo-audits/2026-08-11-three-day-state-audit.md` §4 (LOW findings
  L1–L10), §7 (remaining-work queue, item 8 and the "Later" list).
