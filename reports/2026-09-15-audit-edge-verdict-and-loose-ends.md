# 2026-09-15 — Audit: is there an edge, where is the verdict, and what was left loose

**Session:** Claude (Fable 5.1) with five Opus subagents (evidence audit, literature
memo, market/earnings packet, repo-efficiency audit, brief-41 hand-back review) and
one Opus adversarial review of this session's own code changes. Subagent memos are
preserved verbatim under `reports/2026-09-15-audit/` (A–F). Branch:
`claude/audit-2026-09-15` (worktree `.tmp/worktrees/audit-0915`, based on `main`
@ `6873263`).

**Vocabulary:** survived this test / not yet rejected / rejected / consistent with
zero edge. Every number carries a provenance label: Repo-verified, Run-verified,
Official-source (fetched), Fetched (paper read), LLM-asserted, or Inference.

---

## 0. Plain-English summary

1. **No edge has been shown, and none has been rejected either — because nothing has
   been given a chance to fail.** In two and a half months the paper books hold one
   options position, ever. Zero completed trades. Zero losses booked against loss
   bars of 7–10. The verdict machinery is sound; the entry rules and verdict bars
   were never jointly reachable, and then the data feed the entry rules needed was
   switched off (ThetaData, 2026-07-27). (Repo-verified, memo A §3.)
2. **The published research says the repo's own descriptive findings are the expected
   ones.** Options on single stocks are not systematically overpriced the way index
   options are (Driessen, Maenhout & Vilkov: realized volatility 39.9% *above* implied
   38.6% across S&P 100 names, Fetched). Buying calls on volatile, lottery-like names —
   the shape of H6, H7, H8 and H10 — has documented *negative* after-cost returns
   (Byun & Kim −10 to −20% per month on the most lottery-like stocks, LLM-asserted;
   de Silva, Smith & So −5 to −9% for retail around earnings, Fetched). Four of the
   five registered forward-paper families sit on the documented losing side. (Memo B.)
3. **The one structure the literature supports on these names has never been
   registered:** defined-risk *selling* of volatility across earnings on the two
   mega-caps where the repo itself measured a real IV run-up and crush (MSFT, AMZN).
   A candidate design is in §5 with every number labelled LLM-asserted; the owner
   types anything frozen.
4. **The production pipeline had been silently dead since Thursday 09-11.** One
   network blip left the ops checkout one unpushed evidence commit ahead of GitHub;
   because that commit contained two folders no capture gate recognised as evidence,
   every 15:45 chain capture and the 09-14 morning ritual refused. Root cause fixed
   on this branch with tests; the immediate stall was cleared by a fast-forward push
   at 01:4x ET. Three captures (09-11, 09-14, and 09-15 if the token is not renewed)
   are permanent gaps.
5. **Three owner actions are time-critical this week** (§2): renew the Schwab token
   before **10:36 ET today**; rule on the NVDA paper call that expires **Friday
   09-18** and cannot be closed by its own rules; run the fifteen earnings-store
   refresh commands so the H7 Schwab restart can be judged in October.

Terms used once and then reused: a **call** is the right to buy shares at a fixed
price (the **strike**) until a date (the **expiration**); it is **out of the money**
when the share price is below the strike. **Implied volatility (IV)** is the size of
move the option price is charging for; **realized volatility** is the move that
actually happened; the **variance risk premium** is the gap between them. A
**straddle** is a call plus a put at the same strike — a bet on movement in either
direction. A **loss bar** is the number of losing trades the registered rule requires
before any verdict may be read. A **paper** position is tracked, never executed.

---

## 1. What this session did and did not do

