# H7 historical earnings coverage report — 2026-07-11 (7b-2R section 8)

**Produced BEFORE any change to the registered diagnostic scope and before
any P&L exists.** One bounded collection pass over the eight H7 backtest
names, per the owner's 7b-2R instruction. No assumed-notice proxy, no
aggregator calendars, no announcement dates inferred from report dates.

## What was collected

SEC EDGAR 8-K **item 2.02** filings (Results of Operations) for
2018-01-02..2026-06-30, via the `data.sec.gov` submissions API
(`tools/collect_sec_earnings.py`, one-time run). Each filing became one
append-only v2 assertion: `status=occurred`, `known_as_of_utc` = EDGAR
**acceptanceDateTime** (true point-in-time publication), `occurred_date` =
period-of-report, `source_url` = the EDGAR archive folder. 254 new rows
appended to `data/earnings/assertions_v2.csv` (4 were already present from
the 2026-07-10 research pass); the store re-validates.

| symbol | item-2.02 reports | first in window | >120-day holes |
|--------|------------------|-----------------|----------------|
| NOW    | 35 | 2018-01-31 | none |
| NVDA   | 36 | 2018-02-08 | none |
| PLTR   | 23 | 2020-11-12 (listed 2020-09-30) | none |
| MSFT   | 34 | 2018-01-31 | none |
| AMZN   | 34 | 2018-02-01 | none |
| VST    | 34 | 2018-02-26 | none |
| CEG    | 17 | 2022-05-12 (spun off 2022-02-02) | none |
| SMCI   | 45 | 2018-01-30 | none (delinquency-era monthly business-update 8-Ks all carry item 2.02) |

The occurred-report archive is **quarter-complete for every symbol** from
its first in-window report onward.

## Resulting gate coverage over the eligible manifest (14,917 sessions)

Evaluated with the real session-close cutoffs and the frozen gate
(45-day occurred-only grace; nothing else changed):

| symbol | CLEAR | BANNED | UNKNOWN |
|--------|-------|--------|---------|
| NOW  | 1,033 | 0  | 1,101 |
| NVDA | 1,045 | 2  | 1,087 |
| PLTR | 722   | 9  | 708   |
| MSFT | 1,067 | 0  | 1,067 |
| AMZN | 1,024 | 0  | 1,110 |
| VST  | 1,039 | 33 | 1,062 |
| CEG  | 525   | 17 | 558   |
| SMCI | 925   | 3  | 780   |
| **total** | **7,380** | **64** | **7,473** |

(BANNED arises on bmo-filer report days whose 8-K is visible by that
session's close; amc report days sit in UNKNOWN until the next session —
both are correct causal behavior.)

## What could NOT be established (disclosed limitation)

**Schedule-announcement history is not reconstructible from official
sources for 2018–2026.** "Company X will report on date D" press releases
are not SEC filings; company IR pages carry no timestamped history; the
MIAX/OCC/exchange archives carry nothing relevant; and the owner has
forbidden aggregator calendars and assumed-notice proxies. Therefore no
historical session can be CLEAR via the "next report known" arm — only via
the occurred+grace arm above.

Consequently the 7,473 UNKNOWN sessions split per the owner's taxonomy:

- **PROVEN_UNKNOWN candidates**: sessions inside a period where the SEC
  item-2.02 archive is demonstrably complete (every symbol, first report
  → window end). *Our archive* is complete there; what is unprovable is
  the negative "no schedule was public that day." Declaring these
  PROVEN_UNKNOWN therefore requires the owner to ratify
  source-completeness declarations (`data/earnings/coverage.json`) that
  define completeness **relative to the SEC archive** — a scope statement
  only the owner can make. This file is deliberately NOT written by the
  collector or by this session.
- **DATA_GAP (unconditional)**: the head sessions before each symbol's
  first in-window report (2018-01-02 → first 8-K; and PLTR/CEG
  pre-listing heads are already registry-excluded), where no evidence of
  any kind exists.

## Proposed source-complete periods (for owner ratification, NOT enacted)

    NOW  2018-01-31..2026-06-30      MSFT 2018-01-31..2026-06-30
    NVDA 2018-02-08..2026-06-30      AMZN 2018-02-01..2026-06-30
    PLTR 2020-11-12..2026-06-30      VST  2018-02-26..2026-06-30
    CEG  2022-05-12..2026-06-30      SMCI 2018-01-30..2026-06-30

Each period starts at the symbol's first in-window occurred report and is
based solely on data availability — chosen before any P&L exists.

## Estimand consequence the owner must weigh (before 7b-3)

With schedule announcements unavailable, historical entries are possible
ONLY inside post-report grace windows (7,380 of 14,917 sessions, ~49%).
That is a narrower entry universe than the registered "earnings-aware,
always-on lanes" and is a **scope amendment decision**: (a) ratify the
declarations + amended estimand ("entries restricted to sessions where the
gate is provably CLEAR"), or (b) judge the restricted diagnostic unusable
and fall back to the forward paper window. Fabricating dates is not an
option and was not done.
