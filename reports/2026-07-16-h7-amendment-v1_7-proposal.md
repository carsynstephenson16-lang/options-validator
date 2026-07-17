# H7_AMENDMENT_V1_7 — PROPOSAL — **DECLINED BY OWNER 2026-07-16**

**Date drafted:** 2026-07-16
**Date decided:** 2026-07-16 — **DECLINED. Nothing admitted.**
**Status:** **CLOSED. NOT REGISTERED, NEVER IN EFFECT.**
`config.H7_WATCHLIST` is untouched. **No ledger fact was appended** — a
declined proposal registers nothing, so there is nothing to record in the
ledger. This file is the record.

**Outcome:** owner declined all three candidates (CRWD / NBIS / ZS) on the
evidence below. Owner's stated reasoning, verbatim: *"The evidence shows no
immediate trade, and adding names would increase risk without moving H7 closer
to an answer."* No scope override was invoked; the standing rule (nothing new
before the Phase-0 verdict) therefore stands unbroken.

**Who does what:** Claude drafted the evidence tables below. **The owner types
the decision and any frozen numbers.** Per the operating manual (rule 3), a
parameter Claude fills in is not a pre-registration — it is theater. Blank
decision fields below are deliberate and must stay blank until the owner fills
them.

**Precedent this follows:** `H7_AMENDMENT_V1_5` (IREN, 2026-07-14) and
`H7_AMENDMENT_V1_6` (USAR, 2026-07-15) — the two prior owner-typed ticker
admissions to the H7 watchlist.

---

## 1. What is being proposed

Owner asked 2026-07-16 to add recently-scanned tickers to the universe. Scoped
down, the only coherent version of that request is: **admit one or more of
CRWD / NBIS / ZS to `config.H7_WATCHLIST`** so the H7 daily watcher evaluates
them like any other story name.

Explicitly NOT proposed here:
- **Any change to `config.UNIVERSE`.** That list is the research/display set and
  a risk-math denominator (`MAX_LOSS_PER_TRADE × len(UNIVERSE)`), not a
  trading permission. Adding 5 names would move simultaneous at-risk from
  $2,400 (17.1% of the $14,000 sleeve) to $5,400 (38.6%) with no risk setting
  touched, while the added names are all the same AI factor — concentration
  wearing the costume of diversification. It also silently widens H5's live
  evaluator scope (`options_researcher/attractiveness.py:425` iterates
  `config.UNIVERSE`). It would make nothing tradable.

  **CORRECTION 2026-07-17 (owner-flagged):** this section originally added
  "and would spend paid ThetaData on every run via
  `options_researcher/live_quotes.py`." **That was wrong and is withdrawn.**
  `live_quotes.py` makes ONE BATCHED `stock_snapshot_quote` call for the whole
  list (docstring ~line 475), so cost is flat in `len(UNIVERSE)`; its other
  call site is a one-shot manual `--probe`, and an entitlement denial falls
  back to put-call-parity spot rather than failing. The claim was asserted
  without reading the module. **The decline stands unchanged** — it never
  rested on the spend claim, and the risk-denominator argument ($2,400 ->
  $5,400 with no risk setting touched) is unaffected.
- **IBEX and UNH.** See the evidence table; both fail on measured data.

## 2. Measured evidence per ticker (2026-07-15 chains)

Admission bar = `H7_ADMIT_MIN_CONTRACTS` (>=5) near-the-money (+/-10% spot)
monthly contracts at 30-120 DTE with spread <= `H7_ADMIT_MAX_SPREAD_PCT` (5%)
and OI >= `MIN_OPEN_INTEREST` (100). Route computed by
`options_researcher/h7_signals.py` (the single decision authority).

| Ticker | Admits? | Route today | Earnings on file? | Verdict of the evidence |
|---|---|---|---|---|
| **CRWD** | **YES — 8** | `none` (IV/RV **1.152272**, misses lane_b by 0.0023) | **YES** (`data/earnings/calendar.csv`) | **Only coherent candidate** |
| **NBIS** | **YES — 7** | `none` (IV/RV **1.1734**, dead zone 1.15–1.25) | **NO** | Would be entry-banned on admission |
| **ZS** | **NO — 4** | `none` (**no expiry in the registered 72–108 DTE band**) | **NO** | Fails the bar; argues against |
| UNH | NO — 1 | n/a | n/a | Fails bar (EOD artifact; unresolvable on EOD data) |
| IBEX | NO — 0 of 72 | n/a | n/a | Rejected 2026-07-16; chain deader than HYLN |
| *IREN (live ref)* | *YES — 5* | *`h7c` (1.38)* | *YES (health CLEAR)* | *already admitted V1_5* |

Incumbent reference: PLTR 31, NVDA 69, AMZN 71 admitted contracts. **Every
candidate here clears by 5–8 — a thin margin that can vanish day to day.**

## 3. Arguments AGAINST each candidate (read these first)

**CRWD**
- Routes `none` today. The 0.0023 miss is a **miss**; a threshold rounded
  toward when convenient is not a threshold. There is no signal to act on.
- Admits by 8 contracts vs incumbents' 31–71. Thin.
- Deepens the AI/high-beta-tech factor concentration the standing correction
  names as the book's single biggest exposure.
- **It is new scope before the Phase-0 verdict**, which the standing rule
  forbids without an explicit owner override (as H7 itself got 2026-07-09).

**NBIS**
- All of the above, plus **no earnings data** -> source health UNHEALTHY ->
  per-name entry ban under amendment v1.4 (CRWV precedent). It would be
  admitted and immediately unable to trade. An earnings source must land first.
