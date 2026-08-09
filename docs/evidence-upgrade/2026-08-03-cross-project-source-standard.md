# Cross-project research source & extraction standard (v2026-08-03)

**Status: PROPOSAL** — extension of `docs/evidence-upgrade/source-policy.md`
to all five of the owner's active projects. This document does **not** resume
the paused EC-1 packets (PROJECT_STATE P2.4 / OD-D gate stands) and grants no
new authority in this repo. Owner may ratify, amend, or veto; until ratified
it binds agent behavior as doctrine-of-record for *how to fetch and cite*,
and binds nothing else.

**Provenance:** provider numbers verified against official vendor/government
pages 2026-08-03 (labels: OFFICIAL / UNVERIFIED preserved below). The scoring
rubric in §6 is LLM-asserted (external-advisor proposal, adapted) and is
ADVISORY — its numbers are unratified and must not be encoded into any gate.
Design rationale: `docs/superpowers/specs/2026-08-03-cross-project-research-source-standard-design.md`.

**Governed repos and their adoption artifacts:**

| Repo | Adoption artifact |
|---|---|
| options-validator | this file + `.agents/skills/web-fetch-order/SKILL.md` |
| ~/Documents/tik tok | `docs/research-source-policy.md` |
| ~/Documents/tiktok-affiliate-system | `docs/STATUS-2026-08-03.md` (pointer; repo superseded-pending-decision) |
| ~/Documents/Codex/sunwest-lead-engine | `docs/research-source-policy.md` + `docs/runbooks/collector-readiness.md` |
| ~/equity-research | `docs/research-source-policy.md` (maps onto existing AGENTS.md hierarchy + `data/source_registry.json`) |
| ~/Claude (kalshi dev) | `docs/data-sources-policy.md` |

---

## 1. Claim-type → preferred source

Start every research question by classifying the claim, then go to that row's
source class first. A weaker source may *lead* you to the right one but may
not *carry* the claim when a stronger class exists.

| Claim type | Preferred source class | Never sufficient on its own |
|---|---|---|
| Company financials | SEC filing / earnings release / IR deck (accession-tagged where SEC) | aggregators, news rewrites |
| Price / market data | exchange or the repo's approved provider | search snippets, stale pages |
| Economic data | FRED, BLS, BEA, Treasury, Federal Reserve | commentary citing them |
| Government/legal records | the issuing registry itself (Sunbiz, county portals, USAspending, UCC, DBPR) | lead-gen resellers |
| Software behavior | official docs / source repo / release notes of the installed version | blog tutorials, memory |
| Product/vendor claims | vendor doc **plus** one independent source; else label **VENDOR-REPORTED** | vendor marketing alone |
| Platform/regulator policy | the platform's or regulator's own published text | creator folklore, videos |
| News event | original announcement + one independent report | single reblog chains |
| Opinion/analysis | named, dated author, explicitly labeled opinion | anonymous aggregation |

## 2. Evidence receipt — minimum fields

Every claim that can influence a decision carries: `source_url`, `final_url`
(after redirects), `publisher`, `published_at` (or `undated`), `retrieved_at`,
`fetched_via` (tool + route), `capture_path` or content hash when a local copy
is kept, `source_class` (§1 row), `independence_group` (who *authored* the
underlying fact — five outlets reprinting one press release are ONE group).

**Do not invent new receipt schemas.** Map these fields onto what each repo
already has: equity-research `build_front_matter()` + `data/source_registry.json`
+ `docs/evidence-upgrade/source-ledger.csv`; sunwest `provenance.py` blobs +
`evidence_receipts`; options-validator `attractiveness_research_v2.py`
SOURCE_FIELDS; kalshi's dev-branch settlement-evidence capture. A repo missing
a field adds the field, not a schema.

## 3. Discovery pattern

For any decision-relevant question, up to three searches, any provider
(built-in WebSearch is the default and costs nothing extra on the current plan):

1. **Primary-source search** — constrained to the §1 class (site:/domain
   filters where the provider supports them).
2. **Independent search** — excluding the subject's own domain.
3. **Counterevidence search** — add terms like *restatement, lawsuit, recall,
   criticism, correction, failure, limitations, methodology*.

Then fetch the originals. Never cite a search engine's or AI assistant's own
answer text as a source. Before counting corroboration, cluster results by
underlying origin (§2 `independence_group`).

## 4. Fetch ladder and etiquette floor

1. **Official structured API** when one exists (EDGAR, FRED, NWS, platform
   partner APIs) — always preferred over scraping the same data.
2. **The repo's installed fetcher chain** for pages (each repo's adoption file
   pins its measured order; do not trust doctrine that names uninstalled tools).
3. **Keyless Jina Reader** — `https://r.jina.ai/<url>`, ~20 req/min anonymous
   (OFFICIAL, verified 2026-08-03; keyed rate limits UNVERIFIED) — last resort
   for public JS-heavy pages only.
4. **Hard walls are respected.** Cloudflare/bot walls, robots.txt disallow,
   logins, paywalls ⇒ record a DATA GAP; never bypass, never present a partial
   capture as evidence.

Etiquette floor (all repos): declared User-Agent with contact where the source
requires it — SEC verbatim: "Please declare your user agent in request
headers" and "Current max request rate: 10 requests/second"; NWS requires app
name + contact email. Politeness sleeps on any unofficial endpoint. Cache every
capture locally; fetch once per need, not once per session.

## 5. Vocabulary and claim labels (all repos)

