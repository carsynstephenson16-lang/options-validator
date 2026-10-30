# P — Round-4 independent adversarial review of the Packet 1 fact text

**Target:** `reports/2026-09-15-audit/H-owner-fact-packets.md`, **Revision 4**,
Packet 1 (`H6_0001_UNMARKED_EXPIRY`).
**Prior receipts:** `J` (round 1, Rev 1 text), `L` (round 2, Rev 2 text),
`M` (round 3, Rev 3.1 text), all in this directory. `M` was read in full first.
**Packet 2** (`H9_RECEIPT_FULL_DOCUMENT_HASH_V1`) is out of scope except for the
byte-identity confirmation in §0.
**Date:** 2026-09-15. **Worktree:** `.tmp/worktrees/audit-0915`, branch
`claude/audit-2026-09-15`. Repo facts re-derived in the `main` checkout
`/Users/carsynstephenson/options-validator-ops` at `a3745ab` = `origin/main`.
**Stance:** show how the Revision 4 text could be lying, over-claiming, or unsafe
to append. Not a confirmation pass.

**Nothing was appended. Nothing was committed. No ledger-writing tool was
called.** The guarded program was executed only against a **stubbed**
`append_fact` that captured its arguments and asserted the prefix invariant; the
stub was injected by prepending a `sys.modules` shim and the program was
otherwise byte-identical to the one in `H`. The packet file was not edited. A
throwaway synthetic repository under `/tmp/acc` was used to exercise the
accept path. The only file created is this one.

---

## §0. Verdict

### Packet 1 — `H6_0001_UNMARKED_EXPIRY` — **NOT READY**

**The Packet 1 fact text must NOT be appended as written.** It contains a
statement of fact that the repository's own cache falsifies:

> The best bid anywhere in the window is 13.50 on 2026-08-14, which is 1335.35
> USD of registered conservative-fill proceeds against the 1841.30 USD the rule
> requires - 72.5 percent of the trigger, a gain of plus 45.04 percent against a
> required plus 100 percent.

`.cache/intraday/` holds **66 further observations of exactly this contract**
(NVDA 220 call, expiry 2026-09-18) between 2026-08-07 and 2026-09-03, each bound
by a **committed** receipt under `reports/intraday_capture/` (132 tracked files,
31 sessions, `status: ok`) **on `main`**. The best bid observed anywhere is
**15.05 on 2026-08-14 at 09:31 ET**, worth **1488.35 USD** of registered
conservative-fill proceeds — **80.8 % of the trigger**, a gain of **+61.66 %**.
Fifteen of the 66 exceed 13.50.

This is the round-3 failure mode repeated one lane later. `M-1` caught the text
generalising a true statement about the ThetaData lane into a false statement
about all evidence. Revision 4 fixed that by disclosing the Schwab lane — and
then generalised a true statement about the **Schwab** lane ("best bid") into a
false statement about all evidence again, this time in the deflationary
direction. Rounds 2, 3 and 4 have each found the same paragraph wrong.

Every figure derived from the Schwab lane reproduced **exactly** — all 14 rows,
bid, ask, proceeds, P&L, percentages, parquet sha256 and receipt status. So did
every other number, hash, path, `seq`, `record_hash`, line number and date in
the text. As in all three prior rounds, the failure is evidence coverage, not
arithmetic.

Because the text must change, the invariant hash
`09b944ce1e6d6e90d6f7ef0d66b134bad919513db4d84bd11c97c4180845d916` must be
recomputed against Revision 5, and the fact's own review citation must move from
`P` to a round-5 receipt: **this file reviewed words that will not be the words
appended.** That is the `L-4` / `M` carry-forward defect, one round later.

### Packet 2 — byte-identity confirmed

The Packet 2 blockquote is **character-identical** to the string its command
passes to `append_fact` (4,638 characters, no `'`, `"`, `$`, backtick, `!` or
byte above ASCII 126), and `sha256(TEXT)` reproduces
`c837b27e522f0c9c300e3163985a1b0aab7549dc1cde55baa77b1a7b5dfb10f4` — matching
both the pinned constant in its guard and the hash `M` recorded. **It is
byte-identical to what `M` reviewed.** Nothing in this review asks for a
character of it to change. Its guard, however, shares the two structural holes
at **P-8** and **P-9** below.

---

## §1. Disposition of M-1 … M-9 and M's provenance blocker

