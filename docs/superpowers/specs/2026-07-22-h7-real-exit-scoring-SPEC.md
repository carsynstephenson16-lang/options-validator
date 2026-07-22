# H7 real-store exit and scoring path — SPEC

**Status: BUILD-AUTHORIZED (ledger fact `H7_C1_EXIT_AND_SCORING_SPEC_RATIFIED`,
2026-07-22T15:59:44Z, spec_sha256=ca639c1e…, further amended same day by
`H7_EXIT_SCORING_SPEC_AMENDMENT_V1_1` for §4a.1, spec_sha256=84aeb2f2…).
REAL EXITS AND REAL-STORE SCORING REMAIN INACTIVE** pending the SPEC §9
fresh-context independent adversarial review and a separate owner-typed PASS
after the build. This document defines the next H7 implementation arc
required by `H7_C1_EXIT_AND_SCORING_DEADLINES`. Being build-authorized does
not itself authorize an exit, score the live window, change a frozen
parameter, or create an order path.

**Amended 2026-07-22 (same day, pre-registration):** an adversarial review of
this candidate against the live code and store (ten findings confirmed or
plausible; three suspected defects refuted after direct measurement) was folded
in before registration or build. Material additions: a pre-registered
expiration-settlement convention (§4a), explicit post-window exit authority
(§4 item 2), a distinct exit-evidence publisher (§5), corrected identity
checks (§4 item 4, §8 item 4), a separate real-scoring wrapper module (§7),
concrete ritual ordering (§7), two added result disclosures (§8), and an
evidence appendix (§11). This pre-registration pass does NOT count as the
fresh-context independent adversarial review the build arc requires in §9 —
that review still happens after the build, on the built code.

## 1. Goal and deadline

Promote the already reviewed synthetic exit and scoring mechanics through
narrow, receipt-bound doors to the registered real **paper** ledger. The
implementation must preserve the existing frozen logic and add only the
authority, evidence, CLI, and durable-result surfaces missing from the real
path.

The exit door must be implemented, independently adversarially reviewed, and
owner-approved before the first real `entry_intent` can fire. An entry can fill
one session later and can require an exit observation on that same fill
session, so an entry without the exit door would create an unmanaged paper
position. If any daily watcher first reports `ENTRY-OK` for an included name,
this arc becomes the only permitted options-validator implementation work until
the exit door is reviewed or the entry door is explicitly held closed.

Real-store scoring must be reviewed before the registered final decision
session, 2026-10-26, and before results are visible. The window scores exactly
once, only after every included decision and opened position is resolved.

The operable exit horizon extends past the decision window: a position entered
near 2026-10-26 at the top of `H7_LONG_DTE_BAND` (120 DTE) with its scheduled
close at `H7_CLOSE_AT_DTE` (30 DTE) is monitored until roughly 2027-01-25. The
window's final decision session bounds new entries only, never the management
of positions the window already opened (§4 item 2). Seq 0 records ThetaData
daily-EOD coverage confirmed only through 2026-11-30; the owner must extend
confirmed data coverage — and keep the daily ritual operating — through the
full exit horizon, or late-window exits will hit an unconfirmed feed.

## 2. Existing machinery that must remain unchanged

- `options_researcher.h7_paper_lifecycle.observe_exit` and
  `process_exit_fill` own the frozen trigger order, T+1 fill behavior, adverse
  quote transforms, costs, liquidity refusals, retry rules, and paper-ledger
  event shapes.
- `options_researcher.h7_forward_scoring.score_forward_window` owns trade
  reconstruction, per-lane and overall dependence-aware CI90 scoring, and the
  frozen `SURVIVED` / `REJECTED` / `INCONCLUSIVE` mapping.
- Sequence-zero `window_registration` is the source of truth for the included
  cohort, window bounds, config/cost identities, and scorer identity:
  `options_researcher.h7_forward_scoring`, `min_losses_for_verdict=10`, and
  `bootstrap_samples=5000`.
- `RealStoreSession` stays entry-only. Its explicit refusal of exit calls is a
  safety boundary, not a temporary inconvenience to bypass.
- No dated receipt, existing H7 event, registration payload, frozen threshold,
  or historical artifact is rewritten.

