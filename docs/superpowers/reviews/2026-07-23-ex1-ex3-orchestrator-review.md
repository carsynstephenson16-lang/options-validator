# EX1–EX3 orchestrator adversarial review — 2026-07-23

**Reviewer role:** adversarial verification of Codex's "EX1–EX3 complete" claim.
**Branch:** `docs/replan-2026-07-22` (read-only; no commits).
**Commits under review:** `a0d2861` (honest scanner wording + RQ1 runner),
`7d1bde9` (one-run result + queue status).
**Acceptance source:** `docs/superpowers/plans/2026-07-23-codex-execution-queue.md`
(EX1, EX2, EX3 sections).
**Method:** offline only. Never ran `tools/score_backtest.py` or the RQ1 runner
itself; never wrote to `ledger/`.

---

## Verdict

**BLOCKERS-FOUND**

One explicit EX3 acceptance criterion is unmet: the required
causal-reconstruction property test does not exist and the actual
cache-reconstruction code path is entirely untested. Everything else verified
clean. The **recorded one-run result's integrity is fully intact** (hashes,
ledger chain, labels, no-verdict framing all verify) — the blocker is a
missing test of the causal path, not a corrupted artifact.

### Blockers

1. **EX3(a) — the causal-reconstruction property test does not exist.**
   The queue's EX3 acceptance requires a "causal-reconstruction property test
   (truncated cache reproduces day-D board exactly)." No such test exists.
   `CausalBoardTests` in `tests/test_rq1_runner.py:41-58` only feed injected
   dict rows to `filter_causal_board_rows` and assert the synthetic/future-row
   exclusion counters. The function that actually reconstructs boards from the
   parquet cache — `rq1_runner._default_rows` (`rq1_runner.py:325-431`) — is
   called by **no test** (`grep` for `_default_rows` / `.cache/chains` /
   `load_features` / `read_parquet` in `tests/test_rq1_runner.py` → none). The
   reconstruction's causal fidelity (its `features.index <= day_iso` truncation
   and its past-only earnings restriction) is the linchpin of the whole
   descriptive claim and is currently unverified. The review doc itself
   (`...-rq1-runner-adversarial-review.md:33`) honestly describes the tests as
   "future-row and synthetic-row exclusion" — so the review didn't overclaim,
   but the queue's "EX3 — DONE" status does.

### Non-blocking notes (record, not gate)

- **EX1 added no dedicated "board present-vs-absent byte-identical" test.** The
  queue's global rule wants each display build to ship one. The change is a
  pure verdict-string append that provably does not touch grade dicts or the
  `annualized_yield` numeric value (see EX1 evidence), and existing ordering /
  grade-badge tests stay green, so risk is low — but the dedicated pin was not
  added.
- **Silent error-day drops in `_default_rows` (`rq1_runner.py:427-430`).** The
  broad `except (FileNotFoundError, KeyError, TypeError, ValueError,
  IndexError): continue` drops a whole board-day with no log and no counter.
  The inline comment calls it "a disclosed gap," but nothing is logged or
  counted — such days never appear in the report's `excluded` block (which only
  counts summarize-stage exclusions). Fail-closed (no fabricated score), but
  "disclosed" is overstated.
- **Dead try/except (`rq1_runner.py:354-357`).** The `try/except Exception`
  wraps only a lambda *assignment* (`earnings_loader = lambda: ...`), which
  cannot raise; `load_earnings` executes later when the lambda is called.
  Harmless but misleading.
- **Hardcoded constants not sourced from `config.py`.** `HORIZON_SESSIONS=21`,
  `NOTABLE_ABS_RHO=0.30`, `np.sqrt(252.0)`, and `"2017-01-01"` live in
  `rq1_runner.py`. 21 and 0.30 are the registered seq-17 study params; per the
  queue's "every constant into config.py" rule they should cite config. Minor —
  this is a descriptive study runner, not grade/rank/trigger logic.

---

## Check-by-check results

