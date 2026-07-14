# ThetaData cancellation checklist (subscription ends 2026-07-29)

Owner update 2026-07-13: July 29 supersedes the earlier approximate July 25
date in `THETADATA_EXIT_PLAN`. The four-name historical cache remains frozen;
H7's historical diagnostic remains permanently retired. The only paid-data
work required before cancellation is the exact 12-name H7 forward-cache
top-up through the last completed session available before expiry. This is
data preservation only: it does **not** open Stage 8, register a window, or
authorize a real forward event.

## Before cancel day (read-only)

Run this as often as useful; it never touches the network:

```bash
uv run python data/recent_topup.py --scope h7 --dry-run
```

It must name the exact 12-name H7 scope and list every session still missing.
The original default remains the four-name core scope, so omitting
`--scope h7` is insufficient for cancellation readiness.

## On July 29 (run locally, in order)

1. Re-run the dry-run command above. The tool excludes July 29 itself because
   that EOD report is not final before the subscription ends; the expected
   terminal session is July 28.
2. With explicit owner execution authorization, run:

   ```bash
   uv run python data/recent_topup.py --scope h7 --refresh-closes
   ```

   This blind-caches every missing 12-name ThetaData EOD chain, skips and logs
   genuine gaps without substitution, audits each new chain, and refreshes
   the independent Yahoo close stores for the same exact scope. Any `BLOCK`
   verdict stops the checklist.
3. Run the complete forward-cache audit and write its content-addressed
   receipt:

   ```bash
   uv run python tools/thetadata_exit_audit.py \
     --scope h7 --as-of 2026-07-29 --write
   ```

   Require `PASS` or `PASS WITH WARNINGS`. Every warning remains in the
   receipt; known examples are deep-ITM IV solver artifacts and genuine
   low-liquidity lane admissions. Do not silently filter them.
4. Recompute the receipt against the current cache and source surface:

   ```bash
   uv run python tools/thetadata_exit_audit.py \
     --verify reports/thetadata_exit/2026-07-28.json
   ```

   Require `receipt VALID`.
5. Run the operational read-only gates for the same cutoff:

   ```bash
   uv run python -m options_researcher.h7_source_health --as-of 2026-07-29
   uv run python -m options_researcher.h7_data_gate --as-of 2026-07-29
   uv run python -m options_researcher.h7_event_ledger verify
   ```

   The data gate must be 12/12 GO and the real forward ledger must remain
   `VALID EMPTY`. Source health may still block activation; record its honest
   result rather than weakening it.
6. Prove the frozen cache can reconstruct the registered H6 input surface on
   the same terminal session, then write and independently recompute its
   immutable exact-session receipt:

   ```bash
   uv run python -m options_researcher.h6_features --as-of 2026-07-28
   uv run python -m options_researcher.h6_watch --as-of 2026-07-28 \
     --write-receipt reports/h6_forward/2026-07-28.json --json
   uv run python -m options_researcher.h6_watch --as-of 2026-07-28 \
     --verify-receipt reports/h6_forward/2026-07-28.json --json
   ```

   Require receipt action `WROTE`, then `VERIFIED`, with no blockers. The
   feature command must first create three adjacent
   `*_features.manifest.json` files. The watch independently verifies that
   every manifest still matches all contributing chains, the close store,
   exact feature bytes, feature parameters, runtime, source, and every
   timestamped content-matching `BLIND_CACHE` acquisition fact. Any missing or
   mismatched fact blocks the build/watch. The receipt then binds those
   manifests plus the trial-7 registration, full tracked book, raw/promoted
   earnings stores, three exact-session chains, frozen H6
   parameters/cost/bootstrap model, and evaluator source. Preserve its SHA-256
   in the cancel fact. If a prospectively operated H6 process records an entry
   or close, that CSV action must cite this hash; one receipt can authorize
   only one action, so rerun under a new sequenced filename before any second
   same-session action. The terminal cache-readiness receipt itself authorizes
   no action.

   This is a cache-readiness check, not permission to backfill a paper entry.
   If the watch prints `ELIGIBLE`, record it only if H6 was already being run
   prospectively under its tracked-book process. Never create a cancel-day
   row after seeing the candidate and call it forward evidence.
7. Append one `THETADATA_CANCEL` fact recording all 12 final chain dates, the
   exit-receipt hash, the Stage-2 artifact identity, and the source-health
   result, plus the exact H6 feature/watch session, outcome, and verified H6
   receipt hash.
8. Cancel the subscription in the ThetaData account portal.

## After cancellation

- H7 Stage 8 remains **NOT OPEN**. A verdict-bearing H7 forward window needs
  continuous daily EOD chains; it cannot start after the feed lapses unless
  the owner restores ThetaData or authorizes a separately audited replacement.
- H5 trigger watching still needs no live chain feed: `uv run python -m
  options_researcher.entry_watch` uses free underlying closes plus the frozen
  cache. A trigger `FIRE` requires fresh audited quotes before any entry
  evaluation.
- H6 can reconstruct features and watch output through the terminal cached
  session. It cannot accrue new prospective forward-paper evidence after the
  daily chain feed stops; frozen-cache replays are diagnostic only and must
  never be counted toward its eight completed positions.
- Scanner CLIs keep working against the frozen cache and must continue showing
  their as-of dates.
- Never regenerate `data/chain_cache_manifest.txt` to absorb forward files.
  It is an immutable historical baseline. The dated exit receipt is the
  forward-cache evidence.
