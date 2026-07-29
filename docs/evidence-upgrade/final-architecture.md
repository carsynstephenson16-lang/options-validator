# Evidence-Ingestion Architecture — Final (v1)

Date: 2026-07-29. Author: Claude Fable 5 (lead architect), from three
Sonnet-5 repository audits, four Sonnet-5 primary-source research reports,
and an independent adversarial verification pass (see
`verification-report.md`). Owner: Carsyn Stephenson.

Scope: one evidence-ingestion contract across `equity-research`,
`options-validator`, and `kalshi-weather-bot` (checkout: `~/Claude`),
supporting trading research, paper-trading, and settlement labeling.
Governing goal: unsupported, stale, temporally unsafe, corrupted, or
weakly sourced evidence must never gain decision authority.

Provenance note: the previously circulated evidence-ingestion plan and
"Evidence Architecture Corrections, Revision 3" were not found as documents
anywhere reachable (three repos + worktrees, Desktop, Downloads, Documents,
Google Drive, Notion — searched 2026-07-29). This architecture audits the
commissioning prompt's 23 invariants (standing for the earlier plan) and 5
correction areas (standing for Revision 3) against repository reality and
primary sources. Where this document deviates from an invariant, the
deviation is recorded in `decision-log.md`.

---

## 1. Current-state findings (verified 2026-07-29)

Baselines (all commands actually run by auditors this session):

| Repo | HEAD | Branch | Suite | Lint/types |
|---|---|---|---|---|
| options-validator | `eb97be9` | feature/strategy-enhancement | 2109 unittest, OK, offline | ruff clean, pyright 0 errors |
| equity-research | `adcb0c9` | main (+1 ahead origin) | 1544–1546 unittest, OK, offline (count drifted +2 between two same-day runs at the same HEAD; re-baseline at packet start) | none configured (compileall only) |
| kalshi-weather-bot | `42d3113` | main | 2252 pytest, OK, offline | none configured |

The three repos already contain most of the primitives this architecture
needs. **The design below is an alignment-and-completion program, not a
green-field build.**

Prior art that the architecture reuses (file:line evidence in the audit
reports):

- **options-validator** — `research/receipts.py` (content-hashed immutable
  receipts, create-once, atomic hardlink publish, macOS `F_FULLFSYNC`);
  `research/hashing.py` (`canonical_json`, versioned `config_hash` /
  `diagnostic_source_hash` v3); `options_researcher/h7_event_ledger.py`
  (hash-chained typed-event append-only ledger with an honest
  "crash-detecting, not crash-atomic" model); `h7_data_gate.py` (refuses to
  write output without a hash-verified link to the upstream receipt);
  `options_researcher/flow/` (typed availability/quarantine states,
  machine-readable `authority: DISPLAY_ONLY_RESEARCH_NONCAUSAL` tag);
  `tools/h7_refresh_earnings.py` (append-raw/promote with supersession);
  `data/options_flow/raw_store.py` (manifest+receipt-bound raw capture).
- **equity-research** — `market_updates/` (typed providers → identity-hashed
  events → append-only SQLite with `schema_version`, provider watermarks,
  `provider_runs` receipts, trust levels) paired with options-validator's
  `options_researcher/market_context.py` (read-only, tz-aware, `as_of`-gated
  consumer that refuses naive timestamps) — the one working cross-repo
  producer/consumer contract today; `integrations/openbb_adapter/schemas.py`
  (hard-coded `canonical: false` provenance envelope);
  `scripts/research_controls.py` (typed evidence→decision enums);
  `timeline_ledger.json` per-record `parser_version`+`rule_version`.
- **kalshi-weather-bot** — `claude/storage/research_provenance.py`
  (content-addressed `blob_root/<sha[:2]>/<sha>.json.gz` raw store;
  idempotent-insert-or-`ProvenanceConflict` immutable typed tables incl.
  `cli_reports`-adjacent research tables, `weather_verifications`,
  `exchange_settlements`; fail-closed `evaluate_freshness()` and
  `assert_available_at_decision()`); `storage/shadow_decisions_log.py`
  (multi-writer atomic append-only ledger with a documented race
  postmortem); `storage/research_capture.py` `cohort_id` =
  f(run_id, regime_id, code_sha, config_hash);
  `data/nws_cli_client.py` (fail-closed morning-partial CLI detection).

