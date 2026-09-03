# Brief 36 — owner rulings before merge (2026-09-03 00:17 ET, in-session, owner wording verbatim)

Owner: "keep the full closure, F3/F5 as follow-up, merge #147"

| # | Ruling | Effect |
|---|--------|--------|
| 1 | **Keep the full closure.** `FEASIBILITY_SOURCE_PATHS` stays the recomputed transitive first-party import closure (50 files) despite the quantified breadth (49 of 163 first-party files; ~2 of every 3 working days over the last 60 would have invalidated a qualifying feasibility receipt). | Round-4 F6 CLOSED by owner ruling. Any edit inside the surface invalidates a qualifying receipt and forces re-measurement; that is now the accepted operating cost. |
| 2 | **F3 / F5 as follow-up.** F3 (HIGH: quote-age gate has no recompute-vs-sidecar numeric disagreement signal) and F5 (MEDIUM: no end-to-end test feeding `tools/h7_schwab_feasibility.summarize_counts` output through `_validate_feasibility`) are not merge blockers. | Tracked here as open follow-ups for a future brief; not silently dropped. |
| 3 | **Merge #147.** Head `54b2396` (Codex implementation through `19468f7`, restored receipts `53d409c`, round-3 blocker fixes `1a68de1`/`8fa4085`, round-4 fixes `fee356f`, receipts `1156325`/`f34c9cb`, main merged in `54b2396`); CI green; full offline suite 3685 OK at `fee356f`. | Squash-merged by the orchestrating session on owner instruction. |

Review chain on this branch: round 1 FAIL → fixes → round 2 FAIL → fixes → (Codex's claimed "Terra PASS", no receipt, void) →
round 3 FAIL (B1/B2) → fixes → round 4 PASS WITH FIXES → fixes applied → owner rulings above.

## What merging does NOT do
No registration, activation, receipt, or ledger event is created by this merge. Next, in order:
1. The 09:09 daily ritual produces fresh source-health + data-gate receipts at the post-merge `config_hash`.
2. Regenerate the cohort-9 feasibility receipt (`tools/h7_schwab_feasibility.py`) at the post-merge config — pre-merge receipts cannot qualify by design.
3. Owner runs `tools/h7_schwab_manual_activate.py`, typing the activation spec's SHA-256, bar 7, the OD-3 line, and the pre-acceptance. That is the single real door; nothing else appends.
