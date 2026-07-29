# Decision Log — Evidence-Ingestion Architecture (EC-1)

Date: 2026-07-29. One entry per material decision. Fields: **Prior** (what
the supplied plan/Revision 3 proposed, as embedded in the commissioning
prompt), **Decision**, **Evidence**, **Opposing**, **Tradeoff**, **Effect**
(on implementation), **Confidence**, **Gap** (unresolved assumption).
Source IDs refer to `source-ledger.csv`; audit citations refer to the three
repository audit reports (session scratchpad, 2026-07-29).

---

**D01 — Proceed without the full supplied plan documents.**
Prior: audit "the supplied evidence-ingestion plans" and "Evidence
Architecture Corrections, Revision 3." Decision: neither document exists
as a file anywhere reachable (3 repos + worktrees, Desktop, Downloads,
Documents, Google Drive, Notion — searched 2026-07-29); treat the
commissioning prompt's 23 invariants + 5 correction areas as the governing
summary and audit those. Evidence: exhaustive local + connector search
this session. Opposing: the full documents may contain nuances the prompt
summary drops. Tradeoff: proceeding beats stalling; fidelity risk accepted
and labeled. Effect: every invariant audited individually (D02–D26).
Confidence: high that the search was thorough; medium that the summary is
complete. Gap: if the owner locates the original documents, re-diff this
architecture against them.

**D02 — Keep incubation in equity-research; contract-first, pattern
replication, no premature shared package.**
Prior: invariants 1–3 (one contract; incubate in equity-research; extract
shared package only after two repos use a stable interface). Decision:
uphold all three; add the explicit reading that *domain* corrections (SEC
→ equity-research; NWS/Kalshi → kalshi) land in their home repos while the
*contract* incubates in equity-research; conformance travels as shared
fixture vectors, not imports. Evidence: `market_updates/` +
`market_context.py` is the only working cross-repo producer/consumer pair
(equity-research audit §4, §10); options-validator and kalshi each have
strong local primitives that must not be replaced (audits §17). Opposing:
options-validator has the best primitives — one could incubate there
instead. Tradeoff: equity-research has the weakest tooling (no
linter/type-checker, no hash chain) but the strongest cross-repo seam;
building where the seam is beats building where the tooling is. Effect:
packets 1–5 target equity-research; packet 10 is an extraction checkpoint,
not a build. Confidence: high. Gap: none material.

**D03 — Storage: no SQLite in options-validator; Alembic adopted only in
equity-research; kalshi keeps hand-rolled migrations until touched.**
Prior: invariant 19 ("Alembic-managed schema versions") read as
program-wide. Decision: scope Alembic to relational stores this program
changes (equity-research `market_updates` now; kalshi if/when its schema
is materially changed by an EC-1 packet); options-validator stays
file-based (receipts/JSONL/parquet + schema-version constants). Evidence:
options-validator has zero SQLite and a mature file-based versioning
discipline (audit §7–9); kalshi has working hand-rolled migrations +
`schema_migrations` (audit §9); forcing Alembic everywhere adds risk with
no failure mode fixed. Opposing: uniform tooling is simpler to reason
about long-term. Tradeoff: heterogeneity accepted to honor
smallest-architecture; revisit at the D10 extraction checkpoint. Effect:
packet 2 adopts Alembic (batch mode) in equity-research only. Confidence:
high. Gap: if kalshi packet 6/7 turns out to need column changes on
legacy tables, decide Alembic-in-kalshi then, not now.

**D04 — Bitemporal fields: `observed_at` (valid), `recorded_at`
(transaction, system-assigned), `available_at` (business attribute).**
Prior: invariant 7 (point-in-time availability semantics). Decision:
adopt, with the SQL:2011-grounded refinement that availability is NOT a
bitemporal axis and must be an ordinary attribute computed by versioned
rules; quarantine `recorded_at < available_at`. Evidence: FRM-S2
(SQL:2011 survey, read directly); kalshi already implements
`assert_available_at_decision()` and market_context already enforces
`published_at <= as_of` (audits). Opposing: none found. Tradeoff: three
timestamps cost schema width; they buy auditable no-look-ahead. Effect:
packet 2 columns; consumer contract in packet 8. Confidence: high. Gap:
none.