| # | Check | Grade | Evidence |
|---|-------|-------|----------|
| EX1-1 | "(simple, not compounded)" on every `annualized_yield` render in `attractiveness.py` | PASS | All 6 renders carry it: `attractiveness.py:182-183, 238-239, 301, 493-494, 516-517, 542-543`; grep found no `%/yr` render without it |
| EX1-2 | Dashboard render also updated | PASS | `_headline` `attractiveness_dashboard.py:716-719`; only render there (line 276 is a tie-break sort, not a render) |
| EX1-3 | 252-vs-365 day-count disclosure in footer | PASS | `attractiveness_dashboard.py:2554-2560`: "annualization uses 365 calendar days; realized-volatility inputs use 252 trading sessions … simple, not compounded" |
| EX1-4 | Strings test-pinned | PASS | `test_attractiveness.py:58` ("simple, not compounded"); `test_attractiveness_dashboard.py:214-215` ("365 calendar days"/"252 trading sessions") |
| EX1-5 | Card ordering + grades byte-identical | PASS (with note) | Diff touches only verdict f-strings / `main()` prints; `ann` calc (`178/235/295`) and stored `annualized_yield` (`189/247/307`) unchanged; grep for added grade/threshold lines → none; `config.py` untouched. Existing ordering/grade tests pass. No *dedicated* present-vs-absent board test added (note above) |
| EX1-6 | Pinning tests actually run green | PASS | `test_attractiveness` 29 OK; `test_attractiveness_dashboard` 93 OK (offline) |
| EX3(a) | Causal-reconstruction property test truncates cache & reproduces day-D board | **FAIL** | No such test; `_default_rows` untested; `CausalBoardTests` only exercise the row-filter on injected dicts (`test_rq1_runner.py:41-58`) |
| EX3(b) | One-run gate refuses a second run | PASS | `run_once` refuses on `report_path.exists()` before loader (`rq1_runner.py:278`), test `test_existing_report_refuses_before_loader_is_called` PASS; also `O_EXCL` atomic create (`:203`) and ledger dedupe (`:244-249`). Report file now exists → default rerun blocked. Did NOT run the real runner |
| EX3(c) | Adversarial review exists and predates the run | PASS | Review in `a0d2861` (commit 09:43:21 EDT); run at ledger ts `2026-07-23T13:49:47Z` = 09:49:47 EDT; report `rq1-v1.json` in `7d1bde9` (09:54:37 EDT). Review → run → report order holds. Content is a genuine adversarial review (scope, probes, limitations, one-run authorization) |
| EX3(d) | `runner_sha256` matches runner @ `a0d2861` | PASS | `git show a0d2861:…/rq1_runner.py \| shasum -a 256` = `e880014b…615d4` = report's `runner_sha256` (and working tree identical) |
| EX3(d) | `observation_count` 4886 vs pooled n's | PASS | rv n=4802 → 4886−4802=**84=4×21** exactly (21 trailing forward-RV NaNs per each of 4 symbols); iv_change n=4854 (32 fewer). Both < obs_count, consistent with end-of-window forward gaps |
| EX3(d) | Symbols = AMZN/CEG/MSFT/VST only | PASS | `results.symbols` = ["AMZN","CEG","MSFT","VST"] |
| EX3(e) | Ledger seq 20 matches report, retrospective_result citing seq 17 | PASS | `entry_type` retrospective_result, `hypothesis_id` RQ1; rho/cross_sectional identical to report; verdict "NO VERDICT — descriptive…"; `prereg_ref_sha256` = seq-17 `record_hash` `37ce43ee…`; labels include outcome-selected/self-deceiving/no-verdict/cannot-promote; `source_commit` a0d2861; chain `seq20.prev_hash == seq19.record_hash` |
| EX3(e) | `report_sha256` in ledger matches file | PASS | `shasum -a 256 reports/rq1/rq1-v1.json` = `a46abcd…4230d` = ledger `report_sha256` |
| EX3(f) | Frozen GREEN recipe NOT modified | PASS | `config.py` untouched by both commits; `attractiveness.py` diff adds no grade/threshold/`GREEN` logic — verdict strings + prints only |
| EX2-1 | Focused H10 suite passes | PASS | `test_h10_config` 2 OK, `test_h10_observe` 4 OK, `test_h10_watch` 12 OK |
| EX2-2 | Capture-receipt suite passes | PASS | `test_ritual_receipt` 5 OK |
| EX2-3 | H7-exit suite passes | PASS | `test_h7_exit_session` 56 OK; `test_h7_daily_exit_order` 2 OK |
| EX2-4 | No activation / trigger surface added | PASS | Scan of all 658 added lines for order/trigger/broker tokens → 6 hits, all benign disclaimer prose ("does not grade, rank, trigger", "No activation or trigger surface was added"). No order-placement code. Live-trading guard hook fired on my grep containing a banned literal — hook working |
| §4 | Look-ahead in RQ1 reconstruction | PASS (with note) | Score uses only at-or-before features + same-day close/chain; `forward_rv`/`forward_iv_change` are outcomes computed with proper `+1..+h` shift (`forward_realized_vol` `:62-79`); earnings restricted to `<= day` (conservative). No leak into the score. Fidelity caveat feeds Blocker 1 |
| §4 | Magic numbers in config.py | MINOR | 21 / 0.30 / 252 / "2017-01-01" hardcoded in `rq1_runner.py` (note above) |
| §4 | Silent exception swallowing | MINOR | Dead try/except `:354-357`; silent, uncounted day-drops `:427-430` (notes above) |
| §4 | Network calls in tests | PASS | `test_rq1_runner` uses injected rows + tempfiles; `_default_rows` never invoked in tests; ran offline in 8.8s |
| — | Ruff clean on changed files | PASS | `ruff check` on all 6 changed/new files → "All checks passed!" |