| ID | M severity | Disposition | Evidence |
|---|---|---|---|
| **M-1** — window called empty | BLOCKER | **PARTIAL** | The false sentence is deleted. The replacement correctly scopes the absence to the registered ThetaData lane (re-verified: `.cache/chains` last session `2026-07-27` for NVDA and overall) and discloses the Schwab series. All 14 rows independently re-derived and **exact**: bid, ask, proceeds, P&L, % of entry, % of trigger, parquet sha256 prefix and `names.NVDA.status = ok`, all 14 receipts tracked on `main`. **But** the replacement still misdescribes the evidence base: it presents the Schwab series as the whole of the off-lane record and dates it from 2026-08-14, while a third committed lane observes the contract from **2026-08-07** and adds five sessions the fact never mentions (08-07, 08-12, 08-13, 08-17, 08-18). See **P-2**. |
| **M-2** — take-profit "not ruled out" | BLOCKER | **OPEN (regressed in the other direction)** | The `UNKNOWN` framing is gone and every Schwab-lane figure is exact: 13.50 → 1335.35 (72.52 %), 12.55 → 1241.35 (67.4 %), 11.70 → 1157.35 (62.9 %), 08-28 5.55 → 548.35 / −372.30 / −40.44 %, 09-10 3.75 → 370.35 / −550.30 / −59.77 %. **But the headline claim is false**: the best bid anywhere is 15.05 (80.8 % of trigger), not 13.50 (72.5 %). See **P-1**. |
| **M-3** — provenance absent from `main` | BLOCKER | **PARTIAL** | Re-verified today with `git cat-file -e origin/main:<path>`: all six provenance documents **still ABSENT** from `origin/main`; `G`–`O` are untracked on the audit branch. PR **#175** exists, is `OPEN`, `MERGEABLE`, base `main`, head `claude/audit-2026-09-15` — the packet's step 1 is accurate. Both commands gained a cited-path check that does refuse when paths are missing. **But the check is bypassable** — it tests disk existence, not tracking, and the porcelain carve-out permits untracked paths under `reports/2026-09-15-audit*`. Demonstrated **rc 0** with all six present-but-untracked. See **P-8**. |
| **M-4** — 18.41 derivation and trigger level | MUST | **CLOSED** | Solved independently over the cent grid: bid 18.60 → 1840.35 (< 1841.30, fails); bid **18.61** → 1841.35 (passes). The minimum raw bid is exactly 18.61. `adverse_sell(p) = floor(p × 0.99 × 100)/100` confirmed at `strategies/base.py:17-19` with `SLIPPAGE_HAIRCUT = 0.01` and `COMMISSION_PER_CONTRACT = 0.65` at `config.py:94-95`; the rule `proceeds >= entry_cost × (1 + H6_TAKE_PROFIT_PCT)` confirmed at `h6_watch.py:440-446`. Wording is exact. One citation quibble at **P-11**. |
| **M-5** — "closes reproduced in the drafting record" | MUST | **CLOSED** | All twelve are now in §1.1 and all twelve re-derived exactly: 08-07 223.96, 08-12 224.09, 08-13 225.30, 08-14 225.16, 08-17 225.01, 08-27 227.98, 08-31 220.78, 09-02 224.41, 09-03 228.45, 09-04 230.36, 09-08 225.73, 09-09 223.67. The clause is now true. |
| **M-6** — impossible append routes | MUST | **CLOSED** | `git worktree list` confirms `main` is checked out only at `/Users/carsynstephenson/options-validator-ops`. `BASE` now points there. Refusals verified: primary checkout → *"is on branch claude/rest-2026-09-09, not main"*; audit worktree → *"is on branch claude/audit-2026-09-15, not main"*. |
| **M-7** — 579 unprotected characters | MUST | **PARTIAL** | The skeleton hash is real and reproduces `09b944ce…` from the blockquote. It now leaves only the four slot **values** free — 107 characters, of which two are format-locked numerics and one is a two-value whitelist. Verified refusals: prose tamper (`72.5` → `99.9 percent`) → rc 1; label `Blog-source` → rc 1; intrinsic `whatever I want` → rc 1. **But M's actual exploit still passes.** See **P-7**. |
| **M-8** — dirty / stale tree | MUST | **CLOSED** | Verified refusals: modified `ledger/facts.log` → rc 1; the ops tree as it stands today (`?? reports/intraday_capture/2026-09-15/`) → rc 1; HEAD one commit behind `origin/main` → rc 1 with both SHAs printed. |
| **M-9** — wrong repository | SHOULD | **PARTIAL** | A wrong origin URL refuses (rc 1, URL printed). **But the test is a bare suffix match**: my synthetic accept-tree passed with `origin = /tmp/acc/carsynstephenson16-lang/options-validator.git`, a local path. See **P-9**. |
| **M's provenance blocker (both packets)** | BLOCKER | **PARTIAL — sequencing correct, enforcement weak** | The five-step sequence is correct and executable (§4), PR #175 is real and mergeable, and the packet is right that `repo-reconcile` will not move the evidence commit (`~/bin/repo-reconcile:67` `ro=1`; `:98` leaves uncommitted changes on a `main` checkout alone; `:142` and `:174` skip `main` for push and PR). The enforcement gap is **P-8**. |

---

## §2. New findings

### P-1 — **BLOCKER** (fact text). The stated maximum is falsified by a third committed lane.

**Exact text:**

> The best bid anywhere in the window is 13.50 on 2026-08-14, which is 1335.35
> USD of registered conservative-fill proceeds against the 1841.30 USD the rule
> requires - 72.5 percent of the trigger, a gain of plus 45.04 percent against a
> required plus 100 percent.

