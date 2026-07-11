# H7 7b-2R correction arc (2026-07-11)

**Status: EXECUTING.** Base commit `679325c`. Ordered by the owner's
independent review of 7b-0..7b-2 (2026-07-11): eight launch blockers found,
three result-corrupting. 7b-3 REMAINS CLOSED: no backtest, no
diagnostic_attempt, no lane P&L, no adjudication, and the existing blocked
receipt is never overwritten.

## Standing decisions recorded up front (ledger H7_7B2R_DECISIONS)

- The v1 audit receipt (`reports/h7_audit/receipt.json`, receipt_hash
  `3bd098ef…`) is retained as a BLOCKED historical artifact and is
  INELIGIBLE to authorize any run, forever.
- NO assumed-notice earnings proxy is authorized. The 45-day
  post-report grace and the 14-day estimate cluster stay frozen.
- Trading-state UNKNOWN is distinct from missing historical provenance:
  - PROVEN_KNOWN: schedule or recent occurred report causally available.
  - PROVEN_UNKNOWN: archive complete, nothing was public, grace expired —
    trading gate stays UNKNOWN; the skipped session is logged; the audit
    does NOT block on it.
  - DATA_GAP: archive completeness/provenance absent or conflicted —
    trading gate UNKNOWN AND the formal audit blocks.
  This is an audit correction, never a relaxation of the trading gate.
- New launch gate: a v2 PASS receipt plus ONE mechanically gated command
  (`tools/h7_run_diagnostic.py`). The multi-command sequence and the public
  `allow_oos=True` escape hatch are removed.
- F1–F5 remain ratified. No frozen strategy threshold changes. F3's
  year-seam monthly-risk loss and F4's conflict handling are fixed as code
  defects, not re-registrations.

## Review findings being corrected (numbering = owner message)

2. **Manifest unification.** One canonical eligible-session manifest
   consumed by both audit and runner; the runner must not scan the cache
   independently (today 163 SMCI parquets inside the excluded interval are
   loadable). Present-but-excluded and unexpected files are reported and
   quarantined, never consumed. VST 2018-04-23..26 missing-put days become
   a lane-aware note (VST is H7c-ineligible). SMCI exception corrected to
   official-source listing history (suspension 2018-08-23, delisting
   2019-03, relisting 2020-01); listing status separated from verified
   listed-options availability; PLTR/CEG option-inception exclusions
   re-based on official sources or reclassified as data-coverage
   limitations requiring amendment.
3. **Receipt v2.** No mtime fallback. Provenance tiers: ledger-fact tier
   (BLIND_CACHE timestamp+SHA) vs legacy tier (exact SHA in the
   pre-existing tracked chain manifest + session predates manifest
   construction + adapter shown to use option_history_greeks_eod +
   owner-ratified legacy assumption recorded); otherwise BLOCK. v2 binds:
   eligible manifest + exclusions, every chain SHA, present-but-excluded
   and unexpected identities, closes SHAs (raw+adjusted inputs), earnings
   assertion + coverage-manifest SHAs, fetch-provenance-map hash, session
   calendar identity + generated-session hash, exception-registry hash,
   audit + diagnostic source hash/version, config/frozen-config/cost-model
   hashes, complete machine-readable findings, verdict == PASS. One
   mutation test per input class.
4. **Earnings causality.** Session-close-UTC cutoff helper (XNYS close
   incl. early closes) shared by watcher/strategy/audit; regressions for
   the MSFT/AMZN 2026-04-29 after-close filings; `--as-of` uses the
   historical cutoff (never `datetime.now()`); conflicting unresolved dates
   for one symbol/fiscal period → UNKNOWN (not BANNED); supersession keyed
   (symbol, event_id); append-only v2 assertion store (record types
   assertion|retraction, source types, explicit supersession target,
   `label:*` sources rejected); v1 file preserved as evidence, no longer
   consumed after cutover.
5. **Execution fidelity.** One canonical adverse-price transform (buy:
   ask+haircut ceil-to-cent; sell: bid−haircut floor-to-cent) used by feed,
   decision layer, T+1 revalidation, exit marks, P&L; revalidation on exact
   engine prices with boundary tests; non-finite/one-sided/crossed quotes
   rejected everywhere incl. exit lookup/marks (invalid exit quotes retain
   the pending exit); vertical bounds (0 < credit < width; 0 < debit ≤
   width; out-of-bounds exit combinations rejected as invalid marks);
   monthly risk carried across year chunks (regression: Dec signal → Jan
   entry+close → later Jan signal cannot reuse the risk); verdict-affecting
   escaped numbers into frozen config (contracts/position, call-feed
   inclusion band, chunk/warm-up buffers).
6. **Explicit gaps.** Missing closes/chains/raw spot/empty feed/missing
   legs emit structured gap records (symbol, lane, session, stage, reason);
   the adjudicator refuses results containing unexplained eligible-session
   gaps.
7. **Gated launch.** `tools/h7_run_diagnostic.py`: verifies ledger chain,
   committed attempt, no prior result, attempt↔invocation scope match,
   supported source-hash version, current registration/config/cost/source
   hashes, bound v2 PASS receipt whose hash matches the attempt, runner
   inputs == receipt manifest; runs deterministically; appends raw result +
   automatic adjudication to the write-once ledger record BEFORE printing;
   verifies the ledger again; trial count stays 10. `allow_oos` removed
   from `run_lane`'s public signature (internal injected capability for
   synthetic tests only). Results are never inspected via the standalone
   adjudicator before being ledgered.
8. **Historical earnings coverage** (only after code is green): one bounded
   collection pass over the 8 backtest names using SEC acceptance
   timestamps + earliest timestamped company IR/PR announcements +
   timestamped reschedules. Never infer announcement dates from eventual
   report dates or modern aggregator calendars. Coverage report before any
   scope change; if history is incomplete, pre-register source-complete
   symbol periods from data availability alone (never after seeing P&L);
   forward-only is the honest fallback.
9. **Verification/stopping rule.** Red-green, small commits. Full suite,
   ruff, pyright, pre-commit, ledger verify, trial-count check, synthetic
   engine paths, audit v2, receipt v2 verify. NO H7 backtest. If audit v2
   blocks: stop with every blocking identity. If it passes: commit the
   receipt, then hard-stop BEFORE creating any diagnostic attempt — the
   next independent review authorizes attempt creation and 7b-3.
