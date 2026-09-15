# PROJECT_STATE — canonical status and next task

**As of:** 2026-09-15 (audit session — full findings, owner packets, and evidence:
`reports/2026-09-15-audit-edge-verdict-and-loose-ends.md` and `reports/2026-09-15-audit/`).

**Authority:** this file is the repository's single current status and execution
plan. Older plans and reports are evidence or history, never an active queue.
The dated status-refresh log that used to be prepended here (2026-08-02 →
2026-09-09) and the 2026-08-02 audit body (§1–§15, queue Q0–Q15) were moved
**verbatim** on 2026-09-15 to `docs/status-history/` — every section number
other documents cite (§3.1, §4–§5, §6, §9, §13, Q4 …) resolves there:

- `docs/status-history/2026-08-02--2026-09-09-status-refresh-log.md`
- `docs/status-history/2026-08-02-audit-body.md`

Keep this head under ~150 lines. Append new dated status refreshes to the log
file above, not here; update the sections below in place.

## 1. Where the book stands (plain language)

- **Verdicts landed: none.** Across 32 ledger records (seq 0–31) and ~2.5
  months the repo holds zero loss-gated verdicts, **one** paper options
  position ever opened (H6-0001, NVDA $220 call, expires 2026-09-18), zero
  completed paper trades, zero losses booked. The lowest registered loss bar
  is 7. This is a sample problem, not a strategy result: no registered design
  has yet had the chance to be wrong.
- **Registry:** `README.md` "Scope status" (source of truth behind it:
  `ledger/experiments.jsonl`). H1/H2 rejected in-sample; H5 observe-only
  (trigger retired 08-17); H6 one open position, evaluator dark since the
  ThetaData cache froze 2026-07-27; H7 paused, Schwab restart lane prepared
  but NOT activated; H8 zero positions and no scorer in the codebase; H10a
  closed STARVED; H10b running with zero fires; RQ1 spent; RQ2-v1 window open
  with no badge module built; A2-v1 built, never run, fail-closed on data.
- **Data:** ThetaData cache immutable, edge 2026-07-27 (OD-4). Schwab
  pre-close capture lane (15:45 ET) is the live exact-session source for the
  H5-observe and H10b lanes; the 10:00/13:00 intraday lane is tracked but not
  installed (owner-gated).
- **Literature check (2026-09-15, `reports/2026-09-15-audit/B-literature-memo.md`):**
  the repo's own findings match the published record — single-name variance
  premium is weak-to-absent, and directional long calls on volatile,
  lottery-like names (the shape of H6/H7/H8/H10) have documented negative
  after-cost returns. The one structure with documented after-cost support
  on these names (defined-risk short volatility across earnings on MSFT/AMZN)
  has never been registered. Candidate designs are in the audit report §5;
  every number there is LLM-asserted and the owner types anything frozen.

## 2. Live blockers (as of 2026-09-15)

| Blocker | Who | Detail |
|---|---|---|
| Schwab refresh token expires **2026-09-15 14:36 UTC (10:36 ET)** | Owner | `uv run python tools/setup_schwab.py` (Keychain prompt). After expiry the 15:45 capture fails until re-auth; each missed session is a permanent gap. |
| H6-0001 expires **2026-09-18** with no executable close path | Owner | The H6 evaluator binds to the frozen ThetaData cache, so the registered 21-DTE close (due ~08-28) could never fire. Last verifiable mark (Schwab pre-close 09-10): bid 3.75 / ask 3.80 vs $9.21 entry; NVDA closed $210.96 on 09-14 (strike $220 is out of the money). Disposition packet: audit report §7. |
| Earnings source health **2/15 healthy** | Owner (runs the refresher) | All 15 last-report dates are now SEC-8-K-confirmed (audit report §6 has the 15 ready `append-raw` commands); no name has announced its next date yet. H7 Schwab activation needs all nine cohort names healthy → realistic window October 2026. |
| Ops pipeline stalled 09-11 → 09-15 | **Cleared 2026-09-15 01:4x ET** | Root cause: the ritual's own evidence commit contained paths no capture-side allow-list knew, so a single failed push (network blip 09-11) made every later capture and ritual refuse. Fast-forward pushed; root fix on this branch (allow-list superset + self-healing gate). Confirm the next 09:09 ritual prints `OK`/`OK_STARVED`, not the alignment refusal. |
| `research-refresh` LaunchAgent installed but not loaded | Owner | Brief 41 (installed-vs-loaded check) is implemented by Codex on `codex/brief-41-launchagent-loaded-check`; hand-back review 2026-09-15: `reports/2026-09-15-audit/E-brief41-handback-review.md`. |

## 3. Next actions, in order

1. **Owner, this morning:** re-auth the Schwab token (blocker 1).
2. **Owner, before Friday:** rule on H6-0001 (blocker 2) and on whether H6/H8
   get a Schwab-lane amendment (like H10b/H5) or are retired pending
   re-registration.
3. **Owner:** run the 15 earnings `append-raw` commands, then `promote` per
   name, then `uv run python -m options_researcher.h7_source_health`.
4. **Owner:** merge the 2026-09-15 audit PR, then sync ops
   (`git -C ~/options-validator-ops merge --ff-only origin/main`) so the
   self-healing gate is what runs at 09:09.
5. Land brief 41 per the hand-back review; then the rest of the audit
   report's owner-decision list (§4): H9 receipt full-hash fact, hook
   registration switch to `.agents/hooks/`, seven stale local branches.
6. **Research direction (owner call):** decide whether to register Candidate
   A (earnings-window defined-risk short volatility, MSFT/AMZN) — the only
   family with literature support that is feasible under the 2026-07-24 gate
   inside 12 months. Owner types every frozen number.

## 4. Standing gates (unchanged by this refresh)

- Research-integrity guardrails per `.cursorrules` (pre-registration before
  results, append-only ledger, no look-ahead, conservative costs,
  validator-only, no live orders). The pre-verdict ship-blocker stays retired
  (2026-08-03).
- The owner types every frozen number, new registration, and verdict
  ratification; amendments follow the 2026-07-25 delegation.
- Ops jobs run only exactly-aligned reviewed code from `origin/main`; the
  2026-09-15 gate change adds tolerance ONLY for the ritual's own
  evidence-only commits (same push authority Step 8 already had).

## 5. What changed on 2026-09-15 (this branch)

- Ops: `reports/pick_tracker` and `reports/closes_receipts` added to every
  `EVIDENCE_ALLOW` copy; `FULL_TIER_PATHS` gains the two Schwab activation
  namespaces; the ritual's alignment gate fetches first, refuses BEHIND, and
  self-heals an AHEAD-by-evidence-only divergence with one bare push (tests:
  `tests/test_daily_ritual_alignment_gate.py`, +2 in
  `tests/test_ops_alignment_check.py`).
- Docs: CLAUDE.md pointer-style rewrite; `.cursorrules` ↔ `AGENTS.md`
  reconciled (draft-PR hold and catalyst-calendar rule now in both; hard
  guardrails now in AGENTS.md); README paper-book row no longer restates
  positions; this file restructured; dead Node files removed.
- Hooks: `block_live_trading.py` and `session_note_guard.py` now tracked in
  `.agents/hooks/` with tests (previously laptop-only and untested). The local
  registration still points at the laptop copies until the owner switches the
  two `command` paths in `.claude/settings.local.json` after merge.
- Nothing in `ledger/`, `config.py`, cache bytes, or `data/` changed.
