# VST Post-Earnings Analyst Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the committed VST Capital IQ source index into a primary-source-verified, institutional-quality post-earnings HTML review and an auditable claim matrix, without changing any ranking, hypothesis, backtest, ledger, position, or trading authority.

**Architecture:** Treat the JSON claim matrix as the evidence system of record and the standalone HTML report as a human-readable projection of adjudicated claims. Build in five gates: source integrity, primary-source reconstruction, analyst synthesis, adversarial review, and final boundary validation. Every gate fails closed at the affected claim rather than substituting weaker evidence.

**Tech Stack:** Python 3.12 standard library (`json`, `hashlib`, `pathlib`, `unittest`), static HTML/CSS, existing `uv`/Ruff/Pyright toolchain, PDF text extraction plus rendered-page visual inspection, direct SEC/issuer/PJM sources, and Git.

## Global Constraints

- Implement on the current `codex/attractive-exp-wiring` branch, which already contains source-index commit `06768aa` and approved-design commit `342c85d`. Before every task, confirm the Git root, branch, and worktree status.
- Do not commit licensed Capital IQ PDFs, extracted transcript text, private bundle paths, or long proprietary excerpts. The private package is read-only evidence at `/Users/carsynstephenson/Documents/Codex/2026-08-10/bas/outputs/capitaliq-vst-2026-08-10/`.
- Use direct SEC or Vistra investor-relations documents for material filing and issuer claims. Use Capital IQ only for timestamped vendor estimates, classifications, and transcript commentary not available from an issuer source.
- Treat the two byte-identical transcript files as one source independence group. Treat the one-page ARS placeholder as non-substantive.
- Preserve `DISPLAY-ONLY` and `NOT VERDICT-ELIGIBLE`. Do not edit option-chain data, H5/H6/H7/H8/H10 evidence, rankings, Top-3 logic, triggers, thresholds, sizing, FIRE logic, backtests, ledgers, positions, paper books, or order paths.
- Preserve the mandatory unconfirmed next-PJM-BRA catalyst. An exact date may be stated only when an official PJM source publishes it.
- Do not create a price target, rating, trade recommendation, valuation model, or prediction that fundamental context implies options edge.
- Apply test-driven development within every task: write the named failing assertion, run it and record the expected failure, make the smallest artifact change, rerun to green, then commit only the task's paths.
- Render and visually inspect source PDFs when page layout, table structure, footnotes, or GAAP/non-GAAP bridges matter. Text extraction alone is not layout evidence.
- Use retrieval timestamps in UTC and dates in ISO 8601. Preserve the period and accounting basis on every quantitative claim.

---

## Task 1: Establish the source-integrity contract and seed evidence ledger

**Files:**

- Create: `tests/test_vst_capitaliq_review_packet.py`
- Create: `reports/capitaliq/vst_2026-08-10-claim-matrix.json`
- Read: `reports/capitaliq/vst_2026-08-10-source-index.md`
- Read privately: `.../capitaliq-vst-2026-08-10/manifest.json`
- Read privately: `.../capitaliq-vst-2026-08-10/normalized_snapshot.json`

### Step 1.1: Confirm the isolated scope

- [ ] Run:

```bash
git rev-parse --show-toplevel
git branch --show-current
git status --short
```

- [ ] Stop if the root is not `/Users/carsynstephenson/options-validator`, the branch is not `codex/attractive-exp-wiring`, or unexpected changes overlap the four planned deliverables.

### Step 1.2: Write the failing schema and boundary tests

- [ ] Create `tests/test_vst_capitaliq_review_packet.py` with a loader and the first contract tests:

