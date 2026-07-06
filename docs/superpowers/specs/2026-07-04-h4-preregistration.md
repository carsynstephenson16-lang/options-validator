# H4 pre-registration — composite thesis portfolio (2026-07-04, FROZEN on commit)

Owner picks (2026-07-04): 1–2 LEAPS + 1 cash-secured put + monthly long-call
tactical sleeve; new thesis risk bucket approved; covered calls parked LATER;
vertical credit spreads REJECTED by measurement (Study E: ~$0 in 8/8 configs).

## H4 (falsifiable, portfolio-level)

> A rules-frozen composite on the 4-name universe — (a) 1–2 LEAPS calls
> (~0.70Δ, DTE 270–500 nearest 365) from {MSFT, VST, CEG}, annual roll at
> DTE ≤ 90; (b) exactly one cash-secured ~0.20Δ MONTHLY short put on VST or
> AMZN, rolled monthly at expiration, assignment accepted as share
> acquisition; (c) 0–2 tactical ~0.40Δ MONTHLY long calls held to expiry,
> ≤ 1 per name — executed at conservative fills, produces **positive total
> P&L versus doing nothing, and the LEAPS legs capture ≥ 50% of their
> underlyings' moves per unit of premium capital**, over a FORWARD paper
> window of ≥ 2 calendar quarters starting when the owner seeds positions.

- **Verdict path:** forward paper trades accumulate in the portfolio
  tracker; at window end they feed metrics.scoreboard (existing frozen CI
  machinery; losses-gated). The in-era studies (C/D/E reports, committed)
  are EVIDENCE ONLY — hindsight-contaminated by name selection, never the
  verdict. No in-era composite backtest is registered as a result.
- **Kill criteria:** any rule change mid-window = new hypothesis; skipping
  a scheduled roll or adding an unlisted structure = protocol breach,
  recorded; NO EDGE / INSUFFICIENT SAMPLE at window end stand as reported.
- **Risk buckets (config-frozen):** THESIS (LEAPS): ≤ $4,000 premium per
  name, ≤ $10,000 total, ≤ 2 positions. TACTICAL: existing $600
  economic-max-loss cap per trade, ≤ 2 open. CSP: exactly 1 position,
  names {VST, AMZN}; collateral = 100×strike committed on the EQUITY side
  (outside the $14k options sleeve) — assignment is a planned share
  purchase, not a loss event; the tracked options-side risk is premium
  mark-to-market only.
- **Cadence:** LEAPS annual; CSP + tactical MONTHLY expirations only
  (measured cadence; weeklies require a dedicated liquidity/economics
  study before admission — pre-declared future study, not a variant).
- **No-discretion clause:** selection = nearest target delta within ±0.15
  on the nearest in-band expiration, conservative fills, no stops, no
  mid-cycle adjustments. Owner CHOOSES which names to seed (that's
  allocation, pre-declared here as free) but never overrides structure
  rules, deltas, or cadence.
- **Analytics duty:** `options_researcher/portfolio.py` marks the book
  daily-on-demand against cached chains/closes: conservative liquidation
  value, per-leg P&L, bucket utilization vs caps, roll/earnings/assignment
  flags. This tracker is the forward window's data source.