| Done (on this branch unless noted) | Not done, and why |
|---|---|
| Pushed the stalled ops evidence commit `6873263` to `origin/main` (fast-forward, main checkout too). Live pipeline unblocked 01:4x ET. | Did not re-auth the Schwab token — owner-only (`tools/setup_schwab.py`, Keychain). |
| Root fix: `reports/pick_tracker` and `reports/closes_receipts` added to all four `EVIDENCE_ALLOW` copies and the activation-day routine list; two Schwab activation namespaces added to the ritual's full-tier staging list. Tests pin the superset relation and replay the 09-11 commit shape. | Did not touch `ledger/`, `config.py`, `data/`, cache bytes, or the paper books. |
| Ritual self-heal: the alignment gate now fetches first, refuses when behind, and pushes its own evidence-only divergence once before proceeding (no merge, no new authority), and notifies the desktop when it refuses. After the independent review (memo F) the shared evidence-only predicate in all five scripts also refuses any code-suffixed path and any non-regular file mode (symlink, gitlink). 15 behavioural + structural tests against a real temp repo with a bare origin. | Did not register, amend, or close any hypothesis — owner-only or delegated-with-review; packets below instead. |
| Docs: CLAUDE.md pointer-style rewrite; `.cursorrules` ↔ `AGENTS.md` reconciled (both now carry the draft-PR hold, catalyst rule, hard guardrails, verdict rule); README paper-book row de-duplicated; PROJECT_STATE.md restructured with its 1,043-line history moved byte-for-byte to `docs/status-history/`. | Did not collapse the two long owner-directed amendment paragraphs in `.cursorrules` (memo D, A6) — governed wording; proposal only. |
| Hooks: byte-identical copies of the two laptop-only hook bodies (`block_live_trading.py`, `session_note_guard.py`) are now tracked in `.agents/hooks/`, with their first tests (`tests/test_block_live_trading.py`, `tests/test_session_note_guard.py`). | Did not switch the local hook registration (`.claude/settings.local.json`), so **enforcement today still runs the untracked laptop copies** — a two-line owner change once this lands (§4 item 4); switching before the files exist in the main checkout would fail-closed and block every tool call. |
| Dead Node files removed (`crawler.js`, `package.json`, `package-lock.json`; no consumer anywhere — Run-verified grep). | Did not delete untracked `node_modules/` (120 MB), `.coverage`, `Untitled*` — owner runs the deletion after the repo's guard, per the worktree rule. |
| Brief 41 hand-back reviewed adversarially (memo E): PASS WITH FIXES. | Did not open its PR: it must rebase and recompute the same line-number registries this branch changes (§4 item 6). |

Deviation from `CLAUDE.md` "Division of labor" (Claude does not write ops-script
code): done under Carsyn's in-session directive to implement loose-end fixes on a
worktree. The ops-script change was adversarially reviewed by an independent Opus
agent before commit (memo F) and carries new tests.

---

## 2. Owner actions this week, in order

| When | Action | Why |
|---|---|---|
| **Before 10:36 ET Tue 09-15** | `uv run python tools/setup_schwab.py` | Refresh token expires 14:36 UTC (Run-verified, `schwab_token_age`). After that the 15:45 capture fails and each missed session is a permanent gap. |
| **After this PR merges** | `git -C ~/options-validator-ops fetch -q origin main && git -C ~/options-validator-ops merge --ff-only origin/main` | Puts the self-healing gate and widened allow-lists into the checkout the LaunchAgents run. Confirm `rev-parse HEAD == origin/main` before 15:45 ET. |
| **Before Fri 09-18** | Rule on H6-0001 (§7) | Expires Friday; no registered close path is executable. |
| This week | Run the 15 `append-raw` + `promote` commands (§6) | Source health is 2/15; activation needs 9/9 cohort names healthy. |
| Next | Ratify or veto the four record-level items in §4 | H9 seal fact, hook registration switch, branch deletions, brief-41 landing order. |

---

## 3. The edge question, answered honestly

### 3.1 What the repo has actually measured (memo A, all Repo-verified)