Verified gaps the architecture must close:

1. equity-research `scripts/edgar_fetch.py` captures only `filingDate`,
   never `acceptanceDateTime` — sub-day point-in-time precision does not
   exist there today.
2. equity-research raw payload archive is id-keyed with skip-if-exists —
   a changed payload for the same source item id is silently never
   re-archived; not content-addressed.
3. equity-research has no hash chain, no Alembic, no linter/type-checker.
4. kalshi legacy calibration-artifact loading lacks lineage gating, and the
   legacy runtime path lacks persisted issue/valid timestamps (independent
   review 2026-07-27, findings F05/F06); the *new* research_provenance layer
   already solves both — the fix is extension, not invention.
5. kalshi has no CLI product version-chain: multiple versions of the same
   Daily Climate Report are not ordered by issuance time + WMO BBB sequence,
   and no quarantine exists for contradictory chains.
6. No repo has: a declarative versioned source registry, freshness classes
   with re-verification dates, a claim-level verify-support step, or a
   golden-question retrieval benchmark.
7. `market_data/providers/*.py` in options-validator do **not** exist (only
   stale `.pyc`); any plan naming them as live adapters is wrong.

## 2. Accepted architecture (summary of decisions)

One **shared evidence contract (EC-1)**, three local implementations:

- **Contract incubates in equity-research** (invariant 2 upheld): the
  `market_updates` store is extended to the full contract; it is already the
  only working cross-repo producer.