**D05 — SEC availability rule (versioned), conservative
`earliest_public_ts`, and a ban on the "2-minute" figure.**
Prior: invariant 8 + Revision-3 correction area 2. Decision: adopt the
sourced 17:30 ET cutoff / next-business-day-06:00 rule with the 24-form
exception list and holiday calendar (rule id
`EDGAR-FilerManual-v77-2026-03-16`); availability modeled as an INTERVAL:
`earliest_public_ts_utc` (optimistic lower bound = acceptance for
in-window/exception, next business day 06:00 ET otherwise) plus
`public_by_ts_utc` (conservative upper bound = 22:00 ET on the
dissemination business day) which is the `available_at` for
look-ahead-sensitive gating — all DESIGN CHOICE labeled; any
minutes-level latency number is banned unless internally measured and
labeled. *(Amended per verification findings F01/F02, 2026-07-29: the
exception list has 24 distinct strings, not 21 as first transcribed; and
the original single-point `earliest_public` design used the optimistic
bound for gating, which inverted "conservative" for anti-look-ahead
purposes — replaced with the interval.)* Evidence:
SEC-S1..S9 (Filer Manual v77 §3.2, byte-identical v70→v77; hours/holiday
pages; PDS spec full-text-searched — the "2 minutes" claim does not
appear). Opposing: a web summarizer asserted the 2-minute figure;
verification refuted it. Tradeoff: the conservative bound sacrifices
same-day granularity the SEC never promised. Effect: packet 1 (pure rule
module + tests: winter/summer/boundary/DST/holiday/exception forms).
Confidence: high. Gap: dissemination latency remains officially
unquantified (recorded gap; conservative bound stands until an internal
SLO is measured).

**D06 — Capture `acceptanceDateTime` in equity-research.**
Prior: implied by correction area 2. Decision: extend `edgar_fetch.py` to
record acceptance datetimes (additive). Evidence: audit finding —
`edgar_fetch.py` captures only `filingDate`; zero "acceptance" hits
(equity-research audit §10). Opposing: none. Tradeoff: none material.
Effect: packet 1. Confidence: high (repo-verified gap). Gap: none.

**D07 — Numeric financial facts must come from SEC structured endpoints
with `accn` recorded; scraped values capped at `display_only`.**
Prior: not in the plan (improvement-scan addition). Decision: adopt as a
claim-type authority rule, with the recorded caveat that custom XBRL tags
degrade comparability (logged confidence downgrade, not silent trust).
Evidence: IMP-S05 (live `companyconcept` call returns `accn`/`form`/
`filed` per fact), IMP-S07 (as-filed fidelity), IMP-S06 (SEC staff FAQ on
custom tags), IMP-S08 (as-filed vs vendor-standardized signal divergence).
Opposing: S08 also shows vendor standardization sometimes *removes*
anomalies — structured-as-filed is not automatically "better," it is
*as-first-knowable*, which is what a point-in-time system wants.
Tradeoff: a new fetcher + schema field vs eliminating silent misreads.
Effect: packets 3 (rule) + 4 (fetcher + as-of query layer). Confidence:
high. Gap: XBRL custom-tag handling policy beyond "downgrade + log" is
deferred until real cases accumulate.

**D08 — As-first-reported query discipline for restated facts.**
Prior: invariant 11 (immutable version chains) — this makes it concrete
for financial numbers. Decision: historical reads return the fact whose
`available_at` ≤ as-of; restatements append, never replace. Evidence:
IMP-S08 (look-ahead bias through restated data is real and monetized);
falls out of D07's fields. Opposing: none. Tradeoff: negligible once D07
lands. Effect: packet 4. Confidence: high. Gap: none.

