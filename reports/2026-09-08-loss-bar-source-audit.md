# Where each live window reads its verdict rule — read-only audit

**Date:** 2026-09-08
**Trigger:** `reports/2026-09-02-pm-closeout-owner-actions.md` §5 item 2 — "the
scorer-reads-config-at-verdict-time defect (Brief 36 round-3 N1) exists for
every registered window, not only Schwab. The 08-31 note flagged H10b/H5.
Recommendation: one read-only audit that lists, per live window, where its
loss bar comes from (event vs config)."
**Method:** one read-only Explore agent over `origin/main` @ `863eff2`; every
claim below cites a file:line the agent read. **Provenance: Agent-asserted.**
Nothing here was independently re-verified by a second reader yet — treat
the file:line anchors as the verification path, not as settled fact, before
acting on any row. No file outside this report was created or modified.
**Authority:** none. This audit proposes nothing to the ledger and changes no
threshold.

## Plain-language summary

The question is simple: when a window decides "enough losses, verdict now",
does it use the number that was frozen when the window was registered, or the
number currently sitting in `config.py`? The first is honest; the second means
an edit to config after registration silently changes the experiment.

- **The two H7 lanes are safe.** Both read the bar from the ledger event and
  refuse to fall back to config; tests pin that.
- **H6 has the real defect**, and its own test enshrines it: the test patches
  config and asserts the verdict follows the patched value.
- **H8 has no scorer at all** — a registered lane whose stated verdict rule has
  zero implementation.
- **H10b and H5 are not what the 08-31 note feared.** H10b's bar and window end
  live in config but the exact literals are pinned by CI to the registration
  text, so drift fails tests. H5 has no loss bar anywhere. Both, however, read
  their resume-floor dates from config with no value pin.
- **The repo-wide config-drift guard only checks the set of constant names**,
  never their values, so `H6_MIN_COMPLETED_POSITIONS` 8→5 passes it.

## Table

