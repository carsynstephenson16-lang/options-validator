# Ideas parking lot

Not-now, not-rejected. Per the scope guard: an idea lands here when it does not
move the current phase to a verdict. Pull one out only with an explicit owner
decision (and, where noted, a pre-registration first).

## Attractiveness-scanner enrichment (parked 2026-07-06)

Context: the seller lanes now carry a `vrp_for_seller` VRP-*proxy* badge
(front-month IV vs trailing 21d realized -- descriptive, horizon-mismatched,
never a forecast; see `H5_VRP_SELL_GREEN` in config.py). The two ideas below
were proposed alongside it in an external deep-research report. They are
valuable but bigger and easier to overfit, so they wait.

### Term-structure signal (front vs back-month IV)
- **What:** an IV30/IV90 (contango/backwardation) badge or ranking input.
- **Why parked:** needs a second ATM-IV tenor added to the feature layer
  first; and once it *ranks* candidates it becomes fittable logic.
- **Gate before building:** owner decision + **pre-register** the exact tenors,
  threshold, and grading rule in the ledger before it influences any ranking.
  Descriptive-only display could ship earlier, but must not order candidates
  until pre-registered.

### Event-edge signal (implied move vs realized event move)
- **What:** compare the option-implied move into an earnings/event to the
  *historical realized* move over the last N like events.
- **Why parked:** needs an event-move history dataset and a validation design;
  highest overfit risk of the three (small event samples, look-ahead traps).
- **Gate before building:** owner decision + **pre-register** the event window,
  the "N like events" definition, the implied-move source, and the accept/reject
  thresholds *before* it grades or ranks anything. This is a hypothesis, not a
  display tweak.

### Explicitly rejected (not parked) from the same report
- Composite weighted `TAOV` scalar -- unfitted weights; destroys per-dimension
  honesty. Do not build.
- Ranked trade-suggestor with named structures (iron fly, short straddle) --
  that is a suggestor, out of scope per `.cursorrules`.
- Ticker-specific narrative scores (regulatory/weather/segment) -- discretionary
  contamination; belongs in the equity-research repo, not a systematic screen.
