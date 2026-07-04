# M4 — Structure menu (2026-07-04) — OWNER DECISION REQUIRED

Inputs: committed profiler tables (nearest-37-DTE + monthlies), Studies A/B/C
(reports/2026-07-04-*), frozen cost model (config), $14k sleeve / $600 cap,
owner share holdings (VST, AMZN at 100+). Everything below is descriptive
synthesis; nothing here registers anything.

## The three measured facts that shape the menu

1. **No raw premium edge in the high-IV state** (Study A): on days when IV
   rank ≥ 0.70, subsequent realized vol MET OR EXCEEDED implied on all four
   names (MSFT .330r/.314i, AMZN .435/.406, VST .505/.489, CEG .587/.507).
   Selling options *because IV looks high* had no raw edge before frictions
   on these names, 2018–2026.
2. **Earnings dynamics exist only on the Mag-7 pair** (Study B): MSFT/AMZN
   show real run-up (+0.04/+0.05) and crush (−0.08/−0.15) around ~3–3.5%
   moves; VST/CEG show none (sector vol dominates their surface).
3. **Covered-call arithmetic is friction-proof but upside-expensive**
   (Study C, monthly cycles, conservative fills): friction is ~1.5–2% of
   premium (one leg, sold at bid, −1% haircut, $0.65) versus the 30–100%
   friction shares that killed the spread family. The cost that matters is
   the CAP, not the frictions:
   | Name (era) | Δ | Cycles | Assigned | Premium | CC total | B&H total | CC − B&H |
   |---|---|---|---|---|---|---|---|
   | AMZN (2022-07→) | 0.20 | 47 | 9 (19%) | $7,594 | $13,551 | $13,542 | **+$8** |
   | AMZN | 0.30 | 47 | 18 | $13,170 | $12,840 | $13,542 | −$702 |
   | AMZN | 0.40 | 47 | 22 | $19,757 | $12,654 | $13,542 | −$888 |
   | VST (2023-01→) | 0.20 | 42 | 13 (31%) | $5,823 | $10,818 | $14,148 | −$3,330 |
   | VST | 0.30 | 42 | 16 | $10,462 | $9,949 | $14,148 | −$4,198 |
   | VST | 0.40 | 42 | 22 | $15,610 | $9,262 | $14,148 | −$4,885 |
   Read: on AMZN, 20Δ income exactly paid for the caps across 4 years
   including a strong up-move — a statistical tie with holding. On VST, a
   rocket market made every cap expensive (income covered only ~2/3 of the
   surrendered upside). Lower delta dominates on both names.

## The menu

| Structure × name | Verdict | Why (numbers) |
|---|---|---|
| **Monthly covered call, AMZN, 0.20Δ** | **RECOMMEND as H4** | Deepest liquidity in the universe (monthly ATM OI ~6.5k, 2.1% spreads); CC−B&H = +$8 over 47 cycles = income historically covered its cost even in an up-market; owner holds shares; friction ~2% of premium; earnings rule testable (Study B crush −0.145 is the largest measured) |
| Monthly covered call, VST, 0.20Δ | Robustness sleeve only | Real income ($139/cycle) but bull-market cap cost measured at −$3.3k/42 cycles; tradable era only 2023+; keep as non-verdict companion to H4 |
| Covered calls at 0.30–0.40Δ (either name) | REJECT | Monotonically worse than 0.20Δ on both names (more assignment than premium) |
| Put credit spreads (any name) | REJECT | Killed three ways: H1/H2 registered FAILs, single-name diagnostics (universal FAIL), and Study A (no high-IV premium edge to harvest) |
| IV-rank-conditioned premium selling (any structure) | REJECT | Study A: realized ≥ implied in the high-rank state on all four names |
| Long vol / straddles on high IV rank | REJECT | Study A's parity of implied and realized leaves nothing after two-leg frictions at EOD conservative fills |
| Earnings-week premium selling, MSFT/AMZN | RESEARCH-ONLY (not registrable yet) | Crush is real (−0.08/−0.15) but n=34 events/name, single-event gap risk at EOD cadence, and the implied-vs-realized EARNINGS move spread isn't yet measured; candidate for a later study |
| PMCC / LEAPS-based (MSFT, CEG) | DEFER | No shares held; long-leg valuation is close-LEVEL dependent → requires the paid clean close feed; revisit after H4 |

## The close-data decision (bundled, because H4's verdict depends on it)

Covered-call assignment turns on close-vs-strike. Our interim closes are
parity-derived: daily returns are near-exact, but levels carry a +0.27–0.37%
disclosed bias. Two ways to register H4 honestly:

- **Option B (recommended, $0):** register with parity closes + a frozen
  borderline rule: any cycle with |close − strike| ≤ 1% is scored BOTH ways;
  if the headline verdict flips inside the band, the result is recorded
  INSUFFICIENT PRECISION (no rescue, no re-run) and the paid feed becomes
  mandatory for the successor hypothesis. Study C observed assignment
  margins are typically far outside 1%, so flips are unlikely — but the rule
  is frozen before we look.
- **Option A (~paid):** approve the ThetaData STANDARD stock tier before M5
  registration; exact closes end-to-end; delete the band machinery.

## What H4 would look like (preview — full prereg written only after your pick)

Sell 1× 0.20Δ monthly call per 100 AMZN shares at each monthly expiration
roll (conservative fill: bid −1% haircut, $0.65/contract), hold to expiry,
no repair trades, no rolling down; earnings rule = one frozen variant chosen
now (skip cycles containing an earnings date, or hold-through — Study B
argues hold-through since crush pays sellers, but skip is the conservative
default); benchmark = buy-and-hold on the same shares; in-era backtest
2022-07→2026-06 is EVIDENCE, and the registered PASS bar lives in a
**forward paper window ≥ 2 earnings cycles** (the only untouched data these
names have left). VST 0.20Δ runs as the non-verdict sleeve.

## Decisions needed from the owner (everything else proceeds without you)

1. **Pick the H4 structure** — recommended: AMZN monthly 0.20Δ covered call.
2. **Earnings rule** — recommended: hold-through (crush measurably pays the
   seller on AMZN; skip-earnings is the cautious alternative).
3. **Close data** — recommended: Option B ($0, frozen borderline rule);
   Option A if you prefer paying for exactness now.
4. Green-light M5 plan-writing + registration on those picks.
