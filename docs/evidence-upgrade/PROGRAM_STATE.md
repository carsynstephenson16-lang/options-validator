# Evidence-Upgrade Program — State File

**Updated 2026-07-29.** Paste this at the top of a new session instead of
re-reading a long transcript. Authoritative detail lives in the six sibling
artifacts in this directory; this file is the resume point only.

## What this program is

One evidence-ingestion contract (EC-1) across three repos — `equity-research`
(producer), `options-validator` (consumer), `Claude`/kalshi (parallel
producer) — so that unsupported, stale, temporally unsafe, or weakly sourced
evidence can never gain decision authority. Incubated in `equity-research`
and pattern-replicated, NOT extracted into a shared package until at least
two repos consume a stable interface (that call is Packet 10).

Division of labour: this session ORCHESTRATES (architecture, specs, briefs,
adversarial review, decisions). **Codex (GPT-5.6 Sol, Extra High) implements
in two threads.** Sonnet-5 high-effort subagents do the reading and
reviewing. No production code is written from the orchestrating session.

## Packet status

| # | Scope | Repo | Status |
|---|---|---|---|
| 1 | SEC availability rule module | equity-research | MERGED (PR #13) |
| 2 | Alembic baseline + EC-1 store expansion | equity-research | MERGED (PR #14) |
| 3 | Source registry v1 + claim-type authority | equity-research | MERGED (PR #15 @ e01bff2) |
| 4 | XBRL structured facts + as-first-reported queries | equity-research | MERGED (PR #16 @ cffcd8d) after 2 blocking fixes, both re-verified by execution |
| 5 | Admission gates, verify-support, lineage junctions | equity-research | **PROMPT SENT — Codex building; plan drafted + reviewed** |
| 6 | CLI chain, BBB parsing, quarantine, freeze, settlement capture | kalshi | MERGED @ 104947d |
| 7 | Lineage gating for legacy calibration artifacts | kalshi | MERGED @ 0d78b16 |
| 7a | Four untested guards closed | kalshi | MERGED @ 8ee715a — APPROVE |
| 8 | Consumer availability/admission filtering in market_context | options-validator | MERGED @ c27aa67 — APPROVE_WITH_NITS |
| 8-tail | UTC-normalize before SQL comparison | options-validator | **PROMPT SENT — Codex building** |
| 9 | Golden-question benchmark + provider health metrics | equity-research | Queued behind 5, same thread |
| 10 | Shared-package extraction checkpoint | cross-repo | Owner go/no-go after ≥1 month of real use. NOT a build. |

Thread layout now: **Thread A = 5 → 9** (equity-research). **Thread B =
8-tail + a kalshi record note**, then done. Never two Codex threads in one
checkout.

## What the next session must do first

Two Codex reports are outstanding (Packet 5; Thread B's two closeouts). When
they arrive, run the SAME review protocol that has caught a real defect every
single round:

- Dispatch **3 Sonnet-5 subagents at high effort in parallel**, one per repo
  (never two in one repo — they corrupt each other's measurements).
- Every reviewer MUST mutation-test: delete each guard, confirm the suite goes
  RED, restore, confirm GREEN. Report a guard→red/green table. A guard that
  stays green is untested and blocks.
- Every reviewer MUST do mutation work in an isolated `git worktree`, run
  attacks by EXECUTION not by reading, and independently reproduce every
  claimed number.
- Then write a decision-log entry and commit. Do not merge without review.

## Standing rules earned the hard way this program

1. **A guard is not done until it has been shown to fail with the guard
   removed.** "N tests passed" is never evidence a specific guard works.
   Two separate rounds shipped something documented-as-enforced but
   unexercised (D29 orphaned guard; D35 four kalshi guards).
2. **Report measured counts from the runner's own summary line**, never
   assertion counts (Codex reported an assertion count as a test count once).
3. **Trust the delta, not the absolute test count.** `unittest discover`
   counts untracked files physically present, so a shared checkout cannot
   produce a clean absolute. Always state which tree you measured.
4. **Never two Codex threads (or two mutating subagents) in one checkout.**
5. **Encode verbatim lists, never counts** (a "21 types" label was really 24).
6. Codex refusing a packet as NOT_READY has been CORRECT — adjudicate on
   evidence, and amend the record when the plan was wrong (D28).

## Owner action items (not blocking Codex)

- **Run `uv sync --extra web-fetchers` in options-validator.** A bare
  `uv sync` pruned 52 packages, all web-fetcher transitives. Trafilatura is
  currently `ModuleNotFoundError` — that is the tool that gets through SEC's
  403 on ordinary fetching, so earnings-date research is broken until restored.
- **~209 equity-research tests never run in CI.** CI uses `unittest
  discover` (1608); `pytest` finds 1817 + 101 subtests, because six files use
  pytest-native functions invisible to `unittest.TestLoader`. Pre-existing,
  outside this program, worth scheduling.
- **One judgment call is yours to confirm or reverse (D32).** Migration 0002
  blanket-marked all pre-existing evidence rows ADMITTED. I chose to LABEL
  those rows `legacy-grandfathered` rather than re-run the gates over
  history. Labeling keeps old evidence working; it also means history never
  gets audited against the new standard. Reversible whenever you want it.

## Repo facts a fresh session would otherwise re-derive

- **equity-research** migration chain: 0001 legacy baseline, 0002 EC-1
  expand, 0003 admitted immutability, 0004 provider-run registry version,
  0005 xbrl_facts, 0006 xbrl_fact_natural_key. Packet 5 authors **0007** on
  `down_revision="0006_xbrl_fact_natural_key"` — confirm with `alembic heads`.
- **Sole event writer:** `MarketUpdateStore.ingest()` at
  `market_updates/storage.py:287` holds the only `INSERT ... INTO events`
  (line 394). Admission has exactly one place to live.
- `run_evidence` and `provider_runs` already exist (migration 0002),
  `run_evidence` with both directional indexes. `conflicts_with` does not
  exist yet — Packet 5 adds it.
- `available_at` IS populated: it is the conservative `public_by_ts_utc`
  bound for SEC submissions-path rows, deliberately NULL for Atom-feed rows
  (`tests/test_sec_availability_wiring.py:104-153`).
- **Baselines:** equity-research 1608 (unittest) / 1817+101 (pytest);
  kalshi 2324; options-validator **2109 clean-tree, 2115 after Packet 8**
  (2116/2122 are the same numbers plus 7 tests from an untracked
  concurrent-session file). options-validator suite takes ~9 minutes and
  writes its summary to STDERR while tests print to STDOUT — redirect to a
  file and grep `^Ran `/`^OK`/`^FAILED`; never grep a tail for "OK".
- **Branch situation in options-validator:** a concurrent session moved the
  main checkout to `schwabapi` with heavy uncommitted work. This program's
  docs live on `feature/strategy-enhancement` (latest `2969af5`), which also
  carries Packet 8 at `c27aa67`. Commit program docs through a separate
  worktree rather than switching the shared checkout's branch.

## Decision log pointers

`decision-log.md` D01–D37. The ones that changed the architecture:
D05 (SEC availability as an interval), D12 (composite scores rejected),
D14 (double-order verify-support), D20 (SQLite WAL gate made fail-closed),
D28 (Packet 1 rescoped after Codex's correct NOT_READY),
D31–D34 (migration renumber; legacy-grandfathered labeling; Packet 8
unblocked and threads rebalanced; `gating_basis` rename),
D36 (a NULL admission_reason now MEANS grandfathered, so the writer must
never emit an ADMITTED row without a reason — enforced, not intended),
D37 (Packet 4 fixes verified fixed; 7a and 8 approved; three follow-ups).

## Open, non-blocking

1. **B3 TOCTOU** in equity-research: the XBRL store's ownership marker is a
   configuration fence, not an atomic lock — a reproduced interleaving leaves
   one file carrying both schemas. Inert while XBRL keeps a dedicated file.
   XBRL must take Packet 2's writer lock around its complete write path
   before it ever shares the live DB.
2. **Packet 8 non-UTC-offset drop** — assigned to Thread B (8-tail).
3. **Cross-repo conformance fixture** must stay byte-identical:
   `options-validator/tests/fixtures/market_context_ec1_conformance.json`,
   SHA-256 `7d8012023e34b71587164c0dcb4cb6f513fd430f40f56e772314b6c4559b1228`.
   Packet 5 adopts these exact bytes; if Thread B changes it, the new SHA
   must be published to Thread A.
4. **WMO `Pxx`** remains undefined in every governing source read —
   quarantine-on-unrecognized stands; locate the 1994 WMO BBB guidelines
   before ever changing that rule.
