# 2026-08-13 — PM scope audit: what's done, what's blocked, and the one chain that unblocks everything

**Session:** Claude orchestrating (Fable), three Sonnet read-only audit agents
(automation diagnosis, H7 gap map, branch/merge disposition), one Opus
adversarial reviewer over this bundle (rev 1 verdict FAIL, 16 findings; all
applied in rev 2 of the three documents). Session writes: this report, the
two dated plan docs, one display-only regeneration of
`.tmp/dashboard/experiments.html` from cached data, commit 401f78b
(pre-canary hardening, suite exit 0) on its existing branch, and pushes of
`codex/pre-canary-capture-hardening`, `codex/h7-schwab-evidence-mode`,
`codex/handoff` (backup, not integration). No merges, no ledger writes, no
provider calls.
**Claim labels:** everything below is Repo-verified against origin/main
@7fbe013, live receipts in `~/options-validator-ops`, or `launchctl` state,
except where labeled Inference.

## 1. Executive summary

The system is not broken — it is fail-closed exactly as designed, and has
been since 2026-07-28. One hardcoded owner-gated switch
(`data/ritual_authority.py`: `h7_active=False`,
`exact_session_source_active=False`) blocks the daily ritual, which in turn
blocks the research refresh, both dashboards' automated rebuilds, and all
watches. The switch is the LAST step of the owner-approved H7 Schwab restart,
and the restart is stalled on a chain whose current head is a **git fork**:
origin/main (7fbe013, the 2026-08-12 audit-cleanup line) vs local main
(eea4700), with the production ops checkout on the local side, causing the
15:45 ET chain pre-close wrapper to refuse daily ("HEAD is not aligned with
origin/main") — so the first real canary capture has never happened.

Schwab OAuth, believed broken, **recovered on 2026-08-12 09:31** — intraday
capture has been 15/15 healthy since (Repo-verified from receipts). The former
"reauth" owner blocker is gone; the fork is the active blocker.

## 2. The dependency chain (each link verified)

```
fork healed → ops checkout syncs → 15:45 wrapper alignment gate passes
→ first real canary capture (15/15 + manifest verify) → backup/restore drill
→ owner decision packet (bound feasibility number, starvation choice, OD-3)
→ guarded registration → owner flips ritual authority
→ daily ritual resumes → dashboards rebuild daily + research-refresh resumes
```

Independent of that chain: blocker **B2** (Schwab gate → registration receipt
path) must be closed in code before registration — brief
`docs/superpowers/plans/2026-08-13-07-h7-schwab-b2-receipt-path-codex-brief.md`.
The fork-healing/canary sequence is runbook
`docs/superpowers/plans/2026-08-13-08-fork-healing-ops-sync-canary-runbook.md`.

## 3. Automation lanes (2026-08-13 state)

| Lane | Last success | State | Root cause | Fix owner |
|---|---|---|---|---|
| daily-ritual (07:10 wd) | 2026-07-28 | BLOCKED BY TRACKED AUTHORITY (by design) | authority switch not flipped (owner-gated, end of H7 chain) | Carsyn (last step) |
| research-refresh (07:40/08:10 wd) | 2026-07-27/28 | refusing correctly (needs same-day ritual receipt) | downstream of ritual | same as ritual |
| intraday capture (5×/day) | today, 15/15 | HEALTHY since 08-12 09:31 | token outage: last success 08-07 15:45, failures 08-10 09:31 → 08-11 15:45, recovered 08-12 09:31. Recovery is Repo-verified; that a manual reauth caused it is Inference (an OAuth `ensure_active_token` failure is also consistent with a provider-side outage) | resolved |
| chain pre-close 15:45 | never (lane added 08-09) | refuses: ops HEAD ≠ origin/main | the fork | agent, after owner OK on ops sync |
| live-dashboard server | up, but code frozen 07-27 | serving 2.5-week-old code | never restarted after later merges | agent (kickstart) |
| dashboards (index/attractiveness) | 07-28 via ritual; manual regens 08-04/08-11 | stale, honestly self-labeled | downstream of ritual | same as ritual |

Perplexity: zero references in this repo, ops checkout, or LaunchAgents
(verified by grep). Whatever chat-side scheduled updates use it, it is not
part of this machine's stack; the local research lane's failure is the ritual
gate above, nothing to do with Perplexity.

## 4. Branch & work inventory (full table in session transcript; highlights)

- **Was uncommitted, now secured (this session):**
  `codex/pre-canary-capture-hardening` — the review's H1/H2/H3/M-c hardening
  (11 files, 277 ins) committed @401f78b after full offline suite exit 0 on
  that exact tree, and pushed. Merge remains owner-gated (runbook 08).
- **Were unpushed with real loss exposure, now pushed (this session):**
  `codex/h7-schwab-evidence-mode` (609d43a), `codex/handoff` tip (2c8332a) —
  hygiene rule 2026-08-04; pushing is backup, not integration.
- **Fork healer:** `codex/capitaliq-ownership-inputs` (c54c7c8) supersedes
  local main's unique commit eea4700; clean merge-tree into origin/main.
- **Needs adversarial review before merge:** `codex/h7-schwab-recovery`
  (registration CLI + B3-bound 2026-08-11 feasibility receipt: **4/1050**,
  expected entries 4.0 — vs the stale disclosed 3/1050).
- **Owner-read before merge:** `codex/short-positioning-phases-1-4` (new FINRA
  short-interest provider — provider-policy check), `codex/options-validator-plugins-design`
  (plugin program decision).
- **Stale, delete later with guard:** the four `codex/attractive-exp-*`
  branches (content already on origin/main).
- **Merged and done:** experiments dashboard split, RQ2 K=3 amendment
  (ledger seq 25), ops failure classification, attractiveness experiment
  program (all four experiment lanes render 18/18 from cache with honest
  per-lane as-of stamps — verified visually this session).

## 5. Owner decision queue (nothing here is an agent call)

1. **Approve ops-checkout sync** to healed origin/main (runbook 08 step 5).
2. **Starvation decision:** the B3-bound feasibility receipt says 4 expected
   entries per 70-session window (4/1050; exact 95% CI [1.09, 10.21] expected
   entries — recomputed for the bound number; the previously published
   [0.62, 8.74] belongs to the superseded 3/1050) vs the 20 the 2026-07-24
   gate requires. Two caveats travel with the number: it lives on the
   still-unreviewed `codex/h7-schwab-recovery` branch, and per review finding
   B4 it was measured on ThetaData EOD chains, not Schwab 15:45 pre-close
   data — every known simplification inflates it. Choices: redesign the entry
   rule/universe, or pre-accept starvation in writing (H10 precedent).
   Reviewer recommends redesign.
3. **OD-3 namespace wording** (template ready in the 2026-08-09 owner gate
   packet) + registration authorization + authority flip (strictly last).
4. **Optional decoupling** (new, this session — Inference, needs its own
   spec + review if chosen): approve Schwab as the ongoing exact-session
   source (`exact_session_source_active=True`) after canary+drill but BEFORE
   H7 registration, so the ritual/dashboards/research resume while the H7
   decision is taken calmly. Trade-off: weakens the single all-or-nothing
   gate; keeps H7 verdict authority fully gated. If declined, research stays
   down until H7 registration completes.
5. **Provider policy read** for FINRA short-interest branch; **plugin program**
   go/no-go; **stale experiment branch deletion** batch.

## 6. Corrections to prior belief (say-it-plainly log)

- "Schwab reauth is an open owner blocker" → **stale**; captures healthy since
  08-12 09:31. (The Saturday reauth reminder task remains useful — the token
  expires every 7 days.)
- "Monday 15/15 canary" wording in PROJECT_STATE/README → stale; the only
  specified Monday (08-10) fell inside the token outage. Correct reading:
  "next valid completed-session 15:45 ET canary" (the recovery branch already
  fixed its own copy of the wording).
- Receipt-directory freshness ≠ success: the 08-10..08-12 chain-capture
  "receipts" are refusal logs, not captures.