**Evidence.** `.cache/intraday/` holds 117 NVDA option-chain snapshots spanning
2026-07-24 → 2026-09-15, captured at 09:31, 09:35, 11:00, 13:00 and 15:45 ET.
Filtering each for `strike == 220.0`, `right == "C"`,
`expiration == 2026-09-18` returns **66 observations** of exactly this contract,
2026-08-07 → 2026-09-03. Each is bound by a committed receipt at
`reports/intraday_capture/<session>/<tag>.json` (`receipt_kind
intraday_capture/v1`, `names.NVDA.status = "ok"`,
`names.NVDA.chain_cache_path` naming the parquet); **132 such files are tracked
on `main`** across 31 sessions. Applying the registered fill model:

| Observation | bid | registered proceeds | % of entry | % of trigger |
|---|---|---|---|---|
| **2026-08-14T09:31** | **15.05** | **1488.35** | **+61.66 %** | **80.8 %** |
| 2026-08-14T09:35 | 14.75 | 1459.35 | +58.51 % | 79.3 % |
| 2026-08-17T09:31 | 14.60 | 1444.35 | +56.88 % | 78.4 % |
| 2026-08-13T09:35 | 14.35 | 1419.35 | +54.17 % | 77.1 % |
| 2026-08-17T13:00 | 14.40 | 1424.35 | +54.71 % | 77.4 % |
| … 15 observations exceed 13.50 in total | | | | |

The data is genuine and cross-checks against the Schwab lane where the two
overlap at the same minute: 08-14T15:45 → 13.50 (Schwab 13.50), 08-20 → 8.55
(8.55), 08-24 → 4.85 (4.85), 08-25 → 6.15 (6.15), 08-26 → 5.05 (5.05),
09-03 → 11.70 (11.70). The 15.05 peak is consistent with the underlying: NVDA
opened 2026-08-14 at **226.77**, above its 225.16 close, with a 227.49 high.
The quote passes `quote_valid` (15.05 / 15.30 is a 1.6 % spread against
`MAX_SPREAD_PCT = 0.10`).

**Why this is a blocker.** Two numbers in a permanent append-only record are
wrong — the stated maximum bid (13.50, actually 15.05) and the stated peak
proximity to the trigger (72.5 %, actually 80.8 %) — and the error is in the
direction that flatters the fact's own conclusion. A 2027 reader who opens
`.cache/intraday/` or `reports/intraday_capture/` sees it in one query. The
underlying conclusion survives: **nothing reached the trigger on any lane** —
0 of 66 intraday and 0 of 14 Schwab observations produce proceeds ≥ 1841.30.
It is the "best" and "72.5 percent" claims that fail, not "never fired".

**Replacement wording:**

> On the pre-close and intraday quotes that exist, the plus 100 percent
> take-profit never fired: no observation on any lane reaches the 1841.30 USD
> the rule requires. The best bid observed anywhere is 15.05 on 2026-08-14 at
> 09:31 New York time, from the intraday capture lane, which is 1488.35 USD of
> registered conservative-fill proceeds - 80.8 percent of the trigger, a gain
> of plus 61.66 percent against a required plus 100 percent. The best Schwab
> pre-close bid is 13.50 on 2026-08-14 (1335.35 USD, 72.5 percent). On the
> 2026-08-28 21 DTE date the Schwab pre-close bid was 5.55, which is 548.35 USD
> of proceeds and a loss of 372.30 USD, minus 40.44 percent of the entry.

### P-2 — **BLOCKER** (fact text). The off-lane disclosure omits a whole committed lane.

**Exact text:**

> Off that lane the repository does hold Schwab pre-close captures of this exact
> contract, NVDA 220 strike call expiring 2026-09-18, on 14 sessions between
> 2026-08-14 and 2026-09-10 …

**Evidence.** True, and incomplete in a way that matters. The intraday lane of
**P-1** observes the same contract on five sessions the fact never mentions —
**2026-08-07, 08-12, 08-13, 08-17, 08-18** — all of them **before** the
2026-08-14 start date the fact gives, and four of them above-220 closes. Union
across all three lanes: **19 of the 33 sessions** in the window carry at least
one observation of this contract, not 14.

This is the `M-1` finding restated. The fact's own sentence — "They are recorded
here so that no reader concludes the window is evidentially empty" — is
undercut by a disclosure that itself understates the record by five sessions and
one lane.

**Replacement wording (opening of the same paragraph):**

> Off that lane the repository holds two further, non-registered observation
> lanes for this exact contract: Schwab pre-close captures on 14 capture dates
> between 2026-08-14 and 2026-09-10, each with a committed receipt under
> reports/schwab_chains/ whose names.NVDA status is ok and whose recorded sha256
> matches the corresponding .cache/schwab_chains parquet on disk; and intraday
> chain captures at 09:31, 09:35, 11:00, 13:00 and 15:45 New York time on
> sessions between 2026-08-07 and 2026-09-03, each with a committed receipt
> under reports/intraday_capture/ recording names.NVDA status ok and the chain
> cache path, though those receipts bind no sha256. Across all three lanes 19 of
> the 33 sessions in the window carry at least one observation of this contract.
> All of them are tabulated in the drafting record.

### P-3 — **MUST-FIX** (fact text). "Anywhere in the window" and "never close to firing" claim coverage the record does not have.