---

## Bottom line for the owner (plain language)

The honesty-wording work (EX1) is done and correct — the "(simple, not
compounded)" note is on every place a per-year income number is shown, the
footer explains the 365-vs-252 day-count mismatch, and the wording change
provably did not move any card's grade or order. The recorded RQ1 study result
(EX3) is trustworthy as an artifact: every fingerprint checks out, the ledger
entry matches the report exactly and correctly points back to the seq-17
registration, and it is clearly stamped "no verdict, descriptive only, cannot
promote a badge." No order or trigger machinery was added anywhere.

The one real gap: the study's most important safety test was never written. The
code that rebuilds each day's scanner board from old data — the part that must
never peek at the future — has **no test at all**, and the specific
"truncated-cache reproduces the day's board exactly" test the plan required
does not exist. The result is already recorded and can't be re-run, so this is
about trust in the method, not a corrupted file. Recommend: before EX3 is
marked truly DONE, add the missing causal-reconstruction test (and, cheaply,
count/log the silently-dropped board-days so the usable-row disclosure is
honest).

---

## EX3a closure addendum — 2026-07-23

**Status:** PASS. This addendum closes the blocker above; it does not revise
the historical review's evidence or re-run the spent RQ1 study.

`CausalBoardTests.test_truncated_cache_reconstructs_day_board_without_future_inputs`
now calls `_default_rows` directly with offline fixtures. It compares the
day-D reconstructed row from a full chain/feature/earnings fixture to the row
from that fixture truncated at D. The fake card is deliberately sensitive to
the feature value, so a later feature leak changes the day-D board; the rows
match. The test also asserts that a later earnings date never reaches a
day-D card build.

`test_reconstruction_logs_counted_skipped_board_days` confirms a malformed
chain day is logged individually and in a final aggregate count. The registered
21-session horizon, 0.30 notable threshold, 252-session annualization, and
2017-01-01 cache start are now named in `config.py` with their seq-17 scope.

No `run_once` call, report change, or ledger append was made. The recorded
report remains provenance-bound to `a0d2861` and its historical runner hash;
the current source is intentionally newer only for this test/observability/
configuration follow-up.
