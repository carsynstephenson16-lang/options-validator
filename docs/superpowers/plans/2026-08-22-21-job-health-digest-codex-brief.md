# Job-health digest tool — Codex brief

- **Date:** 2026-08-22
- **Author:** Claude Fable 5 orchestrating session
- **Executor:** Codex (default model, high reasoning)
- **Status:** rev 2 — a v1 implementation already landed on main (PR #67, `tools/job_health_digest.py`) against rev 1 of this brief; the PR-68 Codex-review hardenings below (per-tag intraday coverage, preclose force/invocation/manifest checks, receipt binding, research-root, symlink containment, out-dir semantics) are now the FOLLOW-UP requirements for that existing tool, each needing its own review.
- **Provenance:** Repo-verified against origin/main @accd165bd2a7aeacf8ff6f1630d0b3b815b39703 unless labeled otherwise; PR-68 review corrections verified 2026-08-23.

## Why this exists (plain language)

On 2026-08-21 the daily ritual ran with no network: closes stale, H5/H10 refused, capture receipt missing — and nothing surfaced it. Separately, two equity-research LaunchAgents failed silently for weeks. The audit's conclusion: exit codes are useless as a health signal in this ecosystem because fail-closed jobs exit non-zero **on purpose**; the truth lives in each job's receipt file. This brief builds a read-only digest that reads receipts and writes one small daily human-readable summary the owner can glance at (and that a scheduled Claude task can read aloud).

## Scope

**IN:** a new `tools/job_health_digest.py` + tests. Read-only over receipts; writes exactly one output file per run under `.tmp/job_health/`.

**OUT:** no ledger writes, no registration, no authority flips, no live-order paths, no frozen values. No sending (no Telegram/email — display only; alerting is a later separate decision). No changes to any existing job or receipt writer. No network. Not a scheduler — invocation wiring is a follow-up owner step.

## Work packages

**WP-A — Receipt readers.** For each source below, classify OK / DEGRADED / FAILED / MISSING for a given session date. Roots (Codex PR-68 review corrections): `--root` (default cwd) is the OPS-checkout read root; add a separate `--research-root` (default `~/options-validator-research`) because the research-refresh LaunchAgent runs from that checkout and writes its receipts there — checking it under the ops root would report every successful refresh as MISSING. **Containment (comment 3839191082):** every resolved candidate path — including globbed intraday files — must remain beneath the resolved read root after symlink resolution (`Path.resolve()` check); a file- or directory-symlink escaping the root is classified as a FAILED finding, never followed. Tests must cover both symlink escape shapes.

| Source | Path | Classification rule (Repo-verified + PR-68 review hardening) |
|---|---|---|
| Ritual overall | `reports/ritual/run_status_{as_of}.json` | `"status"` ∈ RUNNING/OK/OK_STARVED/BROKEN — `options_researcher/ritual_status.py:90-125`, values at :58. **Binding check:** the producer records `schema_version`, `as_of`, `capture_receipt_path`, `capture_receipt_sha256` — the digest must verify `as_of` matches, recompute the capture receipt's sha256, and downgrade OK/OK_STARVED to FAILED on any mismatch (stale/replaced receipt). |
| Ritual per-hypothesis | `reports/ritual/capture_receipt_{as_of}.json` | `hypotheses.*.status` — `options_researcher/ritual_receipt.py:407-451`. **Require the exact key set {H5,H6,H7,H8,H10}** (the producer always writes all five): any absent or unexpected hypothesis key = FAILED, never a reduced denominator. |
| Intraday capture | `reports/intraday_capture/{date}/{tag}.json` (docstring `:31`) | **One receipt per scheduled tag, all five** (`config.INTRADAY_CAPTURE_TIMES` + the intraday LaunchAgent's five daily runs): classify each expected tag independently; an absent expected tag = MISSING for that tag. Within a receipt, aggregate per-symbol `"status"` (**lowercase** `ok`/`unavailable`, set at `options_researcher/intraday_capture.py:536,:541,:778`; coverage at `:816`; no overall field exists). One good tag must never mask four failed launches. |
| Schwab preclose | `reports/schwab_chains/{session}/preclose.json` (`:324`) | `"overall_status"` (`:317`) is necessary but NOT sufficient: the receipt is written BEFORE `verify_session()` runs, and can be OK-shaped with `force=True` or `invocation_source` ≠ `launchd`. OK requires ALL of: `overall_status=="ok"`, `force==False`, `invocation_source=="launchd"`, AND a passing offline manifest verification for the session (reuse the existing verifier; cite it in the PR). Anything less = DEGRADED or FAILED with the failing condition named. |
| Alignment check | `.tmp/alignment_check/{date}.log` (dir at `:29`) | `status=` token in log line — `tools/ops_alignment_check.sh:127-128` |
| Research refresh | `{research-root}/.tmp/research_refresh/receipt_v2_{as_of}_{slot}.json` | Presence-based (the writer hardcodes `"status":"ok"` at `tools/research_refresh.sh:110`, success-only) — but **presence alone is not enough**: `{as_of}` is the market session, which consecutive scheduled weekdays can share (holiday → next morning), and the script neither removes the prior receipt nor records a run date. Require the receipt's mtime (or an embedded timestamp if one exists — verify) to fall on the invocation date being assessed; an older same-session receipt = MISSING for today's run. |

`live-dashboard` writes no receipt by design (`options_researcher/live_dashboard.py:538`) — exclude it, with a comment. `research-display-refresh` has no discrete receipt — report it as NOT_INSTRUMENTED rather than guessing.

**WP-B — Digest output.** `uv run python -m tools.job_health_digest --as-of YYYY-MM-DD [--root PATH] [--research-root PATH] [--out-dir PATH]` writes `{out-dir}/digest_{as_of}.md` and prints it: one table (job / status / one-line reason / receipt path), worst status first, and a top line `ALL OK` or `N PROBLEMS`. **Output semantics (corrected per comment 3839097034 — the old wording was self-contradictory when `--root` defaulted to cwd):** `--out-dir` defaults to `<cwd>/.tmp/job_health`; the invariant is that the tool writes ONLY under `--out-dir`, and `--out-dir` must not resolve to a location under a `--root`/`--research-root` that points at a DIFFERENT checkout (the acceptance run points `--root` at the production ops checkout — writing anything there is a failure; reading roots equal to cwd is fine). Weekend/holiday sessions must report NO_SESSION, not a wall of MISSING: use the XNYS calendar — `pandas-market-calendars` 5.4.0 is already a locked dependency; the four-line pattern is at `data/cache_runner.py:112-125` (`_xnys()`), but do NOT import `data.cache_runner` itself (it pulls in grpc + the ThetaData adapter at module level) — call `mcal.get_calendar("XNYS")` directly or lift the helper. A weekday-only approximation is NOT acceptable.

**WP-C — Tests.** Fixture receipts for each shape proving classification, MISSING handling, and NO_SESSION handling — including the 2026-08-21 real-world case, which is (Repo-verified 2026-08-22, both checkouts): run_status file **absent**, capture receipt **absent**, preclose receipt **absent**, `.tmp/alignment_check/2026-08-21.log` **present** — a scheduled trading day where the ritual left no status artifact at all. The digest must classify that day as problems-found from absence alone. Fixtures generated from the real producers' current shapes, not hand-invented, where a producer can run offline; otherwise copy a real on-disk receipt (verify no secrets before copying).

## Acceptance / verification

```
uv run python -m unittest discover -s tests
uv run ruff check . && uv run pyright
```
Exit codes define done. Additionally: running the tool read-only with `--root ~/options-validator-ops --as-of 2026-08-21` must classify that day as problems-found via the absent-artifact path (that is the incident that motivated the tool); state the observed output in the PR description and confirm nothing was written under the ops checkout.

## Status addendum 2026-08-26 (orchestrating session)

**IMPLEMENTED AND MERGED.** v1 via PR #67 (merge `53f0a84`, 2026-08-23);
every rev-2 hardening via PR #81 (merge `16659ff`, 2026-08-26) with
RED-before-GREEN and the mandated read-only 2026-08-21 ops acceptance run
("10 PROBLEMS"; ops fingerprint identical before/after). Remaining
follow-ups this brief declared out of scope: invocation wiring is now
specified in brief 31
(`docs/superpowers/plans/2026-08-26-31-audit-closeout-followups-codex-brief.md`,
WP-B — build-only; install stays owner-run); alerting remains a later owner
decision.
