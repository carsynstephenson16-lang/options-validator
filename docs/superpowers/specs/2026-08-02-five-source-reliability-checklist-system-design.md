# Five-Source Research Reliability Checklist System Design

**Date:** 2026-08-02

**Status:** owner-approved design

**Coordinating repository:** Options Validator

**Coordinating branch:** `sfix`

**Base:** `f6b5aa25f92d520ea29a682b89c945c3dfa6f740`

## 1. Objective

Build a source-faithful, auditable checklist system from five established ML
and research-reliability references, then integrate the applicable controls
into four repositories without creating a shared production dependency or
changing their authority boundaries:

1. Kalshi weather bot (`/Users/carsynstephenson/Claude`)
2. Options Validator (`/Users/carsynstephenson/options-validator`)
3. Equity Research (`/Users/carsynstephenson/equity-research`)
4. Sunwest lead engine
   (`/Users/carsynstephenson/Documents/Codex/sunwest-lead-engine`)

The five sources are:

1. Google, *Rules of Machine Learning*
2. Breck et al., *Data Validation for Machine Learning*
3. Breck et al., *What's Your ML Test Score?*
4. Sculley et al., *Hidden Technical Debt in Machine Learning Systems*
5. Eugene Yan, *How to Test Machine Learning Code and Systems*

The result is a portfolio reliability control plane, not an MLOps platform.
It identifies what is already enforced, what is manual, what is merely
advisory, what does not apply, and what is a verified gap. It does not install
model registries, experiment trackers, hosted monitoring services, paid APIs,
or another database.

## 2. Success criteria

The design is successful only if all of the following are true:

1. All five references have a pinned source manifest and reproducible source
   identity.
2. Every explicitly enumerated source item is accounted for exactly once in
   the canonical inventory.
3. Every locally derived control from narrative prose has an exact section or
   page locator and is labeled `derived_control`.
4. Every applicable source item has a project status, evidence or a gap, an
   owner, and a last-reviewed state.
5. Duplicate source items map to one local control rather than producing
   duplicate validators.
6. No repository imports code from another repository at runtime.
7. Normal audit and CI commands are offline, deterministic, credential-free,
   and side-effect-free.
8. New findings begin advisory-only. Existing fail-closed repository rules
   retain their current enforcement.
9. No checklist can authorize trading, alter a research conclusion, make an
   outreach decision, or weaken privacy, retention, consent, or compliance
   policy.
10. Existing test, lint, type, integrity, and verification gates continue to
    pass after integration.

## 3. Non-goals

This work does not:

- train or deploy a model;
- select a trading strategy or threshold;
- change a hypothesis verdict or evidence ledger;
- authorize live or paper trading;
- automate lead outreach, credit decisions, or protected-trait inference;
- replace repository-native validators;
- claim that a checked box proves model quality or commercial value;
- copy or redistribute full copyrighted source documents;
- add a hosted service, credential, telemetry channel, or paid API; or
- make the five sources equal in authority when they are not.

## 4. Architecture decision

### 4.1 Rejected: shared runtime package

A Python package imported by all four repositories would remove some duplicate
parsing code, but it would introduce cross-repository release coupling and
make an optional governance tool operationally significant. A standards
package failure must not affect trading, research production, or lead-engine
verification.

### 4.2 Rejected: independently maintained checklists

Copying and editing the five checklists separately in every repository is easy
to start but causes definition drift, inconsistent source locators, duplicated
controls, and unverifiable claims about which source version was used.

### 4.3 Selected: federated contract

Create one lightweight standards repository at:

```text
/Users/carsynstephenson/Documents/Codex/portfolio-reliability-standards
```

It owns source manifests, normalized catalog records, schemas, crosswalk
fixtures, deterministic catalog validation, and publication of a versioned
catalog snapshot.

Each project vendors a compact catalog snapshot plus its own profile and owns a
small repository-native reporter. The snapshot is locked by version and
SHA-256. Local repositories never import or execute the standards repository.

This provides one semantic contract while retaining four independent runtime,
test, governance, and rollback boundaries.

## 5. Canonical standards repository

The initial layout is:

```text
portfolio-reliability-standards/
  AGENTS.md
  README.md
  pyproject.toml
  catalog/
    sources.json
    items.jsonl
    crosswalks.json
    catalog-manifest.json
  schemas/
    source.schema.json
    item.schema.json
    profile.schema.json
    receipt.schema.json
    report.schema.json
  extraction/
    rules_of_ml.py
    ml_test_score.py
    narrative_coverage.py
    common.py
  reviews/
    narrative-section-coverage.json
    source-review-receipts.jsonl
  fixtures/
    valid/
    invalid/
    golden/
  scripts/
    fetch_sources.py
    extract_catalog.py
    verify_catalog.py
    publish_snapshot.py
  tests/
    test_source_manifests.py
    test_enumerated_extraction.py
    test_narrative_coverage.py
    test_catalog_schema.py
    test_crosswalks.py
    test_snapshot_determinism.py
  vendor/
    portfolio-reliability-catalog-v1.json
    portfolio-reliability-catalog-v1.sha256
  docs/
    source-method.md
    status-semantics.md
    reviewer-runbook.md
```

The project uses Python 3.12 and the standard library. No runtime dependency is
required. If a local `pdftotext` binary exists, it may produce a disposable
review aid, but catalog publication cannot depend on it. PDF-derived records
are reviewed against exact page images or text and checked into the normalized
catalog, not regenerated blindly in CI.

## 6. Source acquisition and identity

### 6.1 Allowlisted sources

`catalog/sources.json` records only authoritative URLs:

| Source ID | Canonical URL | Extraction model |
|---|---|---|
| `RML` | `https://developers.google.com/machine-learning/guides/rules-of-ml` | Enumerated rules |
| `DVM` | `https://proceedings.mlsys.org/paper_files/paper/2019/file/928f1160e52192e3e0017fb63ab65391-Paper.pdf` | Narrative section coverage |
| `MLTS` | `https://research.google/pubs/whats-your-ml-test-score-a-rubric-for-ml-production-systems/` | Enumerated tests |
| `HTD` | `https://research.google/pubs/hidden-technical-debt-in-machine-learning-systems/` | Narrative section coverage |
| `EYT` | `https://eugeneyan.com/writing/testing-ml/` | Practitioner guidance |

No search-engine result, repost, summary, model output, or third-party mirror
can be the canonical source.

### 6.2 Source manifest

Each source manifest contains:

```json
{
  "source_id": "MLTS",
  "title": "What's Your ML Test Score?",
  "authority_class": "peer_reviewed_primary",
  "canonical_url": "https://research.google/pubs/whats-your-ml-test-score-a-rubric-for-ml-production-systems/",
  "content_url": "https://research.google.com/pubs/archive/45742.pdf",
  "publication_date": "2017",
  "retrieved_at": "2026-08-02T00:00:00Z",
  "retrieved_sha256": "<64 lowercase hex characters>",
  "media_type": "application/pdf",
  "extraction_model": "enumerated",
  "expected_enumerated_count": 28,
  "review_status": "human_verified",
  "license_note": "reference metadata and paraphrase only"
}
```

Raw source bytes may be stored in an ignored local cache for verification. They
are not committed unless redistribution rights are confirmed. The manifest
stores the content hash even when raw bytes are not committed.

Source refresh is explicit:

```text
python scripts/fetch_sources.py --refresh --source RML
python scripts/extract_catalog.py --source RML --candidate-out /tmp/rml.jsonl
python scripts/verify_catalog.py --candidate /tmp/rml.jsonl
```

The refresh command never overwrites the published catalog. A changed content
hash creates a candidate and a review diff. Publication requires a dated human
review receipt.

## 7. Extraction method

### 7.1 Enumerated sources

For RML and MLTS, a deterministic source-specific adapter extracts stable
numbered headings and their locators. The adapter produces candidate records,
not authoritative interpretations.

Publication gates are:

1. Extracted ordinal count equals the source manifest's expected count.
2. Ordinals are unique and contiguous where the source uses a contiguous
   sequence.