**D09 — NWS CLI version chain: issuance-time + BBB ordering; `Pxx`
quarantined; corrections not assumed BBB-disciplined.**
Prior: Revision-3 correction area 3 (which assumed a "Pxx segment" type).
Decision: adopt parsed heading fields (`bbb_type` RRx/CCx/AAx +
sequence), order by `YYGGgg` + BBB with logged receipt-time fallback;
**quarantine** unrecognized BBB forms including `Pxx` — the governing
sources read (WMO-386 Attachment II-12; NWSI 10-1701 §4.1.2) define only
RRx/CCx/AAx, and GTS bulletin segmentation was retired 2007-11-07.
Evidence: WMO-S1/S1b/S2 (verbatim quotes); WMO-S3 (NWSI 10-1004 §4.1.4:
corrections "will be done as needed" — no discipline guaranteed).
Opposing: a weather.gov explainer attributes Pxx to a 1994 WMO document
(unread — discovery-only). Tradeoff: quarantining Pxx may occasionally
hold a legitimate segmented legacy product; safer than guessing. Effect:
packet 6. Confidence: high on RRx/CCx/AAx; medium on Pxx nonexistence
(gap below). Gap: the 1994 WMO "Guidelines for the use of the indicator
BBB" was not located; if a Pxx product ever appears in practice, locate
and read it before changing the quarantine rule.