| Lane | Verdict-terminating parameter | Read site (file:line) | Source at verdict time | Pinned by test? | Risk note |
|---|---|---|---|---|---|
| **H7 legacy forward** (`h7-forward-v1`) | loss bar `min_losses_for_verdict` | `options_researcher/h7_forward_scoring.py:358-359,374` | Ledger registration event (`payload.frozen.stage456_parameters.MIN_LOSSES_FOR_VERDICT` and `.scorer.min_losses_for_verdict`, both 10) | Yes — `tests/test_h7_forward_scoring.py:326` (`test_frozen_bar_is_the_registered_one_not_config`), `:543` | SAFE. Config is read once at registration only (`h7_window_registration.py:205-207`). |
| H7 legacy forward | window end | `h7_forward_scoring.py:352-357` vs `registration.payload["window"]["final_decision_session"]` | Ledger event | Yes (`tests/test_h7_forward_scoring.py:364`) | SAFE. |
| **H7 Schwab** (`h7-forward-schwab-v1`) | loss bar | write `h7_schwab_window_registration.py:786-791`; read `h7_real_scoring.py:198`; re-validated `:284` | Ledger event, owner-typed `SCHWAB_MIN_LOSSES_FOR_VERDICT` (no config default exists) | Yes — `tests/test_h7_real_scoring.py:642`, `:735-740`; `tests/test_h7_scoring_identity.py:80` | SAFE (the N1 fix). `h7_scoring_identity.py:204-207` raises instead of defaulting. Store currently VALID-EMPTY. |
| H7 non-blind lane diagnostic | loss bar | `tools/h7_adjudicate.py:79` (`n_losses < config.MIN_LOSSES_FOR_VERDICT`) | **config.py:189 read live** | No value pin | Real, low severity: disclosed non-blind kill-only diagnostic, write-once ledgered. A rerun after a config edit adjudicates under a different bar. |
| **H6** | sample bar `H6_MIN_COMPLETED_POSITIONS` | `options_researcher/h6_watch.py:826` (message `:832`) | **config.py:349 read live in `score_book()`** | Yes — but pins the defective behaviour | **DEFECT REAL.** Seq-6 registration states the bar only in prose ("after 8 completed positions"); nothing compares config to it. |
| H6 | hard-kill `H6_HARD_KILL_FULL_LOSS_MONTHS` | `h6_watch.py:719` (`_kill_month_count`), messages `:806,813` | **config.py:350 read live** | `tests/test_h6_watch.py:493` patches config to 2 and asserts the verdict follows | **DEFECT REAL and test-enshrined.** The test name says "registered"; the value is the live config. `h6_config_snapshot()` (`:898-932`, called `:1050`) records the *current* config into the receipt with no comparison to seq 6. |
| H6 | kill-v2 effective date `H6_KILL_V2_EFFECTIVE_ENTRY_DATE` | `h6_watch.py:710` | config.py:353 read live | `tests/test_h6_watch.py:577-578` (patches config) | Same class. `H6_KILL_V2_TRIAL_INTENT_HASH` (config.py:354) is a comment-level anchor, not enforced. |
| **H8** | `H8_MIN_COMPLETED_POSITIONS`, `H8_HARD_KILL_FULL_LOSS_MONTHS` | **no read site** — names appear only at `config.py:383-384` and `tests/test_ritual_switch_on_hash_containment.py:251,256` | nothing — `h8_watch.py` has no `score_book`/verdict function | No | Distinct defect: registered lane (seq 11) with a stated verdict rule and zero implementation. |
| **H10b** | loss bar `H10_MIN_LOSSES_FOR_VERDICT = 7` | **no read site** — `config.py:625`, `tests/test_h10_config.py:29,46`, `tests/test_ritual_switch_on_hash_containment.py:140` | nothing — no H10 scorer | Value pinned: `tests/test_h10_config.py:46` | Unimplemented bar; literal pinned so drift fails CI. |
| H10b | window end | `options_researcher/h10_watch.py:85` (module-level `_WINDOW_END`), consumed `:95` | **config.py:627 read live** | `tests/test_h10_config.py:48` pins `"2027-01-06"`; `:50-52` anchors it to the seq-16 text; `tests/test_h10_watch.py:809-845` | Config read, effectively frozen by CI. |
| H10b | resume floor `H10B_RESUME_FLOOR_SESSION` | `h10_watch.py:541`; `h10_observe.py:112,266,446`; `ritual_receipt.py:359` | **config.py:629 read live** | **No** — tests reference the constant symbolically (`tests/test_h10_observe.py:15,149`, `tests/test_h10_watch.py:33`) | Real gap: the seq-29 amendment date can move and no test notices. Gates which sessions enter the record. |
| **H5** | loss/sample bar | none exists — no H5 scorer; `portfolio.py:177` enforces caps only | nothing registered numerically (seq 5) | n/a | The 08-31 suspicion does not apply as stated. |
| H5 | resume floor `H5_RESUME_FLOOR_SESSION` | `options_researcher/entry_watch.py:223,225,330,334` | **config.py:630 read live** | **No** — `tests/test_entry_watch.py:66,256` symbolic | Same gap as H10b's floor (seq-30 amendment date). |
| **RQ2-v1** | K / badge thresholds | no implementation (`config.py:225` comment only; mentions in `a2_runner.py`, `attractiveness_dashboard.py`) | nothing | No | No forward window registered, no scorer. Nothing to drift yet. |
| **A2-v1** | board universe | `options_researcher/a2_runner.py:451,843,1039,1219` read `config.ATTRACTIVENESS_UNIVERSE` live | config read live — **deliberate per seq 28** | Registration identity pinned (`a2_runner.py:47-48`, `:352-357` refuse unless seq 19 hash `684b59a2…`); `tests/test_a2_runner.py` | No-verdict lane. Adding a name to the universe silently changes the A2 board; the tuple's contents are unpinned. |
| Global backtest scoreboard (H1/H2/CARD3/power_check) | `MIN_LOSSES_FOR_VERDICT` | `metrics.py:525,527`; `options_researcher/card3_study.py:306`; `analysis/power_check.py:129` | **config.py:189 read live** | No value pin | Sealed post hoc by `config_hash` in ledger records — detectable, not refused. |

## Structural note

The only repo-wide guard against config drift,
`tests/test_ritual_switch_on_hash_containment.py:357-370`, compares the sorted
**set of uppercase names** in `config.py`. It passes unchanged if
`H6_MIN_COMPLETED_POSITIONS` goes 8→5 or `H6_HARD_KILL_FULL_LOSS_MONTHS` 3→2.

## What this audit does NOT do

It does not propose fixes, thresholds, or amendments. Candidate follow-ups
(for the owner to triage, each a separate brief): (1) H6 — freeze the bar and
kill-month count into a machine-readable registration amendment and make
`score_book()` read the event, mirroring `h7_real_scoring.py:198`; rewrite
`tests/test_h6_watch.py:493` to assert the opposite; (2) H8 — decide whether
to build the scorer or record that the lane has no verdict path; (3) pin the
H5/H10b resume-floor literals by test the way `test_h10_config.py:48` pins the
window end; (4) extend the hash-containment test to pin the values of every
verdict-bearing constant, not only the name set.