Even after **P-1** and **P-2** are applied, **14 of the 33 sessions** in the
window carry no observation of this contract on any lane: 2026-07-28, 07-29,
07-30, 07-31, 08-03, 08-04, 08-05, 08-06, 08-10, 08-11, 08-21, 08-31, 09-01 and
**09-04**. Three of those are load-bearing:

- **2026-09-04** is the window's **highest close (230.36) and highest intraday
  high (234.76)** — the fact cites both figures itself — and has **no capture
  of this contract on any lane**. The intraday capture rolled to the 2026-10-16
  monthly expiration from 09-04 onward (verified: `NVDA_2026-09-04T*.parquet`
  contain only `2026-10-16`), and there is no Schwab receipt for 09-04 at all.
- **2026-08-31** and **2026-09-01** have committed Schwab receipts recording an
  honest OAuth failure (`overall_status: failed`, *"Refresh token is invalid,
  expired or revoked"*), so those sessions are known-missing, not merely absent.

A superlative over 33 sessions cannot be asserted from 19. Likewise "was never
close to firing" is an evaluative claim that, at an observed 80.8 % of the
trigger, a reader may reasonably dispute; the numbers say it better than the
adjective does.

**Replacement:** delete "was never close to firing"; say the quantified version
and scope it. Add after the P-1 replacement:

> These are the quotes that were captured. 14 of the 33 sessions in the window
> carry no observation of this contract on any lane, including 2026-09-04, which
> is the window maximum for the underlying on both close and intraday high, and
> 2026-08-31 and 2026-09-01, whose Schwab receipts record an authentication
> failure. Nothing is asserted here about what the contract was worth on those
> sessions.

### P-4 — **MUST-FIX** (fact text). "14 sessions", then one of them is not a session.

**Exact text:** "on 14 sessions between 2026-08-14 and 2026-09-10" … then,
eighty words later, "One of the 14, 2026-09-07, falls on a market holiday …
so it is an artifact rather than a session".

The fact contradicts itself inside one paragraph. Confirmed: 2026-09-07 is
Labor Day, absent from the NVDA OHLCV parquet, and its row carries
`timestamp NaT`, `iv -9.99`, `delta -999.0`. There are **13 sessions and one
holiday artifact**. `M`'s own proposed wording said "13 sessions".
**Fix:** "on 14 capture dates", as in the **P-2** replacement.

### P-5 — **SHOULD-FIX** (fact text). The "next best" ranking silently skips the artifact.

**Exact text:** "The next best are 12.55 on 2026-08-27 (1241.35 USD, 67.4
percent) and 11.70 on 2026-09-03 (1157.35 USD, 62.9 percent)."

The 2026-09-07 holiday row sits between them at bid **12.35 → 1221.35 → 66.3 %**
and is omitted without a stated exclusion. Defensible, because the fact declares
that row an artifact two sentences earlier — but the drafting-record table shows
66.3 % in the same column, so a reader checking the ranking finds a gap. If the
**P-1** rewrite lands this sentence is superseded anyway; if any version of it
survives, add "excluding the 2026-09-07 artifact".

### P-6 — **SHOULD-FIX** (fact text). The 21-DTE value is provider-dependent and given as a single number.

**Exact text:** "On the 2026-08-28 21 DTE date the bid was 5.55, which is 548.35
USD of proceeds and a loss of 372.30 USD" — and, downstream, "The cost of the
outage on this position is 548.35 USD minus that expiration intrinsic value".

Both lanes captured 2026-08-28 pre-close within 21 seconds of each other and
disagree: Schwab at 19:45:31 UTC quotes **5.55 → 548.35**; the intraday lane at
19:45:10 UTC quotes **5.50 → 543.35**. The fact presents 548.35 as *the* value
and then builds the outage-cost arithmetic on it. **Fix:** say "5.55 on the
Schwab pre-close capture (548.35 USD); the intraday capture of the same session
quotes 5.50 (543.35 USD)", and describe the outage cost as a range or name the
lane it uses.

(Separate, minor: the outage-cost subtraction compares **proceeds net of the
0.65 commission** against **gross expiration intrinsic**. The fact labels it
arithmetic and defines it explicitly, so it is not wrong — but a reader may not
notice the asymmetry.)

### P-7 — **MUST-FIX** (guard, and a false claim in the packet's own guard table). M's exploit is not closed.

**The packet claims:**

| Scenario | Result |
|---|---|
| **M-7 exploit**: `"a blog post I found"` as `Official-source`, intrinsic `9999.00` | **rc 1** (Rev 3: rc 0) |

**Evidence.** That refusal is an artifact of the ops tree being dirty today for
an unrelated reason. Run against a **clean** tree on `main` at its `origin/main`
with all cited paths present, the same exploit returns **rc 0** and calls
`append_fact`:

```
[t10_blog_clean.py] rc=0 :: tree: /private/tmp/acc/work on main at 39082ec…
  target: …/ledger/facts.log | lines before: 1
  STUB append_fact: dedupe_prefix=H6_0001_UNMARKED_EXPIRY len=11479
```

