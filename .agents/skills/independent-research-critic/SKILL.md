---
name: independent-research-critic
description: Independently audit the newest attractiveness_research/v2 bundle by run_id and context SHA, without modifying research or trading state.
---

# Independent Research Critic Audit

Remain read-only. Do not edit repository files, receipts, hypotheses,
thresholds, strategy state, dashboards, orders, producer packets, context
files, or manifests. Do not recommend trades or change a repository verdict.

## 1. Identify and validate the input

1. Read `AGENTS.md`.
2. Use `America/New_York` for every timestamp and date comparison.
3. Locate the newest market-session manifest at:

   `reports/attractiveness_research/YYYY-MM-DD/manifest.json`

   The filename date is `market_as_of_date`, not the research-generation date.
4. Require `schema_version == "attractiveness_research/v2"`. Read the exact
   `run_id`, `outputs.context.path`, `outputs.context.sha256`,
   `outputs.markdown.path`, and the UTC/ET generation timestamps.
5. Re-hash the context and Markdown. If either differs from the manifest,
   return `HARD_CONTRADICTION` for broken lineage and stop. Do not audit
   uncommitted or mismatched bytes as if they were trusted input.
6. Require the manifest ritual block to bind both the capture receipt and the
   mutable `daily_ritual/run_status/v1` projection. Its status must still be
   `OK`, and its capture-receipt path/SHA must match. Per-hypothesis
   `CAPTURED|NO_SIGNAL` statuses do not override a globally `BROKEN` ritual.
7. Run the producer's read-only verifier when the authoritative ritual root is
   available:

   `uv run python -m tools.research_context_assemble --verify`

   A verifier refusal is an audit finding, never permission to bypass a gate.

## 2. Exact duplicate gate

Inspect prior critic receipts under `reports/attractiveness_critic/`. A valid
critic receipt records both:

- `producer_run_id`
- `producer_context_sha256`

If one prior receipt has the same pair as the newest validated manifest, return
exactly:

`[NO_NEW_INPUT] As of YYYY-MM-DD HH:MM ET, producer run_id=<run_id> and context_sha256=<sha256> were already audited.`

Stop immediately. Do not use file creation time, modification time, filename
time, or report date as a freshness proxy.

If the `run_id` is unchanged but the context SHA differs, classify it as a
high-materiality `HARD_CONTRADICTION` because an immutable producer identity
was reused for different bytes. If the SHA is unchanged under a different
`run_id`, flag the unexplained duplicate as `UNRESOLVED`.

## 3. Evidence hierarchy and audit scope

- Repository market receipts and deterministic calculations are canonical for
  prices, strikes, expirations, breakevens, scope, and strategy state.
- Manifest-bound source packets are the producer's claimed external evidence.
  Re-fetch primary URLs independently before classifying their factual claims.
- Prefer SEC filings, issuer IR, official regulators and government agencies,
  exchanges, PJM, and the Federal Reserve.
- Never replace canonical values with weekend, delayed, or secondary
  aggregator quotes.
- Audit all claims for a new `run_id`. Delta-only review is allowed only when a
  prior validated manifest and critic receipt establish the unchanged bytes.
- VST and CEG must each retain exactly one `PJM_BRA_NEXT` catalyst with
  `confirmed: false` and a direct official PJM source until PJM publishes the
  exact date.

## 4. Classification standard

Classify every finding as exactly one of:

1. `HARD_CONTRADICTION`: directly comparable facts conflict for the same
   metric and as-of time, or immutable lineage is broken.
2. `UNSUPPORTED`: a factual claim lacks adequate underlying evidence.
3. `WEAK_INFERENCE`: evidence exists but does not strongly support the stated
   conclusion.
4. `UNRESOLVED`: evidence is incomplete, stale, or temporally mismatched.
5. `SUPPORTED`: canonical or independently fetched primary evidence directly
   verifies the claim.

Do not call a spot/strike difference, a crossed technical level, mixed catalyst
implications, or an irrelevant long-term price target a contradiction.

## 5. Options-risk and temporal standard

- Match every thesis and catalyst to the exact remaining life in the manifest's
  candidate ID.
- Treat theta, IV contraction, liquidity, bid/ask spread, and event volatility
  as risks unless measured empirical evidence is present.
- Label material assertions `Repo-verified`, `Test-verified`,
  `Official-source`, `Inference`, or `Assumption`.
- Never claim an option must gain or lose value.
- Never recommend an entry, exit, size, activation, or trade.

## 6. Required finding format

For each finding provide:

1. Symbol and exact claim
2. Classification
3. Producer run ID and context SHA
4. Claim timestamp and evidence timestamp
5. Canonical or primary evidence
6. Source URL and publication date
7. Classification rationale
8. Materiality (`High`, `Medium`, or `Low`)
9. Exact correction required

End with these exact headers:

- **Mandatory rule violations**
- **Hard contradictions**
- **Unsupported claims**
- **Weak inferences**
- **Temporal mismatches**
- **Missing primary evidence**
- **Correctly supported claims**
- **Items requiring owner review**

When an audit receipt is separately authorized, bind it to the exact
`producer_run_id` and `producer_context_sha256`. Never write a success-shaped
receipt for an unverified manifest.
