# 09 — Session 5 scoping: cache schema v2 + full refetch (owner budget gate)

**Read-only scoping. No refetch performed. No provider call made. Nothing purchased.**

Date: 2026-07-30
Branch/SHA scoped: `sfix` @ `40a6b21`
Companion to: [`08_repo_verification.md`](08_repo_verification.md) (claim C4)

This is the one item in the fix arc gated on **money and owner authorization**
rather than engineering, so it is scoped separately and early. Session 5 is
NOT started and must not be started without an explicit per-pull approval.

---

## 1. What Session 5 is

Claim **C4** is confirmed: the local chain cache stores eleven columns
(`data/thetadata_adapter.py:49-53`) and discards every piece of provider
provenance — option quote timestamp, underlying timestamp, underlying price,
report-created time, Greek/model version, rate type, rate value, dividend
input, contract multiplier. The sharpest evidence is that a `timestamp`
column is *read* to deduplicate (`data/thetadata_adapter.py:263-265`) and
then dropped by the projection at `:291`.

Session 5 would define a **schema v2** carrying that provenance, refetch the
cache under it, and demote every v1-cached file to display-only.

---

## 2. Scale of the refetch — measured, not estimated

Inventory of `.cache/chains/` (file names and byte sizes only; **no parquet
values were read**, so this involved no holdout look):

| Measure | Value |
|---|---|
| Cached symbol-day parquet files | **31,367** |
| Total size on disk | **~2.95 GB** (3,094,132 KB) |
| Date span | **2018-01-02 → 2026-07-27** |
| Distinct real symbols | 22 |

Largest holdings: VST, NVDA, NOW, MSFT, AVGO, AMZN, AMD at 2,152 files each;
SPY/AAPL 2,134; QQQ 2,133; then ET 1,949, SMCI 1,889, PLTR 1,457, CEG 1,118,
IREN 1,063, TEM 519, NBIS 434, CLSK/AMAT 391, CRWV 330, USAR 327, HYLN 29.

**Call volume (Inference, from `data/thetadata_adapter.py:177-228`):** the
adapter makes exactly **two bulk calls per symbol-day** — one
`option_history_greeks_eod`, one `option_history_open_interest`. A full
refetch is therefore **≈ 62,734 provider calls**.

**Operational hazard (Repo-verified):** `data/thetadata_adapter.py:165-169`
records a live transport failure — gRPC `UNAVAILABLE "Stream removed (Socket
closed)"` — after roughly **3,890 sequential calls on one channel**. A 62,734-call
run is ~16× that observed failure point. The recovery path (`_reset_client`)
exists, but a refetch of this size is a multi-hour, restartable operation, not
a single command. Any brief must treat resumability as a requirement, not a
nicety.

---

## 3. Subscription status — the feed is live; the *pulls* are not authorized

From the ledger (append-only, quoted by date):

| Date | Fact | Bearing |
|---|---|---|
| 2026-07-16 | `THETADATA_RENEWAL_DECISION` — owner approved renewing | — |
| 2026-07-16 | `THETADATA_RENEWAL_SCOPE` — **"renewal preserves the data feed only; it does NOT authorize paid pulls or live trading. Per-pull owner approval"** | **This is the binding gate** |
| 2026-07-18 | `THETADATA_RENEWAL_EXECUTED` — owner confirmed payment completed; **"the feed does NOT lapse on 2026-07-29"** | Feed is live |
| 2026-07-23 | `THETADATA_EXTENSION_DECISION` — renew/extend by ~2026-10-01; **coverage confirmed through 2026-11-30** | Runway |

So: the subscription is **active**, coverage runs to **2026-11-30**, and the
cache is current through **2026-07-27**. There is no lapse risk blocking this.
What blocks it is the standing rule that renewal ≠ pull authorization — a
62,734-call refetch is emphatically a paid pull and needs your explicit
per-pull approval.

---

## 4. The dependency that actually matters — and it is smaller than it looks