- Is an AI neocloud — the CRWV/IREN trade in costume. Highest factor overlap
  of the three.

**ZS**
- **Fails admission (4 < 5)** and has no expiry at the registered IV tenor, so
  the route cannot even be computed. No earnings data either. Admitting it
  would mean overriding the mechanical gate on a name the gate rejected.

## 4. Owner decision block — **DECIDED 2026-07-16: DECLINE ALL**

Provenance note: the three NO values below were **dictated by the owner in
session on 2026-07-16** and transcribed here by Claude at the owner's explicit
instruction. Claude decided nothing. A decline freezes no parameter and grants
no permission, so transcription carries no pre-registration risk — this is the
owner's call, recorded. The blank fields below are blank **because the owner
directed them left blank**, and they are moot: every one is conditional on a
YES that did not occur.

```
DECISION (owner, 2026-07-16):

  Admit CRWD to H7_WATCHLIST?          [ YES / NO ]  NO
  Admit NBIS to H7_WATCHLIST?          [ YES / NO ]  NO
  Admit ZS   to H7_WATCHLIST?          [ YES / NO ]  NO

  If any YES — the standing rule (nothing new before the Phase-0 verdict)
  requires an explicit scope override. State the reason in one sentence:

    Override reason: ______  (left blank per owner — no override invoked,
                              none needed; the standing rule stands unbroken)

  If NBIS admitted — earnings source required before entry is possible.
    Source: ______  (left blank per owner)   Landed? [ Y / N ] ______

  Re-measure admission at entry time? [ YES / NO ] n/a — nothing admitted

  Any change to MAX_LOSS_PER_TRADE or the sleeve? [ NO / value ] NO — untouched
    (H7 has its own sleeve: H7_MONTHLY_AT_RISK = 6000, owner-typed 2026-07-09)
```

**Owner's reasoning, verbatim (2026-07-16):** *"The evidence shows no immediate
trade, and adding names would increase risk without moving H7 closer to an
answer."*

**Consequences of the decline (each verified against the tree, nothing done):**
- `config.H7_WATCHLIST` unchanged — still 10 names; universe still 13.
- `config.UNIVERSE` unchanged — still `["MSFT", "AMZN", "VST", "CEG"]`;
  simultaneous at-risk stays $2,400 (17.1% of the $14,000 sleeve), NOT $5,400.
- No ledger fact appended. No hash chain touched.
- No backfill purchased. ThetaData spend avoided ahead of the ~2026-07-29 lapse.
- Read-only diagnostic **not built** — owner declined it absent a specific need
  to watch these names daily.

## 5. If ratified — the mechanical steps (not yet performed)

1. Owner appends the `H7_AMENDMENT_V1_7` fact via the typed API
   (`research/facts.py`) — **never** by hand-editing `ledger/facts.log`; a hand
   edit breaks the hash chain and `verify` refuses.
2. Add the ticker(s) to `config.H7_WATCHLIST` with a comment citing the fact,
   matching the V1_5/V1_6 style already in `config.py:293-295`.
3. Backfill chain history + closes for the admitted name(s). **Cost gate:**
   ThetaData lapses ~2026-07-29 — IREN's backfill was 1,054 chains. Per-pull
   owner approval required.
4. Add earnings provenance for NBIS if admitted, else it stays entry-banned.
5. Run `h7_source_health` (must be healthy per-name), then `h7_data_gate`
   (must exit 0), then `h7_watch` — the operator order fixed by amendment v1.4.
6. Update the test universe count (currently 13; `tests/` asserts it).

## 6. Recommendation

**Admit nothing today.** The scan produced no signal on any of the three, the
one coherent candidate (CRWD) routes `none` and clears the bar by a thin
margin, and all three deepen the book's single largest factor exposure. None of
this moves H5, H6, or H7 toward its declared verdict — which is the scope-guard
question, and the answer is no.

The cheapest honest alternative, if the goal is simply eyes on these names: a
**read-only diagnostic view** that reports their lane routing daily without any
of them entering a hypothesis. No amendment, no scope change, no ticker in any
config list, no verdict impact.

If CRWD is genuinely wanted, the honest sequence is: owner-typed override
reason -> `H7_AMENDMENT_V1_7` fact -> watchlist entry -> backfill -> source
health -> the watcher routes it like any other name. That is a registration
decision, not a scan result.

**Outcome 2026-07-16: owner concurred with this recommendation and declined all
three.** The read-only diagnostic was also declined absent a specific need.

## 7. If this question returns

Do not re-run the scan per-ticker from scratch. The mechanical gate is cheap
and comes first: compute admission (`>=5` NTM monthly 30-120 DTE contracts at
`<=5%` spread, `OI>=100`) and the `h7_signals` route BEFORE any analysis or
narrative. A name that fails admission needs no thesis; a name that routes
`none` has no trade regardless of how good the story is.

Note the standing asymmetry this proposal illustrates: **admission is necessary
but nowhere near sufficient.** CRWD and NBIS both admitted and still produced
nothing, because routing is a separate gate. Clearing the liquidity bar is the
beginning of the question, not the answer to it.

Chain data for CRWD/ZS/NBIS/UNH @ 2026-07-15 is cached in `.cache/chains/` and
free closes sit in `.cache/underlying` — a re-check of these five names costs
nothing while those files survive (both dirs are disposable/gitignored). After
ThetaData lapses ~2026-07-29, a fresh measurement is not purchasable at all
without a renewal.

**This file changes nothing. It records a declined proposal.**
