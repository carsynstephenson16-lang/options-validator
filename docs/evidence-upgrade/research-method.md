# Research Method (EC-1)

Date: 2026-07-29. How the evidence for this architecture was gathered, which
formal foundations were accepted or rejected, and the ongoing method the
system itself uses to evaluate and improve retrieval quality.

## 1. Search strategy used for this design

- Targeted primary-source retrieval, not broad browsing: each open question
  was assigned to a dedicated researcher with instructions to open and read
  governing sources (manuals, specs, contract terms, live APIs) rather than
  cite snippets or abstracts.
- Repository reconstruction preceded external research: three parallel
  read-only audits (one per repo) ran the actual test/lint commands and
  cited file:line evidence, so the plan audits against reality, not memory.
- Verification-first habits that paid off this cycle and are retained as
  method: (a) full-text-search the actual document for any number a
  search-summarizer surfaces (caught the fabricated "2-minute" SEC
  dissemination figure — absent from the real PDS spec); (b) when a source
  is unreachable, record the limitation and substitute an official
  secondary explicitly (Murphy 1973 → ECMWF guide), never silently.
- Delegation pattern: parallel Claude Sonnet 5 subagents at high effort for
  independent workstreams; the lead session (Fable 5) reserved for
  synthesis, conflict resolution, and final decisions. A fresh-context
  adversarial verifier reviews the finished artifacts without access to the
  lead's reasoning.

## 2. Formal foundations — accepted / rejected

| Foundation | Verdict | Concrete consequence |
|---|---|---|
| Bitemporal modeling (SQL:2011 valid vs transaction time) | **Accepted** | `recorded_at` system-assigned, never edited; `observed_at` corrections insert new rows; `available_at` modeled as a business attribute (not a bitemporal axis); quarantine `recorded_at < available_at`; test that superseded rows are never mutated |
| Selective prediction / abstention (Chow 1957; El-Yaniv & Wiener 2010) | **Accepted** | ABSTAIN maps to the rejected region; risk reported conditional on admission, always paired with coverage; abstention threshold + coverage floor pre-registered together (zero-risk targets can force coverage → 0, so the pair is registered, not aspired to independently) |
| Evidence combination under dependence (Bovens & Hartmann 2002) | **Accepted, with nuance** | `independence_group` field; corroboration counts distinct groups; per-source reliability / false-confirmation carried as data where measured (the correction's sign is parameter-dependent — same-source repetition is not always weaker) |
| Proper scoring & calibration (Brier 1950; Gneiting & Raftery 2007; Murphy decomposition) | **Accepted, marginal** | Brier (already used) is strictly proper; any blended metric must be re-proven proper; reliability and resolution stored as separate per-provider metrics beside the pooled Brier |
| Gates vs composite scores (GRADE lineage) | **Accepted** | Hard per-dimension admission gates + ordinal confidence moved only by named, logged reasons; numeric weighted composites rejected (prior composite systems showed low reproducibility; a composite missed bias a domain gate caught; no comparable-rigor defense of composites found — absence noted honestly) |
| Provenance semirings (Green/Karvounarakis/Tannen 2007) | **Rejected** | Why-provenance (a junction table) already covers "which sources support this claim"; the semiring apparatus pays off only for engines that algebraically compose annotated relations — this system doesn't |
| Trusted timestamping (RFC 3161), Memento/WARC archiving, signed feeds | **Rejected** | Solve adversarial third-party proof; the threat model here is self-integrity, already covered by content-addressed capture + hash chains; would add always-reachable external dependencies |
| Tooling facts (Alembic batch mode; SQLite ALTER limits; SQLite WAL-Reset bug fixed 3.51.3; zoneinfo/tzdata pinning) | **Accepted** | Batch-mode migrations mandatory on SQLite; SQLite ≥ 3.51.3 gate before concurrent multi-writer WAL; `tzdata` pinned in lock files and version-stamped on receipts |

## 3. Source-quality dimensions (kept separate, never blended)

Authority · directness · version specificity · temporal safety ·
reproducibility · source independence · extraction fidelity · internal
consistency · conflict status · fitness for proposed use. Each is a gate or
a recorded field; the only aggregate is the ordinal confidence level with
its logged movement reasons. Separated concerns: source reliability ≠
claim support ≠ extraction confidence ≠ temporal availability ≠ decision
eligibility.

## 4. Retrieval evaluation design

- **Golden-question benchmark**: 10–15 hand-curated questions per domain
  (filings facts, options contract/chain facts, NWS climate values, Kalshi
  rules), each keyed to a primary-source answer (accession number /
  contract quote / CLI value / rule text), including deliberate
  correctly-abstain items — abstention is a distinct, harder skill and is
  scored separately.
- Metrics: retrieval precision (right primary source found), recall (all
  needed sources found), abstention quality (said "insufficient evidence"
  exactly when true). Reported per domain, always with coverage.
- Runs offline in CI against cached fixtures; regressions block release of
  retrieval-affecting changes. Lexical baselines are measured before any
  fancier retriever is credited (curated-relevance methodology; strong
  lexical baselines frequently win).
- LLM-judged reference-free checks (faithfulness / context relevance) are
  permitted as a cheap between-benchmark signal only — never as the release
  gate, because single-call LLM judging carries measured position,
  verbosity, and self-preference biases; where an LLM verdict gates
  anything, it is double-order judged.

## 5. Research stopping conditions

Stop researching a question when: (1) an authoritative source establishes
the governing fact; (2) material conflicts have been checked; (3) the
operational consequence is clear; (4) further search no longer changes the
decision. Otherwise record an evidence gap explicitly — a gap is a valid,
citable finding (this cycle produced four: SEC dissemination latency is
officially unquantified; WMO `Pxx` is undefined in governing sources read;
Murphy 1973 original unverified; WMO-386 amendment text unread). Gaps must
not gain implementation authority: each maps to a conservative default or
a quarantine rule, never a guessed value.

## 6. Human-review triggers

- Settlement-label quarantine (weather chain contradiction, parity
  mismatch, unrecognized BBB form).
- Verify-support disagreement (double-order split) on decision-bearing
  claims.
- Conflict without a named resolution rule.
- Provider health drop past registered thresholds; any gate override.
- Anything touching owner-typed territory (new registrations, frozen
  numbers, verdict ratifications) — always human, by standing division of
  labor.

## 7. Continuous-improvement loop

Confirmed error → (1) regression fixture added; (2) source-policy /
registry supersession if source-related; (3) selector version bump if
extraction-related; (4) durable note in the repo's institutional-memory
section ("Things That Have Failed" pattern); (5) golden set extended when
the error class was previously unmeasured. Provider health metrics
(precision/recall on the golden set, null rate, freshness, conflict rate,
quarantine rate) are recomputed from receipts on the existing scheduled
cadence, and the whole policy is re-audited quarterly alongside the
standing quarterly usage audit. Self-reported provider quality is never an
input to promotion.