```python
from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = ROOT / "reports/capitaliq/vst_2026-08-10-claim-matrix.json"
HTML_PATH = ROOT / "reports/capitaliq/vst_2026-08-10-analyst-review.html"
INDEX_PATH = ROOT / "reports/capitaliq/vst_2026-08-10-source-index.md"

REQUIRED_CLAIM_FIELDS = {
    "claim_id", "symbol", "topic", "claim_text", "period", "known_as_of",
    "value", "units", "accounting_basis", "source_id", "source_url",
    "source_kind", "source_tier", "document_date", "locator", "retrieved_at",
    "content_hash", "independence_group", "classification", "countercase",
    "thesis_effect", "confidence", "project_disposition", "eligible_surfaces",
    "prohibited_surfaces", "open_question",
}
CLASSIFICATIONS = {
    "SUPPORTED", "UNSUPPORTED", "WEAK_INFERENCE", "UNRESOLVED",
    "HARD_CONTRADICTION",
}
THESIS_EFFECTS = {"STRENGTHENED", "WEAKENED", "UNCHANGED", "UNRESOLVED"}
DISPOSITIONS = {"INTEGRATE", "RESEARCH_NEXT", "NO_CHANGE", "REJECT"}
ELIGIBLE_SURFACES = {
    "event_chronology",
    "descriptive_catalyst_context",
    "transcript_backed_management_commentary",
    "future_event_study_research_questions",
    "display_only_fundamental_risk_context",
}
REQUIRED_PROHIBITED_SURFACES = {
    "option_chain_truth", "registered_hypotheses", "ranking_and_top3",
    "triggers_thresholds_sizing_fire", "backtests_and_verdicts",
    "ledgers_positions_books_orders",
}


def load_matrix() -> dict[str, Any]:
    return json.loads(MATRIX_PATH.read_text(encoding="utf-8"))


class VstCapitalIqReviewPacketTests(unittest.TestCase):
    def test_claim_matrix_has_governed_shape(self) -> None:
        matrix = load_matrix()
        self.assertEqual(matrix["schema_version"], "vst_analyst_review/v1")
        self.assertEqual(matrix["symbol"], "VST")
        self.assertEqual(matrix["authority"], "DISPLAY_ONLY_NOT_VERDICT_ELIGIBLE")
        self.assertTrue(matrix["sources"])
        self.assertTrue(matrix["claims"])

        source_ids = {source["source_id"] for source in matrix["sources"]}
        for claim in matrix["claims"]:
            self.assertEqual(set(claim), REQUIRED_CLAIM_FIELDS)
            self.assertEqual(claim["symbol"], "VST")
            self.assertIn(claim["classification"], CLASSIFICATIONS)
            self.assertIn(claim["thesis_effect"], THESIS_EFFECTS)
            self.assertIn(claim["project_disposition"], DISPOSITIONS)
            self.assertIn(claim["source_id"], source_ids)
            self.assertTrue(claim["countercase"].strip())
            self.assertEqual(
                set(claim["prohibited_surfaces"]), REQUIRED_PROHIBITED_SURFACES
            )
            self.assertLessEqual(set(claim["eligible_surfaces"]), ELIGIBLE_SURFACES)
            if claim["project_disposition"] == "INTEGRATE":
                self.assertTrue(claim["eligible_surfaces"])

    def test_source_hashes_and_independence_are_honest(self) -> None:
        matrix = load_matrix()
        sources = {source["source_id"]: source for source in matrix["sources"]}
        for claim in matrix["claims"]:
            source = sources[claim["source_id"]]
            self.assertEqual(claim["content_hash"], source["content_hash"])
            self.assertEqual(
                claim["independence_group"], source["independence_group"]
            )
            self.assertRegex(claim["content_hash"], r"^[0-9a-f]{64}$")

        transcript_sources = [
            source for source in matrix["sources"]
            if source["source_id"] in {"ciq-264714280", "ciq-264711362"}
        ]
        self.assertEqual(len(transcript_sources), 2)
        self.assertEqual(
            {source["content_hash"] for source in transcript_sources},
            {"8fda0034988d1a68a5138d2e9cea4f653c23cf5166d6e9de3cf132b0364a87cb"},
        )
        self.assertEqual(
            len({source["independence_group"] for source in transcript_sources}), 1
        )

    def test_placeholder_is_not_substantive_evidence(self) -> None:
        matrix = load_matrix()
        placeholder = next(
            source for source in matrix["sources"]
            if source["source_id"] == "ciq-256990518"
        )
        self.assertFalse(placeholder["substantive"])
        substantive_claims = [
            claim for claim in matrix["claims"]
            if claim["source_id"] == placeholder["source_id"]
            and claim["topic"] != "source_integrity"
        ]
        self.assertEqual(substantive_claims, [])

    def test_committed_artifacts_do_not_expose_private_paths(self) -> None:
        text = MATRIX_PATH.read_text(encoding="utf-8")
        self.assertNotIn("/Users/", text)
        self.assertNotIn("Documents/Codex", text)
```

- [ ] Run the single test module and confirm it fails because the matrix does not yet exist:

```bash
uv run python -m unittest tests.test_vst_capitaliq_review_packet
```

Expected failure: `FileNotFoundError` for the claim-matrix path. A syntax or import failure is not the intended red state.

### Step 1.3: Reconcile the private package without committing it

- [ ] Read the private manifest and normalized snapshot. Recompute every raw-document SHA-256 and compare it with the manifest and source index.
- [ ] Render at least page 1 of every PDF under a temporary directory such as `/private/tmp/vst-review-source-check/`; inspect all one-page or suspicious documents visually.
- [ ] Record these outcomes in the matrix source ledger:
  - the two transcript IDs have the same hash and independence group;
  - one transcript is canonical and the other is marked duplicate;
  - ARS document `256990518` is non-substantive;
  - the DEF 14A page-date/filename conflict remains explicitly recorded;
  - every unreadable or mismatched source is blocked rather than silently accepted.
- [ ] Do not include absolute private paths in the JSON. Use the Capital IQ viewer URL already present in the tracked source index.

### Step 1.4: Add the smallest green claim matrix

- [ ] Create JSON with these top-level keys:

```json
{
  "schema_version": "vst_analyst_review/v1",
  "symbol": "VST",
  "company": "Vistra Corp.",
  "as_of": "2026-08-10",
  "authority": "DISPLAY_ONLY_NOT_VERDICT_ELIGIBLE",
  "source_posture": "Primary sources control material filing facts; Capital IQ is vendor enrichment.",
  "sources": [],
  "claims": [],
  "thesis_ledger": [],
  "review": {}
}
```

- [ ] Seed exactly the source-integrity evidence needed for this gate. Add one `SUPPORTED` / `REJECT` claim explaining the transcript duplication and one `SUPPORTED` / `REJECT` claim explaining why the ARS placeholder cannot support substantive analysis. Populate every required field; use `null` only for genuinely non-quantitative `value` and `units`.
- [ ] For every claim, copy the complete required prohibited-surface list. Keep `eligible_surfaces` empty on `REJECT` claims.

### Step 1.5: Verify and commit the integrity foundation

- [ ] Run:

```bash
uv run python -m unittest tests.test_vst_capitaliq_review_packet
uv run ruff check tests/test_vst_capitaliq_review_packet.py
uv run pyright tests/test_vst_capitaliq_review_packet.py
git diff --check
```

- [ ] Inspect the staged diff for private-path or licensed-text leakage, then commit only the two task files:

```bash
git add tests/test_vst_capitaliq_review_packet.py reports/capitaliq/vst_2026-08-10-claim-matrix.json
git diff --cached --check
git commit -m "test(research): establish VST review evidence contract"
```

---

## Task 2: Reconstruct primary evidence and complete the claim matrix

**Files:**

- Modify: `tests/test_vst_capitaliq_review_packet.py`
- Modify: `reports/capitaliq/vst_2026-08-10-claim-matrix.json`
- Read: `reports/2026-07-16-vst-ceg-earnings-footprints.md`
- Read: `reports/2026-07-08-four-name-market-context-and-thesis.md`
- Read: `reports/attractiveness_context/2026-07-24.json`
- Read privately: the 10-Q, earnings release, investor presentation, and canonical transcript PDFs

### Step 2.1: Add failing analytical-completeness tests

- [ ] Extend the test module with explicit topic, primary-authority, comparability, and catalyst rules:

```python
REQUIRED_ANALYST_TOPICS = {
    "source_integrity", "print_vs_bar", "earnings_quality",
    "operating_drivers", "guidance_estimates", "cash_credit", "catalysts",
    "management_credibility", "project_readthrough",
}
PRIMARY_TIERS = {"sec_filing", "issuer_ir", "market_operator", "regulator"}


    def test_all_analyst_workstreams_are_covered(self) -> None:
        claims = load_matrix()["claims"]
        self.assertEqual(
            {claim["topic"] for claim in claims}, REQUIRED_ANALYST_TOPICS
        )

    def test_supported_material_facts_have_primary_locators(self) -> None:
        for claim in load_matrix()["claims"]:
            if claim["classification"] == "SUPPORTED" and claim["topic"] not in {
                "source_integrity", "guidance_estimates", "management_credibility"
            }:
                self.assertIn(claim["source_tier"], PRIMARY_TIERS)
                self.assertTrue(claim["source_url"].startswith("https://"))
                self.assertTrue(claim["locator"].strip())
                self.assertTrue(claim["period"].strip())
                self.assertTrue(claim["accounting_basis"].strip())

    def test_quantitative_claims_are_comparable_or_explicitly_unresolved(self) -> None:
        for claim in load_matrix()["claims"]:
            if claim["value"] is not None:
                self.assertIsNotNone(claim["units"])
                self.assertTrue(claim["period"].strip())
                self.assertTrue(claim["accounting_basis"].strip())
            if claim["classification"] in {"UNRESOLVED", "HARD_CONTRADICTION"}:
                self.assertTrue(claim["open_question"].strip())

    def test_next_pjm_bra_remains_unconfirmed_official_context(self) -> None:
        claims = load_matrix()["claims"]
        pjm = next(
            claim for claim in claims if claim["claim_id"] == "PJM_BRA_NEXT"
        )
        self.assertEqual(pjm["topic"], "catalysts")
        self.assertEqual(pjm["source_tier"], "market_operator")
        self.assertIsNone(pjm["value"])
        self.assertEqual(pjm["classification"], "SUPPORTED")
        self.assertIn("exact date", pjm["open_question"].lower())
        self.assertEqual(pjm["thesis_effect"], "UNCHANGED")
```

- [ ] Run the module and confirm the new failures are missing workstream coverage and missing `PJM_BRA_NEXT`, not defects in the Task 1 contract.

### Step 2.2: Resolve direct SEC and issuer sources

- [ ] Use SEC submissions for CIK `0001692819` to identify, rather than guess, the Q2 2026 10-Q and the earnings-related 8-K accession and primary document. Retain the direct filing URL, accession, form, filing date, period, locator, retrieval time, and capture hash.
- [ ] Resolve the direct Vistra IR earnings release and investor presentation. If an issuer document is unavailable, record the failed lookup and keep the related claim below `SUPPORTED`; do not promote the Capital IQ copy to primary authority.
- [ ] Use a descriptive SEC User-Agent for automated access. If the environment lacks one, use interactive/public retrieval or stop the automated fetch; do not spoof a browser or bypass SEC controls.
- [ ] Resolve the current official PJM capacity-market or tariff source. Keep `PJM_BRA_NEXT` unconfirmed unless that source publishes an exact date.
- [ ] Store only URLs, metadata, hashes, locators, and paraphrased claims in Git. Keep downloaded primary files temporary or private.

### Step 2.3: Build the number and definition ledger before drawing conclusions

- [ ] Extract the following candidate facts from primary documents and include only those that pass period/unit/basis checks:
  - revenue and GAAP net income;
  - Adjusted EBITDA and its disclosed reconciliation;
  - operating cash flow, capital expenditures, and management-defined free cash flow;
  - cash, debt, net-debt definition, liquidity, maturities, and credit actions;
  - share count and buybacks;
  - segment results for Retail, Texas, East, West, and Asset Closure where disclosed;
  - guidance range, midpoint, prior range, and definition;
  - material acquisition, PPA, nuclear, data-center, regulatory, or hedge disclosures;
  - timestamped Capital IQ consensus or estimates only when the snapshot establishes the as-of date and exact measure definition.
- [ ] For every calculated delta, add input claims first and record the formula in the derived claim's `accounting_basis` or `claim_text`. Recompute arithmetic independently.
- [ ] Do not compare GAAP with adjusted, quarterly with LTM, point-in-time balance-sheet with flow metrics, or differently defined free-cash-flow measures. Mark unresolved comparisons `UNRESOLVED` with a specific open question.
- [ ] Label management claims as management-provided unless corroborated. Label consensus and estimate values as vendor-reported and timestamped.

### Step 2.4: Complete the eight analyst workstreams

- [ ] Add sufficient claims to cover all required topics. Each analytical claim must include:
  - a concise factual or inferential statement;
  - a source locator and independence group;
  - the strongest evidence classification it actually supports;
  - the strongest plausible countercase using the same evidence base;
  - prior-to-posterior thesis effect and confidence;
  - one project disposition;
  - eligible and prohibited surfaces;
  - a concrete falsifier or open question.