| Finding | Number | Strongest reason it could mislead |
|---|---|---|
| H1 / H2 index put-credit spreads, in-sample 2018–22 | H1 n=226, expectancy −$102.79/trade, CI90 [−132.61, −74.46]; H2 n=196, −$39.07, CI90 [−61.28, −18.08] | Fails **at full-quoted-spread costs**; memo B shows careful limit-order traders pay 40–75% of that. Still: rejected under the registered rule. |
| High IV-rank did not mean rich premium (Study A) | forward realized ≥ implied on all four core names at IVR ≥ 0.70 | Names chosen after the AI/power boom; a boom is exactly when realized beats implied. |
| Earnings IV run-up/crush real on MSFT/AMZN, absent on VST/CEG (Study B) | MSFT +0.039/−0.076, AMZN +0.052/−0.145 (17–34 events per name) | Medians on ≤34 events, no confidence interval. |
| Covered calls ≈ or < buy-and-hold (Study C) | VST −$3,098 over 42 cycles; AMZN +$574 over 47 | One bull run; frictionless share re-buy. |
| The only positive result: H9 post-earnings conditional (non-blind, one run) | 16 trades, 12W/4L, +$290/trade, CI90 [+27.82, +574.46] | 4 losses vs a 10-loss bar; declared non-blind; 47% of the P&L is fill timing the rule never promised (+100% take-profit filled at 0.73×–3.84× cost); best trade is 49% of P&L. |
| Forward paper windows (H6, H7, H8, H10a, H10b) | **1 position ever; 0 completed; 0 losses** | Not evidence of anything. Sample starvation. |

Where the verdict went (memo A §3, Repo-verified): H7's measured entry base rate is
0.00635 per symbol-day → 4.0 expected entries against the 14–20 its own feasibility
gate requires; H10b disclosed 11 fires in ~8 years against a 7-loss bar; both were
registered before the 2026-07-24 feasibility gate existed, which binds only future
registrations. The two studies that did produce numbers (H9, CARD3) were one-shot
and landed under their bars. Then the data feed for every entry rule froze on
2026-07-27, and H6/H8 have no Schwab-lane path at all.

### 3.2 What the published research says (memo B; 24 of 29 sources read directly)