**D10 — Settlement-label freeze mirrors Kalshi's own contract-terms
machinery; capture exchange settlement values.**
Prior: correction area 3 ("Kalshi determination-time cutoff"). Decision:
freeze at the contract's expiration trigger (first 7/8 AM ET after data
release, +1 week outer bound; 11 AM ET delay on METAR inconsistency or
later-lower-high); ignore post-expiration revisions for settlement; model
the label lifecycle on Kalshi's `determined → disputed/amended →
finalized` status enum; poll and store actual `result` /
`settlement_value` into the existing `exchange_settlements` table instead
of only computing our own view. Evidence: WMO-S5 (NHIGH contract terms,
verbatim), WMO-S6/S7 (API fields, live sample); kalshi audit §14 (no
settlement-result adapter found today — only series metadata). Opposing:
none; Kalshi's rule is governing for Kalshi labels by definition.
Tradeoff: none — inventing our own freeze rule would create silent
divergence from actual settlement. Effect: packet 6. Confidence: high.
Gap: `exchange_settlements` wiring assumed present-but-unfed; Codex must
verify its current writers before adding one.

**D11 — Weather cross-checks labeled same-agency corroboration, never
independent verification.**
Prior: improvement-scan candidate framed as "independent source
cross-check." Decision: build the cross-check (station observations /
api.weather.gov / GHCN-Daily vs CLI), but record it as ONE independence
group — all trace to the same NWS/ASOS network. Evidence: IMP-S11/S12;
Bovens & Hartmann dependence results (FRM-S4). Opposing: none. Tradeoff:
honest labels reduce apparent corroboration strength; that is the point.
Effect: packet 6 (`corroboration_source`, `corroboration_match`,
independence_group discipline). Confidence: high. Gap: none.

**D12 — Hard gates + ordinal confidence; composite quality score
rejected.**
Prior: prompt required researching whether a composite adds value.
Decision: reject numeric weighted composites; use per-dimension pass/fail
gates + GRADE-style ordinal level moved only by named, logged reasons,
with a test that levels reproduce from their reasons. Evidence: FRM-S6
group (GRADE mechanism read directly; predecessor composite systems showed
low reproducibility; an empirical case where a composite missed bias a
domain gate caught; counter-evidence actively searched for and not found).
Opposing: none of comparable rigor found (absence recorded, not claimed as
proof). Tradeoff: ordinal levels are coarser than a score; coarse and
auditable beats precise and opaque. Effect: admission design (packet 5);
schema `confidence_level` + reasons. Confidence: high within
evidence-assessment practice; medium as a universal law. Gap: none
blocking.

**D13 — Provenance semirings rejected; relational junction-table lineage
retained.**
Prior: invariant 18 (relational lineage) + prompt's formal-foundations
menu. Decision: junction tables with bounded batches, aggregate counts on
run receipts, streaming IDs, high-volume tests; no semiring machinery.
Evidence: FRM-S1 (paper's own why- vs how-provenance hierarchy — a
junction table IS why-provenance; the algebra pays off only for
composed-query engines). Opposing: none for this system's shape.
Tradeoff: we forgo derivation-counting we don't need. Effect: packet 5
(junctions + tests); options-validator keeps receipt `input_files`
lineage. Confidence: high. Gap: none.

**D14 — Verify-support as a separate pipeline stage, double-order judged,
stakes-routed.**
Prior: invariant 16 (no LLM fetch+validate+promote in one step) — this
operationalizes it. Decision: LLM-extracted decision-bearing claims get an
entailment check by a *different* step/model; two calls with swapped
presentation order, admit only on agreement; disagreement ⇒ quarantine +
human review; `display_only` claims may skip (marked `not_checked`).
Evidence: IMP-S01 (AIS), IMP-S02 (ALCE citation precision/recall via NLI),
IMP-S04 (Zheng et al.: position bias flipping verdicts, 91.3%
verbosity-attack failure, +10–25pt self-preference; their own mitigation
is double-order judging). Opposing: cost — two calls per gated claim;
mitigated by stakes routing. Tradeoff: latency/cost vs a measured, large
failure mode of single-judge verification. Effect: packet 5. Confidence:
high. Gap: local-NLI vs LLM-call implementation choice left to the packet
(both admissible; fixtures make it swappable).

**D15 — Freshness classes + `stale_after` with decision-eligibility
expiry.**
Prior: not in the plan (improvement-scan addition). Decision: adopt;
classification by claim-type lookup table, surfaced by the existing
daily-ritual pattern; overdue ⇒ not decision-eligible until re-verified.
Evidence: IMP-S03 (FreshQA: <15% accuracy on fast-changing facts without
live search). Opposing: none. Tradeoff: one enum + one timestamp + one
report. Effect: packet 2 columns; consumer checks in packet 8.
Confidence: high. Gap: the class lookup table's initial assignments are
engineering judgment — reviewed at the quarterly audit.

**D16 — Coverage-paired metrics; pre-registered abstention thresholds +
coverage floor.**
Prior: invariant 14 (abstention states) — this adds the reporting
discipline. Decision: any risk/quality number over admitted claims is
reported with coverage; thresholds and floor registered before data.
Evidence: FRM-S3 (risk defined over the accepted subset; zero-risk can
force zero coverage — Theorem 14). Opposing: none. Tradeoff: more
reporting discipline. Effect: benchmark + health metrics (packet 9).
Confidence: high. Gap: none.

**D17 — Independence groups with parameter-carrying corroboration.**
Prior: continuous-improvement item 7. Decision: adopt
`independence_group`; count distinct groups; carry per-source
reliability/false-confirmation as data where measurable, conservative
one-group-one-unit default otherwise. Evidence: FRM-S4 (dependence
corrections are parameter-dependent, sometimes sign-reversing). Opposing:
the same theorems show same-source repetition can occasionally outweigh
independent confirmation — which is why parameters are data, not a fixed
discount. Tradeoff: modeling honesty vs simplicity. Effect: schema field
(packet 2) + corroboration gate (packet 5). Confidence: high on the
field; medium on ever having good r/a estimates for most sources. Gap:
r/a estimation method undefined until track-record data accumulates.

**D18 — Memento/WARC, RFC 3161, signed feeds: rejected.**
Prior: candidate improvements. Decision: reject all three as
over-engineering for a solo-operator threat model already served by
content-addressed local capture + hash chains; each adds an
always-reachable external dependency. Evidence: IMP-S09/S10/S13 (standards
read; problem-fit analysis). Opposing: archival corroboration would help
if this work were ever published adversarially — out of scope now.
Tradeoff: none current. Effect: excluded (architecture §13). Confidence:
high. Gap: revisit only if outputs become external-facing.

**D19 — PDF/OCR selectors: full spec adopted, OCR implementation
deferred.**
Prior: Revision-3 correction area 1 (full PDF selector machinery).
Decision: adopt the complete field spec (source PDF sha256, rendered-crop
sha256 with fixed coordinate convention, renderer + OCR engine/model/
config/preprocessing provenance, immutable crop storage, explicit
extraction modes, visual-match-with-text-drift review, exact-hash-only
identity) as binding contract; implement `embedded_text` selectors now
(Kalshi contract-terms PDFs have text layers); build the OCR module only
when an OCR-dependent decision input exists. Evidence: repo audits — no
OCR path exists in any repo today; the only decision-relevant PDFs
(contract terms) are text-layer PDFs whose governing values are also in
the series API. Opposing: Revision 3 asked for the machinery outright.
Tradeoff: a deferred build vs speculative code with no consumer — the
prompt's own "no features without demonstrated requirement" rule governs.
Effect: schema + spec in architecture §7; no OCR packet. Confidence:
high. Gap: none until an OCR need appears; the spec prevents ad-hoc
shortcuts then.

**D20 — SQLite ≥ 3.51.3 gate for concurrent-WAL stores; tzdata pinned and
version-stamped.**
Prior: not in the plan. Decision: adopt both as release gates. Evidence:
FRM-S7 group (sqlite.org WAL-Reset bug, fixed 3.51.3 / 2026-03-13,
verified verbatim via raw curl; PEP 615 / zoneinfo fallback semantics;
tzdata 2026.3 current per PyPI — SEC-S12). Opposing: none. Tradeoff:
trivial. Effect: startup/test assertions (packets 2, 6); lock-file pins.
Confidence: high. Gap: the raw IANA release tag corresponding to tzdata
2026.3 was not independently pulled (recorded in SEC report gaps).
*(Amended per verification finding F03, 2026-07-29: both the
equity-research and kalshi venvs measure SQLite 3.50.4 — below every safe
version — while market_updates already runs WAL. The gate is therefore
enforced, not advisory: on an unsafe engine, a non-blocking exclusive
write lock makes single-writer access mechanical (a second writer raises,
fail-closed); engine upgrade is an owner decision recorded when taken.)*

**D21 — Golden-question retrieval benchmark, abstention items included.**
Prior: continuous-improvement item 5. Decision: adopt (10–15 questions
per domain, offline in CI, precision/recall/abstention scored,
lexical-baseline-first). Evidence: IMP-S16 (BEIR qrel methodology; strong
lexical baselines), IMP-S15 (unanswerable items are a distinct skill),
IMP-S17 (LLM-judged reference-free checks as secondary signal only).
Opposing: labor cost — the highest of the adopted set. Tradeoff: the only
item producing an ongoing retrieval-quality regression signal. Effect:
packet 9. Confidence: high. Gap: question authorship is owner-reviewable
labor; start with the filings domain only.

**D22 — Fix equity-research raw archive to content-addressing (with
dual-write migration).**
Prior: invariant 5 (content-addressed raw storage). Decision: replace the
id-keyed skip-if-exists archive with sha256-addressed blobs (kalshi's
`capture_raw_payload` layout as reference), keeping an id→hash index;
migrate via expand/dual-write/shadow-read/reconcile. Evidence:
equity-research audit §12 — a changed payload for the same source item id
is currently *silently never re-archived* (real data-loss failure mode).
Opposing: none. Tradeoff: migration effort in the busiest store. Effect:
packet 2. Confidence: high. Gap: none.

**D23 — Packet order re-derived from dependencies; original PR order not
preserved.**
Prior: an implied original ordering (unknown — documents missing).
Decision: order = SEC rule (pure) → schema expand → registry → XBRL →
admission/verify → kalshi chain (parallel thread) → kalshi legacy lineage
→ options-validator consumer → benchmark → extraction checkpoint.
Evidence: dependency analysis in architecture §12; repo audits confirm
which files each packet touches (no overlap between equity-research and
kalshi packet sets). Opposing: none available (D01). Tradeoff: none.
Effect: `codex-sol-high-execution-plan.md`. Confidence: high. Gap: none.

**D24 — `market_data/providers/*` treated as nonexistent.**
Prior: task leads named them as live adapters. Decision: do not build
against them; live provider paths are `data/thetadata_adapter.py`,
`data/options_flow/adapter.py`, and the keyless Yahoo closes fetcher.
Evidence: options-validator audit §5 — only stale `.pyc` files; nothing
tracked in git. Opposing: none. Tradeoff: none. Effect: packet scoping.
Confidence: high (repo-verified). Gap: none.

**D25 — Reproducibility manifests adopted; canary fixtures optional.**
Prior: neither in the plan. Decision: adopt small per-artifact manifests
(command, commit, lock hash, raw-data pointers); canary/golden-hash
pre-scrape fixtures are labeled engineering-judgment, low priority,
optional. Evidence: IMP-S14 (reproducible-research practice); improvement
report §6 (no rigorous source for canaries — honestly labeled). Opposing:
none. Tradeoff: trivial vs archaeology later. Effect: manifest helper
folded into packet 5; canaries left unscheduled. Confidence: high /
medium. Gap: none.

**D26 — Owner-authority and repo-charter constraints are architectural
invariants, not conventions.**
Prior: implicit. Decision: the evidence layer records and gates; it never
registers hypotheses, freezes numbers, ratifies verdicts, alters sealed
holdouts or pre-committed thresholds, writes `portfolio_state.csv`,
weakens citation bans, or creates any order-routing path. Evidence: all
three audits' "constraints" sections (charter rules, division-of-labor
directives, Ulysses contracts). Opposing: none. Tradeoff: none. Effect:
stated in every packet's constraints block. Confidence: high. Gap: none.

**D27 — Adversarial verification round accepted; all seven findings
fixed (2026-07-29).**
Prior: draft artifacts as of the first writing pass. Decision: an
independent fresh-context Sonnet-5 verifier (report:
`verification-report.md`) returned PASS_WITH_CORRECTIONS — 0 blocking, 7
correctable findings; every finding was independently re-evaluated by the
lead architect, judged supported, and applied: F01 exception-form count
21→24 (verbatim-list-not-count discipline added); F02 availability
became an interval with `public_by_ts_utc` as the conservative gating
bound; F03 SQLite WAL gate made fail-closed via an enforced single-writer
lock (both venvs measured at 3.50.4); F04 holiday count 10→11 in ledger
row SEC-S8 and provider count nine→ten in packet 3; F05 isolation-test
wording reconciled (extend coverage, never weaken); F06 equity-research
baseline recorded as 1544–1546 with re-baseline-at-packet-start
instruction; F07 packet 8 precondition now names the unrelated dirty
files to exclude from commits. Evidence: verifier report (20 checks run;
the passed checks name the specific documents/lines/commands verified).
Opposing: none — no finding was rejected. Tradeoff: none. Effect: the
seven edits above. Confidence: high. Gap: the verifier's F04 advice to
re-scan the ledger for further count errors was followed for stated
counts referenced by the deliverables; counts inside narrative research
reports (non-deliverables) were not re-audited line-by-line.