3. Every ordinal has a source heading and locator.
4. Every candidate has a reviewer-authored control paraphrase.
5. No source sentence is copied beyond the limited text needed to identify a
   heading.
6. A reviewer reconciles the candidate list against the canonical page or PDF.
7. A second deterministic run produces byte-identical normalized output.

RML retains all numbered rules. Applicability is decided later in project
profiles; irrelevant rules are not deleted from the canonical catalog.

MLTS retains all 28 tests in the four source-native areas:

- feature and data tests;
- model-development tests;
- ML-infrastructure tests; and
- monitoring tests.

### 7.2 Narrative sources

DVM and HTD are papers, not official numbered checklists. EYT is a practitioner
article. Their prose must not be presented as if the authors published an
official checklist.

`reviews/narrative-section-coverage.json` enumerates every in-scope section and
records one of:

- `CONTROL_DERIVED`
- `CONTEXT_ONLY`
- `DUPLICATE_OF`
- `OUT_OF_SCOPE_WITH_REASON`

A derived record requires:

1. source ID;
2. exact section and page or stable heading;
3. reviewer-authored paraphrase;
4. expected evidence type;
5. risk tags;
6. crosswalk to any equivalent source items; and
7. a review receipt.

Narrative publication gates use section coverage rather than an invented item
count. Every in-scope section must have a disposition, and every derived item
must be reachable from that coverage ledger.

### 7.3 Source authority

Authority classes are:

1. `peer_reviewed_primary`
2. `publisher_primary_guidance`
3. `practitioner_guidance`

EYT may guide test implementation but cannot override peer-reviewed controls,
repository policy, or primary domain-source requirements. A conflict is
resolved in favor of repository policy and recorded as `SUPERSEDED`, not
silently merged.

## 8. Canonical item schema

Each line in `catalog/items.jsonl` is a normalized record:

```json
{
  "schema_version": 1,
  "item_id": "MLTS-INFRA-04",
  "source_id": "MLTS",
  "item_kind": "enumerated",
  "source_locator": {
    "section": "ML infrastructure tests",
    "page": 8,
    "ordinal": 4,
    "anchor": null
  },
  "title": "Quality before serving",
  "control": "Evaluate candidate quality before serving a replacement model.",
  "evidence_expected": [
    "candidate-versus-current comparison receipt",
    "declared acceptance threshold",
    "promotion decision"
  ],
  "domains": ["model-development", "deployment"],
  "risk_tags": ["regression", "promotion"],
  "source_native_scoring": "mlts_0_1_2",
  "crosswalk_group": "candidate-quality-gate",
  "review_receipt_id": "review-mlts-2026-08-02"
}
```

Required invariants:

- Enumerated RML IDs use `RML-001` through the reviewed final ordinal.
- MLTS IDs use `MLTS-DATA-01`, `MLTS-MODEL-01`, `MLTS-INFRA-01`, and
  `MLTS-MONITOR-01` families, each preserving the source order.
- Narrative IDs use `DVM-<SECTION>-NN`, `HTD-<SECTION>-NN`, or
  `EYT-<PHASE>-NN`; the slug is descriptive and the numeric suffix is stable.
- IDs are stable and never reassigned.
- Published records are append-only. Meaning changes supersede an old record
  with a new version rather than rewriting history.
- A locator cannot be empty.
- An enumerated item must have an ordinal.
- A derived control must have a coverage-ledger reference.
- Every source-native scoring mode is validated against its source.
- Crosswalks may consolidate implementation but cannot erase source items.

## 9. Crosswalk and duplicate control model

`catalog/crosswalks.json` groups semantically overlapping items without claiming
the sources are identical. For example, point-in-time feature capture may
satisfy controls from RML, DVM, MLTS, and HTD through one local control.

Each crosswalk contains:

```json
{
  "crosswalk_id": "point-in-time-data",
  "item_ids": [
    "RML-029",
    "DVM-SKEW-01",
    "MLTS-DATA-03",
    "HTD-DATA-DEPENDENCIES-01"
  ],
  "shared_intent": "Prevent future or mutable data from contaminating evidence.",
  "differences": [
    "RML emphasizes serving-time logging.",
    "DVM emphasizes schema and skew validation.",
    "MLTS treats the behavior as a repeatable test.",
    "HTD frames uncontrolled data dependencies as technical debt."
  ]
}
```