- **Pattern replication, not premature code sharing** (invariant 3 upheld):
  options-validator and kalshi implement the same contract semantics with
  their existing primitives; a shared package is extracted only after two
  repos consume a stable interface (checkpoint gate in §12). Conformance is
  enforced by **shared fixture vectors** (JSON test vectors copied into each
  repo's offline test suite), not by a shared import.
- **Domain corrections land in their home repos**: SEC availability in
  equity-research; NWS/WMO/Kalshi version-chain rules in kalshi-weather-bot.
  This is the documented reading of the incubation invariant — the
  *contract* incubates in one place; domain rules cannot.
- **Storage stays what each repo already uses**: SQLite (+Alembic, batch
  mode) where SQLite already exists (equity-research `market_updates`;
  kalshi when its stores are touched); immutable files + receipts + hash
  chains in options-validator. No SQLite is introduced into
  options-validator (no demonstrated requirement; invariant 19 is scoped to
  relational stores — recorded as a deviation in the decision log).
- **Hard gates + separate quality dimensions; no composite score**
  (GRADE-style ordinal confidence moved only by named, logged reasons).
- **Fail-closed everywhere**: selector drift, missing availability data,
  contradictory version chains, and stale claims quarantine; they never
  default open. This matches the strictest existing house style (kalshi).

Rejected outright (with evidence, see decision log): provenance semirings;
composite weighted source-quality score; Memento/WARC and RFC 3161
timestamping; signed feeds; Airflow; any always-on service; a "2-minute SEC
dissemination" latency constant (shown fabricated — not in the PDS spec).

## 3. End-to-end data flow

```
                      ┌──────────────────────────────────────────────┐
                      │ SOURCE REGISTRY (versioned, per repo)        │
                      │ authority class, scope, format, access,      │
                      │ fallback chain, allowed purposes, health     │
                      └───────────────┬──────────────────────────────┘
                                      │ registry_version recorded on capture
 fetch (network, never in CI)         ▼
 ┌────────────┐   wire bytes   ┌─────────────┐  decoded   ┌──────────────┐
 │  PROVIDER   │──────────────▶│ RAW CAPTURE │───────────▶│  NORMALIZE   │
 │  ADAPTER    │  + request/   │ content-    │ decode hash│  normalized  │
 │ (dry-run    │  response     │ addressed   │            │  hash        │
 │  default)   │  receipt      │ sha256 blob │            │              │
 └────────────┘               └─────────────┘            └──────┬───────┘
                                                                │ typed selector
                                                                ▼ (fail-closed drift)
                                                        ┌──────────────┐
                                                        │  EXTRACT     │
                                                        │  claim rows, │
                                                        │  value hash, │
                                                        │  extraction  │
                                                        │  mode/conf   │
                                                        └──────┬───────┘
                                                                │
                       verify-support (separate step/model,     ▼
                       double-order judged, stakes-routed) ┌──────────────┐
                                                        │  ADMISSION    │
                                                        │ PENDING →     │
                                                        │ ADMITTED /    │
                                                        │ QUARANTINED / │
                                                        │ REJECTED      │
                                                        │ (+SUPERSEDED, │
                                                        │  conflict     │
                                                        │  links)       │
                                                        └──────┬───────┘
                                                                │ as_of-gated,
                                                                │ ADMITTED-only,
                                                                │ freshness-checked
                                                                ▼
                                             ┌────────────────────────────┐
                                             │ CONSUMERS (decision layer) │
                                             │ research context, watchers,│
                                             │ settlement labeling, memos │
                                             │ — may ABSTAIN; risk always │
                                             │ reported with coverage     │
                                             └────────────────────────────┘
```

Every stage writes an immutable receipt binding: input hashes, config/
registry versions, selector versions, and the upstream receipt hash
(mandatory chain-link, per the shipped `h7_data_gate` pattern). No LLM
performs fetch, validation, and promotion in one step (invariant 16): the
fetcher, extractor, and verify-support checker are separate steps; promotion
to ADMITTED for decision-bearing claims is rule-based or human, never the
extracting model's own say-so.

## 4. Data contracts (EC-1)

### 4.1 Evidence record envelope (per extracted claim/observation)

| Field | Semantics |
|---|---|
| `evidence_id` | Deterministic sha256 over canonical identity fields (source_id, claim_type, subject, period, selector_version) — dedup key, not content hash |
| `claim_type` | Registry-scoped enum (e.g. `sec.numeric_fact`, `weather.cli_high`, `kalshi.settlement_rule`) |
| `source_id`, `registry_version` | Registry reference + the registry version in force at capture |
| `independence_group` | Same string = same root origin; corroboration counts distinct groups only |
| `raw_sha256`, `decoded_sha256`, `normalized_sha256`, `value_sha256` | Layered hashes (invariant 6): wire bytes; decoded (e.g. un-gzipped/decoded JSON) bytes; canonical normalized form; extracted value canonical form |
| `selector` | Typed selector spec + `selector_version` (see §7) |
| `observed_at` | Valid time — when the fact held/occurred in reality (tz-aware UTC) |
| `available_at` | Earliest defensible public-availability instant (tz-aware UTC), computed by a versioned per-domain rule (§6); business attribute, not a bitemporal axis |
| `recorded_at` | Transaction time — system-assigned at insert, never editable |
| `freshness_class`, `stale_after` | `immutable` / `slow` / `fast` (+ optional `event_driven`); `stale_after` computed from class; overdue ⇒ not decision-eligible until re-verified |
| `admission_state` | `PENDING` → `ADMITTED` \| `QUARANTINED(reason_code)` \| `REJECTED(reason_code)`; plus `superseded_by` link (never a state overwrite) |
| `extraction_mode`, `extraction_confidence` | e.g. `structured_api` / `embedded_text` / `html_selector` / `ocr` (spec only, §7); confidence is about the extraction, separate from source reliability |
| `purpose_authority` | `decision` \| `display_only` \| `discovery` — machine-readable ceiling, following the shipped `authority` tag pattern |
| `verify_support` | `{status: supported|unsupported|not_checked, method, double_order: bool}` for LLM-extracted claims (§8) |
| `confidence_level` | Ordinal HIGH/MODERATE/LOW/VERY_LOW, moved only by named, logged up/down reasons (GRADE mechanism); never a numeric blend |
| `run_id` | Ingestion-run receipt link (lineage, §9) |

Separated concerns (never collapsed into one number): source reliability
(registry + provider metrics), claim support (verify_support +
corroboration), extraction confidence, temporal availability
(`available_at` + freshness), decision eligibility (`admission_state` +
`purpose_authority` + staleness at read time).

### 4.2 Version chains

Corrections and restatements are new rows with `supersedes` /
`superseded_by` links; in-place UPDATE of an evidence row is forbidden
(matches SQL:2011 system-time discipline and every existing repo ledger
rule). "As-first-reported" queries return the row whose `available_at` ≤
the query's as-of instant; later restatements never silently replace
earlier facts in historical reads.

### 4.3 Consumer contract

A decision at instant `as_of` may use a record iff: `admission_state =
ADMITTED`, `available_at <= as_of`, `purpose_authority = decision`, and the
record is not stale at `as_of` (or the consumer explicitly logs a
stale-accepted override with a reason). Consumers must support ABSTAIN as a
first-class outcome; any reported error/risk metric for admitted claims is
paired with its coverage (fraction answered), and abstention thresholds +
a minimum-coverage floor are pre-registered together, not tuned post hoc
(selective-prediction consequence; see `research-method.md`).

## 5. Source registry design

One declarative registry file per repo (JSON, e.g.
`data/source_registry.json` in equity-research; kalshi and
options-validator adopt the same schema in their conventional locations),
schema shared via EC-1 fixtures:

```json
{
  "registry_schema": "ec1-source-registry/v1",
  "registry_version": "<content hash of entries>",
  "entries": [{
    "source_id": "sec-edgar-companyfacts",
    "authority_class": "governing-primary",
    "scope_claim_types": ["sec.numeric_fact"],
    "access": {"method": "https-json", "rate_limit_rps": 6.6,
               "user_agent_env": "SEC_EDGAR_USER_EMAIL"},
    "expected_format": "json",
    "update_pattern": "event-driven",
    "fallback_chain": ["sec-edgar-archives-html"],
    "allowed_purposes": ["decision", "display_only"],
    "independence_group": "sec-edgar",
    "health_checks": ["watermark_advance", "null_rate", "schema_shape"],
    "notes": "numeric financial facts MUST come from structured endpoints with accn recorded"
  }]
}
```

Rules:
- Registry edits are supersessions (new version, old retained), reviewed
  like code; `registry_version` is recorded on every capture receipt.
- **Claim-type authority rules** live here (see `source-policy.md`), e.g.:
  numeric financial facts → `data.sec.gov` structured endpoints with
  accession number recorded (HTML scrape allowed only as `display_only`
  fallback); earnings dates → SEC acceptance first, IR/PR second,
  aggregators diagnostic-only (already enforced in
  `tools/h7_refresh_earnings.py` — the registry makes it declarative);
  weather settlement values → NWS CLI product with same-agency
  corroboration (api.weather.gov / station observations), honestly labeled
  corroboration, never "independent verification"; Kalshi rules → series
  API + contract-terms PDF, both captured.
- A high-authority source **outside its scope_claim_types** cannot outrank
  an in-scope lower-tier source; scope is enforced at admission, not vibes.
- Provider self-reported quality is never accepted without an independent
  check (health metrics computed from our own receipts, §11).

Existing seeds to migrate into registry form: equity-research AGENTS.md
source-hierarchy + plugin whitelist/ban tables; kalshi
`data/stations.py` + AGENTS.md naming/settlement-station table;
options-validator `h7_refresh_earnings` hierarchy. The bans (e.g. Daloopa/
Capital IQ/Kensho/LSEG citation bans) are preserved as registry entries
with `allowed_purposes: []` — the registry must not weaken them.

## 6. Temporal semantics

- All instants are tz-aware UTC; naive datetimes are refused at write time
  (already enforced in market_updates, openbb envelope, market_context,
  research_provenance — the contract generalizes the strictest behavior).
- Zone math uses IANA keys via Python `zoneinfo`, with the `tzdata` package
  **pinned in each repo's lock file** (current: 2026.3) and its version
  recorded on receipts (`tzdata_version`).
- Calendar dates (backtest windows, config freezes) remain naive dates by
  design — they are calendar boundaries, not instants (existing
  options-validator distinction, preserved).

### 6.1 SEC availability rule (versioned: `EDGAR-FilerManual-v77-2026-03-16`)

Sourced (Filer Manual Vol. II v77 §3.2, wording identical back through v70,
Jul 2024; EDGAR hours & holiday calendar; details + citations in
`source-ledger.csv` rows SEC-*):

- `acceptance_ts` is stated by EDGAR in Eastern Time → convert via
  `America/New_York` (never a fixed offset; wrong for ~half the year).
- `filing_date`: transmission ≤ 17:30 ET on an EDGAR business day → that
  day; after 17:30 ET → next business day (06:00 ET), **except** the 24
  enumerated submission types (Forms 3/3A/4/4A/5/5A, 144/144A, the eleven
  MEF forms + POS 462B, SC 13D/A and the SCHEDULE 13D/13G families —
  24 distinct strings; encode the verbatim list, never the count) which
  keep same-day filing date and disseminate until 22:00 ET.
- EDGAR operates 06:00–22:00 ET Mon–Fri excluding the official holiday
  list; after-hours non-exception filings are **not disseminated until the
  next business day**.
- Public availability is modeled as an **interval, not an instant**
  (design choice — the SEC does not quantify dissemination latency
  anywhere; the circulating "no longer than two minutes" figure is absent
  from the actual PDS spec and is banned from this architecture):
  - `earliest_public_ts_utc` — earliest instant the filing *could* have
    been public: `acceptance_ts_utc` for in-window filings (or exception
    types before 22:00 ET); next business day 06:00 ET for after-hours
    non-exception filings. **Labeled an optimistic lower bound** — PDS
    disseminates "as soon as reasonably feasible", i.e. with a nonzero,
    unquantified lag, so this field must never gate look-ahead-sensitive
    reads.
  - `public_by_ts_utc` — the conservative upper bound that IS the
    `available_at` for `sec.filing_event` decision gating: end of the
    dissemination business day at 22:00 ET (same day for in-window and
    exception filings — grounded in the sourced same-business-day
    dissemination contrast; the next business day for after-hours
    non-exception filings). Design choice, labeled as such.
  - Consumers pick the side that is conservative *for their use*:
    backtests and point-in-time replay gate on `public_by_ts_utc`;
    staleness/freshness math may use `earliest_public_ts_utc` with a
    logged optimistic-basis flag. A tighter same-day bound, if ever
    wanted, must be an internally measured SLO from our own ingestion
    logs, labeled as such — never cited to SEC.
- Raw SEC acceptance time is never used as exact public availability
  (invariant 8 upheld — it is the *input* to the rule, not the output).
- `rule_version` + `tzdata_version` stored on every row; rule changes are
  new versions (none found v70→v77).
- Required tests: winter (EST), summer (EDT), the 17:30/22:00 boundaries,
  a DST-transition day, holiday and weekend rollovers, and each exception
  form type vs a non-exception type.

### 6.2 NWS CLI / Kalshi settlement semantics (versioned rules)

Sourced (WMO-No. 386 §2.3.2.2 + Attachment II-12; NWSI 10-1701 §4.1.2;
NWSI 10-1004 §4.1 (2025-06-05); Kalshi KXHIGHNY series API + NHIGH contract
terms; ledger rows WMO-*):

- Climate day = midnight-to-midnight **Local Standard Time** all year
  (so 1:00 AM–12:59 AM local clock during DST). Per-city IANA zones already
  live in `data/stations.py`.
- CLI is issued ≥ twice daily: a morning issuance carrying the **complete**
  prior LST day, and an afternoon issuance that is inherently a
  current-day-so-far partial; corrections are "as needed" — no cadence or
  BBB discipline is guaranteed at the NWS-instruction level.
- Version ordering (design choice DC-1): order same-product versions by
  bulletin issuance time (`YYGGgg`) with BBB sequence (`RRx`/`CCx`/`AAx`,
  x = A..X, Y = lost sequence, Z = >24h late) as the in-slot monotonic
  check; receipt time is a last-resort tie-breaker only, and every fallback
  is logged. Parsed BBB fields are stored (`bbb_type`, `bbb_sequence`).
- **`Pxx` is not defined in the governing sources read** (WMO-386
  Attachment II-12 defines only RRx/CCx/AAx; GTS segmentation was retired
  2007-11-07). Any observed `Pxx` (or other unrecognized BBB form) is
  quarantined, never guessed.
- Settlement-label freeze (DC-2): mirror Kalshi's own contract-terms
  machinery — freeze at the first 7:00/8:00 AM ET after data release (or
  +1 week), delayed to 11:00 AM ET when (1) the high is inconsistent with
  6-hr/24-hr METAR values or (2) a later report's high is **lower** than an
  earlier report's. Revisions after Expiration are ignored for settlement,
  matching the contract terms verbatim.
- Quarantine triggers (DC-3): later-lower-high; parity mismatch vs
  `station_observations` / `settlement_parity.observed_max_so_far()`
  (existing code — this is the METAR-consistency check, no new feed
  needed); BBB sequence gap or out-of-order letter; unrecognized BBB form.
- Lifecycle (DC-4): keep accepting/logging CLI versions through Kalshi's
  Settlement Date; model our internal label with Kalshi's own status
  machine (`determined → disputed/amended → finalized`), and capture the
  exchange's actual `result`/`settlement_value` into the existing
  `exchange_settlements` table rather than only computing our own view.
- Bulletin reconstruction: raw product text is stored content-addressed;
  the version chain reconstructs the bulletin sequence for any climate day.

## 7. Selector behavior

A selector is a typed, versioned description of *where in immutable source
bytes a value comes from*:

- `structured_api`: endpoint + JSON path + unit expectation (e.g.
  `companyconcept` → `units.USD[i].val` with `accn`, `form`, `filed`
  captured alongside).
- `html_selector`: DOM path/pattern bound to `decoded_sha256`.
- `text_pattern`: anchored regex/heading pattern for text products (CLI
  parsing) bound to the raw product hash.
- `embedded_text` (PDF): `source_pdf_sha256` + page + anchor
  quote/coordinates; extraction from the embedded text layer, with the
  quoted span stored.
- `ocr` (PDF/image): **specified now, implemented only when an
  OCR-dependent decision input exists (none does today — recorded
  deviation from Revision 3 in the decision log).** The spec, binding on
  any future implementation: source PDF sha256; exact rendered-crop sha256
  with fixed coordinate convention (PDF user space, points, origin
  bottom-left, page index recorded); renderer name+version; OCR engine,
  model, configuration, and preprocessing provenance; immutable crop
  storage next to the receipt; explicit `extraction_mode: ocr`; human
  review required when the rendered crop visually matches but OCR text
  drifts; **exact hash identity only — perceptual similarity never
  substitutes for it.**

Drift is fail-closed (invariant 10): if the bytes a selector expects have
changed shape (schema key missing, pattern anchor absent, unit changed),
the pipeline quarantines the capture with a typed reason code and stops
deriving values from it. It never "best-effort" extracts. Selector changes
bump `selector_version`; old rows keep the version that produced them.

## 8. Admission and conflict policy

States: `PENDING` → `ADMITTED` | `QUARANTINED(reason)` | `REJECTED(reason)`,
plus `superseded_by` chains. Conflicts are edges, not a state: a
`conflicts_with` link between records triggers quarantine of *both* sides
for decision purposes until resolved by a named rule or human review;
conflicting sources stay visible, never silently collapsed.

Hard admission gates (each independently inspectable pass/fail — no
composite score):

1. **Authority-in-scope**: source's registry entry covers this claim_type
   and allows this purpose.
2. **Temporal safety**: `available_at` present and computed by a versioned
   rule; `recorded_at >= available_at` is *expected*; a record claiming
   `recorded_at < available_at` (we recorded it before the public could
   know it) is quarantined as a look-ahead violation.
3. **Extraction integrity**: selector matched without drift; layered
   hashes present; value parses to the expected type/unit.
4. **Support** (LLM-extracted claims only): verify-support pass says
   `supported` — a *separate* step/model from the extractor, run
   double-order (two calls with presentation order swapped, admit only on
   agreement) because single LLM-judge calls carry measured position/
   verbosity/self-preference biases; disagreement ⇒ quarantine + human
   review for decision-bearing claims. Verification effort is
   stakes-routed: settlement-label and loss-bearing claims always get it;
   `display_only` claims may skip it (and are marked `not_checked`).
5. **Freshness**: not past `stale_after` at admission; consumers re-check
   at read time.
6. **Corroboration** (where the claim type requires it): minimum count of
   *distinct* `independence_group`s, with same-agency corroboration
   explicitly labeled as such (weather cross-checks are same-agency, not
   independent).

Ordinal `confidence_level` starts from the source's authority class and
moves only by named, logged reasons (e.g. `-1: single-group corroboration`,
`-1: extraction_confidence low`, `+1: structured endpoint + verified
support`). A test asserts every level is reproducible from its logged
reasons.

CI vs runtime (invariants 12–13): CI proves code correctness offline
against fixtures (all three suites already run offline; preserved).
Runtime admission is a separate, fail-closed data-plane decision — a green
CI never implies evidence is admissible, and no CI job ever calls a live
provider.

## 9. Lineage

- Relational stores: junction tables (`run_evidence(run_id, evidence_id)`;
  `claim_evidence(claim_id, evidence_id)`), inserted in bounded batches;
  run receipts carry aggregate counts (rows in/admitted/quarantined/
  rejected) so a receipt is meaningful without scanning the junction table;
  identifiers stream (no unbounded in-memory ID arrays; invariant 18);
  a high-volume test (≥10k links) proves both `run→evidence` and
  `evidence→run` queries stay bounded.
- File-based options-validator: lineage remains receipts'
  `input_files`/`changed_input_files` (path + sha256 per dependency) plus
  mandatory upstream receipt links — already shipped; the contract only
  standardizes field names in new receipts.
- Reproducibility manifest (adopted improvement): each research artifact
  gains a small sidecar recording exact command, git commit, lock-file
  hash, and raw-data pointers — reconstruction from immutable evidence +
  append-only journals (invariant 22) then requires no archaeology.

## 10. Migration design

Applies where relational schemas evolve under this program (equity-research
`market_updates`; kalshi stores when touched). options-validator's
file-based stores version by new receipt/schema versions, not migrations.

- **Alembic adopted in equity-research** with `render_as_batch=True`
  (SQLite has almost no ALTER support; batch mode copy-and-renames; tables
  referenced by FKs need `PRAGMA foreign_keys` handling and a safe order).
  First migration is a baseline capture of the current schema; the existing
  hand-rolled `schema_version` row is retired in favor of Alembic's version
  table in the same migration.
- **Classification is mandatory per migration**: `additive-expand`
  (reversible), `transform` (dual-write + shadow-read + reconcile), or
  `destructive/lossy` (forward-only; **no downgrade path is claimed** —
  claiming a lossless downgrade for a lossy migration is a documentation
  bug by definition).
- Expand → migrate → cutover → contract, with: append-only ingestion
  journal running through the whole window; dual writes where old and new
  shapes coexist; shadow reads comparing old vs new; count + hash
  reconciliation (row counts and content-hash totals per table) before
  cutover; cutover and rollback rehearsed on a copied database file, with
  the rehearsal receipt kept.
- Kalshi keeps its existing hand-rolled migration helpers until an EC-1
  packet materially changes its schema; Alembic is not force-adopted there
  in this stage (smallest-architecture rule; recorded in the decision log).
- **SQLite release gate (enforced, not advisory)**: the WAL-Reset
  corruption bug (fixed in 3.51.3, 2026-03-13; backports 3.44.6/3.50.7)
  affects concurrent multi-writer WAL access. **Measured 2026-07-29: both
  the equity-research and kalshi venvs run SQLite 3.50.4 — below every
  safe version** — and `market_updates` already opens its DB in WAL mode.
  Therefore: on an unsafe version, single-writer access is *mechanically
  enforced* (an exclusive write lock acquired non-blocking at write-session
  open; a second concurrent writer raises, fail-closed) rather than
  assumed. The version check + lock ship together in packet 2. Remediation
  to an actually-safe engine (newer Python build, or a bundled-SQLite
  package) is an owner decision recorded when taken; until then the lock
  is the operative control.

## 11. Continuous improvement loop

- **Provider health** (extends existing `provider_state`/`provider_runs`):
  per-provider precision/recall on the golden set, null rate, freshness
  (watermark advance), conflict rate, quarantine rate — computed from our
  own receipts, never provider self-report.
- **Golden-question retrieval benchmark**: 10–15 hand-curated questions
  per domain (filings facts; options contract/chain facts; NWS climate
  values; Kalshi rules), each keyed to a primary-source answer (accession
  number / contract quote / CLI value), including deliberate
  "correctly abstain" items (abstention is a distinct, harder skill).
  Runs offline in CI against fixtures; scores retrieval precision, recall,
  and abstention quality; regressions block release of retrieval changes.
- **Error taxonomy**: typed reason codes for failed retrieval and bad
  sources (network, drift, parse, temporal, conflict, support-failure),
  extending the existing typed-reason patterns (`*_STALE`/`*_MISSING`,
  freshness reason strings).
- **Human review triggers**: settlement-label quarantine; contradictory
  version chains; verify-support disagreement on decision-bearing claims;
  provider health drop beyond registered thresholds; any admission-gate
  override.
- **Lessons loop**: every confirmed failure adds (a) a regression fixture,
  (b) a registry/policy update if source-related, and (c) an entry in the
  repo's institutional-memory section (kalshi's "Things That Have Failed"
  pattern, adopted cross-repo).
