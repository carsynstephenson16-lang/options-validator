# H5 "Sector Income Core" + Attractiveness Evaluator — design (2026-07-04)

**Status: DRAFT awaiting owner review. Supersedes H4's structure list at
registration (book carries over; zero H4 cycles completed, so no
results-based selection is possible — recorded in the ledger at switch).**

**Owner brief this answers:** "buy LEAPS, then sell puts and covered calls —
build me a design that helps me define which options look attractive; I'm a
beginner, spell everything out." Not mean reversion: a secular-growth core
(LEAPS) with a volatility-income overlay (short puts/calls), fitted to the
measured character of the four names — VST/CEG carry 45–59% IV (rich
premiums to SELL), MSFT ~25% IV with the deepest LEAPS market (cheap upside
to OWN), AMZN's covered calls beat buy-and-hold on exact closes (Study C).

## 1. Beginner glossary (used throughout; the evaluator repeats these inline)

- **LEAPS**: a call option with 1+ year of life. ~0.70 delta means it gains
  ~$0.70 per $1 the stock rises. Max loss = what you paid, ever.
- **Cash-secured put (CSP)**: you collect cash today for a binding promise
  to buy 100 shares at the strike if the stock is below it at expiration.
  The "secured" part: the buying money ($100×strike) is set aside.
- **Covered call (CC)**: you collect cash today for a promise to sell 100
  shares you ALREADY OWN at the strike. Cost = capped upside, not cash.
- **PMCC**: a covered call where a LEAPS stands in for the 100 shares.
- **Assignment**: the promise coming due (you buy at the put strike / sell
  at the call strike). In this design assignment is a PLANNED event.
- **Delta**: rough probability-flavored moneyness (0.20Δ put ≈ ~20%-ish
  chance of finishing in the money). **IV**: the option market's priced-in
  fear. **Extrinsic/theta**: the time-value you pay/collect per day.
- **Naked call**: selling a call with nothing behind it. Unlimited loss.
  **BANNED in this system, permanently.**

## 2. The three engines (frozen rules)

| Engine | Rule (all selections nearest-delta, monthly = standard 3rd-Friday cycle, conservative fills, no stops) |
|---|---|
| CORE | LEAPS calls 0.70Δ, DTE 270–500 nearest 365; names MSFT (held) + CEG when bucket room; roll at DTE ≤ 90; bucket $10k/name, $10k total, ≤2 positions (unchanged) |
| ENTRY | Exactly 1 CSP at a time: 0.20Δ nearest monthly, names {VST, AMZN}; collateral 100×strike on the equity side; assignment accepted → the 100-share lot moves into INCOME |
| INCOME | CC 0.20Δ nearest monthly against every declared 100-share lot in `data/positions/holdings.csv` (schema: symbol,shares,cost_basis,acquired). Strike must also satisfy: assignment price ≥ cost_basis (never locked into selling at a loss); if the 0.20Δ strike sits BELOW cost basis (stock under water), the cycle is SKIPPED and the card says exactly that — no chasing premium below basis. PMCC lane: short call vs a held LEAPS only if K_short ≥ K_LEAPS + net_debit/100 (assignment can then never lock a loss); evaluator prints the truth if that strike pays too little to bother |
| TACTICAL | 0–2 long 0.40Δ monthly calls under the $600 cap (unchanged) |

Earnings inside a cycle: flagged AMBER by the evaluator, never auto-banned
(Studies B/C/E measured hold-through; MSFT/AMZN crush actually pays
sellers). Weeklies remain barred until their own liquidity study.

## 3. The Attractiveness Evaluator (`options_researcher/attractiveness.py`)

One command; per name × role, 2–3 candidate contracts from the latest
cached chain; each criterion graded against FROZEN thresholds anchored to
our measured studies; overall verdict = hard gates first, then greens.
Output is prose-first (a sentence per line), badges second.

**SELL-PUT card criteria:** liquidity hard gate (OI ≥ 100, spread ≤ 10% —
frozen config gates); monthly yield = credit ÷ (100×strike): GREEN ≥ 1.0%
(Study E measured avg), AMBER 0.6–1.0%, RED < 0.6%; cushion = %OTM ÷
typical monthly move (rv21/√12): GREEN ≥ 0.8, AMBER 0.5–0.8, RED < 0.5;
IV rank ≥ 0.5 GREEN *for sellers* — always printed with the Study A
honesty line ("extra pay ≈ extra real risk, not free money"); earnings
flag; verdict sentence states what assignment means in dollars and shares.

**COVERED-CALL card criteria:** liquidity gate; monthly yield = credit ÷
(100×close): GREEN ≥ 0.8% (Study C: AMZN 0.20Δ collected ~0.8%/mo and beat
holding), AMBER 0.4–0.8%; upside room to strike ≥ +3% GREEN; hard gate:
strike ≥ cost_basis; prints "if assigned you sell 100 sh at $K = +X% vs
your cost". PMCC variant adds the safety-strike hard gate from §2.

**LEAPS card criteria (buy side):** cost vs bucket room; breakeven price
and % move needed by expiry; extrinsic ÷ days = theta cost in $/day;
IV rank INVERTED for buyers (RED ≥ 0.7 — paying up; GREEN ≤ 0.3); capture
history from Study D printed for context.

**Integrity rails:** thresholds are constants in config (H5_* block),
changed only by owner amendment; the evaluator READS ONLY (never trades,
never writes positions); every card ends with the reminder that
attractiveness ≠ prediction — it measures price-vs-cushion-vs-liquidity,
not the future.

## 4. Portfolio tracker additions

New structures `covered_call` (short C, income bucket) and `pmcc_call`
(short C, income bucket, linked LEAPS id) in `portfolio.py`; coverage hard
check: every short call must map to a holdings.csv lot (100 sh per
contract) or a live LEAPS satisfying the safety gate — an uncovered short
call fails analyze() loudly. CSP assignment workflow: on expiry with close
< strike, analyze() prints the instruction to move 100 shares into
holdings.csv at the strike price as cost basis.

## 5. Registration & verdict (unchanged machinery)

H5 registers via ledger trial-log with this doc's hash; H4 recorded
SUPERSEDED-AT-ZERO-CYCLES; the 3 live positions carry over; the forward
paper window clock RESTARTS at H5 registration (≥ 2 quarters → the frozen
loss-gated scoreboard). In-era evidence for the new engines already exists
(Studies C/E); the composite evidence backtest gains a CC leg re-run as
evidence only.

## 6. Testing

Evaluator scoring = pure functions with golden fixtures (a card computed
by hand in the test); coverage checks and holdings loader fail-loud tested;
no network in tests; suite stays green throughout.

## 7. Out of scope

Naked calls (banned), weeklies (pending study), auto-trading/alerts, any
threshold tuning against results, changes to the frozen cost model.
