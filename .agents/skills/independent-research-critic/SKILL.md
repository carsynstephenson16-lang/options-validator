---
name: independent-research-critic
description: Run AFTER research-refresh completes, or whenever a research report, deep-research output, or third-party analysis needs verification before it is trusted. Performs an independent research critic audit of the latest Codex research-refresh report in options-validator. Evaluates factual integrity, primary source support, temporal alignment, options risks, and catalyst claims without modifying the repository.
---

# Independent Research Critic Audit Skill

Scope: Audit the latest Codex research-refresh report and its cited sources against repository receipts, primary sources, and temporal rules. Remain strictly read-only: do not edit repository files, receipts, hypotheses, thresholds, strategy state, dashboards, or orders. Do not recommend trades or change any repository verdict.

## 1. Timing & Execution Requirements
- **Timezone:** Use `America/New_York` for every date, timestamp, and comparison.
- **Target File Locations:**
  - Latest Codex Report: `reports/YYYY-MM-DD-attractiveness-research-context.md`
  - Machine-Readable Context: `reports/attractiveness_context/YYYY-MM-DD.json`
  - Raw Work Packets: `.tmp/research_refresh/work/YYYY-MM-DD/*.json`
  - Prior Critic Receipts: `reports/attractiveness_critic/`
- **Timestamp Comparison & NO_NEW_INPUT Gate:**
  1. Inspect the creation/modified date of the latest Codex research-refresh report.
  2. Compare with the timestamp of the most recent Antigravity critic audit report.
  3. If `Codex Report Timestamp <= Prior Critic Report Timestamp`: Return a dated `NO_NEW_INPUT` receipt formatted as:
     `[NO_NEW_INPUT] As of YYYY-MM-DD HH:MM ET, no new Codex research-refresh report has been generated since the prior critic audit.`
     and stop execution immediately to conserve resources.
- **Delta Scope:** If a newer Codex report exists, audit only the information and claims that changed since the last verified report.

## 2. Source of Truth & Hierarchy
- **Repository Guidelines:** Read `AGENTS.md` before beginning every audit.
- **Canonical Data:** Repository market receipts and deterministic calculations are canonical for prices, strikes, expirations, breakevens, scope, and strategy state.
- **No Aggregator Overrides:** Do not replace canonical values with weekend, delayed, or secondary aggregator quotes (e.g. Yahoo, public.com, financecalendar.com).
- **Public Web Research:** Use public web research only for news, official SEC filings, catalysts, and external context.
- **Primary Sources:** Prefer SEC filings (10-K, 10-Q, 8-K), issuer Investor Relations announcements, official regulatory/government agencies, exchanges, PJM, and the Federal Reserve.
- **Issuer Release Flexibility:** A missing SEC filing is not automatically missing evidence if an authoritative issuer press release/IR announcement exists.
- **Mandatory PJM Catalyst Rule:** Preserve the mandatory PJM Base Residual Auction (BRA) catalyst entry for VST and CEG (`confirmed: false` with a PJM source link) until PJM officially confirms the schedule. Dropping this entry is a rule violation.

## 3. Classification Standard
Classify every finding strictly into exactly one of the following 5 categories:

1. **HARD_CONTRADICTION:** Two directly comparable facts conflict on the exact same metric and as-of time.
2. **UNSUPPORTED:** The report makes a factual claim without adequate underlying evidence.
3. **WEAK_INFERENCE:** Evidence exists, but it does not strongly support the stated conclusion.
4. **UNRESOLVED:** Available evidence is incomplete, stale, or temporally mismatched (e.g., market close date vs LLM capture date).
5. **SUPPORTED:** Primary or canonical evidence directly verifies the claim.

### What is NOT a Contradiction:
Do NOT classify something as a contradiction merely because:
- Spot price is currently below an option strike price;
- Spot price is below a previously crossed resistance level;
- A catalyst event has both positive and negative structural implications;
- A long-term sell-side analyst target has weak relevance to a short-dated option contract.

## 4. Options-Risk Standard
- **Remaining Life Matching:** Match every thesis argument and catalyst window directly to the option's actual remaining days to expiry.
- **Unmeasured Dynamics as Risks:** Treat theta decay, IV crush/contraction, liquidity, bid/ask spreads, and event-driven volatility as risks or expectations unless measured, empirical evidence is provided.
- **Evidence Labeling:** Explicitly label every important claim as one of:
  - `Repo-verified`
  - `Test-verified`
  - `Official-source`
  - `Inference`
  - `Assumption`
- **Certainty Limits:** Never claim IV will definitely fall or that an option contract must lose value.
- **No Trade Guidance:** Do not recommend trades, position sizing, entries, exits, or strategy activation.

## 5. Required Output Format

For every identified finding, provide:
1. **Symbol & Exact Claim:** (e.g. `NVDA: Technical breakout above $212`)
2. **Classification:** (`HARD_CONTRADICTION` | `UNSUPPORTED` | `WEAK_INFERENCE` | `UNRESOLVED` | `SUPPORTED`)
3. **Timestamps:** Claim timestamp vs. Evidence timestamp
4. **Canonical / Primary Evidence:** Exact values from repo receipts or primary filings
5. **Source URL & Publication Date:** Direct URL and date (if external)
6. **Classification Rationale:** Concise explanation of why the evidence supports this classification
7. **Materiality:** (`High` | `Medium` | `Low`)
8. **Exact Correction Required:** Clear instruction on what text or receipt field needs adjustment

### Summary Section (End of Report)
Conclude the audit report with bulleted lists under the following exact headers:
- **Mandatory rule violations**
- **Hard contradictions**
- **Unsupported claims**
- **Weak inferences**
- **Temporal mismatches**
- **Missing primary evidence**
- **Correctly supported claims**
- **Items requiring owner review**
