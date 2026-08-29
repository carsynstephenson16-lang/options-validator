# Diminishing-Returns Analysis

## Decision

Only `SEC-01` clears Lane A. Its reproducible score is 90 because the defect is independently verified, remotely reachable in the public repository when the optional OAuth secret is configured, narrow to one unprotected workflow, testable without credentials, dependency-free, and instantly reversible. Its fix removes authority from untrusted callers; it does not change research, execution, provider, data, or operational behavior.

`DATA-01` and `SEC-02` have comparable raw value but are hard-gated. Updating the irreplaceable-data inventory mutates an operational data-authority control. Repairing all global auto-push hooks changes network push authority and overlaps protected `tools/anti-stranding/repo-reconcile`. Both remain plan-only regardless of score.

## Scoring method

Scores use the prompt's 100-point positive scale: correctness/risk reduction 25, evidence 20, incremental value 20, testability/reversibility 15, maintainability or measured performance 10, and architecture/governance fit 10. Complexity, protected overlap, dependency, feasibility, authority, and unsafe-mutation penalties are applied afterward. The 0–5 value columns in the CSV are comparative domain indicators; they are not the arithmetic score inputs.

### SEC-01 reproducible score

| Component | Points | Evidence-based allocation |
|---|---:|---|
| Correctness and risk reduction | 23 / 25 | Removes authorization of metered credential use by untrusted PR commenters when the OAuth secret is configured. Impact is bounded: no secret disclosure or arbitrary commenter-controlled shell execution was established. |
| Evidence strength and reproducibility | 20 / 20 | Exact missing predicates were inspected in both comment branches; current public visibility was checked; the security scanner and a separate Terra verifier agreed on the root cause. |
| Incremental project value | 18 / 20 | Closes a real public caller-authorization gap without duplicating landed work, but affects an optional reviewer rather than research or execution integrity. |
| Testability and reversibility | 15 / 15 | A credential-free offline contract test can deny untrusted associations on both branches, permit the named trusted set, and preserve automatic PR review; safe rollback disables both comment triggers while retaining automatic PR review. |
| Maintainability or measured performance | 8 / 10 | Uses existing GitHub event metadata and no dependency; the repeated expression remains a small workflow maintenance surface. |
| Architecture and governance fit | 10 / 10 | Applies least-authority at the event boundary and leaves research, provider, data, H7, order, and push authority unchanged. |
| **Positive subtotal** | **94 / 100** | |
| Added complexity / maintenance burden | **-4** | Two event branches must keep an identical trusted-association policy, and local static tests cannot execute GitHub's expression engine. |
| Protected WIP overlap | **0** | The workflow is absent from the 136-path protected inventory. |
| New dependency, service, or license | **0** | None planned. |
| Weak data feasibility | **0** | No dataset or provider evidence is required. |
| Authority/data/strategy hard gate | **Absent** | The repair restricts an existing caller boundary; it does not add execution, ranking, provider, migration, or data authority. |
| Irreversible/cache/secret/unsafe-data reject gate | **Absent** | No such action is required. |
| **Final score** | **90** | Lane A threshold is satisfied after penalties. |

### Frontier

| Candidate | Raw decision | Score | Ruling |
|---|---:|---:|---|
| SEC-01 trusted comment caller | Narrow verified access-control repair | 90 | Lane A |
| DATA-01 Schwab retention inventory | High-value retention repair | 90 | Plan-only: data-authority mutation |
| SEC-02 Git remote ownership | High-value operational security repair | 86 | Plan-only: protected WIP and push authority |
| WIKI-01 current-status refresh | Strong knowledge correction | 83 | Lane B: vault current-status authority not granted |
| DATA-02 quote freshness | Decision-critical data check | 82 | Plan-only: protected gate and missing threshold authority |
| DATA-03 close provenance | Strong lineage improvement | 78 | Plan-only: provider/data authority |
| ARCH-01 ritual shadow plan | Architecture risk reduction | 77 | Plan-only: protected operational orchestrator |
| TST-02 macOS CI | Useful platform coverage | 76 | Lane B: runner/cost policy needed |
| TST-03 repo-rag CI | Isolated coverage | 73 | Lane B: lower frontier value and support decision needed |

## Consolidation and rejection decisions

- Chain-consistency diagnostics and fill-adversity context already exist on `main`; the audit does not propose duplicate implementations. Realized-fill calibration remains a different, data-starved question.
- `TST-04` is rejected because adding a format gate would knowingly fail on 281 existing files, while a broad formatting sweep is prohibited.
- `QUANT-03` is rejected because CSCV/PBO needs a homogeneous preregistered grid and enough independent observations. The current heterogeneous ledger correctly records `pbo: null`.
- `PERF-01` has verified repeated reads but no representative timing. The prompt forbids a performance edit without measurement, and the implementation file is protected.
- `SEC-03` is parked because source reachability is conditional on a browser boundary not reproduced in the deployed environment; existing loopback, CORS, cache, and provider gates materially lower expected value.

## Stop condition

Reached. After the three top raw-value candidates, every remaining item is below 85, hard-gated, protected, dominated by a simpler candidate, or lacks named evidence. Additional broad optimization search would have diminishing expected value and would increase false-positive and cleanup risk.