The local profile maps one `local_control_id` to all applicable source items.
The reporter counts each source item for coverage but recommends only one local
implementation. This is the main diminishing-returns control.

## 10. Repository profile contract

Each repository owns:

```text
docs/reliability/
  catalog.lock.json
  catalog.snapshot.json
  profile.json
  command-evidence.json
  README.md
```

`catalog.lock.json` records the catalog version, snapshot SHA-256, source
repository commit, and profile schema version. `catalog.snapshot.json` makes
the repository independently auditable and usable offline.

Each profile mapping contains:

```json
{
  "item_id": "DVM-DRIFT-02",
  "status": "ENFORCED",
  "local_control_id": "OV-POINT-IN-TIME-01",
  "evidence": [
    {
      "kind": "file_symbol",
      "path": "research/experiments.py",
      "symbol": "register",
      "sha256": "<reviewed file hash>"
    },
    {
      "kind": "command_receipt",
      "command_id": "research-integrity-tests",
      "receipt_path": "<local generated receipt>"
    }
  ],
  "owner": "research-governance",
  "reviewed_at_commit": "<git sha>",
  "last_reviewed_at": "<UTC timestamp>",
  "enforcement": "existing_hard_gate",
  "notes": "Retrieval time cannot substitute for availability time."
}
```

### 10.1 Status semantics

| Status | Required proof | Enforcement meaning |
|---|---|---|
| `ENFORCED` | Repeated automated evidence plus implementation evidence | Existing automated control |
| `MANUAL` | Documented procedure, owner, and dated receipt | Human-reviewed control |
| `ADVISORY` | Applicable observation without promotion authority | Report only |
| `GAP` | Applicable control without sufficient evidence | Report and prioritize |
| `NOT_APPLICABLE` | Rationale, owner, review date, and expiry | Excluded transparently |
| `SUPERSEDED` | Stronger repository policy and evidence pointer | Repository rule prevails |
| `STALE` | Previously accepted evidence no longer matches | Cannot count as covered |

`STALE` is computed by the reporter rather than normally authored. A changed
evidence hash, missing path, expired N/A rationale, missing receipt, or catalog
lock mismatch makes the item stale.

Path existence alone cannot establish `ENFORCED`. A mapping must contain both
implementation evidence and recent execution evidence covering the relevant
behavior.

### 10.2 Command evidence

The profile cannot contain executable shell strings. It references command IDs
defined in `command-evidence.json` as structured argument arrays. The default
reporter validates existing signed/hash-bound receipts and does not execute
commands.

A separate explicit `refresh-evidence` mode may execute only command IDs
allowlisted in repository code. Receipts contain:

- repository root and Git SHA;
- dirty-state summary;
- structured argv;
- start and finish UTC timestamps;
- exit code;
- stdout and stderr SHA-256;
- parsed test totals where supported; and
- reporter version.

Receipt output goes to a repository-ignored artifacts directory. Credentials,
environment values, raw data, and private paths are redacted.

## 11. Reporting and scoring

### 11.1 Coverage reporting

The reporter produces deterministic JSON and Markdown with:

- coverage by source, domain, and status;
- stale and missing evidence;
- local controls satisfying multiple source items;
- verified gaps ordered by local priority;
- N/A and superseded rationales;
- source and profile hashes;
- Git SHA and dirty-state disclosure; and
- an explicit advisory/enforcement boundary.

Reports do not claim that coverage proves model accuracy, research validity, or
commercial performance.

### 11.2 Source-native ML Test Score

For an actual ML system, MLTS retains its source-native scoring:

- 0 points: test absent;
- 1 point: test run manually with documented result;
- 2 points: test run automatically and repeatedly.

The four area totals are shown separately, and the final score is the minimum
area total. The reporter does not replace this with a portfolio average.

The source does not define a general N/A mechanism. Therefore a profile with an
N/A MLTS item is labeled `modified applicability profile`; it cannot be
presented as an unqualified source-native ML Test Score. Non-ML repositories,
including the initial Sunwest rules-based pipeline, receive no MLTS score.

