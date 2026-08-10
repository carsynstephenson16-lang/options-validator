# Codex brief 06 — split experiments into their own dashboard artifact (2026-08-10)

Executor model: gpt-5.6-sol · Reasoning effort: medium ·
Orchestrator/reviewer: Claude Fable 5 · Implementation mode: autonomous,
evidence-grounded, test-driven.

Owner directive (2026-08-10, in-session): split the dashboard —
experiments become their own separately refreshable artifact; the exact
form ("two different dashboards or two refreshable artifacts, whatever is
most optimal") was delegated to the orchestrator, whose decision this
brief records: **two artifacts, two modules, zero shared render path.**
This also RESOLVES review finding F4
(`reports/2026-08-10-attractiveness-stage-b-fable-review.md`): the
crash-policy dilemma dissolves because production can no longer crash on
experiment code it does not import, and the experiments page quarantines
per lane.

Base commit: current `origin/main` at task start (fetch first; if
`codex/ops-failure-classification` has merged, base on that result —
sequencing: run that task BEFORE this one if both are pending, because
both touch `tests/test_experiments_baseline.py`).
Branch: `codex/experiments-dashboard-split`.
Worktree: `.tmp/worktrees/experiments-dashboard-split` — nowhere else.
Binding preamble, hard rules, worktree rules: master brief
`docs/superpowers/plans/2026-08-09-attractiveness-experiment-program-codex-master-brief.md`.
Prior receipts worth reading:
`reports/2026-08-10-attractiveness-hardening-fable-review.md` (residuals
R1/R3 — both are retired by this design, see Part 3),
`reports/2026-08-10-attractiveness-stage-c-receipt.md`.

Touch ONLY: `options_researcher/attractiveness_dashboard.py`,
`config.py`, `tests/test_experiments_baseline.py`, NEW
`options_researcher/experiments_dashboard.py`, NEW
`tests/test_experiments_dashboard.py`, NEW receipt
`reports/2026-08-10-experiments-dashboard-split-receipt.md`. The four
`exp_*.py` modules and their tests are UNTOUCHED. `pyproject.toml`/
`uv.lock` untouched. Offline only; no new dependencies; no ledger
writes; no changes to ranking logic, board grading, Top-3 ordering, or
any `h5/h6/h7/h8/h10*` module.

## Part 1 — strip experiments out of the production dashboard

Remove from `options_researcher/attractiveness_dashboard.py`: the four
`exp_*` keywords on `assemble()`, the `exp_*` entries in the assembled
dict, `_experiments_html`, `_experiment_health_html`,
`_experiment_lane_html`, `_experiment_card_line`,
`_experiment_state_class`, `_cli_experiment_payloads`, the
`--experiments` CLI flag, and the four `exp_*` module imports. After
this part, the production module contains NO reference to experiments at
all — grep-clean for `exp_beta|exp_tail|exp_spread|exp_tbill|experiment`
(case-insensitive) outside of comments explaining the split (prefer zero
occurrences including comments; point readers at the new module via one
line in the module docstring if needed, without the word matching the
marker grep — e.g. "The display-only research lanes moved to
experiments_dashboard.py (2026-08-10 split)").

**Byte-identity obligation (a REAL one this time):** the no-args
production build's HTML must be byte-identical before and after this
change. Evidence in the receipt: build
`python -m options_researcher.attractiveness_dashboard` (no args, same
empty-cache fixture state) at the base commit and at your HEAD, and
show the two files' SHA-256 hashes equal. This is achievable because
the embed path was opt-in only — the default render never contained
experiment markup (verified 105,961-byte builds with zero markers in
both prior receipts).

## Part 2 — the new experiments artifact

NEW module `options_researcher/experiments_dashboard.py`:
- Own entry point: `python -m options_researcher.experiments_dashboard`
  writes `.tmp/dashboard/experiments.html` (constant
  `EXPERIMENTS_OUTPUT_PATH` in `config.py`, provenance comment
  "structural, owner-directed split 2026-08-10").
- Move (do not rewrite) the renderer functions removed in Part 1 into
  this module; keep their output copy, per-lane `max as-of` stamps,
  health strip, DATA_BLOCKED refusal copy, and state→CSS-class mapping
  exactly as-is (bring the needed CSS with the page — it is a
  standalone HTML artifact now and must be self-contained).
- Builds ALL FOUR lanes on every invocation. Running the module IS the
  opt-in; there is no production embed left to guard. Accordingly,
  REMOVE `EXPERIMENT_LANES_ENABLED` from `config.py` (its sole purpose
  was gating the now-deleted embed path; dead flags invite drift). The
  sixteen `EXP_*` constants STAY — the experiment modules read them and
  they are unchanged by this brief.
- **Per-lane quarantine (the F4 resolution, scoped to where it is
  safe):** each lane's build+render is isolated; an exception in one
  lane renders a visible ERROR card for that lane (state line + the
  exception's type and message, escaped) while the other lanes and the
  page itself still build. The page never exits nonzero because one
  lane broke — but it MUST exit nonzero if the page itself cannot be
  written. No try/except anywhere may swallow silently: every caught
  exception becomes visible ERROR-card copy.
- The page header carries: "display-only research experiments — not
  part of Top-3 ranking, no verdict authority" plus the build's max
  as-of session, consistent with vocabulary discipline.

## Part 3 — rework the boundary tests

`tests/test_experiments_baseline.py` (rework):
- REPLACE the builder-mock guard (`test_default_path_never_invokes_
  experiment_builders`) with the structurally stronger test this split
  makes possible: parse `options_researcher/attractiveness_dashboard.py`
  with `ast` and assert it contains NO import of any
  `options_researcher.exp_*` or `experiments_dashboard` module. (This
  retires review residual R3 — the mock-target fragility — permanently.)
- KEEP the subprocess no-args test (zero case-insensitive "experiment"
  markers in the production HTML), including the R1 stdout "wrote "
  assertion if the ops-classification task already added it; add that
  assertion here if not.
- KEEP the config-drift test (unchanged semantics; drop only its
  `EXPERIMENT_LANES_ENABLED` special-case, which this brief deletes
  from config).
- DELETE tests that exist only to exercise the removed embed machinery
  (`--experiments` CLI selection, flags-default-False, embed-section
  rendering) — list each deleted test and its replacement (or the
  reason no replacement is needed) in the receipt.

NEW `tests/test_experiments_dashboard.py`:
- Subprocess test of the literal command
  `python -m options_researcher.experiments_dashboard`: exit 0 with an
  empty cache; all four lane headings present; per-lane as-of stamps
  present; DATA_BLOCKED copy present; assert the module's own "wrote "
  stdout line (no stale-file vacuity — hardening-review R1 precedent).
- Quarantine test: monkeypatch one lane's builder to raise; page still
  builds; that lane shows a visible ERROR card containing the exception
  message; other three lanes render normally.
- Self-containment: the emitted HTML contains the status-badge CSS it
  uses (no reference to the production page's stylesheet).
- Renderer-copy fidelity: health strip and refusal copy tests carried
  over from the old embed tests where still meaningful.

Every behavior change gets a RED test first with the failing run's
literal output captured in the receipt (established Stage-C practice).

## Part 4 — receipt + gates + merge

`reports/2026-08-10-experiments-dashboard-split-receipt.md`: captured
RED outputs; the byte-identity hash comparison from Part 1; full suite
(`uv run python -m unittest discover -s tests`) exit code + `Ran N`
line; `uv run ruff check .`; `uv run pyright`; `git diff --check`; both
artifacts built with quoted HTML evidence (production: zero markers;
experiments page: four lanes + stamps + one blocked line + the
quarantine ERROR card from a deliberate local mutation, reverted);
deleted-test inventory per Part 3; commit SHAs; deviations
none-or-listed. Then — owner-authorized 2026-08-10 — merge the branch
into `main` with `--no-ff`, push branch and main. Do NOT touch
`~/options-validator-ops` or `~/options-validator-research`; deploying
the split to the ops checkout stays the owner's move.

## Stop conditions

Master brief's, verbatim (missing capability, network-needing test,
ambiguity forcing invention, hook block = correct, base unavailable,
worktree-hygiene guard failure). Plus: if the Part 1 byte-identity
comparison FAILS (default build differs at all), STOP and report the
diff — do not rationalize it away; that comparison failing means the
embed path was not as opt-in as every prior receipt evidenced.

## Explicitly OUT of scope

- Any change to experiment math, board contracts, or `EXP_*` values.
- Scheduling the experiments page (LaunchAgent) — owner's call later.
- The RQ2-v1 K=3 ledger amendment (separate, handled by the
  orchestrator session with its own adversarial-review gate).
- RQ2 badge implementation (B1/A1/V1 remain registered-but-unbuilt;
  building them has its own future briefs and feasibility quote).