| Family | Literature verdict | Load-bearing evidence |
|---|---|---|
| Short volatility across earnings (never registered here) | Positive, documented; after-cost survival conditional on spreads | Dubinsky et al. (RFS 2019): straddle buyers lose −7.96% mean, −10.24% median across the announcement, negative in all 16 sample years, t = −13.25 (Fetched). |
| H5 income core (LEAPS + CSP + covered call) | Weakly positive; mostly beta, minimal alpha | Cboe BXM 1986–2026: Sharpe 0.56 vs 0.57 for the S&P 500 (Official-source). Israelov & Nielsen: ~25% of covered-call risk is an *uncompensated* reversal bet — which is exactly why VST's bull run cost the writer. |
| Pre-earnings long **straddle** (H8's window, different structure) | Positive before costs; survives only short-dated, low-spread names | Gao, Xing & Zhang: +2.3% for the [−1, 0] window (Fetched); only below-median-spread names stay positive at full quoted spread. |
| H6 post-earnings long calls | Unsupported to negative | No study found with after-cost positive directional calls post-earnings; post-earnings drift in large caps is statistically zero since 2006 (Martineau, Fetched). |
| H8 pre-earnings long calls | Documented negative for the retail implementation | de Silva, Smith & So (Rev. of Finance 2026): retail lose 5–9% on average, 10–14% on high-expected-volatility announcements, and "mainly purchase call options" (Fetched). |
| H10a/b continuation long calls; H7 swing calls on volatile AI names | Documented negative, most strongly for H7 | Option momentum is a long-short *straddle* effect that dies at full spread (Heston et al., Fetched); calls on lottery-like, high-idiosyncratic-vol names underperform 10–20%/month (Byun & Kim, LLM-asserted); the watchlist is selected on precisely those traits. |

Cost model check (memo B Q5): "mid-or-worse + 1% haircut + half-spread both legs" ≈
100% of the quoted half-spread per leg. Muravyev & Pearson's Internet Appendix puts
the conventional effective half-spread on non-S&P-500 names at 76% of quoted, and
execution-timing traders at 20% (Fetched). **The model is conservative but
defensible.** H1/H2 should be described as "rejected at full-quoted-spread costs,"
not "rejected at realistic costs."

### 3.3 Verdict on the question asked

- **Can an edge be proven from current evidence?** No. Nothing in the record clears a
  loss bar; the one positive-looking number (H9) is non-blind, under its bar, and
  half of it is fill timing. Under the repo's own vocabulary the honest state is
  "no answer," which is different from "no edge found."
- **Is there evidence toward zero edge?** Yes, and it converges from two directions:
  the repo's descriptive studies and the peer-reviewed record agree that single-name
  premium is thin and that directional long calls on these names lose after costs.
  For H7 and H10 specifically, "no edge found" is the *expected* outcome — a
  successful result by this project's rules, not a failure.
- **Can an edge be "created"?** Not by this session — creation here means
  registration, and the owner types every frozen number. What the evidence supports
  is a *redirection*: the only family with documented after-cost support on these
  names is event-driven short volatility on MSFT/AMZN, which also solves the sample
  problem (earnings are scheduled, so entries are guaranteed) — see §5.

Market conditions at the time of writing (memo C, all Official-source fetched): VIX
17.10 on 09-14, 20-session close range 14.32–17.84; FOMC decision due Wednesday
09-16 with projections; Friday 09-18 is the standard monthly expiration; NVDA closed
$210.96 on 09-14. None of this changes the analysis above; it is context for the
H6-0001 packet.

---

## 4. Integrity findings (owner decisions)

| # | Finding | Evidence | Proposed disposition |
|---|---|---|---|
| 1 | **H9's receipt hash does not cover H9's numbers.** The recorded `5bea2018…` seals nine scalar keys; `board` (expectancy, CI, total P&L) and the 16-row `trades` sit outside the seal. Recomputed and confirmed by the audit agent. The file itself is unchanged since its one commit (`d91b1ec`). | `tools/h9_run_study.py:169-171`; `ledger/facts.log:17892` (memo A §4.1) | Owner-ratified fact binding the full document: `reports/h9/receipt.json` sha256 `30df74c4e91e0b23c28d7e70391da6d851feb7b21084bf9ab27ae417a63e7a93` at `d91b1ec` (Run-verified 2026-09-15). Future studies hash the whole receipt. |
| 2 | **H6's verdict bar and hard-kill are read live from `config.py`** and a test pins the defect (`test_hard_kill_uses_registered_configured_month_count` patches the bar to 2). H7's scorer reads the bar from the ledger event — the safe pattern exists in-repo. | `h6_watch.py:826,719`; `tests/test_h6_watch.py:493` | Codex brief: bind H6/H8/H10b bars to the ledger record; retire the value-patching test. Not started. |
| 3 | **H8 has a registered verdict rule and no scorer at all.** | grep `score` in `h8_watch.py` → nothing | Same brief as #2, or retire H8 pending re-registration (owner call). |
| 4 | **Two of three "hard enforcement" hooks were laptop-only.** | `.gitignore:22`; memo D D1 | Tracked now in `.agents/hooks/`. Owner switches the two `command` paths in `.claude/settings.local.json` to `.agents/hooks/` after merge. |
| 5 | **The allow-list hazard was named on 09-08 and only patched sideways.** Brief-40 round-2 finding 3 said exactly what happened on 09-11; the fix went into the activation-day script, not the ritual or the capture gates. | `reports/2026-09-08-brief-40-adversarial-review-round2.md:17` | Fixed at root on this branch. Process lesson for `executor-handback-verification`: a finding about a shared list is closed only when every copy and its producer agree, pinned by a superset test. |
| 6 | **Brief 41 is implemented and green but unlanded**, and it renumbers the same test registries this branch renumbers. | memo E (117 targeted + 3,925 full tests OK on its branch, Run-verified) | Land this PR first; then Codex rebases brief 41 and recomputes `PYTHON_DASH_C_CLASSIFICATION` / `MUTATION_VERB_SITES` against the merged script (+68 above line 386 on top of its own +11). Do not hand-pick one side of the conflict. |
| 7 | Seven stale local branches and six remote copies remain deletion candidates (PRs #159–#165 merged). | `reports/2026-09-09-pm-sweep-and-pattern-findings.md` §1 | Owner runs the listed commands after the guard, per-target yes. |

---

## 5. Research direction — candidates for the owner (nothing here is registered)

Per `ledger-discipline`: every number below is **LLM-asserted** (memo B Q6); owner
fields are left blank; a registration packet would need its own independent
adversarial review and the 2026-07-24 feasibility computation from cached data.

| | Candidate A — earnings-window defined-risk short volatility | Candidate B — reversal-stripped monthly overwrite |
|---|---|---|
| Structure | Short at-the-money strangle with protective wings (an iron condor: defined maximum loss), nearest monthly expiration with ≥3 sessions after the report | ~0.20-delta covered call plus cash-secured put, **skipping the call-write in months the name is in the top tercile of 12-month momentum** |
| Names | MSFT, AMZN only (the two where Study B found a real run-up/crush; tightest spreads on the list) | MSFT, AMZN only; explicitly excludes VST/CEG and the AI watchlist |
| Entry / exit | Close before the report → close after (end-of-day cadence) | First session after monthly expiration → hold to expiration |
| Why | Dubinsky et al.: straddle buyers lose across the event in all 16 years; the run-up edge (Gao et al.) stops *before* the news, so the windows separate cleanly | Israelov & Nielsen: strip the uncompensated reversal exposure that cost the VST writer |
| Expected trades / year | 8 (4 reports × 2 names) — scheduled, so the sample cannot starve | ~16 call-writes after the veto, up to 24 put-sales |
| Loss bar feasible in ≤12 months (≥2× rule) | 4 | 8 on the call-write leg |
| Main risk | Thin sample; one outsized gap dominates; four legs of spread cost | Edge is small and mostly beta |
| Owner-typed fields | strikes / wing width / delta band / loss bar / window: ______ | delta / momentum veto rule / loss bar / window: ______ |

Structural recommendation (Inference): future registrations should be
**event-driven** (earnings, auctions) rather than **trigger-driven** (parabolic,
breakout), because the base rate of the trigger stack — not the strategy — is what
has kept every verdict out of reach.

---

## 6. Earnings-store refresh packet (owner runs; all dates Official-source, SEC 8-K Item 2.02)

Fifteen `append-raw` rows, then one `promote --event-class actual_quarterly_earnings`
per row. Two fields per row are not in the packet and must come from the EDGAR filing
index the URL points to: `--known-as-of` (the filing's `acceptanceDateTime`, the
store's convention for occurred records) and `--timing` (bmo/amc; `unknown` is
accepted). Full URLs and the verbatim confirming sentences: memo C Part 1a.

```bash
R="uv run python tools/h7_refresh_earnings.py append-raw --status occurred --source-type sec_filing --record-type assertion"
$R --symbol CRWV --event-id CRWV-2026Q2  --fiscal-period 2026Q2  --occurred-date 2026-08-11 --timing unknown --source-url https://www.sec.gov/Archives/edgar/data/1769628/000176962826000362/crwv-20260811.htm --known-as-of <acceptanceDateTime>
$R --symbol TEM  --event-id TEM-2026Q2   --fiscal-period 2026Q2  --occurred-date 2026-07-30 --timing unknown --source-url https://www.sec.gov/Archives/edgar/data/1717115/000119312526326083/tem-20260730.htm --known-as-of <acceptanceDateTime>
$R --symbol PLTR --event-id PLTR-2026Q2  --fiscal-period 2026Q2  --occurred-date 2026-08-03 --timing unknown --source-url https://www.sec.gov/Archives/edgar/data/1321655/000132165526000039/pltr-20260803.htm --known-as-of <acceptanceDateTime>
$R --symbol NOW  --event-id NOW-2026Q2   --fiscal-period 2026Q2  --occurred-date 2026-07-22 --timing unknown --source-url https://www.sec.gov/Archives/edgar/data/1373715/000137371526000072/now-20260722.htm --known-as-of <acceptanceDateTime>
$R --symbol SMCI --event-id SMCI-FY26Q4  --fiscal-period FY26Q4  --occurred-date 2026-08-11 --timing unknown --source-url https://www.sec.gov/Archives/edgar/data/1375365/000137536526000021/smci-20260811.htm --known-as-of <acceptanceDateTime> --notes "full report; the 2026-07-21 Item 2.02 was PRELIMINARY (do not promote as actual)"
$R --symbol NVDA --event-id NVDA-FY27Q2  --fiscal-period FY27Q2  --occurred-date 2026-08-26 --timing unknown --source-url https://www.sec.gov/Archives/edgar/data/1045810/000104581026000073/nvda-20260826.htm --known-as-of <acceptanceDateTime>
$R --symbol AMD  --event-id AMD-2026Q2   --fiscal-period 2026Q2  --occurred-date 2026-08-04 --timing unknown --source-url https://www.sec.gov/Archives/edgar/data/2488/000000248826000121/amd-20260804.htm --known-as-of <acceptanceDateTime>
$R --symbol AVGO --event-id AVGO-FY26Q3  --fiscal-period FY26Q3  --occurred-date 2026-09-02 --timing unknown --source-url https://www.sec.gov/Archives/edgar/data/1730168/000173016826000076/avgo-20260902.htm --known-as-of <acceptanceDateTime>
$R --symbol IREN --event-id IREN-FY26Q4  --fiscal-period FY26Q4  --occurred-date 2026-08-27 --timing unknown --source-url https://www.sec.gov/Archives/edgar/data/1878848/000187884826000051/iren-20260827.htm --known-as-of <acceptanceDateTime> --notes "the 2026-07-20 Item 2.02 was a business update, not a quarterly report"
$R --symbol USAR --event-id USAR-2026Q2  --fiscal-period 2026Q2  --occurred-date 2026-08-10 --timing unknown --source-url https://www.sec.gov/Archives/edgar/data/1970622/000197062226000056/usar-20260810.htm --known-as-of <acceptanceDateTime>
$R --symbol ET   --event-id ET-2026Q2    --fiscal-period 2026Q2  --occurred-date 2026-08-04 --timing unknown --source-url https://www.sec.gov/Archives/edgar/data/1276187/000127618726000033/et-20260804.htm --known-as-of <acceptanceDateTime>
$R --symbol VST  --event-id VST-2026Q2   --fiscal-period 2026Q2  --occurred-date 2026-08-07 --timing unknown --source-url https://www.sec.gov/Archives/edgar/data/1692819/000169281926000017/vistra-20260807.htm --known-as-of <acceptanceDateTime>
$R --symbol CEG  --event-id CEG-2026Q2   --fiscal-period 2026Q2  --occurred-date 2026-08-06 --timing unknown --source-url https://www.sec.gov/Archives/edgar/data/1868275/000186827526000097/ceg-20260806.htm --known-as-of <acceptanceDateTime>
$R --symbol MSFT --event-id MSFT-FY26Q4  --fiscal-period FY26Q4  --occurred-date 2026-07-29 --timing unknown --source-url https://www.sec.gov/Archives/edgar/data/789019/000119312526323632/msft-20260729.htm --known-as-of <acceptanceDateTime>
$R --symbol AMZN --event-id AMZN-2026Q2  --fiscal-period 2026Q2  --occurred-date 2026-07-30 --timing unknown --source-url https://www.sec.gov/Archives/edgar/data/1018724/000101872426000024/amzn-20260730.htm --known-as-of <acceptanceDateTime>
# then, for each printed raw id A0xxx:
# uv run python tools/h7_refresh_earnings.py promote --raw-id A0xxx --event-class actual_quarterly_earnings
# uv run python -m options_researcher.h7_source_health
```

**Next dates:** none of the 15 companies has announced its next report as of
2026-09-15 05:53 UTC (three independent checks in memo C; Microsoft's IR page says
verbatim that the date "will be announced soon"). Two aggregator dates (CRWV "Nov 16",
PLTR "Nov 2") were seen and rejected per the store's rules. Re-run the check the week
of 2026-10-05.

---

## 7. H6-0001 disposition packet (owner ruling needed before Friday)

**Position (Repo-verified):** H6-0001, NVDA $220 call, expiration 2026-09-18,
1 contract, entered 2026-07-13 at $920.65 premium, receipt-bound; exit fields blank.

**Why it cannot be closed by its own rules (Repo-verified):** the registered exits
are take-profit (+100%) or a time close at 21 days to expiration (~2026-08-28). The
H6 evaluator rebuilds features from the exact-session ThetaData chain, which ended
2026-07-27, so no receipt for any later session can exist; the ritual marks the H6/H8
leg PAUSED behind the H7 gate. The position is orphaned by the provider exit, not
merely late.

**Marks (Repo-verified from the Schwab pre-close capture, not a registered H6 mark
source):** 2026-09-10 bid 3.75 / ask 3.80, delta 0.46, IV 0.339. NVDA closed $210.96
on 09-14 (Official-source), so the strike is out of the money by $9.04 with three
sessions left. Mark-to-market at 09-10 mid ≈ −$543 (−59%); the 07-27 mark was
−$441 (−48%).

**Options for the ruling (owner picks; nothing pre-filled):**

| Option | What it records | Integrity note |
|---|---|---|
| (a) Let it expire; append a disclosure fact | `H6_0001_UNMARKED_EXPIRY`-style fact: entry, the missed 21-DTE close and why, the last Schwab-lane mark, exit at expiration intrinsic value (likely $0 unless NVDA > $220 at Friday's close) | Cleanest. H6 stays `INSUFFICIENT_SAMPLE` (n = 0 completed under registered rules). No retroactive rule change. |
| (b) Record a late `time_21_dte` close at a reconstructed mark | The book validator accepts an exit at ≤ 21 DTE, but every close must cite a watch receipt, and none can be produced | Would require hand-editing a receipt-bound book — contradicts the registration. Not recommended. |
| (c) Amend H6 prospectively to a Schwab-lane evaluator (as H10b/H5 were) | Does not rescue this position; governs future entries only | Only worthwhile if the owner still wants H6 at all given memo B's verdict on post-earnings long calls. |

Whichever option: the fact append is owner-ratified (precedent `H10A_RESULT`,
`A2_ENTRY_CONVENTION_RATIFIED_V1`), via the typed facts API, never by hand.

---

## 8. Efficiency changes and proposals not taken

| Item | Status |
|---|---|
| Full offline suite wall clock | On this branch before the review fixes: **3,918 tests, OK (5 skipped), unittest exit 0, 5 min 32 s** (Run-verified 2026-09-15 on the worktree; the post-fix count is in the commit message). An earlier 9 min 51 s figure on `main` was wall clock only — its "exit 0" came from a `tail` pipeline, not from unittest, and is not relied on. Fast loop documented in CLAUDE.md (`PYTHONPATH=tests … <module>`); no runner change (CLAUDE.md pins `unittest`). |
| Instruction load per session | Roughly unchanged in bytes (CLAUDE.md 8.9 KB → 9.1 KB after adding three commands and two pointers; `.cursorrules` 8.4 KB → 9.4 KB after porting the two Codex-only rules). The win is correctness, not size: the stale scope-gate and P0 references, the hand-maintained skill list, the restated hypothesis list, and the README holdings copy are gone (memo D A1–A3, A7, A9, A10). Memo D's "39% smaller" draft was not adopted because it dropped the od1-v2 incident text, which is not duplicated anywhere else. |
| PROJECT_STATE.md | 100 KB prepend-log → ~7 KB canonical head + two verbatim history files (`docs/status-history/`). All seven section-anchored cross-references resolve in the history files. |
| Not done: `.cursorrules` A6 collapse of the two owner-directed amendment paragraphs (~2.4 KB) | Governed wording; proposal only. |
| Not done: `pytest-xdist` accelerator | 141 of 218 test modules use tempfile; collisions must be proven absent first (memo D P6). |
| Not done: three 2026-07-25 runbook docs (`docs/monday-runbook.md`, `docs/options-validator-readiness.md`, `docs/codex-implementation-plan.md`) | 13 inbound wiki links; propose a one-line SUPERSEDED banner rather than deletion. |

---

## 9. Independent review of this session's own code (memo F)

Verdict **PASS WITH FIXES**. Across a 22-case attack matrix against real scratch
repositories (renames into evidence directories, evil merges, prefix and
traversal confusion, case variants, code deletions, newline filenames, a
non-fast-forward race between fetch and push, a stale ref after a failed fetch)
the gate never pushed unreviewed executable code. Applied from the review:

- the dropped precedence clause restored in all three instruction files (G1);
- `docs/h7-forward-operations.md` and the brief-40 acceptance text corrected (F);
- code-suffix and file-mode rejects added to the shared predicate and to the
  activation routine filter, with tests (D, B/S1);
- desktop notification on gate refusal (I1); `-C "$REPO"` on the network calls (I3);
- the "(non-negotiable)" qualifier and `h7_positions.csv` pointer (G2, G3);
- tests for the two newly tracked hooks (H2); the stale line-number prose and
  the cwd-dependent test path in the provenance suite (E).

Deferred, with reasons: switching the local hook registration (H1) is the
owner's step after merge (§1); the empty-tree / revert push shape (review B
#10/11a) lands unreviewed *history* but never an unreviewed *tree*, and the fix
would break the legitimate self-heal path, so it is documented here rather than
patched. The reviewer also noted the boundedness of the fetch and push relies on
the origin being HTTPS (the `http.lowSpeed*` flags are inert over SSH) — true
today for both checkouts.

## 10. Process notes

- **Privacy slip by a subagent, self-reported:** the earnings-dates agent sent an
  HTTP User-Agent containing Carsyn's personal email address to sec.gov /
  data.sec.gov for its first several EDGAR requests (05:38–05:47 UTC), despite the
  brief saying to use a non-personal identifier. No other host received it; SEC's
  own access guidance invites a contact string, so the exposure is limited to SEC's
  request logs. Any repeat run should use a fixed non-personal UA. Recorded here so
  it is not repeated silently.
- **Two PDF-reading steps hallucinated citations** during the literature work; the
  agent caught both by converting PDFs locally and cross-checking. Every number in
  memo B is tagged Fetched or LLM-asserted for that reason.
- **One audit claim was wrong and caught by verification:** memo D asserted the od1-v2
  worktree-loss narrative was already duplicated in `.claude/rules/data-and-providers.md`;
  it is not, so that paragraph stays in CLAUDE.md.
- IR-site quirks worth persisting for any future earnings job: Broadcom's events page
  lives at `/company-information/events-presentations`; Energy Transfer's live
  calendar is `/presentations-webcasts` (the obvious path is a soft 404); Vistra's
  events page defaults to the Past tab; `ir.usare.com` and `investors.iren.com` do
  not resolve.