### 11.3 Local marginal-value score

Source coverage and implementation priority are separate. A proposed new local
automation uses six owner-reviewed values from 1 to 5:

```text
benefit =
    risk_reduction       * 0.40
  + recurrence           * 0.20
  + auditability_gain    * 0.20
  + cross_project_reuse  * 0.20

cost =
    implementation_effort * 0.70
  + maintenance_burden    * 0.30

priority = 20 * benefit / cost
```

Decision bands:

- Equivalent evidence already exists: `BUILD_NOTHING` regardless of score.
- Below 25: keep manual or advisory.
- 25 through 39: isolated pilot only.
- 40 or above with a verified recurring gap: automation candidate.
- Safety, trading, verdict, privacy, outreach, consent, and retention controls
  still require explicit promotion approval regardless of score.

The report includes the component inputs so the score is auditable rather than
an unexplained number.

## 12. Repository integrations

### 12.1 Kalshi weather bot

Files:

```text
docs/reliability/catalog.lock.json
docs/reliability/catalog.snapshot.json
docs/reliability/profile.json
claude/tools/reliability_checklist.py
claude/tests/test_reliability_checklist.py
```

Initial evidence maps to existing research provenance, artifact lineage, data
quality, structural audit, calibration, settlement, and policy tests.

Initial candidate gaps are limited to:

- declared downstream-consumer inventory;
- explicit underused-data/dependency-utility evidence;
- research/training versus serving-path equivalence assessment; and
- one consolidated source-quality coverage report.

Use point: run after the weekly calibration council and before any separate
promotion proposal. Output is research-only. It cannot alter
`strategy_config.py`, paper/live mode, forecast fusion, order routing,
settlement, or promotion state.

Proposed command:

```text
cd /Users/carsynstephenson/Claude/claude
python tools/reliability_checklist.py audit --format both
```

### 12.2 Options Validator

Files:

```text
docs/reliability/catalog.lock.json
docs/reliability/catalog.snapshot.json
docs/reliability/profile.json
scripts/reliability_checklist.py
tests/test_reliability_checklist.py
```

Initial evidence maps to experiment preregistration, exact code/config/source
and data-window hashes, append-only diagnostics, point-in-time source policy,
provider receipts, and research-integrity tests.

Initial candidate gaps are limited to:

- unified source-to-verdict trace reporting;
- feature and dependency cost-versus-benefit review;
- explicit simpler-baseline evidence; and
- consolidated stale-evidence and monitoring coverage.

Use points: dependency/capability review, hypothesis registration, evidence
upgrade, and pre-promotion review. The tool is descriptive-only. It cannot
register a hypothesis, spend an OOS touch, change a verdict, append a fact,
modify the cache, or reopen a historical gate.

Proposed command:

```text
cd /Users/carsynstephenson/options-validator
uv run python scripts/reliability_checklist.py audit --format both
```

### 12.3 Equity Research

Files:

```text
docs/reliability/catalog.lock.json
docs/reliability/catalog.snapshot.json
docs/reliability/profile.json
scripts/reliability_checklist.py
tests/test_reliability_checklist.py
```

Initial evidence maps to the source registry, temporal admission, look-ahead
controls, citation integrity, reproducibility, calibration, and outcome
tracking.

Initial candidate gaps are limited to:

- source-to-claim-to-report lineage view;
- source-class freshness and drift coverage;
- slice-level failure reporting; and
- declared downstream-consumer inventory.

Use points: source admission, research packet review, phase review, and the
repository optimization scorecard. During the current validator freeze the
integration must not add a new `check_` function or change
`scripts/validation_gate.py`. It is a separate advisory reporter.

Proposed command:

```text
cd /Users/carsynstephenson/equity-research
uv run python scripts/reliability_checklist.py audit --format both
```

### 12.4 Sunwest lead engine

Files:

```text
docs/reliability/catalog.lock.json
docs/reliability/catalog.snapshot.json
docs/reliability/profile.json
src/sunwest_leads/reliability_checklist.py
tests/test_reliability_checklist.py
```

