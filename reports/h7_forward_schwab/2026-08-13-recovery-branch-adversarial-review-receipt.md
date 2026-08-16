# Independent adversarial review receipt — codex/h7-schwab-recovery

**Date:** 2026-08-13
**Reviewer:** independent Opus subagent (adversarial charter: refute, don't confirm),
commissioned by the orchestrating Claude session; repo untouched during review.
**Target:** branch `codex/h7-schwab-recovery` @06ecf75 vs fixed base origin/main @7fbe013.
**Verdict:** **PASS WITH FIXES — B-1, B-2, B-3 must close before merge; H-1..H-4 before any registration.**

This satisfies PROJECT_STATE's 2026-08-12 requirement that the branch receive
its own independent adversarial review before merge. The branch does NOT merge
until the blockers below are resolved (expected route: rebase onto current
origin/main and fix in place, or a fresh Codex pass using this receipt).

## Blockers (before merge)

- **B-1 — Owner decision recorded without provenance.** The branch rewrites
  `reports/h7_forward_schwab/2026-08-09-owner-gate-packet.md` to state "The
  owner selected redesign and rejected starvation-risk acceptance" with no
  date, no quoted owner wording, no provenance label, and deletes the
  blank-decision placeholders. (The owner DID choose redesign in-session
  2026-08-13 — recorded with provenance in PROJECT_STATE's 2026-08-13 block
  and brief 09 — but the branch's undated assertion predates that and must be
  re-recorded in the repo's dated-amendment form.) Fix: dated owner-directed
  amendment quoting actual wording, or restore placeholders.
- **B-2 — Merge would delete main's 2026-08-12 B4 disclosure amendment**
  (gate-packet conflict resolved "theirs" drops the ThetaData-EOD-measured /
  biases-inflate-the-count disclosure that applies verbatim to 4/1050).
  Fix: union resolution — keep main's B4 text, append the 2026-08-11 update
  as a further dated amendment.
- **B-3 — Stale base; semantic conflicts with main's 85e72a8** on
  `h7_schwab_window_registration.py` (+ its test): two independent
  `_validate_feasibility` implementations whose field sets differ
  (main: config_hash + universe_size; branch: config_hash, universe,
  tool_label, lookback_sessions, error_count, errors + window pins + >=20
  floor + owner-line binding). Hand-resolution risks silently dropping a
  guard. Branch alone also regresses B1's `_REAL_STORES` one-door test
  parameterization (merge happens to save it — luck, not design).
  Fix: rebase onto current origin/main, re-review the single merged
  `_validate_feasibility`.

## High (before registration)

- **H-1 — Receipt not bound to an actual measurement:** `input_files`,
  `canonical_data_paths`, `method`, `passing_symbol_days` present in the
  receipt but never validated; a self-consistent hand-authored receipt would
  register. Fix: path-load the receipt, re-hash `input_files`, pin
  `method["data"]`, assert `len(passing_symbol_days) == full_stack_passes`.
- **H-2 — Committed tool cannot reproduce the committed receipt** (4 fields
  post-hoc augmented outside `build_receipt`, provenance says tool-computed).
- **H-3 — `code_sha` provably not the measurement tree** (declared inputs
  first exist at the NEXT commit; ran on a dirty tree). Fix: `_code_sha()`
  refuses dirty tree or records `tree_dirty`.
- **H-4 — `owner_fields` became an injectable parameter of the shared
  activation guard** (`h7_activation_guard.py:79`) — `owner_fields=()` passes
  vacuously; no red test. Fix: require superset of default; add red test.

## Medium

M-1 >=20 floor deletes the 2026-07-24 gate's OR-limb (starvation
pre-acceptance) — agent-narrowed policy needing dated owner provenance
(now factually aligned with the owner's 2026-08-13 redesign decision, but the
record must say so properly); multiplier `2 *` belongs in config.py with an
LLM-proposed label. M-2 required owner decision line is agent-authored
boilerplate — require owner-typed rationale instead. M-3 the 3/1050 → 4/1050
delta is a DATA repair (14 missing Q1-2026 earnings rows appended; one new
pass = 2026-05-18 NOW), not a stack loosening — config_hash unchanged and
re-derives; must be disclosed in the packet. M-4 primary-source captures not
committed (hashes advisory only). M-5 CLI untestable end-to-end while B2
(evidence-mode receipt path) is unfixed; refusal-matrix holes listed. M-6
library imports a CLI script with import-time sys.path mutation.

## Low

L-1 `.superpowers/sdd/` task report location off-convention. L-2 pin
`forward_base` constant. L-3 redundant `--snapshot` surface. Also noted:
OD-3's operative field `H7_STAGE8_EXPLICIT_AUTHORIZATION` is non-emptiness
checked only.

## Attacks that did NOT hold

No second registration door (one-door scan covers `tools/` post-merge); no
ledger writes outside typed APIs; no network in code or tests (36/36 offline
green); no live-order path; no authority flip; no config change; no invented
owner numbers. `restore-check` hardening is real (binds exact `snapshot_id`,
refuses "latest", exact inventory equality, good red tests). The
shortened-denominator and exactly-20 boundary tests are good adversarial work.

## Feasibility receipt fitness (for the owner's already-made redesign decision)

Arithmetic verified independently: `receipt_hash` matches; `config_hash`
re-derives from current config.py; input hashes match; 4/1050 → expected 4.0;
exact 95% CI [1.09, 10.21] expected entries — entirely below the bar of 20;
~350 decision sessions (~17 months) needed at this base rate. With the B4
caveat carried forward (measured on ThetaData EOD, not Schwab pre-close;
every simplification inflates the count) and the 3→4 data-repair delta
stated: fit to present, and it STRENGTHENS the redesign conclusion. Per
vocabulary discipline: the v1 entry stack was **rejected by its own
feasibility gate** — a clean negative result, which is a success under this
repo's standard.