The skeleton hash blanks the slot values, so nothing about the source string is
covered; the whitelist constrains only the *label*, not whether the label is
truthful; and `[0-9]{1,6}\.[0-9]{2}` accepts `9999.00` as an intrinsic value for
a 220-strike call at a 213.40 close (correct value: 0.00). The guard holds both
numbers and never compares them.

**Two fixes, neither touching the fact text:**

```python
# 1. the intrinsic must actually be the intrinsic the fact defines
if round(max(0.0, float(close_s) - 220.0) * 100.0, 2) != round(float(intrinsic_s), 2):
    sys.exit("REFUSED: intrinsic %s is not max(0, %s - 220) x 100 = %.2f. Nothing was appended."
             % (intrinsic_s, close_s, max(0.0, float(close_s) - 220.0) * 100.0))
# 2. an Official-source label requires an official-looking source
if label_s == "Official-source" and not re.search(r"(?i)nasdaq|nyse|cboe|occ|official", source_s):
    sys.exit("REFUSED: source %r is labelled Official-source but names no exchange or official "
             "publisher. Use Vendor-source, or name the exchange. Nothing was appended." % source_s)
```

The packet's guard-behaviour table must also be corrected: that row currently
records a pass as a catch.

### P-8 — **MUST-FIX** (both guards). The provenance check tests the disk, not `main`.

**Evidence.** `missing = [c for c in CITED if not (pathlib.Path(top) / c).exists()]`
is an existence test, and the porcelain carve-out
(`not ln[3:].startswith("reports/2026-09-15-audit")`) allows untracked paths in
exactly the directory the provenance documents live in — and, because it is a
prefix test, also allows untracked
`reports/2026-09-15-audit-edge-verdict-and-loose-ends.md`. So all six documents
can be **copied into the tree and never committed** and the guard passes.
Demonstrated: after untracking all six in the synthetic tree and pushing that
removal, `git status --porcelain` showed only
`?? reports/2026-09-15-audit-edge-verdict-and-loose-ends.md` and
`?? reports/2026-09-15-audit/`, and the program returned **rc 0**.

This defeats the purpose of `M-3`: the fact would be appended to `main` citing
six documents that are not on `main`.

**Replacement:**

```python
missing = [c for c in CITED if git("cat-file", "-e", "HEAD:%s" % c)[0] != 0]
if missing:
    sys.exit("REFUSED: these paths are cited by this fact but are not committed on main: %s. "
             "Land PR 175 on main first. Nothing was appended." % missing)
```

### P-9 — **SHOULD-FIX** (both guards). The origin check is a suffix match.

`url.endswith("carsynstephenson16-lang/options-validator.git")` is satisfied by
any local path ending in that string. My synthetic accept-tree passed with
`origin = /tmp/acc/carsynstephenson16-lang/options-validator.git`. Compare the
whole URL instead:

```python
if url not in ("https://github.com/carsynstephenson16-lang/options-validator.git",
               "git@github.com:carsynstephenson16-lang/options-validator.git"):
    sys.exit("REFUSED: origin is %s, not the options-validator remote. Nothing was appended." % url)
```

### P-10 — **NOTE** (both guards). Porcelain parsing is positional.

`ln[3:]` assumes a three-character status prefix. It is correct for `??` and for
ordinary `M `/` M` entries, but a rename prints `R  old -> new` and a path with
special characters is printed quoted, so `ln[3:]` would not start with the
expected prefix. Low risk on this tree; noted because the carve-out is a
security boundary.

### P-11 — **NOTE** (fact text). The fill model is not at line 446.

**Exact text:** "under the registered fill model at options_researcher/h6_watch.py
line 446 - conservative sell at the bid less the 1 percent SLIPPAGE_HAIRCUT
floored to the cent, less the 0.65 USD COMMISSION_PER_CONTRACT".

Verified: line **446** is `if proceeds >= position.entry_cost * (1.0 +
config.H6_TAKE_PROFIT_PCT):` — the threshold test. The fill model is lines
**440-443**. §1.1 of the packet cites `440-446` correctly; the fact narrows it
to the wrong line. Cite "lines 440 to 446".

### P-12 — **NOTE** (packet prose, §"Where to append from" step 5). Line range is off.

`docs/h7-forward-operations.md:194-198` is cited for two claims. "Success leaves
`git status --porcelain` empty" is at **194-195**; "the commit carries the
artifacts" is at **191-193**; 196 onward is a different subject. Cite
**191-195**.

### P-13 — **NOTE** (fact text). "near 19:45 UTC" has one outlier.

The 13 real Schwab timestamps are 19:45:28 – 19:45:42 UTC except **2026-08-19 at
19:49:27**. "Near 19:45" is loose enough to cover it; noted only so nobody
reports it as a discrepancy later.

### P-14 — **NOTE**. The two off-lane receipt types are not equally strong.

Schwab receipts bind `names.NVDA.sha256` and the packet verified all 14 against
the parquet on disk (re-verified here, all 14 true). Intraday receipts record
`names.NVDA.chain_cache_path` and `status: ok` but **no sha256**. If the
intraday lane enters the fact per **P-2**, that difference should be stated
rather than left for a reader to discover.

---

## §3. Direct answers to the questions asked

