---
name: codex-brief-writing
description: Write or review an implementation brief handing work to Codex. Use whenever a spec, adversarial-review finding, or approved design is being delegated to Codex rather than implemented in-session, when Carsyn says "write a Codex brief" or "hand this to Codex", or before any hand-off of strategy/ledger/gate code changes. Do NOT use for research reports or owner decision packages (those are not executor hand-offs).
---

# Codex Brief Writing

A brief is the contract between the orchestrating Claude session and the Codex
executor. CLAUDE.md's division of labor makes this hand-off standing policy;
14+ briefs exist and their shapes drifted. This is the canonical shape.

## File and header

- Location: `docs/superpowers/plans/<YYYY-MM-DD>-<NN>-<slug>-codex-brief.md`
  (`NN` = the next number in the plans directory's running sequence — it does
  NOT reset daily, and non-brief plans occupy slots too; check the highest
  existing `NN` first).
- Header block, in order: **Date**; **Author** (the orchestrating session);
  **Executor** (Codex model + reasoning tier); **Status** (`DRAFT — pending
  independent adversarial review before hand-off`); **Provenance** (the exact
  commit every constraint was verified against, e.g. "Repo-verified against
  origin/main @<sha> unless labeled otherwise").

## Body, in order

1. **Why this exists (plain language)** — the problem in prose before any
   scope; name the review-finding ID (e.g. "B2") or spec this brief closes.
2. **Scope** — explicit IN and OUT lists. OUT is what stops executor
   over-reach; in this repo it almost always includes: no ledger writes, no
   registration, no authority flips, no live-order paths, no changes to
   frozen values.
3. **Work packages** (WP-A, WP-B, …) — numbered, acceptance-checkable steps.
   Reuse existing constants and paths by exact reference (file:line); never
   restate a value that already has one source of truth.
4. **Acceptance / verification** — the exact commands whose exit codes define
   done (the offline suite, ruff, pyright), plus any proof tests the review
   demanded ("prove both directions with tests").

## Rules

- Every constraint carries a claim-discipline label: Repo-verified (cite the
  commit), Official-source, Inference, or Assumption. A brief with unverified
  constraints is not ready to hand off.
- Cite prior review-finding IDs verbatim so Codex closes the SAME finding,
  not a reinterpretation of it.
- The brief goes to independent adversarial review BEFORE hand-off; the
  Status line stays DRAFT until that review passes.
- A brief delegates implementation, never authority: merge timing, frozen
  numbers, registrations, and verdicts stay with the owner.
- Closest existing example:
  `docs/superpowers/plans/2026-08-13-07-h7-schwab-b2-receipt-path-codex-brief.md`.
