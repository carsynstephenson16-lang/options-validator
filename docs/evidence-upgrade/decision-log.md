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

**D06 — Capture `acceptanceDateTime` in equity-research.** *(SUPERSEDED
by D28, 2026-07-29 — kept for the record.)*
Prior: implied by correction area 2. Decision (original): extend
`edgar_fetch.py` to record acceptance datetimes (additive). Evidence
(original): audit finding — `edgar_fetch.py` captures only `filingDate`;
zero "acceptance" hits in that file. What was wrong: the file-scoped grep
was generalized to "nowhere in the repo." Verified reality (Codex
preflight + two Sonnet verifications): acceptance data already exists in
`data/_sec_submissions/<CIK10>.json` (raw SEC JSON, written by
`validation_gate.py`) and is already parsed by
`market_updates/providers.py:162-183`, where it becomes `published_at`.
`edgar_fetch.py` has no per-filing metadata object to extend. Superseding
decision: see D28.

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

**D28 — Packet 1 rescoped after Codex /plan preflight (NOT_READY) +
two-agent verification; acceptance-as-published_at exposure confirmed
live.**
Prior: D06/Packet 1 as originally written (additive `edgar_fetch.py`
metadata edit). Decision: Codex's refusal was correct and its claims
verified by two independent Sonnet-5 inspections: (a) `edgar_fetch.py`
persists only filing documents, symlinks, an append-only free-text
`_fetch_log.txt`, and raw `_companyfacts.json` — no per-filing metadata
object exists to receive new keys (its own docstring at :346-349 falsely
claiming validation_gate parses the fetch log is a separate stale-doc
defect, noted, not fixed here); (b) `data/_sec_submissions/<CIK10>.json`
already caches per-filing `acceptanceDateTime` verbatim (33/57 tickers,
on-demand); (c) `market_updates/providers.py:172` sets
`published = acceptance or filing_date or retrieved_at` (test-pinned),
the Atom path uses feed timestamps, and the real local store holds ~2,557
SEC rows with acceptance-shaped `published_at` that
`options_researcher/market_context.py:87` gates on — a live, pre-existing
invariant-8 exposure. Rescope: Packet 1 = pure rule module
`market_updates/sec_availability.py` + tests ONLY (module homed in the
package because `market_updates/` uses normal imports while `scripts/` is
a non-package with a sys.path idiom); the interval wiring
(models/providers/normalizer/storage; `available_at = public_by_ts_utc`
going forward; Atom path labeled unruled; `published_at` untouched) moves
into Packet 2 with the schema it needs. A new `edgar_fetch.py` sidecar
was REJECTED (data already durably cached; a new overwrite/append
contract would be invention without a consumer). Codex's suggestion to
"replace raw-acceptance published_at semantics" was PARTIALLY adopted:
gating moves to `available_at`; `published_at` itself keeps its
provider-asserted meaning and stored history is never rewritten
(append-only; legacy rows labeled at the consumer, packet 8). Evidence:
scratchpad reports `verify-edgar-persistence.md`,
`verify-acceptance-flow.md` (file:line cites throughout). Opposing: none
found. Tradeoff: Packet 2 grows by one scope item; Packet 1 shrinks to
pure code. Effect: Packet 1/2/4 amendments + architecture §1/§6.1
corrections, this entry. Confidence: high (all claims repo-verified).
Gap: whether Atom-path SEC events should later derive a conservative
interval from their accession via the submissions cache is deferred until
a consumer needs it.