**Q — the 14-session table, re-verified.** Every cell reproduces exactly from
`/Users/carsynstephenson/options-validator-ops`. Filtering each
`.cache/schwab_chains/NVDA_<session>.parquet` for `strike == 220.0`,
`right == "C"`, `expiration == 2026-09-18` returns exactly one row per file. The
parquet sha256 computed on disk equals `names.NVDA.sha256` in
`reports/schwab_chains/<session>/preclose.json` for **all 14**, every one
`status: ok`, and all 14 receipt pairs are tracked on `main`. Proceeds, P&L,
% of entry and % of trigger all reproduce to the cent under
`proceeds = round(floor(bid × 0.99 × 100)/100 × 100 − 0.65, 2)`.
**No number in that table is off by a cent.**

**The fill model and rounding, exactly.** `h6_watch.py:440-443`:
`proceeds = adverse_sell(bid) * 100.0 * contracts - COMMISSION_PER_CONTRACT * contracts`,
then `proceeds = round(proceeds, 2)` at 444. `strategies/base.py:17-19`:
`adverse_sell(p) = math.floor(float(p) * (1 - SLIPPAGE_HAIRCUT) * 100) / 100`
with `SLIPPAGE_HAIRCUT = 0.01` and `COMMISSION_PER_CONTRACT = 0.65`
(`config.py:94-95`). The take-profit test at 446 is
`proceeds >= entry_cost * (1.0 + H6_TAKE_PROFIT_PCT)` with
`H6_TAKE_PROFIT_PCT = 1.00` (`config.py:347`).

**The trigger and the minimum bid.** `920.65 × 2 = ` **1841.30**. Solving over
the cent grid: 18.60 → `floor(1841.4)/100 × 100 − 0.65` = 1840.35, **fails**;
**18.61** → 1841.35, **passes**. The fact's "about 18.61" is right, and its
parenthetical (`2 × 920.65 ÷ 100 = 18.413`, "the conservative fill lifts the
required bid above that") is right.

**The cited figures.** 72.5 % = 1335.35 / 1841.30 = 72.52 %. 67.4 % =
1241.35 / 1841.30 = 67.42 %. 62.9 % = 1157.35 / 1841.30 = 62.86 %. 2026-08-28:
bid 5.55 → 548.35, −372.30, −40.44 % (−40.4386 %). 2026-09-07: Labor Day,
absent from the OHLCV parquet, `timestamp NaT`, `iv -9.99`, `delta -999.0` —
the holiday-artifact characterisation is correct. All exact.

**Q — every other number, hash, path, seq, line number and date.** Re-derived
independently; all correct unless noted.

`experiments.jsonl` seq 6: `trial_intent`, `H6`,
`2026-07-09T00:50:22.721232+00:00`, `record_hash 5d813b8f…` — exact; the exit
clause is byte-for-byte *"Exit: close at 21 DTE at conservative fills OR
take-profit at +100% of premium, whichever first; NO stop-loss (H1 evidence:
stops were the loss engine)."*, so "in substance" is honest; the 8-completed
verdict rule and the separate 3-consecutive-full-cap-month hard kill are both
present. Seq 22: `H6_KILL_V2`, `record_hash 4c552641…`, "effective only for H6
entries on or after 2026-08-03", "Existing H6 rows retain v1" — exact.
`h6_positions.csv`: `H6-0001,NVDA,220.0,2026-09-18,1,2026-07-13,920.65,cc8ccd80…,,,,`
with `exit_date,exit_proceeds,exit_reason,exit_receipt_hash` all blank — exact.
`reports/h6_forward/` holds exactly five files, 07-13 / 07-22 / 07-23 / 07-24 /
07-27. `2026-07-13.json receipt_hash cc8ccd80d8fdd…e8c0`;
`2026-07-27.json receipt_hash c4b3138dd870…e464` with
`snapshot.exits[0] = {action HOLD, dte 53, pnl -441.3, proceeds 479.35, reason
no_exit_trigger, position_id H6-0001}` and
`snapshot.score = {completed_positions 0, verdict INSUFFICIENT_SAMPLE, reason
"requires 8 completed positions"}`. `config.py:347-349` = 1.00 / 21 / 8;
`config.py:189 MIN_LOSSES_FOR_VERDICT = 10`.
Arithmetic: 9.20 × 100 + 0.65 = 920.65; −441.30 / 920.65 = −47.933 %;
(377.50 − 920.65) = −543.15, / 920.65 = −58.9964 %; mid (3.75+3.80)/2 = 3.775.
2026-09-18 is a Friday; 2026-09-18 − 21 days = 2026-08-28, also a Friday;
2026-07-27 → 2026-09-18 = 53 days, matching the receipt `dte`.
2026-09-10 Schwab row: bid 3.75, ask 3.80, delta 0.463, iv 0.33917,
open_interest 43021, timestamp `2026-09-10 19:45:33.824000+00:00` — exact.
Bindings: `preclose.json` `names.NVDA.path = .cache/schwab_chains/NVDA_2026-09-10.parquet`,
`sha256 9df5291708fe…a0f`, `status ok`, `manifest_hash 4a4d697022…4d63`;
`manifest.json` carries `files` (not `names`), `files.NVDA` the bare filename
with the same sha256, and the same `manifest_hash` — exact, and `shasum` of the
parquet reproduces `9df52917…`.
Underlying: window 2026-07-27 … 2026-09-10 **inclusive** = 33 sessions, 12
closes above 220, 21 highs above 220, max close 230.36 and max high 234.76 both
2026-09-04; strictly between = 31 / 12 / 20. `.cache/underlying_ohlcv/NVDA.parquet`
has **2,437** rows and sha256 `c4c36936…`; `facts.log` line 19621 is
`DATA_PULL_OHLCV 2026-09-15: Yahoo OHLCV refresh NVDA rows=2437
path=.cache/underlying_ohlcv/NVDA.parquet`, so the durable anchor the fact
substitutes for the unbound sha256 is real and unambiguous.
`facts.log` lines: 19347 carries the OD-2 clause *"the final canonical chain edge
remains 2026-07-27; decision-authoritative consumers must fail closed beyond
exact cached coverage"* **inside the OD-2 span** (OD-4, the ThetaData access
cutoff of 2026-08-01, follows it) — the fact's attribution is correct; 17892 is
`H9_RESULT 2026-07-18` carrying `5bea2018…`; 19346 is `METRIC_CORRECTION`; 19413
is `H10A_RESULT`; 19553 is `A2_ENTRY_CONVENTION_RATIFIED_V1`. `facts.log` on
`main` is 19,627 lines, so all cited lines sit below the divergence point and
need no checkout qualifier, as `M-16` concluded.
`ledger/README.md` supports "append-only but not hash-chained … advisory
context, never verdict-feeding" verbatim in its *"facts.log is NOT part of the
chain"* section. `grep -ci schwab options_researcher/h6_watch.py` → **0**.
`.cache/chains` last NVDA session and last session overall = **2026-07-27**.
**Every hash, `seq`, `record_hash`, line number, path and date in the fact text
is correct.** The only wrong numbers are the two in **P-1**.