"Unchanged" means the frozen *computation* stays byte-identical: trigger
order, T+1 and retry rules, adverse quote transforms, costs, liquidity
refusals, trade reconstruction, the confidence interval, and the verdict
mapping. Adding an additive typed-resolution seam to the lifecycle (analogous
to the entry path's `_resolve_base`) and a decision/evaluation two-date helper
(§6) is permitted and required; those are seams, not changes to the frozen
math. The scoring module itself gains no seam and no CLI — its real-store
door lives in a separate wrapper module (§7).

The entry evidence helpers are NOT exit publishers:
`h7_session.record_session_evidence` hardcodes GO / CLEAR / healthy-only
evidence and refuses a non-fully-healthy cohort, and
`h7_watch.validate_data_gate_receipt` refuses NO_GO receipts. The exit arc
adds its own publisher and loader (§5); reusing the entry ones is prohibited.

## 3. Required delta 1 — a distinct real-exit authority type

Add a frozen `RealExitSession` capability, separate from `RealStoreSession`.
Only a reviewed `open_real_exit_session(...)` factory may create it. The type
must carry:

- the verified real-store path and sequence-zero registration id;
- the operational decision session and completed source-evaluation session;
- the immutable included cohort;
- the data-gate and linked source-health receipt paths and hashes;
- config and source-hash identities; and
- the exact per-symbol chain and close bindings for the monitored session.

`observe_exit` and `process_exit_fill` may accept this capability in addition
to their existing explicit synthetic path. Passing a plain path resolving to
`ledger/h7_forward`, a `RealStoreSession`, a forged dataclass, or any other
object must continue to fail closed. The implementation must not weaken
`_synthetic_base`; it must introduce a typed resolution path analogous to the
entry-only `_resolve_base` seam.

Exit authority is mechanical paper-book authority only. It cannot propose an
entry, approve an entry, place an order, or score the window.

## 4. Required delta 2 — re-verify receipts and cache bytes every session

`open_real_exit_session` must re-earn authority from the current session's
immutable evidence. It must mirror the protections in
`h7_session._watcher_receipt_for_session`, `_receipt_input`,
`_load_bound_chain`, and `_load_bound_close`, without depending on actionable
entry rows.

For every monitoring or fill session it must:

1. verify the forward hash chain and load the cohort/window from seq 0;
2. require the operational decision session to be inside the registered
   window, OR to be any XNYS session at or after an in-window opening fill
   and at or before that position's contract expiration — this explicitly
   authorizes post-window MONITORING passes and their T+1 fill/retry sessions
   for positions opened in-window. The registered window's final decision
   session bounds new entry intents; it never bounds exit observation, exit
   fills, retries, or the §4a settlement of positions the window opened.
   Definitions: "causally descended from an in-window entry" means the work
   shares the in-window opening `paper_fill`'s `position_id` and cites it
   (directly or transitively) through `causes`; a "valid fill/retry session"
   is the intent's `planned_fill_session` when no prior exit `data_gap`
   exists for it, else the first XNYS session after the latest such gap
   (matching the frozen retry rule in `process_exit_fill`);
3. load and integrity-check the full-official-scope data-gate receipt and its
   linked source-health receipt for the exact completed evaluation session;
4. require receipt scope, session, link hashes, config hash, source hash, and
   declared source-hash contract to agree — where "agree" for the source hash
   means receipt-vs-LIVE-tree agreement exactly as
   `h7_watch.validate_data_gate_receipt` already enforces, never
   receipt-vs-seq-0: this arc edits hashed directories, so the live source
   hash necessarily differs from the registration commit's; the seq-0
   `gates.source_hash` is provenance, not a runtime gate (see §8 item 4);
5. re-hash every named input before use;
6. load only the exact chain and adjusted close named by the receipt binding,
   then re-hash the binding again after load; and
7. refuse stale, missing, changed, future, fallback, or cross-session data.

The exit factory must be able to represent a valid `NO_GO` data-gate receipt.
`NO_GO` grants no permission to infer a price; it exists so the frozen
lifecycle can append an honest `data_gap` and retry on the first valid later
session. A market-wide data problem must not silently stop exit monitoring.

The data-gate receipt already binds per-symbol chain and close files. The exit
path should reuse those bindings directly or extract shared receipt helpers;
it must not require an `ENTRY-OK` watcher row and must not duplicate a second
mutable cache manifest.

## 4a. Pre-registered expiration settlement (declared now, before results)

Without this rule the window can become permanently unscorable: the frozen
lifecycle fails loud when a position reaches contract expiration without a
resolved exit (`h7_paper_lifecycle.py` raises in both `observe_exit` and
`process_exit_fill`), exit fills append `data_gap` whenever quotes are missing
or fail the liquidity gate (`MIN_OPEN_INTEREST`/`MAX_SPREAD_PCT` — a gate
near-expiry deep-ITM legs routinely fail), and scoring refuses while any
opened position is unclosed. Lane c has only ~7 sessions of retry runway. A
persistent data or liquidity outage in an exit tail would leave a position
open forever and make the registered verdict unreachable — not biased,
unreachable. The settlement convention is therefore frozen here, before any
window result exists, so it can never be chosen with visible P&L:

- If a monitored position reaches its contract expiration with no valid
  closing fill, the real-exit path records a terminal close valued at
  intrinsic settlement of the exact frozen legs against the receipt-bound
  adjusted underlying close for the expiration session: long legs pay
  max(0, S − K) for calls and max(0, K − S) for puts; short legs are charged
  symmetrically; exit commissions apply only to legs settled in the money
  (Assumption: no commission on a leg expiring worthless).
- Basis (Official-source, see §11): OCC settles expiring equity options by
  exercise-by-exception against the underlying's closing price — an option
  in the money by the threshold ($0.01, OCC Rule 805(d), with the sourcing
  caveat disclosed in §11) is exercised automatically. Intrinsic-at-close is
  the honest paper analogue of what OCC actually does.
- If the receipt-bound underlying close for the expiration session is itself
  unavailable, the terminal record is a declared settlement event valuing
  structures OTM beyond doubt at zero and ITM or undeterminable defined-risk
  structures at full-width loss — the conservative bound for a defined-risk
  position.
- This is a terminal accounting rule with zero discretion, not an exit
  trigger and not new exit logic in the §10 sense; it exists only so scoring
  is always reachable. It is reviewed and owner-ratified with the rest of
  this spec BEFORE any real entry fires.
- Disclosure: near the strike, whether a real short leg is assigned is a
  clearing-member decision, not a mechanical rule (pin risk — mechanics in
  §11), so any settlement-closed position carries the §8 assignment
  disclosure in the scoring artifact.

### 4a.1 Settlement-close scoring seam (amendment v1.1, 2026-07-22, owner-approved)

Positions terminally closed under §4a cannot honestly satisfy
`h7_forward_scoring._fill_price` (`:142-169`), which requires each closing
leg to carry raw market quotes passing `quote_valid` and `passes_liquidity`
plus a canonical adverse fill price — validation built for market fills,
meaningless for a quoteless settlement. Resolution, with
`h7_forward_scoring.py` remaining byte-identical (§2, §7):

- Settlement-terminal positions are excluded from `score_forward_window`'s
  leg-quote reconstruction and are instead valued by a new, independently
  reviewed, typed settlement valuator implementing exactly the §4a rules
  above (intrinsic against the receipt-bound adjusted close; the
  conservative zero/full-width-loss fallback; commissions only on ITM
  legs). Zero discretion; fabricating synthetic quotes is prohibited
  everywhere.
- `h7_real_scoring` produces the single §8 artifact by recomputing the
  seq-0-frozen verdict statistics — identical loss gate
  (`min_losses_for_verdict`), bootstrap parameters, and CI thresholds,
  hash-verified against the registration — over the union of
  frozen-scorer-valued market closes and settlement-valued closes.
- The artifact additionally records the frozen-scorer sub-result on market
  closes alone, the settled-position count, and the settled positions'
  aggregate P&L contribution, so the two valuation paths stay separately
  auditable forever.
- This seam is inside the §9 independent-review scope.

## 5. Required delta 3 — monitoring-session evidence events

Every real exit observation and exit-fill attempt must publish the session's
verified `data_gate` evidence event before the lifecycle transition. The event
uses the existing deterministic id `h7:data_gate:<evaluation-session>` and is
idempotent only when its receipt identity is identical.

An exit whose frozen reason depends on earnings (`pre_earnings` or
`earnings_unknown`) must additionally publish and cite the per-symbol
`source_health` evidence event for that session. Its gate, health state,
receipt hash, receipt path, and symbol must agree with the values passed to
`observe_exit`. A non-earnings exit must not fabricate an unnecessary
source-health cause.

No monitoring session disappears:

- GO + priceable + no trigger returns no exit intent but leaves its verified
  data-gate evidence in the ledger.
- NO_GO or unpriceable inputs append the existing `data_gap` event.
- A fired trigger appends one deterministic `exit_intent` citing the opening
  fill, the session data gate, and source health when earnings-dependent.
- A fill attempt appends either the closing `paper_fill` or a visible
  `data_gap`; retries remain first-later-session only.

The entry evidence publisher cannot serve exits and must not be reused:
`h7_session.record_session_evidence` hardcodes `whole_universe_verdict: "GO"`
and per-symbol `healthy: true` / `gate: "CLEAR"`, and refuses unless the
entire cohort is healthy, while `h7_watch.validate_data_gate_receipt` refuses
NO_GO receipts in both of its modes. The frozen `earnings_unknown` exit
requires a source-health evidence event carrying `healthy: false` — which the
entry publisher can never emit. The arc must therefore add a distinct
exit-evidence publisher and exit-scoped receipt loader that:

- accept and faithfully record a NO_GO whole-universe data-gate receipt
  (verdict and go/no-go counts) under the existing deterministic id, while
  still checking scope, session, config hash, live source hash, source-hash
  contract, linked source-health hash, and re-hashing every named input;
- emit per-symbol `source_health` events carrying the receipt's ACTUAL
  `gate` (CLEAR / BANNED / UNKNOWN) and `healthy` (true / false), so the
  recorded values match what `observe_exit` verifies; and
- permit exit management of a position whose name has become unhealthy or
  entry-banned — health bans close the entry door, never the exit door.

## 6. Required delta 4 — decision session versus evaluation session

Real exit calls must preserve both dates explicitly:

- `evaluation_session` is the completed source-data/receipt date and remains
  the stored event's `evaluation_session`.
- `decision_session` is the operational session governed by the registered
  window and is recorded in the exit-intent payload.
- `planned_fill_session` is derived from `decision_session`, never from wall
  clock and never silently from the source date.

For synthetic callers the two dates remain identical, preserving current
tests and public behavior. For a `RealExitSession`, lifecycle code must derive
the operational date through one typed mapping helper, as the entry path does.
It must reject an inconsistent receipt date, an exit before the opening fill,
a decision outside the allowed window/fill lineage, and any attempt to use
today's unfinished EOD as completed evidence.

Transition ordering must be test-pinned: after an opening fill is recorded,
that new position is included in the same session's exit observation pass.
This is what closes the earliest-exit gap identified in
`H7_C1_EXIT_AND_SCORING_DEADLINES`.

"Same session" is defined precisely: the observation pass is keyed to the
source/evaluation session — the completed-data date whose receipts and cache
bytes were verified and on which the opening fill was recorded. The exit
intent's `planned_fill_session` and its window/lineage checks derive from the
mapped operational decision session via the same typed helper the entry path
uses; the stored event's `evaluation_session` remains the source date.
Acceptance test: a real opening fill recorded on source session E must be
observed by an exit pass parameterized with source session E in the same run,
and a triggered intent's planned fill must equal the next XNYS session after
the mapped operational decision date.

## 7. Required delta 5 — owner-visible exit and scoring CLIs

Add an exit CLI with explicit subcommands, no network calls, and no order
surface:

```text
python -m options_researcher.h7_exit_session status ...
python -m options_researcher.h7_exit_session monitor ...
python -m options_researcher.h7_exit_session fill ...
```

`status` validates authority and writes nothing. `monitor` scans every open
real-paper position, records the session evidence, and calls the frozen exit
observer. `fill` processes every due/retry exit intent for the supplied
session. Both mutation commands require explicit receipt paths and print each
event id plus whether it appended or replayed. Exit code 2 means authority or
evidence refusal; partial success must be reported per position and must never
look like a clean run.

Add a scoring CLI with a read-only preview and a separately gated finalizer,
in a SEPARATE wrapper module — not in `h7_forward_scoring.py`:

```text
python -m options_researcher.h7_real_scoring preview
python -m options_researcher.h7_real_scoring finalize --owner carsyn
```

The wrapper calls `h7_forward_scoring.score_forward_window` through a narrow
injected-base seam. Do not add a CLI, a real-store branch, or a resolution
seam to `h7_forward_scoring.py` itself: the seq-0 frozen scorer identity
names that module, and its computation must stay byte-identical (§2).
`preview` may read the verified real store but writes nothing and must still
say `NOT FINAL`. `finalize` is unavailable until the scoring output convention
and all §8 gates pass. Neither command accepts caller-supplied window bounds;
both derive the immutable bounds and scorer identity from seq 0.

The reviewed exit monitor must be wired into the daily ritual before entry
authority is allowed to append an intent, with this concrete shape: a
dedicated step (proposed Step 2c) that executes unconditionally, OUTSIDE the
ritual's `GATE_GO` block, immediately after the data-gate verdict is known and
before any entry preflight or entry-authority step. It must run on NO_GO
sessions — appending honest `data_gap` events and advancing the frozen retry
clock — as well as GO sessions; placing it inside `GATE_GO` would let a
market-wide data problem silently stop exit monitoring, exactly what §4
prohibits. Ordering within the step: due exit fills and retries first, then
same-session monitoring of every open position. If the exit monitor refuses
(exit code 2), the ritual marks CRITICAL and must not run the entry path that
session; no entry intent may be appended in a session with an unresolved due
exit fill. This wiring remains fail-closed and is part of the future
build/review, not this spec commit.

## 8. Required delta 6 — one durable scoring result

Introduce one new forward-ledger event type, `window_score`, and one immutable
receipt artifact:

```text
reports/h7_forward_scoring/<scope-id>/<final-decision-session>.json
```

The artifact is built with the repository's content-addressed receipt
primitive and has receipt type `window_score`. It contains the complete
JSON-safe result returned by the frozen scorer plus:

- scope id/hash and registration event id/hash;
- window start/end derived from seq 0;
- `input_ledger_head` captured before scoring;
- scorer module, config hash, cost-model hash, minimum-loss gate, bootstrap
  sample count, and forward contract count, all checked against seq 0;
- included/excluded cohort identity;
- finalization time and explicit owner acknowledgement; and
- the frozen disclaimer that `SURVIVED` is not validation, profitability,
  live-trading approval, or permission to change strategy rules;
- the assignment disclosure (labeled Assumption / known limitation): this
  paper model prices all closes at adverse quotes and does not model early
  assignment or dividend-driven early exercise; short legs on the cohort's
  dividend and distribution payers (MSFT, CEG, VST, and the MLP ET) may in
  reality be assigned early around ex-dates, altering realized economics —
  results are option-quote-marked paper results only (basis in §11); and
- the small-sample interval disclosure (labeled Official-source, DiCiccio &
  Efron 1996, §11): the frozen 90% expectancy interval is a percentile-type
  bootstrap; percentile intervals are first-order accurate and can
  under-cover at small samples, and the verdict floor of 10 losses is a small
  sample. A SURVIVED lower-bound-above-zero result must be read with that
  known under-coverage in mind; the method stays exactly as registered.

(The scorer's returned `frozen` block does not include the cost-model hash;
the artifact builder computes `cost_model_hash()` directly.)

The deterministic event id is
`h7:window_score:<scope-id>:<final-decision-session>`. Its causes include the
window registration and every included opening/closing fill used by the
score. Its payload carries the artifact path/hash, `input_ledger_head`, trade
count, overall verdict, and per-lane verdicts.

Finalization order is artifact first, ledger event second. An artifact without
the deterministic event is an orphan and is not authoritative; a retry may
append the event only after proving the artifact bytes and input head still
match. An existing event requires the exact existing artifact and makes every
later finalization an idempotent no-op. A different score, head, artifact, or
owner acknowledgement under the same id is a conflict, never an overwrite.

Finalization must refuse until:

1. the registered final decision session has completed;
2. every intent decided inside the window is terminal;
3. every included opening fill has exactly one valid closing fill (a §4a
   settlement close counts as the closing fill);
4. the ledger, registration identities, config hash, cost-model hash, and
   scorer identity (module name, minimum-loss gate, bootstrap sample count —
   each recomputed and equal to seq 0's frozen values), and all reconstructed
   economics verify. Code/source identity is intentionally NOT checked
   against seq 0: `diagnostic_source_hash` covers `options_researcher/` and
   `tools/`, which this arc necessarily edits, so the live source hash
   already differs from the registration commit's (measured 2026-07-22: live
   `8945d6e2…` vs seq-0 `1dcb79c8…`, while `config_hash` `ae5de583…` and
   `cost_model_hash` `af71c7f6…` still re-derive exactly). Receipts are
   validated against the live source hash only, as the entry path already
   does; the seq-0 `source_hash` is provenance, not a runtime gate;
5. no prior `window_score` exists; and
6. a fresh independent adversarial review and owner PASS for this real-store
   arc are recorded.

The scoring capability is a distinct typed door (for example,
`RealScoringSession`) accepted by the scorer only after these checks. Passing
the real path directly remains prohibited.

## 9. Required tests and adversarial review

The build arc must begin with tests and include, at minimum:

- forged/plain real paths and cross-capability objects refused;
- corrupt ledger, absent registration, wrong cohort, wrong date, stale hash
  contract, unlinked receipts, changed cache bytes, and future EOD refused;
- GO, NO_GO, missing quote, earnings-unknown, pre-earnings, scheduled-DTE,
  stop, profit-target, and credit-stop exit paths on the real capability;
- expiration settlement (§4a): a position reaching expiration with no valid
  closing fill settles at intrinsic against the receipt-bound close; the
  no-priceable-close fallback records the declared conservative terminal
  event; scoring becomes reachable in both cases;
- post-window authority: monitoring, fill, retry, and settlement sessions
  after the final decision session are accepted for positions opened
  in-window, and refused for any new entry intent;
- NO_GO evidence: a NO_GO data-gate receipt is publishable as exit evidence,
  produces the frozen `data_gap`, and advances the retry clock; an
  `earnings_unknown` exit publishes source-health evidence with
  `healthy: false`; an unhealthy or entry-banned name's open position can
  still be exit-managed;
- same-session observation of a newly opened fill, keyed per §6 (source
  session E observes E's fill; planned fill derives from the mapped
  operational decision date);
- decision/evaluation offset mapping and T+1 derivation pinned;
- every monitoring and fill attempt leaves the required evidence or gap;
- duplicate/retry/concurrent calls are idempotent or conflict safely;
- scoring before window completion, with unresolved intent/open position,
  wrong scorer identity, changed config/cost, duplicate close, or existing
  different result refused;
- orphan-score-artifact recovery and score-event idempotency proven;
- no CLI can place an order, fetch data, rewrite a receipt, or mutate any
  store outside the explicit real forward ledger and scoring artifact path;
  and
- all current synthetic lifecycle/scoring tests remain green unchanged.

Acceptance requires focused tests, the complete offline suite, Ruff, Pyright,
forward-ledger verification, immutable-artifact snapshots, ritual syntax
check, a fresh-context independent adversarial review, remediation of every
blocker, and an owner-typed PASS.

## 10. Non-goals and frozen boundary

This arc does not add broker connectivity, order routing, live trading,
automatic owner approval, new entry logic, a new discretionary exit trigger
or timing rule, a threshold change, an extra look at results, an interim
verdict, or a second score. The §4a expiration settlement is a pre-registered
terminal accounting rule frozen before results exist — expressly permitted
and required; it is not discretionary exit logic. This arc does not migrate
or rewrite old receipts. It does not convert a paper result into a strategy
claim.

Build authorization, implementation, review, owner PASS, and ritual activation
are separate future steps. Until all of them complete, real exits and
real-store scoring remain locked even though their synthetic mechanics exist.

## 11. Evidence appendix (claim-discipline labels)

Gathered 2026-07-22 for this spec. Each claim carries its label per the
repo's claim discipline; NOT-FOUND entries are disclosed gaps, not omissions.

- **Exercise-by-exception at expiration** — OCC automatically exercises an
  expiring equity option in the money by $0.01 or more unless instructed
  otherwise (OCC Rule 805(d)). Official-source for the mechanism and rule
  number: SEC Release 34-54306 / SR-OCC-2006-05 (read directly; documents
  the threshold's path $0.75 → $0.25/$0.15 → $0.05) and OCC's
  investor-education arm (optionseducation.org, "Options Exercise").
  Disclosed gap: the final SEC filing moving $0.05 → $0.01 was not located
  this session; the $0.01 figure rests on OCC-affiliated secondary
  confirmation.
- **Early assignment timing** — an American-style equity option writer "may
  be assigned an exercise at any time during the period the option is
  exercisable." Official-source, read directly: OCC, "Characteristics and
  Risks of Standardized Options" (June 2024), Ch. X.
- **Assignment allocation** — OCC allocates exercise notices to clearing
  members; member firms must allocate to customers by an exchange-approved
  method (random or FIFO). Official-source, read directly: same OCC
  document, Ch. VIII.
- **Dividend-driven early exercise** — a deep-ITM call is commonly exercised
  just before ex-dividend when the dividend exceeds remaining extrinsic
  value. Official-source: Cboe Insights, "How Early Exercise Order Flow
  Impacts Equity Option Put-Call Ratios."
- **No early exercise of American calls absent dividends** — Merton (1973),
  "Theory of Rational Option Pricing," Bell Journal of Economics 4:141-183;
  restated in Hull, "Options, Futures, and Other Derivatives." Academic
  (citation-confirmed; the original proof was not re-read this session).
- **Broker exercise cutoff** — member firms must accept customer exercise
  instructions until 5:30 p.m. ET on expiration day (firms may set earlier
  cutoffs, never later). Official-source, read directly: FINRA Information
  Notice 2/3/21, "Exercise Cut-Off Time for Expiring Options."
- **Expiration time** — OCC By-Laws define Expiration Time as 11:59 p.m. ET
  on the expiration date; trading stops earlier and hours are exchange-set.
  Official-source via summary (SR-OCC-2013-04 / Federal Register
  2013-14793); primary text not fetched this session.
- **"Pin risk"** — no OCC/Cboe/FINRA document was found that uses the term;
  the underlying mechanics (assignment possible at any time, delayed
  assignment notice, exercise-by-exception discretion near the strike) are
  Official-source per the OCC document above. Disclosed terminology gap.
- **Conservative exit marks** — measured effective spreads in US equity
  options are SMALLER than quoted-spread measures (execution-timing traders
  pay under 40% of conventional measures; the average effective spread is
  roughly one-quarter smaller). Academic: Muravyev & Pearson (2020),
  "Options Trading Costs Are Lower than You Think," Review of Financial
  Studies 33(11):4973-5014. Inference: marking paper exits at the adverse
  quote side plus the 1% haircut plus commissions is conservative relative
  to measured execution — it can only understate paper performance, so it
  hardens a SURVIVED and cannot manufacture one. Illiquidity is priced
  (less-liquid options carry measurably higher costs): Christoffersen,
  Goyenko, Jacobs & Karoui (2018), RFS 31(3):811-851. Disclosed gap: no
  peer-reviewed source was found on opening-vs-closing spread-crossing
  asymmetry specifically.
- **EOD exit marks vs the open** — CBOE option spreads decline sharply after
  the open and then stay roughly flat (an "L-shape," unlike stocks'
  U-shape), so end-of-day quote marks avoid the option market's most
  expensive window. Academic: Chan, Chung & Johnson (1995), JFQA
  30(3):329-346 (abstract-level confirmation).
- **Small-sample bootstrap under-coverage** — percentile-type intervals are
  first-order accurate (coverage error O(1/√n)); BCa is second-order
  (O(1/n)); at n=20 a nominal 90% standard interval showed actual tail
  coverage of 0.12/0.99 in the authors' own demonstration. Academic, read
  directly: DiCiccio & Efron (1996), "Bootstrap Confidence Intervals,"
  Statistical Science 11(3):189-228.