- **Periodic source-policy audit**: quarterly, aligned with the existing
  quarterly re-audit habit; reviews registry entries, health metrics, and
  the golden-set pass rates.
- **Risk-tiered promotion**: claims feeding trading/settlement/verdict
  paths require the full gate stack; exploratory/display context is
  admitted at lower tiers but is machine-labeled (`purpose_authority`) so
  it can never silently cross into a decision path.

## 12. Rollout order and release gates

Packet detail (paths, tests, commands, rollback) lives in
`codex-sol-high-execution-plan.md`. Order, with rationale:

| # | Packet | Repo | Why this position |
|---|---|---|---|
| 1 | SEC availability rule module + acceptanceDateTime capture | equity-research | Pure, additive, closes the sharpest verified gap; no schema dependency |
| 2 | Alembic baseline + evidence-store expand (bitemporal, admission, freshness, independence, content-addressed raw archive, ingestion journal) | equity-research | Schema base every later packet writes into |
| 3 | Source registry v1 + claim-type authority rules | equity-research | Declarative policy the admission gates read |
| 4 | XBRL structured-facts fetcher + as-first-reported query layer | equity-research | Depends on 2 (schema) + 3 (registry rule) |
| 5 | Admission gates + verify-support step (double-order) + lineage junctions | equity-research | Depends on 2–4 |
| 6 | CLI version-chain + BBB parsing + quarantine + determination freeze + exchange settlement capture | kalshi | Independent of 1–5 (separate repo/files); can run as a parallel Codex thread |
| 7 | Lineage gating for legacy calibration artifacts + legacy timestamps (F05/F06) | kalshi | Depends on 6 only for shared table conventions |
| 8 | Consumer upgrade: market_context availability/admission filtering + conformance fixtures | options-validator | Depends on 2/5 field semantics |
| 9 | Golden-question benchmark (filings domain first) + provider health metrics | equity-research | Depends on 5; expands per domain later |
| 10 | Shared-package extraction **checkpoint** (not a build) | cross-repo | Only after ≥2 repos consume a stable EC-1 for a full cycle |