**Q — the invariant hash and the blockquote.** Both confirmed programmatically.
The Packet 1 blockquote is **11,539 characters** and **character-identical** to
the string the command passes. `TEXT.startswith(KEY)` holds. The text contains
no `'`, `"`, `$`, backtick, `!` or byte above ASCII 126. Applying the guard's
two `re.sub` calls yields an 11,440-character skeleton whose sha256 is
**`09b944ce1e6d6e90d6f7ef0d66b134bad919513db4d84bd11c97c4180845d916`** —
matching the pinned constant exactly. Unprotected region: **107 characters**,
the four slot values only, versus 579 in Revision 3. Packet 2: blockquote
**4,638 characters**, character-identical to its `TEXT`, `sha256(TEXT)` =
`c837b27e522f0c9c300e3163985a1b0aab7549dc1cde55baa77b1a7b5dfb10f4`, matching its
pinned constant and `M`'s record.

**Q — the guarded command, dry-run against a stubbed `append_fact`.** The real
`append_fact` was never called. All fifteen scenarios:

| Scenario | Result |
|---|---|
| As shipped, today, placeholders present | **rc 1** — *"It is 2026-09-15T13:01:25…-04:00 in New York, before 2026-09-19 00:00."* |
| Date gate bypassed, placeholders still present | **rc 1** — *"unsubstituted placeholder in the fact text."* |
| Substituted, ops tree as it stands today | **rc 1** — *"uncommitted changes outside the allowed evidence paths: `['?? reports/intraday_capture/2026-09-15/']`"* |
| Substituted, primary checkout (side branch) | **rc 1** — *"is on branch claude/rest-2026-09-09, not main."* |
| Substituted, audit worktree | **rc 1** — *"is on branch claude/audit-2026-09-15, not main."* |
| Label `Blog-source` | **rc 1** — *"must be exactly Official-source or Vendor-source."* |
| Intrinsic `whatever I want` | **rc 1** — *"not a plain number with two decimals."* |
| Prose tampered outside slots (`72.5` → `99.9 percent`) | **rc 1** — skeleton hash mismatch |
| Wrong origin URL | **rc 1** — *"origin is /tmp/acc/somewhere-else.git, not the options-validator remote."* |
| `ledger/facts.log` dirty | **rc 1** — *"uncommitted changes outside the allowed evidence paths: `['M ledger/facts.log']`"* |
| HEAD one commit behind `origin/main` | **rc 1** — *"HEAD 39082ec… is not origin/main b9a3c13…"* |
| Cited paths absent | **rc 1** — *"cited by this fact but are not in this tree … Land PR 175 on main first."* |
| **Clean tree on `main` at `origin/main`, all cited paths present** | **rc 0 — ACCEPTS**, stub called, prefix invariant held, `lines before`/`lines after` printed |
| **M-7 exploit on a clean tree**: `"a blog post I found"`, `Official-source`, intrinsic `9999.00` at a 213.40 close | **rc 0 — PASSES. See P-7.** |
| **Six provenance documents present but untracked and absent from `origin/main`** | **rc 0 — PASSES. See P-8.** |