- [ ] Populate `thesis_ledger` with objects containing `issue`, `prior_belief`, `new_evidence`, `posterior_status`, `confidence`, and `next_falsifier`. Every ledger item must map to at least one `claim_id`.
- [ ] Compare against the existing VST/CEG earnings-footprint and four-name thesis reports. Do not rewrite their conclusions; state what the new quarter strengthens, weakens, leaves unchanged, or cannot resolve.
- [ ] Use `INTEGRATE` only as a proposal for one of the five allowed display-only surfaces. Use `RESEARCH_NEXT` for promising but incomplete context, `NO_CHANGE` for already represented or immaterial facts, and `REJECT` for duplicates, prohibited uses, or analytically invalid evidence.

### Step 2.5: Validate the evidence ledger and commit

- [ ] Run:

```bash
uv run python -m unittest tests.test_vst_capitaliq_review_packet
uv run ruff check tests/test_vst_capitaliq_review_packet.py
uv run pyright tests/test_vst_capitaliq_review_packet.py
python -m json.tool reports/capitaliq/vst_2026-08-10-claim-matrix.json >/dev/null
git diff --check
```

- [ ] Manually spot-check every high-materiality number and at least one claim per topic against the rendered source page.
- [ ] Commit only the matrix and its tests:

```bash
git add tests/test_vst_capitaliq_review_packet.py reports/capitaliq/vst_2026-08-10-claim-matrix.json
git diff --cached --check
git commit -m "feat(research): build VST post-earnings claim matrix"
```

---

## Task 3: Project the adjudicable evidence into a standalone analyst report

**Files:**

- Modify: `tests/test_vst_capitaliq_review_packet.py`
- Create: `reports/capitaliq/vst_2026-08-10-analyst-review.html`
- Read for style only: `reports/crwv_options_review/2026-07-28/crwv_options_review.html`
- Read as content authority: `reports/capitaliq/vst_2026-08-10-claim-matrix.json`

### Step 3.1: Add failing HTML structure and authority tests

- [ ] Add tests that require a portable report and forbid authority leakage:

```python
REQUIRED_HTML_SECTIONS = {
    "source-posture", "print-vs-bar", "earnings-quality", "operating-drivers",
    "guidance-estimates", "cash-credit", "catalysts", "management-credibility",
    "debate-map", "thesis-ledger", "project-disposition", "counter-thesis",
    "open-questions", "source-ledger",
}


    def test_html_is_standalone_and_complete(self) -> None:
        html = HTML_PATH.read_text(encoding="utf-8")
        self.assertIn("DISPLAY-ONLY / NOT VERDICT-ELIGIBLE", html)
        self.assertIn("Content-Security-Policy", html)
        self.assertNotRegex(
            html, r'<(?:script|link)[^>]+(?:src|href)=["\']https?://'
        )
        for section_id in REQUIRED_HTML_SECTIONS:
            self.assertIn(f'id="{section_id}"', html)

    def test_html_contains_no_authoring_markers_or_investment_action(self) -> None:
        html = HTML_PATH.read_text(encoding="utf-8")
        for marker in ("TODO", "TBD", "PLACEHOLDER", "LOREM IPSUM"):
            self.assertNotIn(marker, html.upper())
        for forbidden in (
            "price target", "buy rating", "sell rating", "trade recommendation",
            "position sizing", "fire signal",
        ):
            self.assertNotIn(forbidden, html.lower())

    def test_html_links_every_source_used_by_supported_claims(self) -> None:
        html = HTML_PATH.read_text(encoding="utf-8")
        supported_urls = {
            claim["source_url"] for claim in load_matrix()["claims"]
            if claim["classification"] == "SUPPORTED"
        }
        for url in supported_urls:
            self.assertIn(url, html)
```

- [ ] Run the test and confirm the new failure is the missing HTML file.

### Step 3.2: Build the report from the matrix, not from memory