Release gates (all verified-evidence-based, per invariant 23):

- Per-packet: named suite green at the repo's recorded baseline or better
  (2109 / 1544 / 2252), plus the packet's new tests; ruff+pyright stay
  clean where configured; no live network in any test.
- Boundary tests green: SEC winter/summer/17:30/22:00/DST/holiday set;
  CLI ordering + quarantine set; high-volume lineage test.
- SQLite version ≥ 3.51.3/backport verified, OR the single-writer lock
  active and tested, wherever WAL writing is enabled (both venvs measured
  at 3.50.4 on 2026-07-29 — the lock is the operative control today).
- tzdata pinned and its version asserted in a test.
- Migration packets: reconciliation counts+hashes match, rehearsed
  rollback receipt exists, classification recorded.
- Blind/OOS protections intact: options-validator's sealed holdout
  (`IN_SAMPLE_END`, reveal budget) untouched; kalshi's shadow/live
  isolation test must continue to pass — extending its coverage to new
  modules is expected, narrowing or weakening what it enforces is not.
- Docs: decision log updated when a packet deviates from this document.

## 13. Explicit exclusions

- **Airflow or any orchestrator/always-on service** (invariant 17; no
  requirement demonstrated — existing scheduled scripts suffice).
- **Provenance semirings** — junction-table why-provenance already covers
  the need; the semiring apparatus pays off only for algebraic query
  engines (decision log #7).
- **Composite weighted source-quality score** — rejected on GRADE-lineage
  evidence; gates + ordinal levels with logged reasons instead.
- **Memento/WARC archival, RFC 3161 timestamping, signed feeds** — solve
  an adversarial third-party-proof problem this solo-operator system does
  not have; would add always-reachable external dependencies.
- **OCR build-out** — spec'd (§7) but not built until an OCR-dependent
  decision input exists.
- **A numeric SEC dissemination-latency constant** — no official source;
  the "2 minutes" figure was checked against the actual PDS spec and is
  not there.
- **SQLite in options-validator / forced Alembic in kalshi** — no
  demonstrated requirement in this stage.
- **Live order placement, live-brokerage connectivity, paper-mode changes**
  — permanently out of scope in all three repos (charter constraints).
- **Any change to registered hypotheses, frozen numbers, sealed holdouts,
  or pre-committed thresholds** — owner-typed acts remain owner-typed; the
  evidence layer records, it never registers.
