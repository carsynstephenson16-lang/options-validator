# Live hypothesis map

Derived summary, not the source of truth — every registration, receipt, and
verdict number lives in `ledger/`, `reports/`, and `config.py`; this page
points at them. [[decisions]] has the scope freezes these run inside,
[[automation]] writes their daily receipts, [[data-layer]] is what they read.

**Terms, defined once:** a *call option* is a contract to buy 100 shares at a
fixed price later; its *premium* is the price paid for it. *Delta* (0–1) is
roughly how much the option's price moves per $1 the stock moves. *DTE* =
days to expiration. *IV rank* = is this option's implied volatility high or
low versus its own past year. A *loss-gated verdict* means the platform
refuses to call a strategy good or bad until enough **losing** trades have
happened to trust the read — a winning streak alone proves nothing.

## H5 — Sector Income Core
Sells income (covered calls, cash-secured puts) or buys long-dated calls on
the four core names (VST/CEG/MSFT/AMZN) when price + IV-rank triggers align.
Registered ledger trial 6, 2026-07-04 (`ledger/facts.log:10564`). Entry logic
`options_researcher/entry_watch.py`, frozen triggers (VST ≤$160, AMZN ≤$220,
IV-rank ≤0.5). Receipts: `reports/h5/entry_watch_<date>.txt`. Waiting on a
fired entry to open cycle 1; verdict needs `MIN_LOSSES_FOR_VERDICT=10`
(`config.py:185`) completed losing cycles.

## H6 — Post-earnings tactical long calls
Buys a call on NVDA/PLTR/AMZN shortly after earnings, betting the
post-earnings drift continues. Registered ledger trial 7, 2026-07-08. Cap
$2k/month **shared with H8**. Book `data/positions/h6_positions.csv` (one
open position, NVDA $220C exp 2026-09-18). Receipts:
`reports/h6_forward/<date>.json`. Status `INSUFFICIENT_SAMPLE` (zero
completed positions).

## H7 — Swing options, 15-name watchlist
Three lanes (long call / debit spread / short-premium) chosen by IV vs.
realized vol ([[decisions]] has the exact list). Registered ledger trial 8,
2026-07-09, `f1887c9d` + amendments v1.1–v1.7. Its 2018–2026 historical
version is **permanently withdrawn** (amendment v1.3) — earnings provenance
can't be reconstructed causally. Sole verdict path now: the **forward paper
window**, LIVE since 2026-07-20 (`ledger/h7_forward/events.jsonl` seq 0,
hash-chained) over an immutable 9-name entry cohort, ending 2026-10-26.
Daily chain: source health → data gate → exit fill/monitor → `h7_watch` →
entry preflight; receipts under `reports/h7_receipts/h7-forward-15-v1/` and
`reports/h7_data_gate/h7-forward-15-v1/`. Scores **once** at window end,
≥10 losses.

## H8 — Pre-earnings tactical long calls
Companion to H6: buys a call on PLTR or AMZN in the T-15..T-8 session window
before a **company-confirmed** report date, closes T-2. Registered trial
intent `1eed4ae6`, 2026-07-15. Shares H6's $2k/month cap. Book
`data/positions/h8_positions.csv` is header-only. Receipts:
`reports/h8_forward/<date>.json`. Status `INSUFFICIENT_SAMPLE`; verdict
needs `H8_MIN_COMPLETED_POSITIONS=8` (`config.py:366`) plus a hard kill on 3
consecutive full-cap loss months.

## H10a / H10b — QM signal continuation
Own $2,000/month cap (not shared with H6/H8); buys a long call on a
`H7_WATCHLIST` name that just fired a QM breakout (H10b) or parabolic-fade
(H10a) signal. Registered `ledger/experiments.jsonl` seq 15/16, 2026-07-19.
H10a window ends 2026-10-06; H10b ends 2027-01-06 (disclosed low fire
rate — 11 historical events). Relaxed loss gate,
`H10_MIN_LOSSES_FOR_VERDICT=7` (`config.py:598`, weaker-verdict disclosed).
Receipts: `reports/h10/receipts/h10_watch_<date>.json`; log
`reports/h10/observations.jsonl`.

## Spent one-run studies (never re-run)
- **H9** — historical (non-blind) post-earnings study, run once. Result
  `INSUFFICIENT_SAMPLE` (`ledger/facts.log:17892`; 4 losses < the required
  10, despite a positive-looking raw tally — the loss gate exists for
  exactly this case). Receipt `reports/h9/receipt.json`.
- **RQ1** — descriptive-only: do the scanner's GREEN/AMBER/RED grades
  correlate with what happens next (forward IV change, realized vol)? Not a
  profitability test. Registration seq 17 (`ledger/experiments.jsonl`).
  Result: `"NO VERDICT — descriptive rank-quality measurement only"`
  (`reports/rq1/rq1-v1.json`).
