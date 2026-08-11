# VST Post-Earnings Analyst Review Design

**Date:** 2026-08-10
**Status:** OWNER-APPROVED DESIGN
**Scope:** Convert the committed VST Capital IQ provenance index into an
institutional-quality, source-verified post-earnings review and a governed
display-only project-improvement packet.
**Authority:** Research and documentation only. This design grants no ranking,
hypothesis, H7, ledger, backtest, position, sizing, order, or verdict authority.

## 1. Problem

Commit `06768aa` added
`reports/capitaliq/vst_2026-08-10-source-index.md`, a durable index for a
private Capital IQ capture of Vistra's 2026 Q2 materials. The index proves
which documents were captured and records their hashes, but it does not yet
answer the questions that matter to this project:

1. What changed in Vistra's operating performance, earnings quality, guidance,
   capital structure, and catalyst path?
2. Which changes strengthen, weaken, or leave unchanged the repository's
   existing VST research?
3. Which verified facts can safely improve display-only research context?
4. Which apparent facts are vendor-only, contradictory, non-comparable, or
   irrelevant to an options-validation platform?

The review must be useful at a senior Wall Street analyst's standard without
turning a proprietary source packet into canonical market data, a price target,
or a trading recommendation.

## 2. Decision

Build a governed analyst packet with two complementary outputs:

1. A polished HTML post-earnings review as the first-read human artifact.
2. A machine-readable claim matrix that makes every material fact,
   countercase, source, and project disposition auditable.

Do not wire the packet directly into the attractiveness dashboard during this
implementation. The review must first prove which claims are eligible for a
later display-only integration decision.

### Rejected alternatives

1. **Memo only.** Rejected because prose alone cannot provide reusable,
   testable claim lineage or enforce project-surface restrictions.
2. **Direct dashboard integration.** Rejected because source verification and
   claim adjudication must precede any consumer wiring.
3. **Full valuation or target-price model.** Rejected because the captured
   packet does not contain a complete primary-source forecast model, segment
   assumptions, or a sufficiently governed consensus history. Capital IQ
   estimates remain vendor-reported context.
4. **Full import of the equity-research 15-section workflow.** Rejected as
   unnecessary duplication. This repository needs a focused post-earnings
   delta review tied to its catalyst and options-research surfaces.

## 3. Inputs and source hierarchy

### 3.1 Tracked inputs

- `reports/capitaliq/vst_2026-08-10-source-index.md`
- `reports/2026-07-16-vst-ceg-earnings-footprints.md`
- `reports/2026-07-08-four-name-market-context-and-thesis.md`
- `reports/attractiveness_context/2026-07-24.json`
- The current VST-related configuration and display-only research contracts.

### 3.2 Private inputs

The licensed source package is currently stored outside Git at:

`/Users/carsynstephenson/Documents/Codex/2026-08-10/bas/outputs/capitaliq-vst-2026-08-10/`

The implementation may read the package's manifest, normalized snapshot, and
PDFs. It must not copy licensed PDFs or long proprietary excerpts into Git.
The two transcript PDFs have the same SHA-256 and count as one underlying
source. The one-page annual-report supplement placeholder is inadmissible as
substantive evidence.

### 3.3 Claim authority

Use sources in this order for material claims:

1. Direct SEC filing or issuer-hosted earnings material.
2. Direct market-operator or regulator material for PJM and regulatory facts.
3. Capital IQ for timestamped consensus, estimates, classifications, and other
   vendor-reported enrichment.
4. The Capital IQ transcript for management-language analysis when a direct
   issuer transcript is unavailable, labeled `vendor_transcript`.

Capital IQ is a discovery and delivery layer for filing facts, not the final
authority when the direct filing or issuer document is available.

## 4. Analytical architecture

### 4.1 Source-integrity pass

Before analysis:

- recompute and compare every available private-file hash with the manifest;
- select one canonical transcript and retain both document IDs in the source
  ledger under one independence group;
- exclude the placeholder annual-report supplement;
- reconcile the proxy page-date/filename discrepancy against EDGAR;
- record every unavailable, unreadable, mismatched, or non-substantive source.

A source-integrity failure blocks claims derived from that source but does not
force a success-shaped replacement from a weaker source.

### 4.2 Primary-source reconstruction

Obtain or identify the direct SEC/IR versions of the Q2 10-Q, earnings release,
and investor presentation. For each material fact, retain:

- issuer and ticker;
- reporting period and `known_as_of` date;
- metric or claim text;
- value and units when quantitative;
- GAAP, non-GAAP, management-guided, analyst-derived, or vendor-reported class;
- document ID, accession when applicable, URL, publication date, page or
  section locator, retrieval date, and local hash when retained;
- evidence classification and independence group.