- [ ] Create one standalone HTML file with embedded CSS, a restrictive meta CSP, semantic tables, responsive small-screen behavior, print styles, visible focus states, and no external JavaScript, fonts, stylesheets, images, or analytics.
- [ ] Use the existing CRWV report only as a visual-quality precedent. Do not copy its options conclusions or authority language.
- [ ] Every displayed fact must map to a claim in the matrix. Display claim IDs or source markers near tables and retain a linked source ledger at the bottom.
- [ ] Lead with a one-paragraph post-earnings conclusion that distinguishes verified facts, supported inference, unresolved issues, and vendor context.
- [ ] Limit the header to four to six non-duplicative metric tiles. Show periods and accounting basis directly on each tile.
- [ ] Implement every required section ID. Include:
  - print versus prior period, prior guidance, and timestamped consensus;
  - GAAP-to-adjusted quality bridge and non-recurring drivers;
  - operating and segment drivers;
  - guidance and estimate direction without a valuation conclusion;
  - cash, leverage, liquidity, capital allocation, and obligations;
  - catalyst chronology including unconfirmed `PJM_BRA_NEXT`;
  - management credibility and the distinction between claims and corroborated facts;
  - transcript Q&A/debate map or a visible evidence limitation;
  - prior-to-posterior thesis ledger;
  - `INTEGRATE` / `RESEARCH_NEXT` / `NO_CHANGE` / `REJECT` project summary;
  - counter-thesis, falsifiers, unresolved questions, and complete source ledger.
- [ ] Use short paraphrases only. Do not reproduce transcript passages or tables from licensed documents.

### Step 3.3: Reconcile the report against the machine ledger

- [ ] Check every metric, date, range, delta, and source marker in HTML against the JSON.
- [ ] If HTML needs a fact absent from JSON, add and validate the claim in JSON first; never create an HTML-only fact.
- [ ] If the matrix contains a material accepted fact omitted from the report, either add it or explain the omission in the report's scope note.

### Step 3.4: Run structural checks and commit

- [ ] Run:

```bash
uv run python -m unittest tests.test_vst_capitaliq_review_packet
uv run ruff check tests/test_vst_capitaliq_review_packet.py
uv run pyright tests/test_vst_capitaliq_review_packet.py
git diff --check
```

- [ ] Commit the HTML, matrix changes if any, and tests:

```bash
git add reports/capitaliq/vst_2026-08-10-analyst-review.html reports/capitaliq/vst_2026-08-10-claim-matrix.json tests/test_vst_capitaliq_review_packet.py
git diff --cached --check
git commit -m "feat(report): render VST institutional earnings review"
```

---

## Task 4: Execute and adjudicate the four-stage adversarial review

**Files:**

- Modify: `tests/test_vst_capitaliq_review_packet.py`
- Modify: `reports/capitaliq/vst_2026-08-10-claim-matrix.json`
- Modify: `reports/capitaliq/vst_2026-08-10-analyst-review.html`

### Step 4.1: Add a failing review-completeness test

- [ ] Require all four reviews, actual findings, and explicit adjudication:

```python
REVIEW_STAGES = {
    "number_verifier", "counter_thesis", "citation_spotcheck",
    "analyst_adjudication",
}
ADJUDICATIONS = {"ACCEPTED", "PARTIALLY_ACCEPTED", "REJECTED"}


    def test_adversarial_reviews_are_completed_and_adjudicated(self) -> None:
        review = load_matrix()["review"]
        self.assertEqual(set(review), REVIEW_STAGES)
        for stage_name in REVIEW_STAGES - {"analyst_adjudication"}:
            stage = review[stage_name]
            self.assertEqual(stage["status"], "COMPLETE")
            self.assertTrue(stage["reviewed_at"])
            self.assertTrue(stage["method"].strip())
            self.assertTrue(stage["findings"])
        adjudication = review["analyst_adjudication"]
        self.assertEqual(adjudication["status"], "COMPLETE")
        self.assertTrue(adjudication["decisions"])
        for decision in adjudication["decisions"]:
            self.assertIn(decision["outcome"], ADJUDICATIONS)
            self.assertTrue(decision["reason"].strip())
            self.assertTrue(decision["affected_claim_ids"])
```

- [ ] Run the test and confirm it fails because the review object is incomplete.

### Step 4.2: Perform the number-verifier pass

- [ ] Recalculate every displayed change, midpoint, sum, and bridge from primary inputs.
- [ ] Check periods, units, signs, GAAP/non-GAAP labels, footnotes, and share-count dates.
- [ ] Check every locator against the rendered PDF page or direct HTML section.
- [ ] Record findings even if no arithmetic defect is found. A clean review must state what was recomputed and the sample size.
- [ ] Change affected claim classifications to `UNRESOLVED` or `HARD_CONTRADICTION` when the evidence does not reconcile.

### Step 4.3: Perform the counter-thesis pass