**Q — does the text now over-claim in the other direction?** **Yes.** "The best
bid anywhere in the window is 13.50" is false (**P-1**); "was never close to
firing" is asserted at an observed 80.8 % of the trigger and should be replaced
by the numbers (**P-3**); and "anywhere in the window" asserts a maximum over 33
sessions from 19 (**P-3**). The intraday path is **not** unobserved — 66
snapshots exist at five times per session from 2026-08-07 to 2026-09-03 — but
the three highest-underlying gaps (09-04, 08-31, 09-01) are. The wording is
**not defensible as written**; it should be scoped to the observed quotes, name
the lane, and state the gaps.

**Q — does it still pre-decide, legislate, or change a registered number?**
**No, on all three.**
- *Pre-decide:* the text records that the owner approves by reading and running
  the append, names options (b) and (c) neutrally, states they are "not adopted
  by this append", and pushes the drafting agent's reasons to the drafting
  record "and are not attributed to the owner". The `Owner ratification: ______`
  line is blank. The `M-13` residue (the text asserting that the append *is* the
  approval, where `.claude/rules/ledger.md:22` words it as "review of the exact
  text, then owner approval, then append") is unchanged and remains acceptable.
- *Legislate:* `NO RETROACTIVE RULE CHANGE` is present and explicit — "amends
  nothing, changes no registered exit, and creates no precedent for booking a
  reconstructed close from a quote".
- *Change a registered number:* no. H6 stays `INSUFFICIENT_SAMPLE` at n = 0
  against the 8-completed bar (seq 6 and `config.py:349` both re-checked); seq 22
  is untouched and correctly described as prospective-only; the book row's four
  exit columns are verified blank and the fact says they stay blank and explains
  why.

**Q — is the expiration-intrinsic convention still clearly labelled Assumption
and non-precedential?** **Yes.** The text carries "(Assumption, stated so,
because experiments.jsonl seq 6 registers no expiry handling at all)", "adopted
by this fact and by nothing earlier", "For disclosure purposes only - this
valuation is recorded in this fact and nowhere else; no book row, receipt, or
scoreboard carries it", "a paper valuation convention, not a claim about
contract settlement", the OCC auto-exercise carve-out, and the
`NO RETROACTIVE RULE CHANGE` clause calling it "prospective-neutral". That is
adequate and needs no change.

---

## §4. The five-step append sequence

**Correct and executable, with two caveats.** Re-verified item by item:

1. **Land PR #175.** Real: `OPEN`, `MERGEABLE`, base `main`, head
   `claude/audit-2026-09-15`. All six provenance documents are still **ABSENT**
   from `origin/main` today. `G`–`O` are **untracked on the branch** and must be
   committed before the PR lands, which the packet says. *Caveat:* if the text
   changes per this review, the round-5 receipt — not `P` — is the one that must
   be on the PR, and `H` must be committed at its final revision.
2. **`cd` to the ops tree, `git fetch && git pull --ff-only`.** Workable: it is
   on `main` at `a3745ab` = `origin/main` today.
3. **`git status --porcelain` empty except allowed paths.** Accurate: today it
   shows `?? reports/intraday_capture/2026-09-15/` and the guard refuses on it.
   *Caveat:* that directory is a receipt from the daily capture programme — the
   same programme that produced the evidence in **P-1**. It should be committed
   through the normal route, not deleted.
4. **Run the command.** Verified to reach `rc 0` and call `append_fact` once all
   preconditions hold.
5. **Commit and push by hand, then branch and PR.** Correct and verified:
   `~/bin/repo-reconcile:67` sets `ro=1` for `options-validator-ops`; `:98`
   leaves uncommitted changes on a `main` checkout alone ("needs you"); the push
   loop (`:142`) and the PR loop (`:174`) both `continue` past
   `main|master|deploy/*`. So nothing automatic will move the evidence commit,
   and the `git switch -c claude/facts-append-2026-09-19` route avoids pushing
   `main` directly. One detail worth knowing: after the append the ops tree is
   dirty on `main`, and because that checkout is `ro=1` **and** `main` is
   protected, the daily job will neither rescue-commit nor push it — the state
   is safe but entirely the owner's to clear.

---

## §5. What must change before Packet 1 goes to the owner

**Blocking (fact text — a Revision 5 is required):** **P-1**, **P-2**, **P-3**,
**P-4**. Then recompute the invariant hash and move the fact's review citation
from `P` to a round-5 receipt.
**Blocking (guard only, no text change):** **P-7**, **P-8**.
**Should:** **P-5**, **P-6**, **P-9**.
**Note:** **P-10** … **P-14**, and the correction to the packet's own
guard-behaviour table demanded by **P-7**.

Everything `M` raised that could be closed by Revision 4 was closed correctly,
and every Schwab-lane figure the revision added is exact. The reason this is
round 4 and not the last round is that each revision has widened the evidence
base by one lane and then asserted a superlative over it.

---

*Nothing in this review was appended to any ledger. No ledger-writing tool was
called; `append_fact` was exercised only against a local stub that captured its
arguments and asserted the prefix invariant. No commit was made, no packet or
ledger file was modified, the synthetic repository used to exercise the accept
path was created under `/tmp` and touches nothing in the project, and the only
file created is this one.*
