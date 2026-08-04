# Cross-project research source & extraction standard — design

**Date:** 2026-08-03
**Status:** DESIGN (executed same-session under owner's standing directive to
research → scope → spec → plan → execute; owner retains veto on every artifact)
**Provenance:** synthesized by Claude (Fable) from six read-only discovery
agents (five repo inventories + one provider-pricing verification pass). All
provider numbers below were verified against official vendor/government pages
on 2026-08-03 or are explicitly labeled UNVERIFIED. The scoring rubric in §5
is LLM-asserted (advisor-proposed, adapted) and is ADVISORY until owner-ratified.
**Scope guard note (this repo):** this is a docs-only artifact. It registers no
hypothesis, changes no threshold, resumes no paused EC-1 packet, and touches no
strategy/ledger/backtest code. Per `PROJECT_STATE.md` §6, "correct stale
documentation" and read-only standards work are safe-now.

---

## 1. Problem

Five projects fetch public-web data five different ways, with quality rules
that live (or don't) in each repo:

| Project (priority) | What it needs from the web | State found 2026-08-03 |
|---|---|---|
| options-validator (1) | earnings dates, catalyst/news annotation for a deterministic board | Strong rules (EC-1 docs, banned-host enforcement, receipts) but fetch doctrine stale; dead deps; scheduled lane runs from a sibling checkout |
| tiktok shop (2) | winning-creative discovery, hooks/transcripts, product commercial data | Active repo fetches nothing (manual paste by design); only live pipeline is in the June repo, 66 days stale, built on one unofficial proxy (tikwm.com); **no product commission/sales source at all** |
| sunwest-lead-engine (3) | FL business signals (Sunbiz, permits, UCC, USAspending), verified contacts | Excellent provenance/compliance design; **zero coded collectors** (its own "collector boundary" forbids them until preconditions + owner sign-off); Firecrawl attempt died on credits |
| equity-research (4) | SEC filings, market/consensus pages, macro series, news feed | Most mature: tiered source hierarchy, registry (`data/source_registry.json`, EC-1 schema), receipts, machine checks. But Firecrawl (doctrine tier 1) has been PaymentRequired since ~2026-06-30 and every capture for a month fell through to crawlee; status doc never mentions it |
| kalshi bot (5) | weather forecasts, market prices | Already near-optimal: official free JSON APIs, fail-closed, retries. No scraping. Internal inconsistencies only |

Common failure classes: (a) doctrine describing tools that are dead or not
installed; (b) no single claim-type → source policy outside the two finance
repos; (c) provenance/receipt shapes that differ per fetcher; (d) discovery
(finding the strongest URL) left implicit; (e) status docs silent about
month-old outages.

## 2. Decision

**Adopt one shared STANDARD; do not build a shared package.**

- The canonical standard lives in this repo (the EC-1 home) as a proposal
  extension: `docs/evidence-upgrade/2026-08-03-cross-project-source-standard.md`.
  EC-1's `source-policy.md` already declares cross-repo scope
  (equity-research, options-validator, kalshi-weather-bot); the extension adds
  the two non-finance projects and the pieces EC-1 lacks (discovery patterns,
  source-scoring rubric, per-repo fetch ladders).
- Each repo gets a SHORT self-contained adoption file (its fetch ladder, its
  claim-type table, its receipt mapping) that names the canonical doc + date.
  No cross-repo imports, no pinned shared code.

**Rejected alternatives**

1. *Shared `research_web/` package pinned by commit across repos* (advisor
   proposal). Rejected now: couples five repos' behavior to one codebase;
   equity-research already has working, governed fetchers + registry + checks;
   options-validator's scope guard forbids new infrastructure that doesn't
   move a live hypothesis; sunwest forbids collectors outright pre-sign-off.
   A package would be built for the two repos that are forbidden to use it.
   Revisit only if ≥2 repos independently implement the same receipt code.
2. *Refactor equity-research fetchers into router wrappers.* Rejected: the
   chain (firecrawl→crawlee→scrapling→WebFetch→jina) already shares
   `build_front_matter()` and auto-falls-through; the defect is doctrine
   truth, not architecture.
3. *Pay for a provider now.* Rejected: verified free tiers + already-working
   local fetchers cover current volumes at $0. See §6 tripwire.

## 3. The standard (core, shared by all five repos)

### 3.1 Claim-type → preferred source (binding direction, per repo tables refine)

| Claim type | Preferred source class | Never sufficient |
|---|---|---|
| Company financials | SEC filing / issuer earnings release / IR (accession-tagged) | aggregators, news rewrites |
| Price / market data | exchange or approved provider (repo-specific) | search snippets, stale pages |
| Economic data | FRED, BLS, BEA, Treasury, Federal Reserve | commentary citing them |
| Government/legal records | the issuing registry (Sunbiz, county, USAspending, UCC) | lead-gen resellers |
| Software behavior | official docs / source repo / release notes | blog tutorials |
| Product/vendor claims | vendor doc **plus** one independent source, else label VENDOR-REPORTED | vendor marketing alone |
| Platform policy (TikTok, FTC) | the platform's/regulator's own published policy | creator folklore, YouTube |
| News event | original announcement + one independent report | single reblog chains |
| Opinion/analysis | named, dated source, labeled as opinion | anonymous aggregation |

### 3.2 Evidence receipt — minimum fields (map onto each repo's existing shape; do not invent a fifth schema where four exist)

`source_url`, `final_url` (post-redirect), `publisher`, `published_at` (or
`undated`), `retrieved_at`, `fetched_via` (tool + version/route), `capture_path`
or content hash when a local copy is retained, `source_class` (§3.1 row),
`independence_group` (who ultimately authored the fact — five outlets reprinting
one press release are ONE group).

### 3.3 Discovery pattern (works with any search provider, including built-in WebSearch)

For any claim that will influence a decision: run up to three searches —
(1) **primary-source** (restrict to the §3.1 class), (2) **independent**
(exclude the subject's own domain), (3) **counterevidence** (add terms like
restatement, lawsuit, recall, criticism, correction, limitations). Then fetch
the originals; never cite a search engine's own answer/snippet as the source.
Cluster near-duplicates by underlying origin before counting corroboration.

### 3.4 Fetch ladder (shared shape; per-repo files pin the measured order)

1. Official structured API when one exists (EDGAR, FRED, NWS, platform APIs).
2. Repo's installed fetcher chain for pages.
3. Keyless Jina Reader (`r.jina.ai/<url>`, ~20 req/min anonymous) as last
   resort for JS-heavy public pages.
4. Hard walls (Cloudflare, robots.txt disallow, login, paywall) are respected:
   record a DATA GAP; never bypass. (Already doctrine in both finance repos;
   now standard everywhere.)

Etiquette floor everywhere: declared User-Agent with contact where the source
requires it (SEC verbatim rule; NWS), rate limits at or under published caps
(EDGAR 10 req/s), politeness sleeps on unofficial endpoints, cache every
capture locally so a page is fetched once per need, not once per session.

## 4. Per-repo adoption (what changes where)

| Repo | Adoption artifact | Real changes this session | Explicitly NOT done |
|---|---|---|---|
| options-validator | `docs/evidence-upgrade/2026-08-03-cross-project-source-standard.md` (canonical, PROPOSAL) | refresh `web-fetch-order` skill facts (Firecrawl still dead 2026-08-03 — re-verified via equity-research captures; fetchers not installed in this checkout; Jina keyless fallback); parking-lot entry for code-level items | no EC-1 packet resume (P2.4/OD-D owner gate stands); no dependency changes; no strategy/ledger code |
| tik tok (A) | `docs/research-source-policy.md` | policy codifies: official surfaces first (Creative Center manually, Seller Center exports, **TikTok Shop Affiliate API — verified to exist, owner registration required**), yt-dlp/tikwm as labeled-fragile fallbacks with politeness + explicit ToS-risk statement; provenance fields aligned to `researchPacket.ts`; PROJECT_STATE addendum surfacing the two unmerged built branches | no scraper built; no merge of side branches (owner call); no revival of repo-B pipeline |
| tiktok-affiliate-system (B) | pointer note | status note: pipeline stale 66 days, superseded-pending-owner-decision by repo A phase 2/3 | no code edits |
| sunwest-lead-engine | `docs/research-source-policy.md` + `docs/runbooks/collector-readiness.md` | policy maps standard onto existing `source_registry.csv` + provenance blobs; readiness runbook walks Sunbiz/USAspending/county sources through the repo's six collector preconditions with verified access facts; integrity-flags note (suppression feed absent, restricted-industries change-control miss, unborn git HEAD) | NO code, NO config/*.csv edits (repo's own change control requires owner + audit event), NO commits (unborn HEAD is owner's first-commit decision) |
| equity-research | `docs/research-source-policy.md` (thin, maps to existing registry) | PROJECT_STATE dated status note: Firecrawl outage reality; AGENTS.md routing block amended (dated) to match measured reality — crawlee is primary while Firecrawl is unpaid; brief (not code) for receipt-shape unification (jina front matter) + trafilatura/crawl4ai install-or-delete decision | no fetcher refactor; no EC-1 packet 2/5 work; no validator-freeze changes |
| kalshi (~/Claude dev) | `docs/data-sources-policy.md` | one-pager: official-APIs-only stance is correct and intentional; verified facts (NWS UA requirement; Open-Meteo non-commercial 10k/day + attribution; note: revisit license if bot ever trades real money); parked cleanup list (duplicate retry impls, `nbm`→NDFD label, oddpool fail-open inconsistency) | no code; prod checkout untouched |

## 5. Source-scoring rubric — ADVISORY, LLM-asserted

Start 0; add: primary/original +35, directly supports claim +20, fresh/dated
+15, independent of subject +10, full text captured +10, citation metadata +10.
Penalties: sponsored/affiliate −20, repost −15, undated −10, anonymous −5.
Reject outright: search snippet only; bot-wall partial capture; AI summary
without original. Bands: ≥80 primary evidence; 60–79 supporting; <60 lead
only; failed validation = data gap.

Numbers are advisor-proposed heuristics, unratified. Use as a mental
checklist and tie-breaker; do not encode into any gate until the owner types
their own thresholds (Carsyn rule: owner owns frozen numbers).

## 6. Provider stance — verified 2026-08-03, $0/month

**Use now (no account, no spend):** built-in WebSearch/WebFetch in Claude/Codex
sessions (covered by existing plan); repo-local fetchers (crawlee, scrapling,
trafilatura where installed); SEC EDGAR (free; verbatim rules: declared
User-Agent with contact, 10 req/s max); NWS api.weather.gov (free, UA
required); Open-Meteo free non-commercial (600/min, 5k/hr, 10k/day, CC BY
attribution); keyless Jina Reader (~20 req/min).

**Owner-gated (free, but each needs an ACCOUNT — flagged against the standing
"no new accounts pre-verdict" rule; the manual also predates tiktok/sunwest,
so the owner must reconcile scope before acting):**

| Action | Verified value | Why it matters |
|---|---|---|
| TikTok Shop Partner Center dev registration (OAuth) | Affiliate Seller/Creator/Partner APIs exist officially: product discovery + commission/order data | Closes the #1 tiktok gap (product selection currently has NO commercial data) via the official, ToS-clean route |
| Tavily account | 1,000 API credits/mo free, no card (all advisor claims verified); PAYG $0.008/credit | Structured discovery with domain/date filters, if built-in WebSearch proves limiting |
| Exa account | $20 signup + $10/mo recurring free credits; $7/1k paid | High-precision verification search; category filter has `financial report` (note: no literal `research papers` category — closest is `publication`) |
| FRED key exists (equity-research); BEA/EIA keys absent | free | Would enable 2 already-written, disabled providers in `market_updates` |
| Firecrawl plan decision | free tier 1,000 credits/mo ("no card"); Hobby $16/mo (OVER the $10 budget) | Current key is PaymentRequired since ~06-30. Recommendation: do NOT renew paid; either downgrade the existing account to free tier or keep crawlee-primary (works, $0, local) |

**Spend recommendation: $0.** The $10/month budget stays in reserve.
**Tripwire to revisit:** if, after adopting the standard, discovery quality is
the demonstrated blocker in ≥2 sessions per week for two consecutive weeks
(recorded, not vibes), bring the Tavily/Exa decision back to the owner with
those receipts.

## 7. Risks

- **Copy drift** between per-repo files and the canonical doc → per-repo files
  carry only repo-specific content + a dated pointer; shared core stays in one
  place.
- **Unofficial-source fragility (tiktok):** tikwm/yt-dlp can break or be
  blocked any day; policy labels them fragile, keeps volumes polite, and names
  the official API as the durable path.
- **Rule conflict:** account-requiring upgrades conflict with the pre-verdict
  standing rule as written; all such items are owner-action rows, never agent
  actions (agents cannot create accounts regardless).
- **Concurrent sessions:** options-validator changes ride a fresh docs branch;
  no main merge this session.