- [ ] Attack the leading interpretation using the same primary evidence. Test at least:
  - whether adjusted results mask weaker GAAP economics;
  - whether guidance support depends on marks, hedges, commodity prices, acquisitions, or non-recurring items;
  - whether cash generation is reduced by capital intensity, obligations, or working-capital timing;
  - whether leverage, buybacks, acquisitions, or commitments weaken flexibility;
  - whether claimed data-center, nuclear, or PJM upside is timing-uncertain or already reflected in expectations;
  - whether management credibility conclusions overstate evidence from one quarter.
- [ ] Record the strongest counterevidence, not a ceremonial bear paragraph. Add missing claims or revise thesis effects where warranted.

### Step 4.4: Perform citation spot-check and analyst adjudication

- [ ] Verify 100% of high-materiality claims and at least one lower-materiality claim per topic against source and locator.
- [ ] For each review finding, mark `ACCEPTED`, `PARTIALLY_ACCEPTED`, or `REJECTED`, cite affected claim IDs, explain the evidence-based reason, and record the resulting change.
- [ ] Update the HTML to summarize material accepted objections and remaining limitations. Do not hide unresolved contradictions in footnotes.
- [ ] Ensure the revised HTML remains a projection of the revised matrix.

### Step 4.5: Validate and commit the reviewed packet

- [ ] Run:

```bash
uv run python -m unittest tests.test_vst_capitaliq_review_packet
uv run ruff check tests/test_vst_capitaliq_review_packet.py
uv run pyright tests/test_vst_capitaliq_review_packet.py
python -m json.tool reports/capitaliq/vst_2026-08-10-claim-matrix.json >/dev/null
git diff --check
```

- [ ] Commit the adjudicated artifacts and contract:

```bash
git add reports/capitaliq/vst_2026-08-10-analyst-review.html reports/capitaliq/vst_2026-08-10-claim-matrix.json tests/test_vst_capitaliq_review_packet.py
git diff --cached --check
git commit -m "review(research): adjudicate VST earnings evidence"
```

---

## Task 5: Link the packet, visually verify it, and prove scope containment

**Files:**

- Modify: `tests/test_vst_capitaliq_review_packet.py`
- Modify: `reports/capitaliq/vst_2026-08-10-source-index.md`
- Verify: `reports/capitaliq/vst_2026-08-10-analyst-review.html`
- Verify: `reports/capitaliq/vst_2026-08-10-claim-matrix.json`

### Step 5.1: Add the final failing linkage and scope tests

- [ ] Add tests for source-index links and retained boundary language:

```python
    def test_source_index_links_outputs_and_retains_boundary(self) -> None:
        index = INDEX_PATH.read_text(encoding="utf-8")
        self.assertIn("vst_2026-08-10-analyst-review.html", index)
        self.assertIn("vst_2026-08-10-claim-matrix.json", index)
        self.assertIn("display-only", index.lower())
        self.assertIn("not verdict-eligible", index.lower())

    def test_packet_has_no_machine_local_links(self) -> None:
        for path in (MATRIX_PATH, HTML_PATH, INDEX_PATH):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("file://", text)
            self.assertNotIn("/Users/", text)
```

- [ ] Run the test and confirm it fails on the missing source-index links.

### Step 5.2: Add source-index linkage without changing its authority

- [ ] Add a short `Reviewed outputs` section linking the HTML and JSON with relative Markdown links.
- [ ] State that the analyst review proposes display-only dispositions but does not authorize consumer wiring.
- [ ] Preserve the existing raw-document policy, no-options-evidence statement, and `DISPLAY-ONLY` / `NOT VERDICT-ELIGIBLE` language.

### Step 5.3: Run the affected-scope suite

- [ ] Run the packet checks plus the existing display-only context contracts:

```bash
uv run python -m unittest \
  tests.test_vst_capitaliq_review_packet \
  tests.test_top3_context \
  tests.test_research_context_assemble
uv run ruff check tests/test_vst_capitaliq_review_packet.py
uv run ruff format --check tests/test_vst_capitaliq_review_packet.py
uv run pyright tests/test_vst_capitaliq_review_packet.py
python -m json.tool reports/capitaliq/vst_2026-08-10-claim-matrix.json >/dev/null
git diff --check
```

- [ ] If an existing context test fails, determine whether the packet accidentally crossed an authority boundary. Do not weaken existing guards to make the new packet pass.