No number may be compared across periods until its definition, units, and
accounting basis are shown to be comparable.

### 4.3 Analyst workstreams

The review covers these workstreams:

1. **Print versus bar:** reported results versus prior period, prior guidance,
   and timestamped Capital IQ consensus.
2. **Quality of earnings:** GAAP-to-adjusted bridge; commodity and hedge marks;
   taxes; impairments; restructuring; asset-sale effects; share-count effects;
   and any other non-recurring or below-the-line drivers.
3. **Operating drivers:** Retail, Texas, East, West, and Asset Closure segment
   changes; fleet availability; realized pricing or hedging disclosures; and
   generation or retail volume when disclosed.
4. **Guidance and estimates:** guidance changes, estimate direction, disclosed
   assumptions, and the difference between management facts and vendor
   consensus.
5. **Cash and credit:** operating cash flow, capital expenditure, free-cash-flow
   definitions, net debt, maturities, liquidity, ratings, buybacks,
   acquisitions, and material obligations.
6. **Catalysts:** PJM capacity auctions, nuclear and data-center PPAs, hedge
   roll-off, regulatory events, integration milestones, and management-provided
   dates. The mandatory unconfirmed `PJM_BRA_NEXT` catalyst remains intact
   until PJM publishes an exact schedule.
7. **Management credibility:** prior guidance versus delivery, changes in
   language, Q&A pressure points, disclosed uncertainty, and claims that cannot
   be independently verified.
8. **Read-through to existing research:** compare the new evidence with the
   VST/CEG earnings-footprint study, the existing VST thesis context, and the
   platform's event and descriptive research lanes.

### 4.4 Institutional judgment layer

The report must answer:

- Did the quarter change the existing VST thesis?
- Did the likely estimate direction change, and why?
- Was the headline result cleaner or lower quality than it appeared?
- Which operating or balance-sheet variable is now load-bearing?
- What evidence would falsify the leading interpretation?
- Which next event deserves monitoring, and what would be measured?
- What does the packet improve in this project without altering authority?

The report includes bull and bear interpretations but no price target, trade
recommendation, position sizing, or order instruction.

## 5. Prior-to-posterior and project disposition

### 5.1 Thesis ledger

Each thesis-relevant issue receives:

- prior belief;
- new evidence;
- posterior status: `STRENGTHENED`, `WEAKENED`, `UNCHANGED`, or `UNRESOLVED`;
- confidence and reason;
- next falsifier or proof point.

This is an evidence-change ledger, not a probability rewrite and not a
repository verdict.

### 5.2 Project disposition

Every claim receives exactly one disposition:

- `INTEGRATE`: verified and suitable for a named display-only surface;
- `RESEARCH_NEXT`: potentially useful but missing required evidence or
  comparability;
- `NO_CHANGE`: valid information already represented or immaterial to the
  project's declared surfaces;
- `REJECT`: duplicate, contradicted, non-substantive, prohibited, or
  analytically irrelevant.

An `INTEGRATE` disposition is a proposal, not permission to edit a consumer.
It must name one or more eligible surfaces and retain a non-empty list of
prohibited surfaces.

Eligible surfaces are limited to:

- event chronology;
- descriptive catalyst context;
- transcript-backed management commentary;
- future event-study research questions;
- display-only fundamental or risk context.

Prohibited surfaces include:

- `.cache/chains/` and canonical option-chain truth;
- H5/H6/H7/H8/H10 authority or evidence;
- rankings, Top-3 membership, triggers, thresholds, sizing, and FIRE logic;
- backtest inputs or verdicts;
- receipts, append-only ledgers, positions, paper books, or orders.

## 6. Deliverables

### 6.1 Hero artifact

Create:

`reports/capitaliq/vst_2026-08-10-analyst-review.html`

The HTML report contains:

- direct post-earnings conclusion and source posture;
- high-signal metric tiles that do not repeat the conclusion;
- print-versus-bar and guidance tables;
- quality-of-earnings bridge;
- operating and segment analysis;
- cash, leverage, and capital-allocation review;
- catalyst and management-credibility sections;
- transcript Q&A/debate map when source-supported;
- prior-to-posterior thesis ledger;
- project-disposition summary;
- counter-thesis, falsifiers, unresolved questions, and source ledger.

The report must be standalone and readable locally. It must not depend on
licensed PDFs being present after generation.

### 6.2 Audit artifact

Create:

`reports/capitaliq/vst_2026-08-10-claim-matrix.json`

Each claim object contains:

