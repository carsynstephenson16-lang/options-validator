# Review receipt — durable Schwab intraday pulls (10:00 / 13:00 ET), 2026-09-02

**Change:** branch `claude/schwab-intraday-durable-pulls-2026-09-02`. Owner-directed in-session
(2026-09-02): "this repo only pulls schwab data once a day … I want a pull at 10am and a pull at 1pm."
Times are owner-typed into `config.SCHWAB_CHAIN_INTRADAY_TIMES`. Design = Brief 30's owner-authorized
isolated lane (2026-08-25), generalized to two slots; WP-C overlay not built.

**Reviewer:** independent Opus adversarial subagent, read-only, two rounds.

## Round 1 — findings on the first cut (shared wrapper, wall-clock slot selection)
| # | Sev | Finding | Disposition |
|---|-----|---------|-------------|
| 1 | HIGH (CONFIRMED) | Shared wrapper + clock selection: a missed 10:00/13:00 launchd fire delivered 15:35–15:55 (or an operator kickstart) resolves `preclose` and writes the H7 namespace; the real 15:45 run then CONFLICTs. | FIXED: separate `tools/schwab_chain_intraday_capture.sh` (Brief 30 WP-D.1), `--print-nearest-tag --tags morning,midday` restriction in module AND wrapper grep; pre-close wrapper reverted to `origin/main` + one EVIDENCE_ALLOW entry. |
| 2 | HIGH (CONFIRMED) | Inventory recorded `.cache/schwab_chains_intraday` present with a hand-made empty dir → `MISSING ENTIRELY` false alarm halts `repo-reconcile` on any checkout without the dir. | FIXED: recorded `present: false` per Brief 30 WP-D.3; staged-floor install procedure documented; plist install gated on a committed real floor. |
| 3 | MED (CONFIRMED) | `config_hash()` rotates with the new constant; pre-merge H7 Schwab gate/feasibility receipts must be regenerated. | DOCUMENTED (README, PROJECT_STATE, Brief 30 amendment). |
| 4 | MED (CONFIRMED) | Late fire inside the intraday lane (missed 10:00 at 12:55 → `midday`; real 13:00 then CONFLICTs). | DOCUMENTED; receipt `captured_at_et` is the honest record. |
| 5 | MED (CONFIRMED) | Slot resolution ran before the branch/alignment gates. | FIXED: resolution after the gates in the intraday wrapper. |
| 6 | LOW | Characterization test weaker than assumed. | Covered: `CliRoutingTests` asserts `main([])` → `capture(force=False)` exactly. |
| 7 | LOW | Shared launchd log paths. | FIXED: own `.tmp/schwab_chain_intraday/launchd.*.log`. |
| 8 | LOW | Unreconciled prior Brief 30. | FIXED: append-only status amendment in the brief. |

## Round 2 — re-verification
(a) pre-close namespace unreachable from the intraday job: CONFIRMED FIXED (reproduced 15:40 → NONE);
(b) `--tags` could list `preclose`: residual LOW → FIXED after the round (module now refuses, test pinned);
(c) guard staged floor: CONFIRMED (before capture OK; after capture "RECORDED ABSENT BUT POPULATED";
`--allow-absent` OK); (d) banner-guard allowlist entries honest; (e) one plist wording overclaim → FIXED.
**Verdict: SHIP WITH FIXES → both fixes applied.**

## Evidence
`uv run python -m unittest discover -s tests` → 3671 tests, OK, exit 0 (log outside the repo, because
`test_ritual_authority` snapshots `.tmp/`). `ruff` clean, `pyright` 0 errors. Live check at 10:03 ET:
`--print-nearest-tag` resolved `morning` through the banner filter. No provider call was made.

## Not done (owner-visible)
Brief 30 WP-C (midday board overlay); WP-E.3 AST-level consumer-blindness tests; installation
(owner-gated, staged per README "Schwab chain intraday"). The attractiveness board still reads the
15:45 pre-close chains.
