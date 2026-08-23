# Job-health digest tool — Codex brief

- **Date:** 2026-08-22
- **Author:** Claude Fable 5 orchestrating session
- **Executor:** Codex (default model, high reasoning)
- **Status:** DRAFT — pending independent adversarial review before hand-off
- **Provenance:** Repo-verified against origin/main @accd165bd2a7aeacf8ff6f1630d0b3b815b39703 unless labeled otherwise.

## Why this exists (plain language)

On 2026-08-21 the daily ritual ran with no network: closes stale, H5/H10 refused, capture receipt missing — and nothing surfaced it. Separately, two equity-research LaunchAgents failed silently for weeks. The audit's conclusion: exit codes are useless as a health signal in this ecosystem because fail-closed jobs exit non-zero **on purpose**; the truth lives in each job's receipt file. This brief builds a read-only digest that reads receipts and writes one small daily human-readable summary the owner can glance at (and that a scheduled Claude task can read aloud).

## Scope

**IN:** a new `tools/job_health_digest.py` + tests. Read-only over receipts; writes exactly one output file per run under `.tmp/job_health/`.

**OUT:** no ledger writes, no registration, no authority flips, no live-order paths, no frozen values. No sending (no Telegram/email — display only; alerting is a later separate decision). No changes to any existing job or receipt writer. No network. Not a scheduler — invocation wiring is a follow-up owner step.

## Work packages

**WP-A — Receipt readers.** For each source below, parse the newest artifact for a given session date and classify OK / DEGRADED / FAILED / MISSING (all paths relative to the checkout it runs in; accept a `--root` argument, default cwd):

| Source | Path | Status field (Repo-verified) |
|---|---|---|
| Ritual overall | `reports/ritual/run_status_{as_of}.json` | `"status"` ∈ RUNNING/OK/OK_STARVED/BROKEN — `options_researcher/ritual_status.py:90-125`, values at :58 |
| Ritual per-hypothesis | `reports/ritual/capture_receipt_{as_of}.json` | `hypotheses.*.status` — `options_researcher/ritual_receipt.py:407-451` |
| Intraday capture | `reports/intraday_capture/{date}/{tag}.json` (path per docstring `:31`) | per-symbol `"status"` set at `options_researcher/intraday_capture.py:536` (`"ok"`), `:541` (`"unavailable"`), `:778`; coverage counted at `:816`. Values are **lowercase**; there is NO overall status field — the reader must aggregate per-symbol. |
| Schwab preclose | `reports/schwab_chains/{session}/preclose.json` (`:324`) | `"overall_status"` — `options_researcher/schwab_chain_capture.py:317` |
| Alignment check | `.tmp/alignment_check/{date}.log` (dir at `:29`) | `status=` token in log line — `tools/ops_alignment_check.sh:127-128` |
| Research refresh | `.tmp/research_refresh/receipt_v2_{as_of}_{slot}.json` | **Presence/absence is the only signal** — `tools/research_refresh.sh:110` hardcodes `"status":"ok"` and the receipt is only written on success (adversarial-review M4). Classify on existence per expected slot, never on the field. Note (Repo-verified 2026-08-22): no such receipt currently exists on disk in the research checkout — MISSING is a legitimate finding. |

`live-dashboard` writes no receipt by design (`options_researcher/live_dashboard.py:538`) — exclude it, with a comment. `research-display-refresh` has no discrete receipt — report it as NOT_INSTRUMENTED rather than guessing.

**WP-B — Digest output.** `uv run python -m tools.job_health_digest --as-of YYYY-MM-DD [--root PATH]` writes `.tmp/job_health/digest_{as_of}.md` and prints it: one table (job / status / one-line reason / receipt path), worst status first, and a top line `ALL OK` or `N PROBLEMS`. `--root` governs where receipts are READ from only; output is always written relative to the invoking cwd, and the tool must never write inside `--root` (the acceptance run points `--root` at the production ops checkout — polluting it is a failure). Weekend/holiday sessions must report NO_SESSION, not a wall of MISSING: use the XNYS calendar — `pandas-market-calendars` 5.4.0 is already a locked dependency; the four-line pattern is at `data/cache_runner.py:112-125` (`_xnys()`), but do NOT import `data.cache_runner` itself (it pulls in grpc + the ThetaData adapter at module level) — call `mcal.get_calendar("XNYS")` directly or lift the helper. A weekday-only approximation is NOT acceptable.

**WP-C — Tests.** Fixture receipts for each shape proving classification, MISSING handling, and NO_SESSION handling — including the 2026-08-21 real-world case, which is (Repo-verified 2026-08-22, both checkouts): run_status file **absent**, capture receipt **absent**, preclose receipt **absent**, `.tmp/alignment_check/2026-08-21.log` **present** — a scheduled trading day where the ritual left no status artifact at all. The digest must classify that day as problems-found from absence alone. Fixtures generated from the real producers' current shapes, not hand-invented, where a producer can run offline; otherwise copy a real on-disk receipt (verify no secrets before copying).

## Acceptance / verification

```
uv run python -m unittest discover -s tests
uv run ruff check . && uv run pyright
```
Exit codes define done. Additionally: running the tool read-only with `--root ~/options-validator-ops --as-of 2026-08-21` must classify that day as problems-found via the absent-artifact path (that is the incident that motivated the tool); state the observed output in the PR description and confirm nothing was written under the ops checkout.