### Step 5.4: Perform local HTML visual QA

- [ ] Render the local file in a headless browser at desktop and mobile widths. Capture top-of-page and full-page screenshots with the installed Playwright CLI:

```bash
mkdir -p /private/tmp/vst-review-visual
playwright-cli -s=vst-review open file:///Users/carsynstephenson/options-validator/reports/capitaliq/vst_2026-08-10-analyst-review.html
playwright-cli -s=vst-review resize 1440 1000
playwright-cli -s=vst-review screenshot --filename /private/tmp/vst-review-visual/desktop-top.png
playwright-cli -s=vst-review screenshot --full-page --filename /private/tmp/vst-review-visual/desktop-full.png
playwright-cli -s=vst-review eval '() => ({scrollWidth: document.documentElement.scrollWidth, clientWidth: document.documentElement.clientWidth})'
playwright-cli -s=vst-review resize 390 844
playwright-cli -s=vst-review screenshot --filename /private/tmp/vst-review-visual/mobile-top.png
playwright-cli -s=vst-review screenshot --full-page --filename /private/tmp/vst-review-visual/mobile-full.png
playwright-cli -s=vst-review eval '() => ({scrollWidth: document.documentElement.scrollWidth, clientWidth: document.documentElement.clientWidth})'
playwright-cli -s=vst-review close
```

- [ ] Require `scrollWidth == clientWidth` at both sizes. Inspect all four screenshots with an image viewer.
- [ ] Inspect screenshots for clipped tables, overlapping cards, unreadable source text, missing hierarchy, broken anchors, poor contrast, and horizontal overflow.
- [ ] Open every internal anchor and a representative sample of external source links. Network-unavailable external links may be recorded as unchecked, but malformed URLs are failures.
- [ ] Search the visible report and raw HTML for authoring markers, unsupported readiness language, duplicated conclusions, and accidental proprietary excerpts.
- [ ] Re-run the test module after every visual correction.

### Step 5.5: Prove that no prohibited surface changed

- [ ] Review the complete branch diff from the parent of the VST source commit:

```bash
git diff --name-status 06768aa^..HEAD
git diff --stat 06768aa^..HEAD
git status --short
```

- [ ] The only implementation paths after the approved design and plan must be:
  - `reports/capitaliq/vst_2026-08-10-source-index.md`
  - `reports/capitaliq/vst_2026-08-10-claim-matrix.json`
  - `reports/capitaliq/vst_2026-08-10-analyst-review.html`
  - `tests/test_vst_capitaliq_review_packet.py`
- [ ] If any option data, hypothesis evidence, ranking, trigger, backtest, ledger, position, book, or order path appears, remove that out-of-scope change before completion.

### Step 5.6: Commit and perform final verification

- [ ] Commit the linkage and final test changes:

```bash
git add reports/capitaliq/vst_2026-08-10-source-index.md tests/test_vst_capitaliq_review_packet.py
git diff --cached --check
git commit -m "docs(research): link governed VST analyst packet"
```

- [ ] Re-run the full Task 5 validation commands from a clean worktree.
- [ ] Inspect `git log --oneline -7` and `git status --short`. Completion requires a clean worktree and direct green output from the final checks.
- [ ] Report the final handoff in the repository's required format: verdict, evidence reviewed, changes by file, exact validation results, remaining risks, unsupported assumptions, and ready/not-ready decision.

## Completion Gate

The work is ready only when all of the following are true:

- [ ] Every private source hash is reconciled or its failure is recorded.
- [ ] Material filing facts use direct SEC/IR authority where available.
- [ ] Every material figure carries period, units, accounting basis, source, and locator.
- [ ] GAAP and non-GAAP measures are bridged or explicitly kept separate.
- [ ] Every analytical claim has a countercase and falsifier/open question.
- [ ] The thesis ledger states what strengthened, weakened, stayed unchanged, or remains unresolved.
- [ ] Every claim has exactly one project disposition and a complete prohibited-surface list.
- [ ] The four adversarial stages are complete and every objection is adjudicated.
- [ ] The HTML is visually clean, standalone, and contains no proprietary reproduction.
- [ ] The source index links both outputs and retains its authority boundary.
- [ ] Targeted and adjacent display-only tests, Ruff, formatting, Pyright, JSON parsing, and diff checks pass.
- [ ] The final diff touches no prohibited project surface.
