# Research-context refresh runbook (attractiveness dashboard)

**What this is.** The attractiveness board's research layer — the "Research
evidence" blocks on the Top-3 hero cards, the per-symbol "Company context,
catalysts & sources" blurbs, and the "Market context" backdrop — comes from a
dated JSON file: `reports/attractiveness_context/<data-as-of>.json`. Per the
governing spec (`docs/superpowers/specs/2026-07-16-attractiveness-v2-
technicals-context-design.md` §3, amended 2026-07-16), this layer is
**ON-DEMAND**: the 07:10 daily ritual rebuilds the deterministic board with no
LLM in the loop, and agent research runs **only when the owner asks for it**.

**Why it goes stale (by design).** Three separate honesty mechanisms fire as
the file ages:

1. **Loader fallback banner** — `load_context()` wants an exact
   `<as-of>.json`; otherwise it falls back to the newest older file and shows
   "company-research annotations are from YYYY-MM-DD (stale vs data as-of …)".
2. **Orphaned annotation notice** — annotations are keyed to exact candidates
   (`SYMBOL:lane:expiry:strike`). The board re-derives picks whenever data
   changes, so old keys stop matching and the board reports "N research
   annotation(s) do not match any card on today's board".
3. **Per-card session check** — even a matching annotation renders only when
   its `market_as_of_date` equals the board's data as-of. Research is valid
   for exactly one session; every other card shows "Research evidence
   incomplete — no source-validated annotation".

None of these are bugs. They are the schema doing its job: it protects
ranking membership and provenance, **not** factual truth, and it never
invents content to fill a gap.

## Refresh procedure (owner-triggered; ~30–45 min with subagents)

1. **Confirm the board's data is current first.** The research file must be
   built against today's evaluation session. If the chain/features are stale,
   run the data-refresh steps from `tools/daily_ritual.sh` first (topup →
   `features.build_all` → `qm_dashboard --refresh-ohlcv`). Never write a
   research file for a stale board.

2. **Derive the authoritative candidate IDs** (never guess strikes/expiries):

   ```bash
   uv run python - <<'EOF'
   from options_researcher.attractiveness_dashboard import (
       assemble, select_top_picks, select_qm_top_picks, pinned_picks)
   from options_researcher.qm_dashboard import load_qm_context
   data = assemble()
   qm = load_qm_context(data.get("data_as_of") or "")
   ids = {p["card"]["top3_snapshot"]["candidate_id"]
          for p in select_top_picks(data, include_csp_watch=True)}
   ids |= {p["card"]["top3_snapshot"]["candidate_id"]
           for p in select_qm_top_picks(data, qm, include_csp_watch=True)}
   print("data_as_of:", data["data_as_of"])
   print("hero candidate ids:", sorted(ids))
   print("pinned:", [(p["symbol"], p["pick"]["card"]["top3_snapshot"]["candidate_id"])
                     for p in pinned_picks(data)])
   EOF
   ```

3. **Dispatch web-research subagents** (Sonnet-class; one per hero symbol,
   plus one for market context + pinned-symbol blurbs). Non-negotiable prompt
   rules:
   - Verify every fact on the live web; never from model memory. Cite only
     URLs the agent actually fetched.
   - No blogs/Reddit/YouTube/forums. Primary tiers: `issuer_ir`,
     `sec_filing`, `regulator`, `market_operator`; financial press is
     `secondary`. WebFetch tends to 403 on sec.gov — prefer issuer IR pages
     (or Trafilatura with a real UA for EDGAR).
   - Claim schema is enforced by `options_researcher/top3_context.py`:
     exactly one of `source_url`/`unknown_rationale`; `date_certainty:
     "confirmed"` requires a primary tier AND a URL; `fact_date` may be null
     only when certainty is `"unknown"`; `countercase` is mandatory.
   - The single highest-value claim per hero card is **earnings timing vs the
     card's expiry** (in-window earnings = the dominant risk on a 2-week
     option).

4. **Assemble** `reports/attractiveness_context/<data-as-of>.json`:
   - `as_of` = the board's data as-of; `researched_on` = today;
     `provenance` = `"LLM-asserted (Claude subagents, web research
     YYYY-MM-DD)"`.
   - `market{summary, regime, notes}`, `symbols{...}` (hero + pinned
     symbols), `annotations{candidate_id: {research_as_of_utc,
     market_as_of_date, claims[...]}}`.
   - `market_as_of_date` MUST equal the board's data as-of, or the card
     renders "Research evidence stale".
   - Do NOT include `top_picks` / `legacy_top_picks_unusable` — agent-chosen
     picks are a retired legacy input and only trigger the "ignored" notice.

5. **Validate before writing the dashboard** — round-trip the annotations
   through the real validator with the real candidate IDs:

   ```bash
   uv run python - <<'EOF'
   import json
   from options_researcher.top3_context import normalize_research_annotations
   ctx = json.load(open("reports/attractiveness_context/<AS_OF>.json"))
   ids = [...]  # from step 2
   normalize_research_annotations(ids, ctx["annotations"])
   print("annotations valid")
   EOF
   ```

6. **Rebuild and verify**: `uv run python -m
   options_researcher.attractiveness_dashboard`, then check the HTML for:
   no "annotations are from" fallback banner, no "do not match any card"
   notice, hero cards showing "✓ Research evidence · complete", and the
   "Research updated" chip showing today.

## Cadence

The spec deliberately keeps agents out of the automated ritual. Practical
triggers for asking for a refresh:

- Before actually reading the board to consider any action.
- After any session where the Top-3 membership rotated.
- Any time the board shows the stale-research banners and that bothers you.

**This is now automated.** Per the spec amendment *"2026-07-25
(owner-directed): scheduled research refresh"* in
`docs/superpowers/specs/2026-07-16-attractiveness-v2-technicals-context-
design.md`, a LaunchAgent (label `com.carsyn.options-validator.research-
refresh`, template checked in at `tools/launchd/com.carsyn.options-
validator.research-refresh.plist`, installed by copy to
`~/Library/LaunchAgents/`) runs `tools/research_refresh.sh` Mon–Fri at 07:40
ET and 16:45 ET, plus Sat 09:00 ET as a weekend catch-up. Each run converges
data freshness (topup → attractiveness features → QM OHLCV, all no-ops when
already current), then invokes a headless Sonnet session
(`claude -p "/research-refresh" --model sonnet --max-budget-usd 8`, an
$8/run hard dollar cap) that follows this same refresh procedure end to end,
then rebuilds the dashboard and independently verifies the stale banners are
gone before writing a receipt — it never trusts the agent's own "OK." Logs
land in `.tmp/research_refresh/` (`<stamp>.log`, `claude_<stamp>.out`,
`launchd.out`/`launchd.err`); success receipts are
`.tmp/research_refresh/receipt_<as-of>_<slot>.json`. The run never
auto-commits — a human or session still commits the resulting context file.
Kill-switch: `touch .research-refresh-off` at the repo root makes the script
exit 0 immediately without doing anything; remove the file to re-enable.

The manual procedure above remains the fallback whenever the automation is
off (kill-switch present) or a scheduled run goes red — a missed or failed
run just means the board falls back to its honest stale banners, which is
the correct failure mode, never invented content.

*Provenance: runbook written 2026-07-25 by Claude (Fable) after the first
post-7/16 refresh; procedure mirrors the spec's amended §3.*
