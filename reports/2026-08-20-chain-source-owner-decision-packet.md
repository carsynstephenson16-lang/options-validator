# Owner decision packet — the frozen option-chain history, and the closes cadence

**Date:** 2026-08-20 · **Prepared by:** orchestrating Claude session (3 Sonnet scouts + Opus adversarial review, 2026-08-20)
**Decisions required:** two — one big (chain history source), one small (automating the closes refresh).
**Nothing in this packet is decided. Every option is written so you can pick by circling a letter.**

---

## Plain-English background (what is broken and why)

- The platform used to buy **historical option-chain data** (every option's daily
  prices) from a paid provider, ThetaData. You cancelled that subscription
  effective 2026-07-31 (your ruling OD-2/OD-4: no refill, no network providers).
  The last day of chain history on disk is **2026-07-27**. That archive is
  immutable and cannot grow.
- The **Schwab lane** still captures a free snapshot of option quotes every
  trading day at 15:45 ET. That is what today's dashboard runs on. But it is a
  *live snapshot*, not *history* — it cannot backfill the past, and your rules
  correctly forbid pretending it can.
- The **daily ritual** (the 07:10 health check) requires every registered
  hypothesis lane to produce a data receipt. The lanes that need chain
  *history* (H6, H8, parts of H7's context) can never produce one again, so the
  ritual ends **BROKEN every day** — by design, any critical line means BROKEN
  (`tools/daily_ritual.sh:426-429`), and a starved lane is always a critical
  line (`tools/daily_ritual.sh:404-418`, which itself notes this is "the
  expected shape of a chain-starved day").
- The **research annotations** (the company write-ups on the dashboard) refuse
  to run unless the ritual says OK (`tools/research_context_assemble --preflight`).
  So they are pinned at 2026-07-27 — **not because anything malfunctioned**, but
  because three honest rules chain together: no chain refill → starved lanes →
  ritual BROKEN → research blocked.
- Separately: the **underlying stock closes** went stale (2026-08-04) because no
  scheduled job runs the owner-approved Yahoo refresh. This session refreshed
  all 25 names to 2026-08-19 (Opus-reviewed; drill receipt
  `ops/reports/h7_receipts/backup_restore/2026-08-20.json`, ok=true, 0 problems),
  but **it will go stale again immediately** unless a cadence is authorized.

---

## DECISION 1 — What to do about chain history (pick one)

### Option A — Accept the Schwab-only world and say so formally *(recommended)*

Amend the ritual and research gate so a day whose ONLY critical line is the
expected chain-starvation can still publish an honest status (e.g. a new
`OK_STARVED` state that the research preflight accepts), and formally move the
chain-history-dependent lanes (H6, H8) toward their honest starved closure —
the same path H10a already took (closed STARVED, recorded in the ledger).

- **What you get:** ritual goes green-with-a-note instead of crying BROKEN
  daily; research annotations refresh again (keyed to the Schwab board's
  as-of date); alert fatigue ends, so a *real* break is visible again.
- **What it costs:** $0. H6/H8 stop pretending they might resume; if you ever
  want them back, they need re-registration through the 2026-07-24 feasibility
  gate on a data source that exists.
- **Scope change:** amendments to the ritual-status contract and research
  preflight (delegated path: independent adversarial review + Fable sign-off,
  provenance "owner-delegated standing 2026-07-25", your veto stands). Any
  H6/H8 closure **verdict is yours to type**, as always. README "Scope status"
  updated to match. No new provider, no new spend, $0 doctrine untouched.

### Option B — Pay for chain history again

Re-subscribe to ThetaData or an equivalent historical options provider and
refill the cache forward from 2026-07-28.

- **What you get:** H6/H8 lanes and full-chain context come back to life;
  ritual heals for the real reason instead of by redefinition.
- **What it costs:** money (ThetaData ran roughly tens of dollars per month —
  **LLM-asserted, unverified; get the current price from their site before
  deciding**), plus it reverses your own OD-2/OD-4 ruling and re-opens the
  settled $0-stack doctrine, which per your standing rule only an explicit
  owner directive can do. The 08-15→08-18 Schwab capture hole stays a
  permanent gap regardless — history providers can backfill chains, but the
  verified-capture receipts for those days can never exist.
- **Scope change:** provider decision goes through your opportunity-triage
  habit; a written call-count/cost estimate is required before any endpoint
  call (`.claude/rules/data-and-providers.md`).

### Option C — Do nothing (explicit status quo)

- **What you get:** nothing changes. The dashboard keeps working on Schwab
  snapshots (as it did today).
- **What it costs:** the ritual reports BROKEN every day forever, research
  annotations stay frozen at 2026-07-27, and real breaks hide inside expected
  noise. Choosing this *knowingly* is legitimate; drifting into it is not —
  which is why this packet exists.

**My suggestion: A.** Your own doctrine says a starved lane closing honestly is
a success, not a failure; H10b and H5 already migrated to the Schwab lane; H6/H8
have been paused for weeks with no path back that doesn't cost money you've
twice declined to spend. Option A makes the system tell the truth cheaply.
Pick B only if you actively want H6/H8's historical style of research back.

## DECISION 2 — Automate the closes refresh? (yes/no)

Add the already-owner-approved Yahoo closes refresh (directed 2026-08-04) as a
scheduled step (post-close daily, or in the ritual) with the same guards used
today: refresh all cached symbols, diff against the prior bytes on overlapping
history, refuse and alert on any retroactive change (the unregistered-split
trap), never store a same-day partial bar.

- **If yes:** closes stop going stale; H5's observe lane stops refusing on
  data gaps; disposition B already makes refreshes receipt-safe (verified by
  today's drill). Implementation goes to a Codex brief; small.
- **If no:** today's fix decays within days and H5 resumes refusing.

**My suggestion: yes.** The dangerous part (receipts breaking silently) was
solved by disposition B; today's run proved it end-to-end.

---

## Also attached to this packet (report-not-fix items, no decision forced)

1. 90 close-bindings in 6 watcher receipts (`reports/h7_receipts/h7-forward-15-v1/watcher/`)
   are broken and verified by nothing — the drill only checks data-gate
   receipts (`tools/h7_forward_backup.py:338`). Cheap fix candidate.
2. Ritual bug: an empty source-health receipt logs CRITICAL but falls through
   (`tools/daily_ritual.sh:176-178`) — would call the data gate bare and
   permanently revoke real-entry authority the day H7 activates. Should be
   fixed before H7 activation regardless of Decision 1.
3. Dashboard closes chip is fail-open (`max` across symbols,
   `options_researcher/attractiveness_dashboard.py:1152`) — one-line fix to `min`.
4. `SPLITS` table in `data/underlying_closes.py` ends 2025-12-18; the
   overlap-diff guard is the current mitigation.
5. `~/options-validator-receipts-backup-20260813` sits outside all git repos,
   unprotected.

## How to record your choice

Reply in-session with "Decision 1: A/B/C, Decision 2: yes/no" (plus any edits).
Registrations, frozen numbers, and verdict ratifications stay owner-typed;
amendment drafting then proceeds on the delegated path with review and
provenance labels.
