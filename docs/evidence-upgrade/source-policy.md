# Source Policy (EC-1)

Date: 2026-07-29. Companion to `final-architecture.md`. This policy governs
which sources may support which claims, at which authority, across
`equity-research`, `options-validator`, and `kalshi-weather-bot`.

## 1. Source hierarchy

Authority classes, highest first. A source's class is recorded in the
source registry; a claim's required class is set by its claim type (§2).

1. **Governing primary** — statutes/regulations, exchange rules and
   contract terms (Kalshi rulebook, NHIGH-style contract terms), official
   filings and raw provider records (EDGAR documents, XBRL companyfacts,
   NWS text products), standards bodies (WMO manuals, NWS Instructions,
   IETF RFCs, ISO SQL), official API specifications, source code, and
   versioned vendor technical documentation (SQLite docs, Alembic docs).
2. **Original research** — peer-reviewed papers, original datasets,
   proofs, credible working papers, canonical monographs. Preprints are
   citable with `preprint` noted in limitations.
3. **High-quality synthesis** — systematic reviews, standards commentary,
   institutional technical reports (e.g. ECMWF Forecast User Guide).
4. **Reputable secondary analysis** — named authors, transparent sourcing,
   direct links to primary material.
5. **Current reporting** — news/trade press for recent events only.
6. **Discovery-only** — Wikipedia, snippets, forums, vendor marketing,
   SEO pages, unsourced AI summaries. May guide search; may never be the
   sole support of any final claim, and never enters the source ledger as
   support.

**Scope beats rank**: a high-authority source outside its authoritative
scope does not outrank a lower-class source with direct authority over the
claim (e.g. Kalshi's Help Center DST explainer does not outrank NWSI
10-1004 on the climate-day definition — it is a consistent restatement,
not a second source of the rule).

## 2. Claim-type authority rules

| Claim type | Required source (decision authority) | Notes |
|---|---|---|
| `sec.numeric_fact` (financial statement values) | `data.sec.gov` structured endpoints (`companyfacts`/`companyconcept`/`frames`) with accession number (`accn`), `form`, `filed` recorded | HTML/LLM-read values are `display_only` at best. Caveat recorded: SEC staff FAQ flags custom XBRL tags as comparability risks — "structured" ≠ "clean"; custom-tagged values carry a logged confidence downgrade |
| `sec.filing_event` (what was filed, when) | EDGAR submissions + acceptance datetime, run through the versioned availability rule (`EDGAR-FilerManual-v77-2026-03-16`) | Raw acceptance time is never used as exact public availability |
| `earnings.date` | SEC acceptance evidence first; company IR/PR second; aggregator estimates diagnostic-only, never promotable | Already enforced by `tools/h7_refresh_earnings.py`; registry makes it declarative |
| `weather.cli_value` (settlement-relevant climate values) | NWS CLI Daily Climate Report version chain (issuance-time + BBB ordered), cross-checked against station observations | Cross-checks (api.weather.gov, GHCN-Daily, station obs) are **same-agency corroboration**, labeled as such — never "independent verification" |
| `kalshi.contract_rule` / `kalshi.settlement` | Kalshi series API + linked contract-terms PDF (both captured); exchange `result`/`settlement_value` via official API | Mirror Kalshi's own lifecycle `determined → disputed/amended → finalized` |
| `market.quote` / `options.chain` | The repo's canonical provider adapter (ThetaData in options-validator; documented quote sources elsewhere) with capture receipts | Provider identity + version recorded per capture |
| `macro.series` | Official statistical agency endpoints (FRED/BLS/BEA/EIA/Treasury) | Already implemented in `market_updates/providers.py` |
| Options mechanics / margin / assignment / fees | OCC, Cboe, FINRA, SEC, exchange, or broker official documentation only | Standing repo rule, unchanged: never blogs/forums for these |

Existing bans are preserved, not weakened: Daloopa / Capital IQ / Kensho /
LSEG-family plugins remain banned as primary citation sources in
equity-research (whitelist exceptions unchanged); TipRanks remains
excluded. Registry entries encode bans as `allowed_purposes: []`.

## 3. Discovery vs evidence

- Discovery tools (WebSearch, GDELT, snippets) locate candidates; the
  cited source is always the opened, read artifact — never the snippet.