Only data, provenance, privacy, reliability, monitoring, and audit controls are
initially applicable. Model-training controls are N/A until the system actually
uses a learned model. The rules-based research-order score must not be
misrepresented as ML.

Initial candidate gaps are limited to:

- source-freshness and drift profile;
- claim-to-source completeness;
- declared data-consumer inventory;
- privacy and retention evidence; and
- reviewer precision/disagreement monitoring.

Use points: controlled-pilot review and weekly human lead-queue review. The
reporter cannot enable source collection, automate outreach, infer protected
traits, determine credit eligibility, or resolve the open production host,
backup, source, compliance, and retention decisions.

Proposed command:

```text
cd /Users/carsynstephenson/Documents/Codex/sunwest-lead-engine
uv run sunwest-leads checklists --format both
```

The new CLI subcommand remains advisory and is not folded into the blocking
`verify` command during the pilot.

## 13. Enforcement model

The initial policy is advisory-first:

1. Catalog-schema and catalog-hash failures block catalog publication.
2. Local profile-schema and lock mismatches fail the checklist command because
   the report itself would be untrustworthy.
3. Existing repository hard gates remain hard gates and are reported as such.
4. A newly discovered checklist gap exits successfully with an explicit
   advisory result during the pilot.
5. A new control can become blocking only through a separate repository-local
   owner decision that defines the failure condition, baseline, false-positive
   tolerance, rollback, and tests.

This separates tool integrity from domain enforcement. A broken auditor fails;
a valid auditor reporting a new gap does not silently acquire authority.

## 14. Security, privacy, and data-egress design

- Normal verification performs no network calls.
- Source refresh uses only allowlisted public URLs and is manually invoked.
- No API key, OAuth token, provider credential, or private dataset is required.
- The reporter reads tracked metadata and ignored receipts, not raw customer,
  broker, trading, email, calendar, or lead data.
- Profiles contain repository-relative paths only. Absolute paths, `..`, and
  symlink escapes are rejected.
- Receipt redaction removes environment variables, credentials, and private
  payloads before hashing or reporting.
- JSON and JSONL are parsed as data. No `eval`, dynamic import, shell string,
  templated command execution, or plugin discovery is permitted.
- Generated Markdown escapes untrusted values.
- The standards repository publishes no telemetry.

## 15. Test strategy

Implementation follows test-driven development. Every behavior change begins
with a failing test.

### 15.1 Standards-repository tests

- source-manifest schema and authority allowlist;
- enumerated count, uniqueness, and locator reconciliation;
- narrative section coverage and orphan detection;
- item schema and stable ID rules;
- crosswalk membership and duplicate-ID rejection;
- source-native MLTS scoring fixtures;
- deterministic ordering, serialization, and snapshot SHA-256;
- changed-source candidate workflow;
- path and command-injection rejection; and
- copyright-safe publication fixture.

### 15.2 Repository-local contract tests

- catalog lock matches vendored snapshot;
- every profile item exists in the catalog;
- every applicable catalog item has a disposition;
- evidence paths remain inside the repository;
- evidence hashes and receipt bindings detect staleness;
- status prerequisites are enforced;
- N/A and superseded entries contain rationale and review metadata;
- one local control can cover several source items without duplicate
  implementation recommendations;
- JSON and Markdown outputs are deterministic; and
- advisory gaps do not change existing domain exit behavior.

### 15.3 Baseline and regression verification

Before each repository changes, record:

- Git root, branch, HEAD, and dirty-state disclosure;
- repository-native full test result;
- lint/type/integrity results required by local instructions; and
- any pre-existing failure separated from introduced failures.

After each repository integration, rerun the same gates plus the new contract
tests. A narrow checklist test cannot support a broad claim that the repository
remains healthy.

## 16. Rollout

### Phase 0: source catalog

Create the standards repository, source manifests, schemas, extraction
adapters, narrative coverage ledger, normalized catalog, crosswalks, golden
fixtures, and deterministic snapshot.

Exit criteria: all five sources reconciled, catalog verification green, and a
human review receipt present.