**D29 — Packet 2 (PR #14 @ 04a083a) two-lane review: APPROVE_WITH_NITS ×2,
zero blocking; merge conditioned on one small fix.**
Prior: Codex-reported completion of amended Packet 2 (draft PR #14,
branch feature/evidence-upgrade-packet-2, atop Packet 1 @ b3f3a4b).
Decision: accept both review verdicts; merge is authorized (per the
standing merge-judgment delegation: CI green — independently confirmed
SUCCESS; suite reproduced 1,572 twice; live DB confirmed unmigrated;
no concurrent churn on the touched files) ONCE the one real finding is
fixed on the branch: `market_updates/storage.py:459-480
guard_payload_update` is orphaned — called only by its own test, with no
SQL-trigger backing on `events` (unlike `ingestion_journal`'s real
BEFORE UPDATE/DELETE triggers), so the ADMITTED-row payload-immutability
invariant that docs/market_updates.md states as enforced is not yet true.
Fix = DB-level trigger blocking payload/timing-column UPDATEs on
ADMITTED rows (state-transition and `superseded_by` columns exempt) +
wire or retire the Python guard, before Packet 5 builds on the
invariant. Also: three benign macro-refresh files from an unrelated
weekly-refresh commit ride along in the branch history — declared to the
owner in the PR body rather than rebased away; and the migration
rehearsal exists as PR-body prose only (its 2,818-row count was
independently corroborated against the live store; accepted as-is).
Evidence: scratchpad reports review-p2-conformance.md,
review-p2-adversarial.md (file:line cites; red-green checks on the new
tests; cross-process flock reproduction). Opposing: none. Tradeoff:
one extra commit before merge vs merging a documented-but-unenforced
invariant. Effect: fix lands on PR #14 → mark ready → merge → Packet 3
(Thread A); Packet 6 (kalshi, Thread B) starts in parallel immediately.
Confidence: high. Gap: exact exempt-column set for the events trigger is
decided by Codex in /plan (requirement: supersession and admission-state
transitions must remain possible; payload/timing/hash columns must not).

**D30 — Packet 3 (PR #15 @ 143c77a) reviewed APPROVE_WITH_NITS ×2, merge
conditioned on one test; Packet 6 independently confirmed SHIPPED.**
Prior: Codex reported Packet 2 merged (with the D29 trigger fix), Packet 3
ready as draft PR #15, and Thread B silent. Decision (three parts):
(a) **Packet 3 merge authorized after one fix**: the duplicate-`source_id`
guard in `market_updates/registry.py` has zero test coverage — mutation
testing (guard deleted → full focused suite stayed green) proves it is
unverified, while every other loader guard turned genuinely red under the
same treatment. One test asserting `load_registry` refuses two entries
sharing a `source_id` is required pre-merge. Everything else conformed:
18 entries; all ten `build_providers()` classes matched by name+class;
bans lock-tested (a widened Daloopa entry with a self-consistent hash
turned the lock test red, then reverted); registry_version stable under
whitespace, sensitive to entries; migration 0004 round-tripped
0003→0004→0003→0004 against a COPY of the live store with 2,818 events /
20 provider_runs unchanged and Packet 2's immutability trigger unaffected;
one mechanically-required 2-call-site test edit is legitimate (a new
required kwarg).
(b) **Two Codex claims corrected for the record**: "focused tests: 28" is
an assertion count, not a test count (actual: 10 in the new module, 18
including the migration module); and the "2,818 events + 20 provider runs
snapshot rehearsal" left no committed artifact — the substance was
independently re-established by the reviewer's own rehearsal, but the
claim as stated was unverifiable when made. Standing correction to Codex:
report measured test counts and leave a rehearsal artifact (or say the
rehearsal was transient).
(c) **Packet 6 is DONE**: independently audited as merged to kalshi main
at `104947d` ("feat(research): capture versioned settlement evidence"),
2,304 tests passing (2,252 baseline + 52). Spec-correct on every checked
item: BBB regex routes anything outside RRx/CCx/AAx (incl. Pxx) to
UNRECOGNIZED and quarantines; ordering is issuance+BBB with a logged
receipt-time tiebreak; all four quarantine reasons present; the freeze is
DST-aware with the +7-day bound and 11 AM delayed review, and a frozen
label is structurally immutable to post-expiration versions; exchange
divergence produces a human-review artifact, never an auto-correction;
the shadow/live isolation test was STRENGTHENED (new AST check failing on
any unauthorized import of the Packet-6 modules); guard-protected files
untouched. Note: an unrelated branch `codex/packet-6-execution-validation`
is a name collision (VWAP/fee/latency work), not a second attempt.
Evidence: scratchpad reports review-p3-conformance.md,
review-p3-adversarial.md, status-p6-kalshi.md. Effect: Thread A → fix +
merge #15 → Packet 4; Thread B → Packet 7. Confidence: high. Gap: the
registry's ban preservation rests on one content-locking test; if the
registry grows, consider a structural rule (banned entries must have
empty purposes) rather than per-entry assertions.

---

**D31 — Packet 5's migration number was already taken; renumber to 0006.**
Prior: the plan assigned Packet 5 "migration 0005". Decision: Packet 5's
additive migration is **0006**, and Codex must confirm the head revision
before authoring rather than trusting the plan's number. Evidence:
`market_updates/migrations/versions/` on
`origin/feature/evidence-upgrade-packet-4` reads 0001 legacy baseline,
0002 EC-1 expand, 0003 admitted immutability, 0004 provider-run registry
version (packet 3), 0005 xbrl_facts (packet 4); the plan was written
before packets 3 and 4 chose their numbers. Opposing: alembic revision IDs
are strings, so a collision surfaces as a broken `down_revision` chain
(two heads) rather than silent corruption — arguably self-correcting.
Rejected as a reason to leave it: it wastes a Codex cycle, and a
two-heads error discovered late tends to get "fixed" in a hurry.
Tradeoff: the plan's number will itself go stale if another packet lands
first — mitigated by the confirm-the-head instruction. Effect: plan
§Packet 5 expected-files and schema-effects amended. Confidence: high
(read the versions directory directly). Gap: none.

---

**D32 — Legacy rows are blanket-ADMITTED with no row-level marker.**
Prior: the plan assumed `admission_state` distinguishes gated from
ungated evidence. Decision: Packet 5's migration stamps
`admission_reason='legacy-grandfathered'` on rows that are `ADMITTED`
with a NULL `admission_reason`; Packet 8's consumer labels a NULL reason
on an ADMITTED row as `grandfathered-legacy` rather than gate-passed.
Gates are NOT re-run retroactively. Evidence:
`0002_ec1_expand.py:161` executes `UPDATE events SET
admission_state='ADMITTED'` across every pre-existing row; the rationale
("rows predate admission-state enforcement and were already consumable")
is journalled into `ingestion_journal` only, and `admission_reason` is
left NULL — so nothing *on the row* separates evidence that passed gates
from evidence that predates them, and the packet-8 consumer would read
both as fully gated. Opposing: re-running admission over history would be
more principled — every row would then carry a real verdict. Rejected for
now: it would retroactively quarantine an unknown fraction of live
history behind gates designed for forward ingestion, against this
program's own rule that stored history is never rewritten. Tradeoff: a
consumer that ignores `admission_basis` still reads grandfathered rows as
admitted — the label only helps a consumer that looks; accepted because
mass quarantine is worse and this stays owner-reversible. Effect: plan
§Packet 5 and §Packet 8 exact scope amended; no trigger change needed
(the 0003 trigger already permits updating `admission_reason` on ADMITTED
rows). Confidence: high on the mechanism; medium on the choice not to
backfill — a judgment call the owner can reverse. Gap: whether any
consumer outside this program relies on legacy rows reading as ADMITTED.

---

**D33 — Packet 8 does not block on Packet 5; threads rebalanced.**
Prior: the plan made Packet 8 depend on packets 2 *and* 5, and put it at
the tail of Thread A. Decision: Packet 8 starts immediately in parallel;
remaining layout is Thread A 5 → 9 (equity-research), Thread B 8
(options-validator). Standing rule added: never run two Codex threads
against the same repository checkout. Evidence: every column Packet 8
reads is live on `main` today — `available_at` is written as the
conservative `public_by_ts_utc` bound for SEC submissions-path rows and
deliberately NULL for Atom-feed rows
(`tests/test_sec_availability_wiring.py:104-153` asserts both;
`docs/market_updates.md:139-146` documents it), and `admission_state`,
`admission_reason`, `stale_after`, `purpose_authority` all exist from
migration 0002. Packet 5 adds writers and reason codes, not columns this
consumer reads. Opposing: the original dependency existed to stop the
consumer hardening against semantics that might still move — partially
upheld, since the D32 legacy stamp *is* a moving seam; handled by having
Packet 8 derive `admission_basis` from a NULL reason, which is correct
both before and after the stamp lands. Tradeoff: the conformance fixture
must stay byte-identical across two repos while either thread might
author it first — handled by naming the authoring side in both packet
texts. Effect: Thread B is not idle after kalshi, and the highest-value
consumer fix ships sooner — the bridge still gates on `published_at`,
which is raw SEC acceptance time, a live look-ahead exposure over ~2,557
rows (D28). Confidence: high on the column facts; medium on the
parallelism being conflict-free. Gap: none blocking.


---

**D34 — `availability_basis` collides across the repo boundary.**
Prior: the plan had Packet 8's consumer emit a field named
`availability_basis` with values `available_at` | `published_at-legacy`.
Decision: rename the consumer-side label to `gating_basis`, and derive it
in the consumer — never copy the producer's payload string. Evidence:
`market_updates/providers.py:125,185-191` already writes
`availability_basis` into the raw payload with a disjoint vocabulary
(`submissions-acceptance-interval`, `submissions-acceptance-missing`,
`submissions-acceptance-invalid`, `feed-timestamp-unruled`), and Packet 4
adds a fifth value `filed-date-conservative`. Opposing: one name for one
concept is cleaner, and the vocabularies could be merged. Rejected: they
answer different questions — the producer's records how availability was
*derived*, the consumer's records which column was actually *gated on*;
merging would force one of them to lie. Tradeoff: two field names to
learn. Effect: plan §Packet 8 exact scope and schema effects amended.
Confidence: high. Gap: none.

---

**D35 — Packet 4 (PR #16) REQUEST_CHANGES; Packet 7 approved with a
coverage caveat.** Decision: (a) PR #16 does NOT merge until two defects
in the append-only/availability core are fixed; (b) Packet 7 (kalshi
`0d78b16`) stands as merged, with a small follow-on (7a) to close four
untested guards before that thread leaves the repo; (c) two Codex
reporting claims corrected for the record.

Evidence — Packet 4, two independent Sonnet-5 high-effort reviews. The
conformance pass returned APPROVE with zero blocking items: diff surface
exactly the 8 authorized files against the true base `e01bff2` (local
`main` was three commits stale, which is why the base had to be corrected
mid-review); migration correctly renumbered 0004→0005 with a linear
revision graph; the custom-tag downgrade, availability boundary math
(filed 2021-01-14 8-K → 2021-01-15 06:00 ET = 11:00 UTC, matching the
test's 10:59/11:00 assertions), and DB triggers all verified by execution
rather than reading; test counts 12/20/1595 reproduced exactly against a
measured 1583 baseline; the committed fixture proven genuine by
re-fetching the live SEC endpoint and matching SHA-256 and byte length.

The adversarial pass returned REQUEST_CHANGES on two blocking defects,
both inside the invariant this program exists to protect:
1. **Append-only has a real hole.** `0005_xbrl_facts.py:19-53` puts no
   UNIQUE constraint on the natural key (`cik`, `taxonomy`, `tag`, `unit`,
   `period_start`, `period_end`, `accn`). A second `ingest_concept()` /
   `append()` for the same real accession with a different value gets a
   fresh `fact_id` and is silently accepted; the reviewer executed this
   attack through the public API against the genuine UBER fixture and
   `fact_asof()` then returned the forged value in preference to the real
   one. The two application-layer checks meant to prevent it
   (`scripts/xbrl_facts.py:468-471`, `:478-479`) both stayed GREEN when
   deleted — i.e. unenforced at the DB layer and unverified at the test
   layer simultaneously.
2. **The holiday table covers only 2026.** `sec_availability.py:42-58`
   silently treats every pre-2026 federal holiday as an ordinary EDGAR
   business day: `filed_date_conservative_available_at(2020-01-17)`
   computes dissemination on 2020-01-20, which was MLK Day with EDGAR
   closed. The defect predates this PR (packet 1's module) but packet 4
   is the first consumer to run it against real historical dates — its
   own fixture is 2019-2021 filings.
Mutation results: 9 of 12 guards went RED (naive-datetime refusals,
custom-taxonomy classification, the downgrade, `availability_basis`, the
`fact_asof` `<=` boundary, fair-access sleep, retry codes, both DB
triggers); 3 stayed GREEN (the two above plus naive stored `available_at`
on read). Non-blocking: `DROP TRIGGER` / `PRAGMA writable_schema` bypass
immutability (inherent to SQLite, shared with packet 2's trigger, not
novel); `XbrlFactStore` never acquires packet 2's single-writer lock,
which is inert only because it does not yet share the live db file — it
must acquire the lock before it ever does, given the venv's measured
SQLite 3.50.4 is below this repo's own WAL-safety floor.

Opposing view considered: both defects are latent rather than live —
nothing today writes a conflicting accession, and no production query
runs against pre-2026 filed dates. Rejected as grounds to merge and defer.
A silent wrong answer from an availability rule is precisely the failure
this architecture was commissioned to make impossible, and "the hole is
there but nothing has fallen in yet" is the reasoning that lets it ship.
Both fixes are small and local.

Note on reviewer discipline, recorded because it cuts the other way: the
adversarial reviewer initially flagged the conservative-basis function as
accidentally optimistic, then fetched the governing SEC filing-status
rule, disproved its own finding, and retracted it in the report. The
direction is genuinely conservative — over-cautious by roughly one
business day. A retracted finding is a working process, not a wasted one.

Evidence — Packet 7 (kalshi `0d78b16`), one combined conformance +
adversarial pass: APPROVE_WITH_NITS. It extends `research_capture.py`'s
existing lineage identity rather than duplicating it, is fail-closed in
both loaders, touches no guard-protected file, deletes no assertion
(all four test diffs are pure insertions), and leaves the halt and
order-placement paths alone. 2320 tests vs the 2304 parent baseline =
exactly the 16 added. `tools/check_logging_completeness.py` re-run
against the real production DB reproduced 1109/1109, 731/731, bucket-B 0,
orphans 0. Two caveats: (i) the artifact `a329e4d0d1abe77c` was ALREADY
refused before this commit by a schema_version check that fired first, so
runtime behaviour is unchanged and only the diagnosis improved — the
report's framing overstated it; (ii) four guards survived deletion with
the full suite green: training-cutoff-in-future, `feature_schema_sha256`
mismatch, `training_ids_sha256` validity, and — most importantly —
`main.py::_serialize_source_timestamp_map`, the actual production entry
point for the F06 timestamp fix, which passed even when mutated to drop
every real provider timestamp, because no fixture populates
`FusionResult.source_evidence`.

Tradeoff: 7a costs a thread a short detour before it switches repos.
Accepted — this is the second consecutive round where something was
recorded as enforced while nothing exercised it (D29's orphaned
`guard_payload_update` was the first), and a pattern at two occurrences
is a process gap, not a coincidence.

Effect: standing instruction added for every remaining packet — a guard
is not done until it has been shown to fail with the guard removed, and
"N tests passed" is never evidence that a specific guard works. Thread A:
fix PR #16 (B1 unique key + tests, B2 holiday coverage fail-closed, B3
writer-lock precondition) → merge → packet 5. Thread B: packet 7a (four
tests + the two kalshi AGENTS.md lines) → packet 8 in options-validator.
Confidence: high on both blocking defects (both demonstrated by
execution, not argued). Gap: the holiday fix needs official per-year
sources for every year the store will span; only 2026 is currently
ledgered (SEC-S8).

**D36 — Packet 5 (PR #17) REQUEST_CHANGES on a live mass-quarantine defect;
CI collection gap closed first; Packet 7a verified; Packet 8 merge-ready.**
Decision: (a) PR #17 does NOT merge until the freshness-window defect is
fixed and the missing horizon fails loud; (b) equity-research CI switched to
`pytest` and pushed BEFORE opening PR #17, so this is the first packet PR
gated by the whole suite; (c) Packet 7a stands verified by independent
mutation; (d) Packet 8 cherry-picked clean onto options-validator `main` as
PR #16, all checks green, awaiting owner merge.

Evidence — Packet 5, one independent adversarial pass re-deriving every
claim by execution rather than reading the implementer's report. The
guard-removal claims hold: all eight gates go red when individually
neutralized (authority 2 failed, missing availability 2, unversioned rule 1,
lookahead 1, extraction/drift 2, stale-at-admission 2, corroboration 1,
verify-support 4), returning to 18 passed / 485 subtests on restore. Two
defects the protocol structurally cannot catch survived it.

B1, blocking: `ClaimTypePolicy.freshness_window` is never set anywhere in the
codebase, so `stale_after()` returns None for every non-`immutable` class
(`admission.py:94-95`), and `admit()` reads None as expired
(`admission.py:297-308`). Measured over all eight registered claim types,
`earnings.date`, `macro.series`, `market.quote` and `news.discovery` return
QUARANTINED / stale-at-admission unconditionally; mapped onto
`_INGESTION_ROUTES`, that is 7 of 12 live routes — bea, bls, eia, fred,
treasury_fiscal_data, twelve_data, gdelt. `storage.py:410` is the production
path. This is NOT latent: `admission_enabled` defaults to True
(`config.py:215-219`). Root cause is a semantic collision — the producer
returns None for "no horizon defined", the consumer reads it as "expired".
The 1858-test suite is green because every gate test builds an `immutable`
`BASIC_POLICY` with a synthetic `claim.basic` claim type that is not in
`CLAIM_TYPE_POLICIES`; the registered policies are never run through
`admit()` by any test.

B2, blocking as a process matter: `requires_support=True` occurs exactly once
in the repository, in `tests/test_admission.py:44`. All eight registered
policies set it False, so the support gate and all of `verify_support.py` are
unreachable in production. Third consecutive round of the D29/D35 pattern —
recorded as enforced, exercised by nothing real.

Found sound in Packet 5: migration `0007` correctly numbered on
`0006_xbrl_fact_natural_key` (superseding D31, whose `0006` was taken by
Packet 4's review fix) with a single-head chain; legacy rows stamped
`legacy-grandfathered` before the non-null triggers install, with the row
count journaled; `conflicts_with` carries a canonical-order CHECK making
mirrored duplicates unrepresentable; `downgrade()` reverses only the label
transform it made.

Evidence — the CI collection gap. `unittest discover` imported but never
collected six pytest-native modules totalling 209 tests. Fixed on
equity-research `main` (`pytest`, green at 1832 in 3m04s, inside the
15-minute budget) and pushed before PR #17 opened, so the ordering win is
real rather than promised. Pushing also required unbreaking the fresh-clone
dead-citation gate: the Schwab README pointer was written as
`options-validator/docs/schwab-market-data-setup.md`, and `CITATION_PATH_RE`
is unanchored, so it matched the `docs/...` substring and read a
cross-repository reference as a repo-relative citation. Reworded the pointer;
the guard was left exactly as strict as it was. options-validator was
checked for the same gap and does not have it — zero module-level bare
`test_` functions, no fixtures or parametrize, pytest not a dependency, so
`unittest discover` is a complete gate there.

Evidence — Packet 7a (kalshi `8ee715a`). Verified independently rather than
accepted: the F06 guard D35 singled out as passing while mutated now fails
when `_serialize_source_timestamp_map` is neutralized (1 failed / 12 passed)
and passes on restore (13 passed), because the new test finally populates
`FusionResult.source_evidence`. The two AGENTS.md lines are present.

Tradeoff on B1: fixing it needs per-class freshness windows, which are frozen
numbers and therefore owner-typed under the standing rule; the implementation
must not pick them. Accepted, because the alternative is an implementer
choosing decision-eligibility horizons by default. The interim requirement is
that a non-`immutable` class with no window must refuse loudly at
construction or config load instead of silently quarantining data.

Effect: PR #17 blocked pending B1 fix + a table-driven test over every entry
in `CLAIM_TYPE_POLICIES` + an owner-typed window table; B2 needs either
wiring or an explicit amendment naming the packet that wires it. Packet 8
(options-validator PR #16, `024ccd8`) is green and merge-ready and should
land BEFORE Packet 5, so B1 is caught by behaviour rather than inspection —
its gating is correct, which is exactly why an unfixed Packet 5 would present
as "the board quietly stopped receiving new evidence" rather than an error.
Confidence: high on both defects, demonstrated by execution. Gap: the kalshi
repository is 70 commits ahead of and 2 behind its origin, so Packets 6, 7
and 7a exist only locally; reconciling that push is an owner decision, not
recorded here as done.

**D37 — Freshness-window proposal WITHDRAWN; B4 (no temporal provenance
outside SEC) found; packet 5 resequenced into 5A/5B/5C.** Decision: (a) the
three windows are NOT frozen and must not be typed; (b) `fast=12h` and
`slow=100d` are rejected as final policy, `event_driven=7d` provisionally
accepted but only after temporal provenance exists; (c) packet 5's remaining
scope splits into 5A temporal provenance, 5B typed earnings claims, 5C
source-specific expiry, with packet 8 board authority gated on parity against
H7's `gating_v3` store across all 15 names.

Evidence — the withdrawn proposal's headline claim, "the numbers unblock six
of seven routes", is false, reproduced independently by execution with the
recommended windows applied and availability fields as the non-SEC providers
actually leave them: `fred`, `bls`, `bea`, `eia`, `treasury_fiscal_data`,
`twelve_data` all return QUARANTINED / temporal-missing-availability, and
`gdelt` is blocked before staleness. The windows unblock zero routes.

B4, blocking: `public_by_ts_utc` and `availability_rule_version` are populated
in exactly one place — `providers.py:206-207`, inside the SEC submissions
parser. Every other provider constructs `RawSourceItem` without them, so they
default to None (`models.py:105-106`), and `admit()` quarantines at
`temporal-missing-availability` (`admission.py:225-238`), a gate that fires
before the staleness gate the windows control. B1 was masking B4: with
`stale_after` returning None for every non-immutable class, nothing reached
far enough down the gate order to reveal that availability was missing too.

B3 restated one layer deeper: `earnings.date` is not merely blocked by the
corroboration gate, it has no production route at all. The claim types
actually produced are `sec.filing_event`, `sec.numeric_fact`,
`company.publication`, `central_bank.publication`, `macro.series`,
`market.quote`, `news.discovery`. SEC filings become `sec.filing_event`; IR
records become `company.publication`; nothing extracts or stores a typed
earnings date. Further: `claim_type` is written to the journal but not the
event row, so no typed date, fiscal period, status, or corroborating evidence
IDs are persisted — an admitted earnings row could not feed the H7 gate even
if one existed.

Two D36 claims corrected. First, "the windows are the only edit left for B1"
is wrong: `tests/test_admission.py:240-248` asserts every non-immutable policy
raises, so populating windows breaks that test by design and it must change in
the same edit. Second, D36 and PR #16 both stated that the options-validator
board excludes quarantined rows; `market_context.py` has no live consumer —
only `tests/test_market_context.py` references it. That is implemented
filtering, not an active end-to-end board path, and the packet 8 blast-radius
argument was overstated on that point. Scope facts that compound it: the
market-updates watchlist is 4 names against H7's frozen 15, and `twelve_data`
is `enabled = false`.

Accepted from the review without independent re-derivation, and flagged as
such: FRED's clock is the observation date rather than real-time availability,
so a quarterly observation dated 2026-04-01 but first available 2026-07-30 is
stale on arrival under a 100-day window anchored on `published_at`; Twelve
Data effectively uses fetch time; `corroboration_groups` is an unvalidated
list of strings, so passing "issuer" satisfies the count without proving
matching evidence exists; and an 8-K under Item 2.02 often republishes the
issuer's own press release, so SEC and IR are not automatically independent
channels. The ~91-day BEA advance-GDP interval was confirmed against the
official calendar, so the cadence assumption was sound — it simply does not
justify sharing one window with business-day Treasury data.

Tradeoff: resequencing costs a packet boundary and delays PR #17 further.
Accepted, because the alternative is freezing owner-typed numbers against a
system where no route can reach the gate those numbers control — which would
have produced a plausible, tested, entirely inert change and burned the
owner's one-shot number-freezing authority on it.

Effect: PR #17 stays blocked; no numbers typed; 5A is now the critical path.
Confidence: high — every load-bearing claim above was reproduced by execution
in this session.

Method note, recorded because it generalizes: the defect was found by running
every production route end-to-end and reading the FIRST failure, rather than
the failure being looked for. Checking the gate you know is broken hides every
gate upstream of it. This joins "delete the guard and confirm red" (D35) and
"drive the registered config table, not a fixture that resembles it" (D36) as
a standing check.

**D38 — `available_at` and `freshness_anchor` split into two clocks; 5A
rescoped to the parser layer; three provider contracts corrected.** Decision:
(a) temporal provenance carries two distinct fields, not one; (b) 5A owns
provider/parser provenance only — the production admission matrix moves to 5C;
(c) the SEC, FRED and Twelve Data contracts recorded in the first 5A brief
were wrong and are corrected here; (d) retrieval time is permitted as a
labelled conservative availability bound and forbidden as a freshness anchor.

Evidence — the sequencing contradiction, measured. The first 5A brief demanded
a production admission matrix over every route while preserving the rule that
non-immutable policies raise. With no windows set, `fred`, `twelve_data` and
`gdelt` raise `ValueError` at record construction and never reach the temporal
gate; only `sec_edgar` (immutable) reaches it and returns
QUARANTINED / temporal-missing-availability. Six of seven routes are therefore
unreachable until 5C supplies windows, and the matrix as specified could not
execute. The earlier D37 reproduction reached the gate only because the
harness injected windows via `replace()` — an artifact the production path
cannot reproduce.

Evidence — three corrected contracts, all Repo-verified. (i) Only the
structured `sec_edgar` submissions parser populates the availability interval;
`sec_edgar_atom` and `sec_companyfacts` populate neither field. Atom should
inherit provenance by accession from the canonical submissions record or stay
discovery-only; companyfacts has no accession or acceptance timestamp on its
aggregate record and must use Packet 4's conservative XBRL filing-date rule or
remain unresolved. (ii) FRED is queried with `series_id, api_key,
file_type=json, sort_order=desc, limit=2` — no `output_type`, no real-time
period — so the returned `realtime_start` describes the query's current
information set rather than first publication, and the no-API-key
`fredgraph.csv` fallback carries no real-time field at all; initial-release
data requires a vintage/ALFRED-style query. (iii) Twelve Data `/quote` is
called with no `interval` and the parser reads `row["close"]`, so `datetime`
is a daily bar's opening time, not the quoted price's timestamp. Both were
described as "free wins, already captured in payload" in the first brief;
both had the right field name and the wrong semantics, decided by query
parameters the brief never examined.

D37's "absolute ban on retrieval time" is superseded. It conflated two clocks.
Retrieval time never overstates availability — a replay before first capture
demonstrably could not see the record — so it is a legitimate conservative
bound for `available_at` when labelled `observed-at-retrieval`. What it must
never do is reset freshness. Collapsing the two is what makes a repeatedly
fetched stale quote look current while a genuinely fresh release looks stale.
Effect: provenance now returns a typed EXACT / BOUNDED / UNRESOLVED result,
UNRESOLVED is an explicitly successful outcome, and rule identity (`rule_id`,
`rule_version`, `governing_source_url`, `governing_effective_date`,
`captured_at`, `source_snapshot_hash`, `coverage_horizon`) is kept separate
from evidence metadata — a document retrieval date is not a rule version.
Calendar coverage is fail-closed, following `EdgarHolidayCalendarCoverageError`.

Also required and recorded: macro rules must distinguish initial release,
revision, and current-vintage retrieval, because a release calendar alone
cannot timestamp a revised value; and the 5A matrix must run real parser
fixtures rather than hand-constructed `RawSourceItem` objects, since
hand-built records encode the author's belief about the data instead of the
data — the mechanism by which B1 and B4 both hid.

Tradeoff: 5A ships narrower and the end-to-end proof slips to 5C. Accepted.
The alternative was a brief whose central deliverable cannot execute, which
would have consumed a full implementation round to discover.
Confidence: high — the contradiction and all three contract corrections were
reproduced by execution or by reading the construction sites in this session.
Method note: the first brief was written without running the matrix it
specified. Reachability is now checked before any matrix is specified, which
is the same lesson as D37 one level up — verify the thing you are about to
ask for, not the thing you are looking at.

**D39 — Packet 5A merged; the automated review lane has never run on this
program.** Decision: (a) 5A stands as merged (PR #17); (b) the Claude PR
Review workflow's `ready_for_review` trigger gap is fixed now, the expired
OAuth token and the required-check decision are owner actions; (c) 5B and 5C
remain the open scope.

Evidence — 5A verified independently rather than accepted. Suite reproduced at
exactly 1871 passed + 630 subtests on merged `main`; single alembic head
`0007_admission_gates`. The audit's one medium finding — invalid GDELT
timestamps labelled EXACT from retrieval time, fixed in `1630b35` — was
re-derived by mutation: reverting the `bounded_at_retrieval` branch to
`exact_temporal_provenance` turns
`test_invalid_gdelt_seendate_cannot_become_exact_retrieval_time` red, and
restoring returns 12 passed / 36 subtests. The fix is real, and it is the
exact failure mode D38's two-clock split was written to prevent, caught by the
guard rather than by inspection.

Evidence — the review lane, and it is the more serious finding. `gh run list`
over the review workflow shows: EC-1 packets 1, 2, 3 and 4 each ran on
`pull_request` and concluded **skipped**; packet 5 ran on `pull_request` three
times and concluded **failure**. Two independent causes. (i) The job's `if`
skips drafts, but `ready_for_review` was absent from the `types:` list, so a
PR opened as a draft is skipped at `opened` and never re-evaluated when marked
ready. (ii) `CLAUDE_CODE_OAUTH_TOKEN` exists but was set 2026-07-16 and has
since expired, which is precisely the failure the workflow's own header
comment predicts. Net: **no EC-1 packet has ever been seen by the automated
review lane**, and packet 5 merged with that check red.

A first diagnosis blaming an empty `ANTHROPIC_API_KEY` in the job env was
wrong and is retracted: the workflow authenticates by Max/Pro subscription
OAuth, so an empty API key is by design and not the cause.

This is the fifth occurrence of the program's signature pattern — recorded as
enforced, exercised by nothing. D29's orphaned `guard_payload_update`, D35's
four untested guards, D36's inert verify-support gate, D37/D38's unreachable
policies, and now the CI control whose entire purpose is catching that class
of defect. The pattern has never once been a coincidence.

Effect: trigger gap fixed and pushed (`2758b94`). Two owner actions remain —
re-run `claude setup-token` and update the secret, and decide whether the
review lane becomes a required check, since packet 5 demonstrated that an
advisory red review does not stop a merge. Recorded limitation carried from
the audit: rule snapshot hashes cover normalized retained statements rather
than downloaded source bytes, disclosed in the source ledger. An unrelated
pre-existing `uv.lock` change remains uncommitted and was not merged.
Confidence: high — every claim above was reproduced by command in this
session.