Claim labels: Repo-verified / Test-verified / Official-source / Inference /
Assumption (existing finance-repo discipline, now standard everywhere), plus
**VENDOR-REPORTED** for unverified vendor claims. Banned result words stay
banned ("proven", "confirmed", "guaranteed"). A missing source is written as a
data gap, not papered over.

## 6. Source-scoring rubric — ADVISORY, LLM-asserted, unratified

Start 0. Add: original/primary +35; directly supports the claim +20;
fresh/properly dated +15; independent of subject +10; full text/data captured
+10; strong citation metadata +10. Penalties: sponsored/affiliate −20; repost
−15; missing publication date −10; unnamed author −5. Reject outright: search
snippet only; bot-wall/incomplete capture; AI summary without the original.
Guidance bands: ≥80 primary evidence; 60–79 supporting; <60 discovery lead
only; failed validation = data gap.

Use as a checklist and tie-breaker. Owner has not ratified these numbers; no
gate, script, or registered process may hard-code them.

## 7. Provider stance (verified 2026-08-03) — $0/month

**In use now, no account, no spend:** built-in WebSearch/WebFetch under the
existing Claude/Codex plans; repo-local fetchers (crawlee, scrapling,
trafilatura where installed); SEC EDGAR (free, rules in §4); FRED (free, key
already held in equity-research; v2 API uses `Authorization: Bearer` header);
NWS api.weather.gov (free, UA required, no official rate-limit number — the
circulating ~5,000/hr is UNVERIFIED); Open-Meteo free non-commercial
(600/min, 5,000/hr, 10,000/day, CC BY attribution); keyless Jina Reader.

**Owner-gated (each requires creating an ACCOUNT — conflicts with the
standing "no new ventures, accounts, or spend" pre-verdict rule as written;
the operating manual also predates the tiktok/sunwest projects, so the owner
must reconcile scope before acting; agents never create accounts):**

| Owner action | Verified value (2026-08-03) | What it unlocks |
|---|---|---|
| TikTok Shop Partner Center developer registration | Affiliate Seller/Creator/Partner APIs exist (OFFICIAL: TikTok for Developers); OAuth 2.0 via partner.tiktokshop.com | The only ToS-clean route to product/commission/order data — the tiktok project's #1 gap |
| Tavily account | 1,000 credits/mo free, no card; basic=1 credit, advanced=2; PAYG $0.008/credit; free for students (all OFFICIAL) | Structured discovery with domain/date filters |
| Exa account | $20 signup + $10/mo recurring free credits; $7/1k standard search; `financial report` category exists, `research papers` does not (closest: `publication`) | High-precision verification search |
| BEA / EIA free API keys | free | Turns on two already-written, disabled `market_updates` providers in equity-research |
| Firecrawl plan decision | free tier 1,000 credits/mo "no card" (OFFICIAL); Hobby $16/mo — exceeds the $10 budget | Key failing intermittently since 2026-06-30: last successful capture receipt 2026-07-16, hard `PaymentRequiredError` on nearly all equity-research captures 2026-07-29..08-03, two 08-03 captures show `RateLimitError` (throttled-but-live signature — check the account dashboard before deciding). Recommendation: do NOT pay; downgrade the existing account to free, or stay crawlee-primary |

**Spend: $0. The $10/month budget stays unspent.** Tripwire to revisit: only
if discovery quality is the *recorded* blocker in ≥2 sessions/week for two
consecutive weeks, re-open the Tavily/Exa decision with those receipts. (The
tripwire threshold is itself LLM-proposed and unratified; owner may reset it.)

**Owner ruling 2026-08-04 (Carsyn-directed, in-session): the Tavily/Exa
decision is CLOSED as "settle".** No paid or account-gated search API; the $0
no-account stack above (built-in WebSearch/WebFetch + repo-local fetchers +
keyless Jina) is the standard. Exa MCP config was briefly wired
(dormant, env-var only, no key, no account) into equity-research, tik tok, and
sunwest-lead-engine earlier the same day and fully reverted on this ruling.
The tripwire above no longer re-opens the decision on its own — only an
explicit new owner directive does.

**Receipt limitation (added 2026-08-04 after adversarial review):** the
numbers above were read from official pages on 2026-08-03 by the verification
agent — Tavily `docs.tavily.com/documentation/api-credits` + `tavily.com/pricing`;
Exa `exa.ai/pricing` + `exa.ai/docs/reference/search`; Firecrawl
`firecrawl.dev/pricing`; Brave `api-dashboard.search.brave.com/documentation/pricing`;
Jina `jina.ai/reader`; SEC `sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data`
(verbatim quotes retained); FRED `fred.stlouisfed.org/docs/api/fred/v2/api_key.html`
(verbatim); NWS `weather-gov.github.io/api/general-faqs`; Open-Meteo
`open-meteo.com/en/pricing`; TikTok `developers.tiktok.com` (2024 Shop
Affiliate APIs launch post); Anthropic `platform.claude.com` web-search tool
docs; Google `mapsplatform.google.com/pricing` (verbatim). Page CAPTURES were
not retained, so under §2 these are Inference-grade until recaptured —
re-verify any number before it justifies spend or an account action.

## 8. What this standard explicitly does not do

No shared code package. No new fetchers or collectors anywhere. No EC-1
packet resume in this repo. No change to any registered hypothesis, gate,
threshold, ledger, cache, or book. No account creation by agents. Sunwest's
collector boundary and options-validator's scope guard remain fully binding
over anything this document says.