### Phase 1: existing-control baseline

Map only controls already supported by current files, commands, and receipts.
Do not implement gaps while measuring coverage.

Exit criteria: every catalog item has a disposition in each project, with no
unsupported `ENFORCED` claim.

### Phase 2: repository-native reporters

Add one small, reversible reporter and contract-test module to each repository.
Generate the first advisory report.

Exit criteria: local and complete repository test matrices pass, and no domain
authority path changes.

### Phase 3: four-week advisory pilot

Run the report at the defined weekly review point. Track false positives,
staleness noise, manual review time, cross-source duplicates, and whether each
finding changed a real decision.

Exit criteria: a pilot summary identifies controls to keep manual, automate,
defer, or remove.

### Phase 4: selective promotion

Use the marginal-value gate to propose only verified recurring gaps. Each
promotion is a separate owner-approved design with local TDD evidence and
rollback.

### Phase 5: maintenance

- Weekly: local profile audit.
- Monthly: stale evidence and N/A expiry review.
- Quarterly: source-hash refresh and catalog review.
- On source change: candidate diff and human approval before publication.
- On repository policy change: profile review before claiming coverage.

## 17. Rollback

Every repository integration is commit-scoped and contains no migration.
Rollback removes the reporter, profile, snapshot, and tests for that repository
without changing runtime code or data.

The standards repository is optional to project execution. Removing it stops
future catalog publication but does not affect any project runtime. Vendored
snapshots retain the last auditable state.

No rollback deletes receipts or rewrites append-only ledgers. Generated audit
artifacts may be removed because they are reproducible and ignored.

## 18. Design self-audit

### 18.1 Risk: checklist theater

Mitigation: path existence is insufficient; enforced status requires execution
evidence. Reports explicitly disclaim accuracy and commercial-performance
proof.

### 18.2 Risk: misrepresenting narrative papers as checklists

Mitigation: narrative items are labeled derived, tied to section coverage, and
human-reviewed. Enumerated and derived items use different publication gates.

### 18.3 Risk: misapplying ML controls to non-ML systems

Mitigation: N/A requires a rationale and expiry. Sunwest receives no MLTS score
until a learned model exists.

### 18.4 Risk: duplicate validators and diminishing returns

Mitigation: crosswalks consolidate several source items into one local control;
equivalent evidence forces `BUILD_NOTHING`.

### 18.5 Risk: central governance coupling

Mitigation: only versioned data snapshots cross repositories. There is no
shared runtime import, network lookup, or automatic update.

### 18.6 Risk: stale status inflation

Mitigation: file hashes, Git SHA, receipt bindings, N/A expiry, and lock hashes
compute `STALE`; stale items do not count as covered.

### 18.7 Risk: false precision in prioritization

Mitigation: every component score and rationale is shown. The numerical score
cannot override hard policy, safety, or owner approval.

### 18.8 Risk: scope expansion into production authority

Mitigation: advisory-first rollout, explicit non-goals, isolated reporters,
commit-scoped rollback, and repository-local promotion designs.

## 19. Definition of done

The portfolio checklist system is complete only when current-state evidence
proves all of the following:

1. The standards repository exists at the declared path and has a clean,
   committed source catalog.
2. Five valid source manifests match reviewed source identities.
3. RML and MLTS enumerated item counts reconcile exactly.
4. DVM, HTD, and EYT section-coverage ledgers have no undisposed sections.
5. Every catalog item validates and every crosswalk reference resolves.
6. Snapshot reproduction produces the published SHA-256.
7. All four repositories contain matching locked snapshots and complete
   profiles.
8. Every `ENFORCED`, `MANUAL`, `NOT_APPLICABLE`, and `SUPERSEDED` status meets
   its evidence prerequisites.
9. Each repository's advisory report runs offline and deterministically.
10. Repository-native full test, lint, type, integrity, and verification gates
    have current post-change evidence.
11. No authority boundary, credential surface, telemetry path, or paid service
    was added.
12. The four-week pilot and selective-promotion phases remain open work until
    elapsed-time evidence exists; implementation completion must not be
    confused with pilot completion.
