# Brief 41 — independent review, round 5 (scoped + implementability sweep)

**Target:** `docs/superpowers/plans/2026-09-09-41-launchagent-loaded-check-codex-brief.md` rev 6 (uncommitted on `claude/brief-41-launchagent-loaded-check-2026-09-09`; rev 5 committed @ `4b48eba`; `origin/main @ 645365b`).
**Trigger:** Codex's first-dispatch stop report (`reports/2026-09-09-brief-41-codex-stop-report.md`) found a test contract unreachable through the specified interface. This round re-checked R5-1/R5-2 and swept every test (D.1–D.4) and acceptance step (1–7, 3a) for the same defect class.
**Reviewer:** fresh Opus subagent, read-only, dispatched 2026-09-09 ~14:50 ET; closure, `classify()` enumeration, harness lines, CI list, and acceptance one-liners executed or traced.
**Verdict:** **FAIL** — 2 blockers, 4 majors, 4 minors, 3 nits; all exact wording, no design change. R5-1 CLOSED; R5-2 CLOSED in principle with one residual (M6).
**Disposition:** all thirteen applied verbatim in rev 7.

## Findings (condensed)

**BLOCKER**
- **R5-B1** Scope OUT (rev 3 wording) forbade importing "anything else in the closure", but A.4 requires `data.atomic_io.atomic_text_write` and `data/atomic_io.py` IS in the closure (Test-verified, 50 paths). The ban was wrong on the merits: the closure is the forward import closure of one entry module, so importing a member cannot add the importer; `ritual_status.py:20` does exactly this and is outside. Fix: permit and explain; acceptance 5 is the proof.
- **R5-B2** `build_receipt(*, as_of, run_date, run_at_utc, states)` could not produce `summary.unavailable_reason` / `unavailable_inputs`; `Observation` had no fields; `UNAVAILABLE` was not a `State`. Fix: `Observation` dataclass defined; `build_receipt` takes the observation; `UNAVAILABLE` is observation-level.

**MAJOR**
- **R5-M3** D.1 asserted the `.bak` exclusion on `compare()`, which never sees filenames. Fix: test it on `installed_labels()`.
- **R5-M4** `tracked_labels()`'s `ValueError` was specified only on the regex fallback; a well-formed plist without `Label` had no defined behaviour. Fix: identical raise on both paths.
- **R5-M5** `as_of: null` had no assigned digest status. Fix: `DEGRADED` row with a fixed reason, `OK` suppressed.
- **R5-M6** The pinned-ref dispatch fallback had no revision self-check; the tip at dispatch time carried rev 5, so Codex would have stopped again; receipts were not on `origin/main`. Fix: single-ref read of the brief + all receipts, mandatory `rev 7` header check, stop on mismatch.

**MINOR**
- **R5-m7** D.3(c) said stub `$UV` "on `PATH`"; `UV` is set at `daily_ritual.sh:35` outside the slice and the slice reads `$REPO/$AS_OF/$RUN_DATE`. Fix: explicit prelude via the `_stage` idiom (`:281-309`).
- **R5-m8** `run`'s call shape unpinned, so the list-vs-print disagreement stub was non-deterministic. Fix: argv shape documented; stubs dispatch on `argv[1]`.
- **R5-m9** `--no-receipt` left the summary line's `receipt=` undefined. Fix: `receipt=none (--no-receipt)`.
- **R5-m10** `summary` lacked a `loaded_not_installed` count. Fix: added; six counts sum to `len(states)`.

**NIT**
- **R5-n11** "receipt absent" wording; **R5-n12** stale "read the four receipts" sentence in the dispatch prompt; **R5-n13** CLI synopsis brackets.

## Verified reachable by the reviewer

D.1 `classify()` sixteen tuples (enumerated: fourteen states, two raises, `DISABLED` precedence honoured); `compare()` no-row cases; real-tree `tracked_labels()`; adapter stubs; `observe()` disagreement (given m8); CLI exit 0. D.2 every fixture maps to a named `HealthStatus`; `_copy` at `:49-53`. D.3(a) `DATA_TIER_MODULES :51-66` and the set-equality at `:531-535`; D.3(b) line sets `{406, 449}` and `{428, 592, 601, 613, 614, 615, 632}` exact and the only two line-keyed registries. D.4 nineteen modules at `ci.yml:89-107`. B.1 insertion between `:385` and `:387`; `_region` matches; no region-ordering test breaks; no banner-guard span. C.2 splice at `:740` clean. Acceptance 3a runs as written (no stdout pollution from `import data.atomic_io`); 5's closure half runs (50 paths); 6 consistent with A.5 given m9. Facts the executor takes on faith (laptop-only `launchctl` shapes, plist inventory, uid) are listed and correctly assigned to the reviewer.