- `claim_id`
- `symbol`
- `topic`
- `claim_text`
- `period`
- `known_as_of`
- `value`
- `units`
- `accounting_basis`
- `source_id`
- `source_url`
- `source_kind`
- `source_tier`
- `document_date`
- `locator`
- `retrieved_at`
- `content_hash`
- `independence_group`
- `classification`
- `countercase`
- `thesis_effect`
- `confidence`
- `project_disposition`
- `eligible_surfaces`
- `prohibited_surfaces`
- `open_question`

Allowed `classification` values are `SUPPORTED`, `UNSUPPORTED`,
`WEAK_INFERENCE`, `UNRESOLVED`, and `HARD_CONTRADICTION`.

### 6.3 Integrity test

Create:

`tests/test_vst_capitaliq_review_packet.py`

The test verifies:

- the JSON parses and contains only VST claims;
- required fields and enumerations are present;
- every source ID and hash maps to the source ledger or a direct primary
  source record;
- byte-identical transcripts share one independence group;
- the placeholder annual-report supplement supports no substantive claim;
- every analytical claim has a countercase;
- every claim has exactly one project disposition;
- `INTEGRATE` claims name only eligible display surfaces;
- prohibited authority surfaces remain present and non-empty;
- no field attempts to encode a trade, ranking, trigger, size, order, or
  registered-hypothesis verdict.

### 6.4 Source-index linkage

Update:

`reports/capitaliq/vst_2026-08-10-source-index.md`

Add links to the completed HTML report and claim matrix while preserving the
existing `DISPLAY-ONLY` / `NOT VERDICT-ELIGIBLE` boundary.

## 7. Adversarial review sequence

The draft packet passes four ordered reviews:

1. **Number verifier:** recompute arithmetic; check period, units, and source
   locators; reject nonexistent or mismatched artifacts.
2. **Counter-thesis:** attack the leading interpretation using the same primary
   evidence; identify missing risks, inconsistent reasoning, and thesis-
   changing counterevidence.
3. **Citation spot-check:** verify every high-materiality claim and a sample of
   lower-materiality claims against the underlying source.
4. **Analyst adjudication:** mark each objection accepted, partially accepted,
   or rejected with an evidence-based reason; revise the packet before final
   validation.

No review step changes a project verdict or authority surface. The final HTML
summarizes material accepted objections and remaining limitations.

## 8. Failure behavior

- Conflicting filing and vendor figures become `UNRESOLVED` or
  `HARD_CONTRADICTION`; the implementation does not silently choose one.
- A missing primary locator blocks `SUPPORTED` classification for a material
  filing claim.
- Non-comparable periods, units, or accounting bases block quantitative
  comparison.
- Missing transcript evidence produces a visible limitation rather than an
  empty debate map.
- Missing or stale consensus is labeled and cannot be represented as current.
- Any consumer-wiring, ranking, trigger, H7, ledger, backtest, position, or
  verdict change is out of scope and must be removed from the diff.
- Licensed text is paraphrased. Long transcript passages or proprietary
  document reproduction are forbidden.
- An unreadable private package is a blocker for claims unique to it, not
  permission to fabricate or weaken provenance.

## 9. Validation

At minimum, run:

```bash
uv run python -m unittest tests.test_vst_capitaliq_review_packet
uv run ruff check tests/test_vst_capitaliq_review_packet.py
uv run pyright tests/test_vst_capitaliq_review_packet.py
git diff --check
```

Also inspect the HTML visually and verify that it contains no unresolved
authoring placeholders, broken local links, clipped tables, unreadable source
text, or unsupported readiness language.

The final evidence ledger must show:

- every material number's period, units, and source;
- every calculation's inputs and formula;
- every management claim as management-provided rather than independently
  established unless corroborated;
- every vendor estimate as timestamped vendor-reported enrichment;
- every data gap and unresolved conflict.

## 10. Completion criteria

The implementation is complete only when:

1. All private source hashes are reconciled or failures are recorded.
2. Material filing facts use direct SEC/IR authority where available.
3. Every material figure has source, period, locator, units, and accounting
   basis.
4. GAAP and non-GAAP measures are explicitly bridged or kept separate.
5. Every analytical conclusion has a countercase and falsifier.
6. The prior-to-posterior ledger states what changed and what did not.
7. Every claim has one project disposition.
8. The four-stage adversarial review is adjudicated.
9. The claim-matrix integrity test and applicable static checks pass.
10. The HTML renders cleanly and remains display-only.
11. The final diff changes no prohibited project surface.

## 11. Expected project value

This design improves the project by turning an inert source catalog into:

- a verified post-earnings understanding of a core name;
- a reusable claim-level evidence packet;
- a ranked list of safe display-only improvements;
- explicit research questions for future causal event studies;
- a record of rejected claims that prevents duplicate, vendor-led, or
  authority-leaking work later.

It does not claim that fundamental context predicts option returns. Any future
signal, ranking, or verdict use requires a separate registration and evidence
gate.