- A summarizing fetcher's output (e.g. WebFetch) is never treated as
  verbatim source text; verbatim claims require the captured bytes.
- Anything that cannot be opened and read is an access limitation recorded
  in the ledger; the dependent claim is marked an evidence gap, not
  papered over. (Live examples this cycle: Murphy 1973 blocked by a
  CloudFront 403 → substituted ECMWF official documentation and said so;
  the "2-minute" SEC dissemination figure failed verification against the
  actual PDS spec and was banned.)

## 4. Source independence

- Every source carries an `independence_group` (same root origin ⇒ same
  group: one wire story re-syndicated, one filing quoted by three
  write-ups, one agency's data re-served by two APIs).
- Corroboration counts **distinct groups**, never raw report counts.
- The Bayesian result behind this (Bovens & Hartmann 2002) is
  parameter-dependent, so where a source has a measurable track record,
  its reliability and false-confirmation tendency are carried as
  per-source data rather than a fixed discount; where unmeasured, the
  conservative default is one group = one unit of evidence.
- Weather cross-checks are the canonical same-group example: CLI reports,
  api.weather.gov observations, and GHCN-Daily all trace to the same
  NWS/ASOS network — one independence group, useful for catching
  transcription/parse errors, silent about instrument error.

## 5. Conflict handling

- Conflicts are recorded as edges (`conflicts_with`) between visible
  records; both sides lose decision eligibility (quarantine) until a named
  rule or human review resolves the conflict; resolution appends — it
  never deletes or rewrites the losing record.
- Named auto-resolution rules exist only where a governing source defines
  them (e.g. a later CLI version with a valid BBB correction supersedes an
  earlier one; but a later-**lower** high triggers quarantine per the
  contract-terms logic, not silent supersession).
- Sources that conflict remain visible in outputs ("sources conflict:
  A says X, B says Y") — silent picking is banned.

## 6. Version and freshness rules

- Rules and sources are versioned: `rule_version` (e.g. the SEC
  availability rule), `registry_version`, `selector_version`,
  `tzdata_version` are recorded on receipts.
- Prefer the current effective version for rules, software, standards,
  APIs, and operational facts; older foundational work remains eligible
  where it is still governing or canonical (e.g. WMO-386 2009 BBB text,
  amendment-checked).
- Every claim carries `freshness_class` (`immutable` / `slow` / `fast` /
  `event_driven`) and `stale_after`. Overdue claims lose decision
  eligibility until re-verified. Classification is a lookup by claim type
  (e.g. contract strike = immutable; earnings date = slow until confirmed;
  quotes/forecasts = fast), not an LLM call.

## 7. Citation requirements

Every material claim cites: source identifier, exact location (section /
page / table / field / line), publication + effective date or version,
retrieval time, and — for SEC numeric facts — the accession number. The
existing repo claim-discipline labels (Repo-verified / Test-verified /
Official-source / Inference / Assumption) remain mandatory in prose; the
evidence store's structured fields are the machine-readable equivalent.
Never cite a paper from its abstract alone when the method matters; never
cite a secondary description when the accessible primary governs.

## 8. Promotion and abstention policy

- **Promotion is risk-tiered**: claims feeding trading, settlement labels,
  hypothesis verdicts, or model training require the full admission-gate
  stack (authority-in-scope, temporal safety, extraction integrity,
  verify-support where LLM-extracted, freshness, corroboration where
  required). Exploratory/display context admits at lower tiers but is
  machine-labeled (`purpose_authority`) and can never silently cross into
  a decision path.
- **Abstention is a success state**: when required evidence is missing,
  stale, quarantined, or conflicted, consumers ABSTAIN and say why. Any
  quality metric over admitted claims is reported **with its coverage**;
  abstention thresholds and a minimum coverage floor are pre-registered
  together (never tuned after seeing the data) — consistent with the
  repos' standing "no edge found is a successful outcome" doctrine.
- Provider self-reported quality never promotes anything; health metrics
  are computed from our own receipts.
- Human review is mandatory for: settlement-label quarantines,
  verify-support disagreements on decision-bearing claims, conflicts
  without a named resolution rule, and any gate override (overrides are
  logged, reasoned, and appear in the quarterly source-policy audit).
