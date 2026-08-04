# Cross-Project Research Source Standard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> **This session:** executed inline by the authoring session (autonomous owner directive); TaskList is the tracker.

**Goal:** Land one canonical research-source/extraction standard plus thin per-repo adoption artifacts across five projects, at $0/month, without violating any repo's own governance.

**Architecture:** Docs-only standard (canonical in options-validator's EC-1 home) + per-repo self-contained adoption files; zero shared code, zero new fetchers, all account/spend items routed to owner-decision rows.

**Tech Stack:** Markdown, git. No code, no deps, no network calls at execution time.

**Spec:** `docs/superpowers/specs/2026-08-03-cross-project-research-source-standard-design.md`

**Hard rules carried from spec §4:** sunwest = write files, NO commits, NO `config/*.csv` edits. kalshi = dev checkout (`~/Claude`) only, prod untouched. equity-research AGENTS.md = minimal dated amendment of the routing block only. options-validator = docs branch only, no main merge, no EC-1 packet resume.

---

### Task 1: options-validator — canonical standard doc

**Files:**
- Create: `docs/evidence-upgrade/2026-08-03-cross-project-source-standard.md`

- [ ] **Step 1: Write the doc** with sections: (a) header — Status: PROPOSAL / extension of `source-policy.md`; explicit sentence "This document does not resume the paused EC-1 packets (PROJECT_STATE P2.4 / OD-D gate stands) and grants no new authority in this repo."; provenance labels (verified-2026-08-03 pricing; ADVISORY LLM-asserted rubric). (b) claim-type → source table (spec §3.1 incl. VENDOR-REPORTED rule). (c) evidence-receipt minimum fields (spec §3.2, with the instruction to MAP onto existing schemas: equity `build_front_matter()`/`source_registry.json`, sunwest `evidence_receipts`, options `attractiveness_research_v2.py` SOURCE_FIELDS — named explicitly). (d) discovery pattern (3-search rule + dedup-by-origin clustering + "never cite the engine's own answer"). (e) fetch ladder + etiquette floor (declared UA w/ contact for SEC/NWS verbatim rules, EDGAR 10 req/s, politeness on unofficial endpoints, cache captures). (f) advisory scoring rubric (spec §5 with unratified-numbers caveat). (g) provider stance + owner-action table (spec §6 verbatim values incl. UNVERIFIED flags). (h) per-repo adoption index (paths of the five adoption artifacts).
- [ ] **Step 2: Verify vocabulary discipline**
Run: `grep -nE "\b(proven|confirmed edge|guaranteed|works)\b" docs/evidence-upgrade/2026-08-03-cross-project-source-standard.md`
Expected: no output (or only quoted-context hits reviewed by hand).
- [ ] **Step 3: Commit** (spec + plan + standard together)
```bash
git add docs/superpowers/specs/2026-08-03-cross-project-research-source-standard-design.md docs/superpowers/plans/2026-08-03-cross-project-source-standard.md docs/evidence-upgrade/2026-08-03-cross-project-source-standard.md
git commit -m "docs(evidence): cross-project research source standard (proposal) + design spec + plan"
```

### Task 2: options-validator — web-fetch-order skill truth refresh

**Files:**
- Modify: `.agents/skills/web-fetch-order/SKILL.md`

- [ ] **Step 1: Edit three facts** (Edit tool, minimal diffs): (a) Firecrawl line gains: "Re-verified 2026-08-03: sibling repo equity-research shows `firecrawl:PaymentRequiredError` on every capture 2026-08-01..03 — still out; do not reach for it." (b) Add near the top: "This checkout does not have trafilatura/crawl4ai/scrapling installed unless `uv sync --extra web-fetchers` was run this session — check before citing them as available." (c) Add last-resort rung: keyless Jina Reader `https://r.jina.ai/<url>` (~20 req/min anonymous, public pages only, never for paywalled/login content), citing the cross-project standard doc.
- [ ] **Step 2: Verify symlink intact**
Run: `ls -la .claude/skills/web-fetch-order && head -5 .agents/skills/web-fetch-order/SKILL.md`
Expected: symlink resolves; frontmatter unchanged.
- [ ] **Step 3: Commit**
```bash
git add .agents/skills/web-fetch-order/SKILL.md
git commit -m "docs(skills): web-fetch-order truth refresh (firecrawl still dead 2026-08-03; install caveat; jina keyless rung)"
```

### Task 3: options-validator — parking-lot entry for code-level items

**Files:**
- Modify: `ideas-parking-lot.md` (append one section at end)

- [ ] **Step 1: Append** section "## Web-layer code cleanups (parked 2026-08-03)" listing, each with a one-line gate: (1) remove dead top-level `scrapy` dependency (zero call sites; gate: full suite green after removal, owner ok on uv.lock churn); (2) remove tutorial `crawler.js`/`package.json` crawlee boilerplate (gate: confirm nothing external invokes `npm start`); (3) align `.claude/settings.local.json` WebFetch allowlist with doctrine domains — sec.gov, pjm.com, issuer IR (gate: owner reviews permission widening); (4) receipt-shape participation if EC-1 packets resume (gate: OD-D); (5) `market_context.py` first real caller (gate: a live consumer with a registered purpose).
- [ ] **Step 2: Commit**
```bash
git add ideas-parking-lot.md
git commit -m "docs(parking): park web-layer code cleanups surfaced by source-standard inventory"
```

### Task 4: tik tok repo A — research-source policy + PROJECT_STATE addendum

**Files:**
- Create: `/Users/carsynstephenson/Documents/tik tok/docs/research-source-policy.md`
- Modify: `/Users/carsynstephenson/Documents/tik tok/PROJECT_STATE.md` (append addendum section only)

- [ ] **Step 1: Write policy** with: (a) source ladder — 1. own-account data via Seller Center exports (official, already the `import_outcomes_csv` contract on the ops branch); 2. TikTok Creative Center Top Ads (manual browser, official surface); 3. **TikTok Shop Affiliate APIs** (verified to exist 2026-08-03: Affiliate Seller/Creator/Partner APIs, product discovery + commission/order tracking, OAuth via partner.tiktokshop.com; OWNER ACTION: developer registration; note standing-rule conflict verbatim); 4. yt-dlp harvest of public hashtag/user/sound feeds — labeled FRAGILE-UNOFFICIAL, politeness floor (existing 3–8s sleeps, no cookies default, no credentialed scraping, stop on block); 5. tikwm.com — labeled FRAGILE-UNOFFICIAL THIRD-PARTY PROXY with an explicit honest ToS-risk paragraph (neither repo previously stated one); banned: login automation, bot-wall bypass, Research-API misrepresentation. (b) provenance: every research packet field that came from the web carries source URL + retrieved_at; map onto `researchPacket.ts` product.facts sourceLocator. (c) claim rules: product claims = label-verbatim or VENDOR-REPORTED; endorsement/rights checks per existing brief-builder SKILL (cite the Rogan/Oz miss as the motivating incident, factually). (d) the product-selection data gap named, with the official API as the durable remedy.
- [ ] **Step 2: Append PROJECT_STATE addendum** titled "Addendum 2026-08-03 (research-source standard session)": two unmerged built branches exist (`claude/tiktok-shop-phase-2-3-221d6f` = harvest/decompose; `codex/tiktok-shop-ops` = ops package audited in `docs/REQUIREMENTS_AUDIT.md`) — merge decisions are owner's; new `docs/research-source-policy.md` governs web data; medicube images live at repo root (not `source-materials/` as line 14 states); `cloud-video-runner/uv.lock` untracked.
- [ ] **Step 3: Verify + commit**
```bash
cd "/Users/carsynstephenson/Documents/tik tok" && git status --short
git add docs/research-source-policy.md PROJECT_STATE.md
git commit -m "docs: research-source policy (official-first ladder) + PROJECT_STATE truth addendum"
```
Expected: only the two intended paths staged.

### Task 5: tiktok-affiliate-system — status pointer

**Files:**
- Create: `/Users/carsynstephenson/Documents/tiktok-affiliate-system/docs/STATUS-2026-08-03.md`

- [ ] **Step 1: Write note**: canon last written 2026-05-29 (66 days stale); `weekly_hunt.py` never scheduled (no cron/launchd exists); `scripts/scrape-and-render.sh` documented but absent; deep-scrapes missing for creatine/foodscale; pipeline superseded-pending-owner-decision by repo A's phase-2/3 branch; governing source policy now at repo A `docs/research-source-policy.md`; do not revive tikwm pipeline without reading that policy's ToS-risk section.
- [ ] **Step 2: Commit**
```bash
cd /Users/carsynstephenson/Documents/tiktok-affiliate-system && git add docs/STATUS-2026-08-03.md && git commit -m "docs: status note — canon stale, pipeline superseded-pending-decision, source policy pointer"
```

### Task 6: sunwest-lead-engine — policy + collector-readiness + integrity flags (NO COMMITS)

**Files:**
- Create: `/Users/carsynstephenson/Documents/Codex/sunwest-lead-engine/docs/research-source-policy.md`
- Create: `/Users/carsynstephenson/Documents/Codex/sunwest-lead-engine/docs/runbooks/collector-readiness.md`
- Create: `/Users/carsynstephenson/Documents/Codex/sunwest-lead-engine/docs/notes/2026-08-03-integrity-flags.md`

- [ ] **Step 1: Write policy**: maps the cross-project standard onto existing machinery by name (`config/source_registry.csv` approval workflow, `provenance.py` blobs/receipts, `source_family()` independence, weekly staleness windows); government-registry-first source table for its claim types (existence/status → Sunbiz; property/permits → county portals; federal awards → USAspending API; licenses → DBPR; UCC → FL registry); rule restated: public availability ≠ consent to contact; no scraping of the Sunbiz search UI (their own registry note); URL-only evidence is second-class vs captured blobs.
- [ ] **Step 2: Write collector-readiness runbook**: for each of Sunbiz / USAspending / county permits, walk the repo's six collector preconditions (verified access method, confirmed terms, format fixture, retry/coverage reporting, provenance/idempotency tests, owner sign-off) and record current status per precondition (all end at "owner sign-off: NOT GRANTED — do not build"). Include verified facts: USAspending has an official API (already used once, bounded, per `final-report.md` §14); Google Places free per-SKU calls (10k/mo Essentials, verified 2026-08-03) listed under enrichment ONLY as a future owner-contract decision per `outreach-controls.md`.
- [ ] **Step 3: Write integrity-flags note** (facts, no fixes): suppression feed absent (`data/suppression/` missing, 0 rows) = highest-risk gap; `config/restricted_industries.csv` populated (27 rows) while `config/README.md` says intentionally empty, and no audit event records the change — flag for owner to regularize via their own change-control; git HEAD unborn (nothing committed) — first commit is an owner decision; controlling PDF lives in `~/Downloads`, outside the repo, metadata date conflict already documented in `pdf-coverage.md`.
- [ ] **Step 4: Verify no repo state touched**
Run: `cd /Users/carsynstephenson/Documents/Codex/sunwest-lead-engine && git status --short | grep -v "^??"`
Expected: no output (only untracked additions exist; nothing tracked modified, nothing staged, no commit made).

### Task 7: equity-research — policy pointer, status truth, routing amendment, fetcher brief

**Files:**
- Create: `/Users/carsynstephenson/equity-research/docs/research-source-policy.md`
- Modify: `/Users/carsynstephenson/equity-research/PROJECT_STATE.md` (append dated note)
- Modify: `/Users/carsynstephenson/equity-research/AGENTS.md` (routing block lines ~45-50 only, dated)
- Create: `/Users/carsynstephenson/equity-research/docs/briefs/2026-08-03-fetcher-alignment-brief.md`

- [ ] **Step 1: Write thin policy**: points to canonical standard (path + date); states this repo's implementation IS `AGENTS.md` hierarchy + `data/source_registry.json` + `source-ledger.csv`; adds only what's new (3-search discovery pattern, dedup-by-origin, VENDOR-REPORTED vocabulary, keyless-Jina last rung).
- [ ] **Step 2: Append PROJECT_STATE note**: "2026-08-03: Firecrawl API key PaymentRequired since ~2026-06-30; every fresh capture 2026-08-01..03 fell back to crawlee (receipts in tickers/*/web/quote_2026-08-03.md). Crawlee chain is the working primary. Owner decision open: downgrade Firecrawl account to free tier (1,000 credits/mo, verified 2026-08-03) or keep crawlee-primary; Hobby $16/mo exceeds the $10 research budget."
- [ ] **Step 3: Amend AGENTS.md routing block** (Edit, minimal): mark item 1 (firecrawl_fetch.py) with "(amended 2026-08-03: key unpaid since ~06-30 — currently skip to 2; restore only when the owner re-funds or downgrades the plan)" and leave the rest of the chain untouched.
- [ ] **Step 4: Write fetcher brief** (for Codex, no code this session): (a) unify `jina_fetch.py` front matter through shared `build_front_matter()` (paths + current divergent fields listed); (b) decide install-or-remove for declared-but-absent `crawl4ai`/`trafilatura` (pyproject lines cited; recommendation: install trafilatura — the options-validator twin measured it as the SEC-403 workaround — drop crawl4ai unless a JS-render need is documented); (c) fix crawlee PDF mangling (binary detection → save-as-file, incident path cited); (d) add scrapling smoke test or demote it in doctrine. Each item with acceptance checks.
- [ ] **Step 5: Verify + commit (my files only)**
```bash
cd /Users/carsynstephenson/equity-research && git status --short
git add docs/research-source-policy.md docs/briefs/2026-08-03-fetcher-alignment-brief.md PROJECT_STATE.md AGENTS.md
git commit -m "docs: source-policy pointer, firecrawl outage status truth, dated routing amendment, fetcher alignment brief"
```
Expected: pre-existing dirty files (if any) left unstaged.

### Task 8: kalshi dev repo — data-sources stance doc

**Files:**
- Create: `/Users/carsynstephenson/Claude/docs/data-sources-policy.md`

- [ ] **Step 1: Write one-pager**: stance — official APIs only, correct as-is, no scraping wanted; verified facts (NWS free + UA-with-contact required; no official NWS rate-limit number exists — the circulating ~5k/hr figure is UNVERIFIED; Open-Meteo free non-commercial 600/min-5k/hr-10k/day + CC BY attribution; caveat: revisit Open-Meteo licence before any real-money trading); parked cleanup list (two duplicate retry implementations `_http.py` vs `alt_weather_clients.py`; `nbm` label actually NDFD — correlation note already in module docstring; oddpool fail-open vs weather fail-closed inconsistency); pointer to canonical standard (path + date). Explicitly: no code changes made; prod untouched.
- [ ] **Step 2: Commit (dev only)**
```bash
cd /Users/carsynstephenson/Claude && git add docs/data-sources-policy.md && git commit -m "docs: external data-sources policy (official-APIs-only stance) + parked cleanups"
```

### Task 9: Adversarial review, fixes, wrap-up

- [ ] **Step 1: Dispatch review agent** (Opus): given all diffs/paths, attack for: factual claims not traceable to an inventory/verification receipt; rule violations (EC-1 resume, sunwest commits, prod edits, frozen-number freezing); vocabulary violations; copy drift between spec/standard/per-repo files.
- [ ] **Step 2: Fix confirmed findings; re-commit per repo.**
- [ ] **Step 3: Final report** (per-project breakdown, owner-action table) + memory update + `session-synthesis` note (Stop-hook requirement).