Session 2 (causal clock) is specified to enforce `fill_ts > data_available_at`.
The obvious worry is that this is unenforceable on a v1 cache, because v1 has
no availability timestamp — which would make Session 5 a hard blocker on the
P0 fix and force the expensive work to the front of the queue.

**It does not, and here is why.** Every row in an EOD chain shares one
publication event: ThetaData's EOD report, generated at 17:15 ET on the
chain's own date (`data/thetadata_adapter.py:9-13`). `data_available_at` can
therefore be **derived** as a constant per chain-date without any new column.
Session 2 can proceed on the v1 cache.

The honest caveat, which belongs in the Session 2 brief: a derived constant is
an **Assumption** (the repo's own claim-discipline label), not a measurement.
It is correct only if the provider's actual per-row timestamps really do all
fall at or before the derived instant. Schema v2 is what converts that
assumption into a **Repo-verified** fact. So the relationship is:

> **Session 5 does not block Session 2. Session 5 is what lets you stop
> trusting Session 2's timestamp assumption.**

That is a real reason to do it, but it is a *strengthening* reason, not a
*blocking* one — which means it does not have to be bought today.

---

## 5. Owner decision table (STOP-gate-E format — no values proposed)

| Slot | What it controls | Candidate options | Reasoning | What breaks if wrong |
|---|---|---|---|---|
| **Refetch authorization** | Whether ~62,734 paid calls may run at all | (a) authorize full refetch; (b) authorize a bounded pilot first; (c) defer entirely | Ledger rule requires per-pull approval. A pilot buys the schema-v2 design evidence at a small fraction of the calls | Unauthorized spend; a wasted full run if the v2 schema turns out wrong |
| **Refetch scope** | Which symbol-days get v2 | (a) all 31,367; (b) in-sample only (≤ 2022-12-31); (c) live-hypothesis names only; (d) forward window only | Not every cached day feeds a live hypothesis. H1/H2 need in-sample; H7/H8/H10 need recent | Over-scoping wastes calls; under-scoping leaves the fix incomplete where it matters |
| **v2 column set** | What provenance gets persisted | The nine fields C4 lists, or a subset | Must be driven by what the *fix* needs (availability timestamp, multiplier), not by what the provider happens to return | A second refetch later if a needed field was omitted |
| **v1 disposition** | What happens to 2.95 GB of v1 files | (a) keep, mark display-only; (b) keep + machine-enforced display-only gate; (c) delete after v2 lands | Program plan says "v1 caches display-only". Marking without enforcing is how a v1 file silently prices a v2 result | A v1 file reaching a verdict path and being trusted |
| **Timing vs Sessions 2/3/4** | Ordering | (a) after the engineering fixes; (b) pilot now, full later; (c) now | §4 shows S5 is not a blocker. But every result produced before S5 rests on the derived-timestamp assumption | Buying data to support code that then changes |

**Every value above is yours to type.** Nothing here is a recommendation
dressed as a menu — the scope and column-set choices in particular depend on
how much you want to spend to convert one Assumption into one verified fact.

---

## 6. What this scoping did NOT do

- **No provider call, no network, no spend.** Nothing was fetched or priced.
- **No parquet values read.** The inventory used file names and byte sizes
  only, so no holdout data was touched.
- **No dollar cost computed.** I have the call count (62,734) but not the
  subscription's pricing model or whether calls are metered at all beyond the
  flat fee. That is a question for the ThetaData account, not the repo — the
  ledger records the renewal but not the terms.
- **No v2 schema designed.** That belongs in the implementation brief, once
  Sessions 2–4 have established which provenance fields the fixes actually
  consume.
- **Not verified:** whether the provider still returns the discarded fields at
  all under the current subscription tier. `data/thetadata_adapter.py:9-13`
  records 43 columns observed live on 2026-07-03; whether that still holds is
  an Assumption until probed, and probing costs a call.
