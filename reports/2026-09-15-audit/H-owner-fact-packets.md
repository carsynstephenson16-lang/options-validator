# H — Owner fact-append packets (2026-09-15)

**Revision: 6.2.** Review history: Rev 1 → **J**. Rev 2 → **L**. Rev 3.1 → **M**.
Rev 4 → **P**. Rev 5 → **Q**
(`reports/2026-09-15-audit/Q-fact-packets-adversarial-review-round5.md`; **P1 NOT
READY**, blocker Q-1). This Revision 6 applies **Q-1 through Q-7**. Changelog is
§4. Packet 2's fact text is **byte-identical** and Q re-confirmed it.

**Nothing has been appended. Nothing was committed.**

### The headline from round 5

Revision 5 listed **2026-07-28, 07-29, 07-30 and 07-31** among sessions that
"carry no observation of this contract **on any lane**". A **fourth** committed
lane holds an exact-session ThetaData chain for this contract on **each of those
four dates**: `.cache/chains_v2/od1-2026-08-01/`, owner-approved at
`facts.log` **19348–19350** — *three lines below the line Revision 5 cites for its
own premise*. Independently re-derived here (§1.1e), sha256-verified against the
namespace manifest for all five in-window sessions.

**Rounds 2, 3, 4 and 5 each found the same paragraph wrong, for the same reason
each time:** a statement true of the lanes the drafter happened to look at,
promoted into a statement about the record. Rev 2 → unsupported; Rev 3 → the
ThetaData lane generalised; Rev 4 → the Schwab lane generalised; Rev 5 → three
lanes enumerated, a fourth missed. Q ran an **exhaustive** search this time —
48,758 cache parquets (all 2,542 NVDA files opened), 523 structured files,
every `.md`/`.txt` and every other binary store — and found **no fifth lane**.
Corrected counts: **23 of 33 observed, 10 unobserved, 86 in-window rows on four
lanes, 84 off-lane quotes.**

**What survives, and is stronger for it:** the chains_v2 maximum bid is **5.40**,
so the **15.05 / 1,488.35 / 80.8%** global maximum is undisturbed, and **0 of all
86 rows on all four lanes reach the 1,841.30 trigger.** The conclusion has now
survived four lanes and an exhaustive search.

### One correction to Q itself

Q's chains_v2 table gives proceeds of **321.35 / 400.35 / 534.35** for bids
3.25 / 4.05 / 5.40. Under the registered floor-then-subtract fill model those are
**320.35 / 399.35 / 533.35** — Q rounded up where `adverse_sell` floors. Its
07-27 and 07-28 rows (479.35, 474.35) are right, and the same formula reproduced
all 14 Schwab and all 66 intraday rows to the cent. **The fact text is
unaffected** — it quotes only the five *bids*, which are correct — and §1.1e
carries the corrected proceeds. Flagged so nobody propagates the slip.

### Packet 2

**Byte-identical** to Revisions 3.1, 4 and 5; Q re-confirmed blockquote/command
identity and `sha256(TEXT)` =
`c837b27e522f0c9c300e3163985a1b0aab7549dc1cde55baa77b1a7b5dfb10f4`. Only its
`CITED` list changed. **Packet 1's** text changed, so its citation moves to
rounds 1–6 with a round-6 receipt
(`reports/2026-09-15-audit/R-fact-packets-adversarial-review-round6.md`, which
does not exist yet) and its invariant hash is recomputed. **After the 6.1
wording fix the operative Packet 1 constant is
`b157ac976e18c03b45609e1922d515ecaf24d83905cd91eb5f442e0465920062`** — the value
pinned in the §1.5 command. (The Revision-6 skeleton hash it supersedes is
recorded in the §4 changelog, so it is not erased from the record.)

---

## Preamble

Both facts go to `ledger/facts.log` via `research/facts.py::append_fact` — never
by hand, never through the chained ledger (`ledger/README.md`).

Evidence labels: **Repo-verified** (read from a tracked file, path given);
**Run-verified** (produced by the command shown, 2026-09-15 — cache reads resolve
outside the repo and are marked *(cache)*); **Official-source** /
**Vendor-source** (exchange-published vs commercial feed — not interchangeable);
**Inference** (model-based, never a measurement); **Not verified**.

```python
def append_fact(text: str, base_dir="ledger", *, dedupe_prefix: str | None = None) -> None
```

Writes `<base_dir>/facts.log` as `<UTC ISO>\t<text>\n` under `flock`, then
`fsync`s. `dedupe_prefix` must be a prefix of `text`; identical re-append returns
silently, divergent re-append raises.

### The seven hazards, and what guards each

1. **A bad first write burns the key** — `append_fact` raises on every corrected
   re-append and `facts.log` is never edited. [F-2]
2. **Premature append of a future event** — Packet 1's command refuses before
   **2026-09-19 00:00 America/New_York**, and the text says so itself. [L-1]
3. **Wrong tree** — `branch == main`, `fetch` succeeds, `HEAD == origin/main`.
   [L-3]
4. **Right branch, wrong repository** — the guard now checks
   `git remote get-url origin` ends with
   `carsynstephenson16-lang/options-validator.git`. M demonstrated an `rc 0`
   against a throwaway clone on a branch called `main` at its own `origin/main`.
   [M-9]
5. **Right repo, dirty tree** — `git status --porcelain` must be **completely
   empty** (Rev 4 carved out `reports/2026-09-15-audit*`; P-8 showed that
   carve-out is exactly the hole, since it is a prefix test over the directory
   the provenance documents live in), and `ledger/` must be clean. M got `rc 0` against a tree with an uncommitted line already appended
   to `facts.log`. **This is not hypothetical:** `~/bin/repo-reconcile:98` leaves
   uncommitted changes on a `main` checkout alone ("needs you"), so a dirty
   append tree is a state the daily job is designed to preserve. [M-8]
6. **Provenance that does not resolve** — six documents cited *inside* the facts
   are absent from `main`, the only tree the guard permits. Both commands now
   check every cited path with **`git cat-file -e HEAD:<path>`** — committed on
   `main`, not merely present on disk. P demonstrated **rc 0** with all six
   copied in and never committed. [M-3, P-8]
7. **Substitution inside the slots** — the skeleton hash covers 100% of the
   prose but by construction cannot cover the four slot *values* (107
   characters). Revision 4 claimed M's blog exploit was closed; **it was not** —
   the rc 1 the packet recorded was an artifact of the ops tree being dirty for
   an unrelated reason, and on a clean tree the same exploit returned **rc 0**.
   That table row was wrong and is corrected in §1.5. Revision 5 constrains the
   values themselves: the label must be exactly `Official-source` or
   `Vendor-source`; both numerics must match `[0-9]{1,6}\.[0-9]{2}`; the
   guard **recomputes `max(0, close − 220) × 100` and refuses on mismatch**; and
   an `Official-source` label requires the source string to name one of
   **Nasdaq, NYSE, Cboe, OCC or SEC**. [M-7, L-5, P-7]

8. **Right-looking origin** — Rev 4 tested `url.endswith(...)`, which P satisfied
   with the local path `/tmp/acc/carsynstephenson16-lang/options-validator.git`.
   The URL is now normalised (scheme, `git@` form, `.git` suffix) and compared
   **exactly** to `github.com/carsynstephenson16-lang/options-validator`. [P-9]

**Substitution character set:** digits, letters, spaces, dots, slashes, hyphens
and colons only. Never paste an apostrophe or a dollar sign. *(The guard programs
contain `!=` comparisons; verified harmless — neither `zsh` nor `bash` expands
history inside single quotes. Neither program contains `'`, `$`, or a backtick.)*

### Where to append from [M-6 — both Revision 3 routes were impossible]

Revision 3 told the owner to check out `main` in the primary tree or run
`git worktree add .tmp/worktrees/facts-append main`. **Both fail.** `main` is
already checked out at `/Users/carsynstephenson/options-validator-ops`, and git
refuses to check out a branch twice. Re-verified here:

```
$ git worktree add /tmp/m6-probe main
Preparing worktree (checking out 'main')
fatal: 'main' is already checked out at '/Users/carsynstephenson/options-validator-ops'
```

**The only tree on `main` is `/Users/carsynstephenson/options-validator-ops`**
(`a3745ab` = `origin/main`, Run-verified). That is where both commands point.
`/Users/carsynstephenson/options-validator` is on `claude/rest-2026-09-09` and
is refused by the branch check.

**Sequence (all of it, in order):**

1. **Land PR #175** (`claude/audit-2026-09-15` → `main`) with the
   `reports/2026-09-15-audit/` receipts — **H, J, L, M** and the round-4 receipt
   **P** — committed on it. Until then the path check refuses: all six
   provenance documents are absent from `origin/main` (Run-verified with
   `git cat-file -e origin/main:<path>`, all six ABSENT).
2. `cd /Users/carsynstephenson/options-validator-ops && git fetch && git pull --ff-only`
3. `git status --porcelain` must be **completely empty**. **Today it is not:**
   it shows `?? reports/intraday_capture/2026-09-15/` (Run-verified). That is a
   ritual artifact of exactly the kind the intraday lane in §1.1b is built on —
   **it should be committed by the ritual, not deleted.** Deleting it would
   discard a same-day capture receipt. `repo-reconcile` will not commit it for
   you, by design (hazard 5).
4. Run the command. It prints the tree, branch, commit, target and the line count
   before and after.
5. **Commit and push the evidence commit yourself.** `repo-reconcile` treats this
   tree as read-only (`~/bin/repo-reconcile:67`, `ro=1`) and skips `main` for
   rescue-commits, pushes and PRs, so nothing automatic will move it. Follow the
   repo's evidence-commit convention (`docs/h7-forward-operations.md:191-195`:
   the commit carries the artifacts and *"success leaves `git status --porcelain`
   empty"*), e.g. `ledger(facts): append H6_0001_UNMARKED_EXPIRY (owner-ratified,
   rounds 1-4 reviewed)`. **Pushing `main` directly bypasses the PR-and-green-
   checks flow and may hit branch protection** — so after the append,
   `git switch -c claude/facts-append-2026-09-19`, commit there, push, and let
   the normal flow land it. The guard's precondition was satisfied at append
   time regardless. [M-15]

---

## Packet 1 — H6-0001 disposition, option (a)

### 1.1 What was verified

| Claim | Status | Source |
|---|---|---|
| seq 6 (`trial_intent`, `H6`, `record_hash 5d813b8f…`, ts `2026-07-09T00:50:22.721232+00:00`) | Repo-verified | `ledger/experiments.jsonl` |
| Registered exits, **exact bytes**: `"Exit: close at 21 DTE at conservative fills OR take-profit at +100% of premium, whichever first; NO stop-loss (H1 evidence: stops were the loss engine)."` The fact says **"in substance"**, not "verbatim" | Repo-verified | seq 6 `reason` |
| 8-completed verdict rule; separate hard kill of 3 consecutive full-cap loss months (not an exit) | Repo-verified | seq 6 `reason` |
| seq 22 `H6_KILL_V2` (`4c552641…`), entries on/after 2026-08-03, existing rows keep v1 | Repo-verified | `ledger/experiments.jsonl` |
| Row `H6-0001,…,920.65,cc8ccd80…` with four blank exit columns | Repo-verified | `data/positions/h6_positions.csv` |
| **The registered take-profit rule**: `proceeds = adverse_sell(bid) * 100 - 0.65`, fires iff `proceeds >= entry_cost * (1 + H6_TAKE_PROFIT_PCT)`; `adverse_sell(p) = floor(p * 0.99 * 100)/100` | Repo-verified | `options_researcher/h6_watch.py:440-446`; `strategies/base.py:17`; `config.py:94-95` |
| **Required proceeds 1,841.30; minimum raw bid that satisfies it = 18.61.** Rev 3's "mark near 18.41 (arithmetic on the 9.20 ask)" was wrong twice: 2 × 9.20 = 18.40, and 2 × 920.65/100 = 18.413 is the *entry-cost* derivation, not the ask; and the rule tests proceeds, not a mark | **Run-verified** (solved by search over bids) | the rule above |
| `cc8ccd80…` = 07-13 `receipt_hash`; `reports/h6_forward/` holds exactly 5 files ending 07-27 | Repo-verified | `reports/h6_forward/` |
| 07-27 receipt: `HOLD, dte 53, pnl -441.3, proceeds 479.35, no_exit_trigger`; `completed_positions 0 / INSUFFICIENT_SAMPLE`; `c4b3138d…` | Repo-verified | `reports/h6_forward/2026-07-27.json` |
| Registered-lane chain cache ends **2026-07-27**; durable citation **OD-2**, `ledger/facts.log:19347`, owner-approved. OD-4 in that line is the ThetaData **access** cutoff | Repo-verified + Run-verified *(cache)* | `facts.log:19347` |
| **No H6 evaluator exists on the Schwab lane** — `grep -ci schwab options_researcher/h6_watch.py` → **0** | **Run-verified** | that command |
| 21-DTE date **2026-08-28** (Friday); 07-27 → 09-18 = 53 days | Run-verified (arithmetic) | 07-27 receipt |
| `H6_TAKE_PROFIT_PCT 1.00`, `H6_CLOSE_AT_DTE 21`, `H6_MIN_COMPLETED_POSITIONS 8` | Repo-verified | `config.py:347-349` |
| The five cited `facts.log` line numbers (17892, 19346, 19347, 19413, 19553) are valid in **all three** checkouts — the copies diverge only above 19,553, and an append-only file's earlier line numbers cannot move. **The facts therefore do not name a checkout**, and should not | Run-verified | all three trees |
| Binding: `preclose.json` → `names.NVDA` (full path, `9df52917…`, `status ok`); `manifest.json` has `files`, not `names` | Run-verified | both JSONs |
| −$441.30 = **−47.93%**; mid 3.775 → $377.50 = **−58.996%**; both labelled arithmetic in the fact | Run-verified | — |

#### The fourteen Schwab captures of this exact contract [M-1, M-2 — independently re-derived]

Filter on every `.cache/schwab_chains/NVDA_<session>.parquet` in the window for
`strike == 220.0`, `right == "C"`, `expiration == "2026-09-18"` — exactly one row
each. Session receipt is `reports/schwab_chains/<session>/preclose.json`; every
one records `names.NVDA.status = "ok"` and a `sha256` that **matches the parquet
on disk** (checked for all 14, all true). Proceeds/P&L columns apply the
registered fill model above against the 1,841.30 trigger.

| Session | bid | ask | NVDA close | receipt | parquet sha256 | registered proceeds | P&L | % of entry | % of trigger |
|---|---|---|---|---|---|---|---|---|---|
| **2026-08-14** **best bid** | 13.50 | 13.60 | 225.16 | `ok` | `90faa8ff8ad6…` | 1,335.35 | +414.70 | +45.04% | 72.5% |
| **2026-08-19** | 9.25 | 9.30 | 217.56 | `ok` | `4ba805db05f4…` | 914.35 | -6.30 | -0.68% | 49.7% |
| **2026-08-20** | 8.55 | 8.65 | 216.85 | `ok` | `fc1e64c61d9b…` | 845.35 | -75.30 | -8.18% | 45.9% |
| **2026-08-24** | 4.85 | 4.95 | 208.48 | `ok` | `50a7f415c4e1…` | 479.35 | -441.30 | -47.93% | 26.0% |
| **2026-08-25** | 6.15 | 6.25 | 213.05 | `ok` | `265e40fbb479…` | 607.35 | -313.30 | -34.03% | 33.0% |
| **2026-08-26** | 5.05 | 5.10 | 209.66 | `ok` | `f58840a3ccb8…` | 498.35 | -422.30 | -45.87% | 27.1% |
| **2026-08-27** | 12.55 | 12.70 | 227.98 | `ok` | `66be05728956…` | 1,241.35 | +320.70 | +34.83% | 67.4% |
| **2026-08-28** **21-DTE date** | 5.55 | 5.65 | 217.55 | `ok` | `951ad293ab68…` | 548.35 | -372.30 | -40.44% | 29.8% |
| **2026-09-02** | 8.60 | 8.70 | 224.41 | `ok` | `981876139758…` | 850.35 | -70.30 | -7.64% | 46.2% |
| **2026-09-03** | 11.70 | 11.80 | 228.45 | `ok` | `3bab19cbde2a…` | 1,157.35 | +236.70 | +25.71% | 62.9% |
| **2026-09-07** **holiday artifact** | 12.35 | 12.65 | — (market holiday) | `ok` | `0d55c98cd5d3…` | 1,221.35 | +300.70 | +32.66% | 66.3% |
| **2026-09-08** | 8.50 | 8.60 | 225.73 | `ok` | `cc46980d50b8…` | 840.35 | -80.30 | -8.72% | 45.6% |
| **2026-09-09** | 6.95 | 7.00 | 223.67 | `ok` | `37f0701d8384…` | 687.35 | -233.30 | -25.34% | 37.3% |
| **2026-09-10** *(the mark the fact already cited)* | 3.75 | 3.80 | 218.36 | `ok` | `9df5291708fe…` | 370.35 | -550.30 | -59.77% | 20.1% |

**Run-verified 2026-09-15 from `/Users/carsynstephenson/options-validator-ops`.**
Reading: the take-profit **never fired and was never close** — best 72.5% of the
trigger, a +45.04% gain against a required +100%. 2026-09-07 is Labor Day; that
row carries `timestamp NaT`, `iv -9.99`, `delta -999.0` — a sentinel artifact,
not a session (its proceeds column is shown for completeness only). The other 13
carry real timestamps at ~19:45 UTC and sane greeks, and the mids track the
underlying coherently (227.98 close → 12.625 mid at 22 DTE; 217.55 → 5.600 next
session), so these are genuine quotes.

**The outage's cost is a number.** On 2026-08-28 the registered time close would
have realised **548.35** (−372.30, −40.44%). The 09-10 mark implies **370.35**
(−550.30, −59.77%). Difference: **178.00** — and against expiration intrinsic it
is `548.35 − intrinsic`, which the fact states as arithmetic once the owner fills
the close.

#### 1.1b The intraday lane — 66 further observations [P-1, P-2, P-14]

Revision 4 missed this entirely. `.cache/intraday/` holds **117 NVDA chain
snapshots** captured at 09:31, 09:35, 11:00, 13:00 and 15:45 ET; filtering each
for `strike == 220.0`, `right == "C"`, `expiration == "2026-09-18"` returns
**66 observations** of this contract across **15 sessions, 2026-08-07 →
2026-09-03**. Each is bound by a receipt at
`reports/intraday_capture/<session>/<tag>.json` (`receipt_kind
intraday_capture/v1`, `names.NVDA.status = "ok"`, `names.NVDA.chain_cache_path`
naming the parquet). **132 such files are tracked on `main`** across 30 session
directories. **Run-verified 2026-09-15.**

**Best bid per session** (tag is the capture slot; receipt path as tracked on
`main`; proceeds under the registered fill model against the 1,841.30 trigger):

| Session | tag | bid | ask | proceeds | % of trigger | receipt (tracked on `main`) |
|---|---|---|---|---|---|---|
| 2026-08-07 | 1100 | 14.05 | 14.20 | 1,389.35 | 75.5% | `reports/intraday_capture/2026-08-07/midmorning.json` |
| 2026-08-12 | 1100 | 13.35 | 13.55 | 1,320.35 | 71.7% | `…/2026-08-12/midmorning.json` |
| 2026-08-13 | 0935 | 14.35 | 14.55 | 1,419.35 | 77.1% | `…/2026-08-13/open.json` |
| **2026-08-14** | **0931** | **15.05** | **15.30** | **1,488.35** | **80.8%** | `…/2026-08-14/open_auction.json` |
| 2026-08-17 | 0931 | 14.60 | 14.80 | 1,444.35 | 78.4% | `…/2026-08-17/open_auction.json` |
| 2026-08-18 | 0935 | 10.85 | 11.00 | 1,073.35 | 58.3% | `…/2026-08-18/open.json` |
| 2026-08-19 | 0931 | 11.35 | 11.55 | 1,122.35 | 61.0% | `…/2026-08-19/open_auction.json` |
| 2026-08-20 | 0935 | 9.40 | 9.60 | 929.35 | 50.5% | `…/2026-08-20/open.json` |
| 2026-08-24 | 0931 | 7.00 | 7.20 | 692.35 | 37.6% | `…/2026-08-24/open_auction.json` |
| 2026-08-25 | 1545 | 6.15 | 6.25 | 607.35 | 33.0% | `…/2026-08-25/preclose.json` |
| 2026-08-26 | 0931 | 6.35 | 6.50 | 627.35 | 34.1% | `…/2026-08-26/open_auction.json` |
| 2026-08-27 | 1300 | 13.55 | 13.70 | 1,340.35 | 72.8% | `…/2026-08-27/midday.json` |
| 2026-08-28 | 0935 | 11.15 | 11.35 | 1,102.35 | 59.9% | `…/2026-08-28/open.json` |
| 2026-09-02 | 0935 | 5.95 | 6.05 | 588.35 | 32.0% | `…/2026-09-02/open.json` |
| 2026-09-03 | 1545 | 11.70 | 11.80 | 1,157.35 | 62.9% | `…/2026-09-03/preclose.json` |

**Top observations overall**, all intraday: 08-14T0931 **15.05** (80.8%),
08-14T0935 14.75 (79.3%), 08-17T0931 14.60 (78.4%), 08-17T1300 14.40 (77.4%),
08-13T0935 14.35 (77.1%), 08-13T1545 14.30 (76.8%). **15 of the 66 exceed
13.50**, the Schwab-lane best. **0 of 66 and 0 of 14 reach the 1,841.30
trigger** — the conclusion the fact now states.

**The two off-lane receipt types are not equally strong [P-14].** Schwab receipts
bind `names.NVDA.sha256` and all 14 were verified against the parquet on disk.
Intraday receipts record `status` and `chain_cache_path` but **no sha256**
(Run-verified against `reports/intraday_capture/2026-08-14/midday.json` on
`main`: keys are `atm_iv, chain_cache_path, chain_contracts_admitted,
chain_contracts_total, greeks_note, iv_label, iv_rank_preview, iv_source,
min_spread_pct_observed, monthly_expiration, open_interest_asof, spot_ask,
spot_bid, spot_mid, spot_source, spot_ts, status, symbol` — no `sha256`). The
fact states this difference rather than leaving it to be discovered.

#### 1.1e The schema-v2 lane — the fourth lane [Q-1, Q-2, Q-3]

`.cache/chains_v2/od1-2026-08-01/` is a ThetaData **schema-v2 side-by-side
backfill** namespace. It holds an exact-session EOD chain for this contract on
**five in-window sessions**, four of which Revision 5 listed as unobserved.
**Run-verified 2026-09-15**; sha256 computed on disk and compared to
`_meta/chain_manifest.txt` (4,610 lines, of which the first two are headers — **4,608 entries**, matching the audit report's 18 symbols x 256 XNYS sessions) — **all five match**:

| Session | bid | ask | quote timestamp | registered proceeds | % of trigger | sha256 (manifest-bound) |
|---|---|---|---|---|---|---|
| 2026-07-27 | 4.85 | 4.95 | 15:59:56.932 ET | 479.35 | 26.0% | `6760a9edf0fb…` |
| **2026-07-28** | 4.80 | 5.10 | 15:59:12.172 ET | 474.35 | 25.8% | `2a115885e02a…` |
| **2026-07-29** | 3.25 | 3.40 | 15:59:37.887 ET | **320.35** | 17.4% | `dda5c7501b1f…` |
| **2026-07-30** | 4.05 | 4.15 | 15:59:13.217 ET | **399.35** | 21.7% | `875dc4c81f50…` |
| **2026-07-31** | 5.40 | 5.55 | 15:59:54.734 ET | **533.35** | 29.0% | `cf5829591821…` |

Paths are `.cache/chains_v2/od1-2026-08-01/NVDA_<session>.parquet`. The bolded
proceeds are the three Q rounded up (see the header note). The 2026-07-27 row is
**bid 4.85 / ask 4.95, identical to the v1 registered chain** — so v2 is a
verified drop-in superset at the boundary, not a different measurement.

**Provenance, re-verified:**

- **Owner-approved**, `ledger/facts.log` **19348** `OD1_SUPERSEDING_DECISION`
  (*"supersede the 2026-07-31 OD-1 DECLINE with APPROVE…"*), **19349**
  `OD1_V2_PULL_APPROVAL`, **19350** `OD1_V2_EXPANDED_PULL_APPROVAL` — expanded
  through **2026-07-31**, 18 symbols including NVDA, destination
  `.cache/chains_v2/od1-2026-08-01`.
- **Audited and tracked on `main`**:
  `reports/thetadata_v2/2026-08-02-od1-full-audit.md`
  (`git cat-file -e origin/main:…` → **TRACKED**), *"PASS WITH WARNINGS"*, NVDA
  not quarantined.
- **Parked**, `tools/fill_haircut_calibration.py:39-43`, verbatim: *"Owner ruling
  2026-08-24: Tier-2 chains_v2 read-only access is approved for this descriptive
  study; the namespace remains parked and excluded from verdict eligibility."*
  **This ruling is not in `facts.log`** — no 2026-08-24 entry exists there. It
  lives as that Python string constant, a tracked supporting report
  `reports/fill_calibration/2026-08-24-fill-adversity-context.md`, and a
  parked-namespace row at `docs/provider-transition.md:57`. It is the one
  load-bearing claim in the fact carrying a date rather than a path, hash or line
  number. Mitigation applied, hash-neutral and **not** a text change: both
  `tools/fill_haircut_calibration.py` and
  `reports/fill_calibration/2026-08-24-fill-adversity-context.md` are added to
  Packet 1's `CITED` list — both verified **tracked on `origin/main`** — so the
  guard's `cat-file` check now binds the anchor. [R-3]

That last point is why this lane belongs in a **descriptive disclosure fact** and
nowhere near a verdict: read-approved, parked, non-verdict-feeding. The fact says
all three things.

**Two things a careful reader will notice, recorded rather than smoothed over.**

*The manifest disagrees with the ruling, and both are right [R-6].* Each of the
five NVDA rows in `_meta/chain_manifest.txt` is tagged
`schema_version=2  usage=verdict-eligible` (verified verbatim on the 07-29 row).
That tag was written at capture time on **2026-08-01**; the parking ruling came
**2026-08-24** and supersedes it. A reader who opens the manifest without knowing
the ruling will read a contradiction. The fact's operative restraint is its own
clause — *"never as a mark source"* — which holds either way. No text change was
made for this; it is flagged here instead.

*Line 951 is a default, not an enforcement [R-7].* `h6_watch.py:951` is a
keyword-argument default (`chain_dir: Path = Path(".cache/chains")`), and
`:1306` exposes `--chain-dir` as an overridable CLI argument with the same
default — so strictly, the evaluator reads `.cache/chains` **by default** rather
than exclusively. The conclusion does not rest on it: the v1 cache's last session
for every name is 2026-07-27 regardless, and
`grep -ci chains_v2 options_researcher/h6_watch.py` → **0**, so no H6 code path
reaches the v2 namespace even if someone pointed it there. Recorded, not
rewritten.

**Why the registered-lane sentence had to be renamed [Q-2].** Revision 5 called
the registered lane "the exact-session ThetaData chain" — but chains_v2 *is* an
exact-session ThetaData chain, from the same provider, and it holds this contract
through 07-31. The true, verifiable statement is narrower: the H6 evaluator reads
**`.cache/chains`** and only that (`options_researcher/h6_watch.py:951`,
`chain_dir: Path = Path(".cache/chains")`), and demands an exact-session file
(`:990-991`, `raise FileNotFoundError(f"exact chain missing: …")`). The fact now
names the directory and the line.

**Why the OD-2 citation needed a clause [Q-3].** A reader who checks
`facts.log:19347` and reads three lines on hits an owner approval that looks like
a direct contradiction. It is not — OD-2 governs the **v1 canonical cache**, and
19348–19350 created a **separate, parked** namespace. The fact now says so inside
the same parenthesis.

#### 1.1c Coverage: 23 of 33 sessions observed, 10 unobserved [Q-1, Q-7]

Union across all **four** lanes (v1 `.cache/chains` 07-27; chains_v2 07-27→07-31;
intraday 15 sessions; Schwab 14 capture dates) = **23 of the 33** sessions.
**Run-verified.** The **10** that carry none:

> 2026-08-03, 08-04, 08-05, 08-06, 08-10, 08-11, 08-21, **08-31**, **09-01**,
> **09-04**

Three matter, unchanged from Revision 5: **2026-09-04** is the window maximum on
both close (230.36) and intraday high (234.76) and **no lane captured this
contract that day** (no Schwab receipt; the intraday snapshots hold only the
2026-10-16 expiration); **2026-08-31** and **2026-09-01** carry committed Schwab
receipts recording an authentication failure, so they are *known-missing*.

**Row census across all four lanes:** 1 (v1) + 5 (chains_v2) + 66 (intraday) +
14 (Schwab) = **86 in-window rows**; **84 off-lane quotes** (excluding the v1
registered mark and the chains_v2 duplicate of it). **0 of 86 reach 1,841.30.**
Q's exhaustive search — 48,758 cache parquets with all 2,542 NVDA files opened,
523 structured files, every `.md`/`.txt`, every `.db`/`.sqlite`/`.duckdb`/
`.feather`/`.pkl` — found **no fifth lane**, and confirmed `.cache` in the ops
checkout is a **symlink** to the primary checkout's, so all three trees share one
cache and there is no second cache to miss.

#### 1.1d The 21-DTE value is provider-dependent [P-6]

Both off-lane sources captured the 2026-08-28 pre-close seconds apart and
disagree:

| Lane | bid | proceeds | P&L | % of entry | receipt `captured_at_utc` |
|---|---|---|---|---|---|
| Schwab pre-close | 5.55 | 548.35 | −372.30 | −40.44% | `2026-08-28T19:45:08.089405Z` |
| Intraday preclose | 5.50 | 543.35 | −377.30 | −40.98% | `2026-08-28T19:45:10.679603Z` |

Rev 4 gave 548.35 as *the* value and built the outage-cost arithmetic on it. The
fact now gives both and describes the cost as **provider-dependent within the
543.35–548.35 band**. *(Note: P reported the two captures as 21 s apart; the
**receipts** are 2.6 s apart — the 21 s figure compares a receipt timestamp to
the quote timestamp inside the Schwab parquet, `19:45:31`. Both framings are
defensible; the fact says only "seconds apart".)* The fact also flags that the
21-DTE figures are proceeds **net** of the 0.65 commission while the expiration
intrinsic is **gross**.

#### The twelve above-220 closes, reproduced [M-5]

Rev 3's fact promised "the closes are reproduced in the drafting record" while
the record named only four of twelve. All twelve, Run-verified *(cache)* from
`.cache/underlying_ohlcv/NVDA.parquet` (2,437 rows; durable anchor is the
`facts.log` `DATA_PULL_OHLCV 2026-09-15` entry recording `NVDA rows=2437` at that
path — its sha256 `c4c36936…` is bound nowhere in the repo, so the fact cites the
`DATA_PULL_OHLCV` anchor instead [M-10]):

| | | | | | |
|---|---|---|---|---|---|
| 08-07 **223.96** | 08-12 **224.09** | 08-13 **225.30** | 08-14 **225.16** | 08-17 **225.01** | 08-27 **227.98** |
| 08-31 **220.78** | 09-02 **224.41** | 09-03 **228.45** | 09-04 **230.36** | 09-08 **225.73** | 09-09 **223.67** |

**Window definition [M-11]:** 2026-07-27 → 2026-09-10 **inclusive of both
endpoint sessions** = **33** sessions, 12 closes above 220, 21 highs above 220.
Strictly between: 31 / 12 / 20. The fact now says "inclusive of both endpoint
sessions" so the denominator cannot be misread.

**The Black-Scholes inference from round 2 is withdrawn [M-12].** It modelled
16.4–17.7 at the intraday highs; the real quotes bracket that peak at **11.70
(09-03)** and **8.55 (09-08)** — the model overstated by ~45%. It was correctly
labelled `Inference` and correctly kept out of the fact; it is now superseded by
measurement and plays no part in Revision 4.

### 1.2 Why the registered exits could not be evaluated

Both registered exits require an H6 watch receipt, and the H6 evaluator rebuilds
features from the **v1 canonical chain cache at `.cache/chains`**, whose last
session for every name is 2026-07-27 (OD-2). Naming the directory rather than
"the exact-session ThetaData chain" is the Q-2 fix: the schema-v2 namespace is
*also* an exact-session ThetaData chain and does hold this contract through
07-31. That is a statement about **one lane**. Revision 3 generalised it into a
claim about all evidence; Revision 4 fixed that and then generalised the
**Schwab lane's** maximum the same way. Revision 5 keeps the lane-scoped
version, which is both true and sufficient — no registered-lane observation
exists after 2026-07-27, so no receipt could be produced, so neither exit could
fire — and states the off-lane evidence as a **union over all three off-lane
sources** — 84 quotes, 23 of 33 sessions observed — with its coverage gaps
named. The recurring failure was promoting a
per-lane fact to a claim about the record; the fix is to say which lane, every
time.

### 1.3 The three options — corrected [M, Q4]

The owner has selected none of these. **Revision 3 misdescribed (b) and thereby
undersold (c); that is corrected here, and it changes the trade-off.**

**(a) Let it expire; append a disclosure fact.** Exit columns stay blank; the
fact records the entry, the lane-scoped reason neither exit fired, the 84
off-lane observations across three lanes with what they show, the two
registered-lane marks, and a
stated **disclosure-only** valuation at expiration intrinsic. H6 stays
`INSUFFICIENT_SAMPLE` at n = 0. *The drafting agent's reason for recommending
it*, recorded here and not in the fact: it requires no invention. It is not pure
disclosure — it adopts one convention, the expiration-intrinsic valuation,
because seq 6 registers no expiry handling at all, and the fact says so.

**(b) Record a late `time_21_dte` close at a reconstructed mark.** *Revision 3
said "none for 2026-08-28 can be produced". That was wrong.* The **data** for
2026-08-28 exists, with a committed `status: ok` receipt and a verified parquet
hash, and it gives a defensible number: bid 5.55 → 548.35 proceeds, −372.30.
What is missing is not evidence but an **evaluator**: no H6 code reads the Schwab
lane (`grep -ci schwab options_researcher/h6_watch.py` → 0), so no *H6 watch
receipt* — the artifact the registration requires an exit to cite — was or can be
produced for that session. So (b) still means booking a completed position
against an 8-completed bar from a lane the registration never named, which is the
`A2_ENTRY_CONVENTION_CORRECTION_V1` (`facts.log:19511`) shape. But the honest
statement of the objection is *governance*, not *absence of data*.

**(c) Amend H6 prospectively onto a Schwab-lane evaluator — more live than
Revision 3 presented.** Revision 3 treated this as speculative engineering. In
fact the **data lane already exists and is already committed**: 14 captures of
this contract, receipts on `main`, hashes verified, a documented gap-aware
capture programme (two sessions carry honest OAuth-failure receipts, one has
none). What is missing is only the evaluator wiring. That materially lowers the
cost of (c) relative to how Revision 3 described it. It remains prospective by
construction — it does **not** rescue H6-0001, so the (a) disclosure is still
needed either way — and it would want its own feasibility computation against the
2026-07-24 gate. **Choosing (a) does not foreclose (c); the owner should re-read
this section before choosing.**

### 1.4 Draft fact text — Packet 1 (Revision 6.1 — unchanged by 6.2)

Key: `H6_0001_UNMARKED_EXPIRY`. **Four** substitution slots, all angle-bracketed
and all now value-validated by the guard (P-7):
closing price, source, evidence label (constrained to exactly `Official-source`
or `Vendor-source`), and intrinsic value. Intrinsic =
`max(0, close − 220) × 100 × 1`. None pre-filled.

> H6_0001_UNMARKED_EXPIRY 2026-09-18: H6-0001 reached its 2026-09-18
> expiration with no exit ever executed. This fact is appended only after that
> date has passed; the append command refuses to run before 2026-09-19 00:00
> America/New_York. Provenance: agent-drafted 2026-09-15 as option (a) of the
> three-option disposition packet at
> reports/2026-09-15-audit-edge-verdict-and-loose-ends.md section 7 (drafting
> record reports/2026-09-15-audit/H-owner-fact-packets.md, Revision 6).
> Independent adversarial review rounds 1 to 6, 2026-09-15; receipts
> reports/2026-09-15-audit/J-fact-packets-adversarial-review.md (Revision 1
> text), reports/2026-09-15-audit/L-fact-packets-adversarial-review-round2.md
> (Revision 2 text),
> reports/2026-09-15-audit/M-fact-packets-adversarial-review-round3.md
> (Revision 3 text),
> reports/2026-09-15-audit/P-fact-packets-adversarial-review-round4.md
> (Revision 4 text),
> reports/2026-09-15-audit/Q-fact-packets-adversarial-review-round5.md
> (Revision 5 text) and
> reports/2026-09-15-audit/R-fact-packets-adversarial-review-round6.md (this
> exact text). The owner approves this exact text by reading it and running
> the append themselves; that act is both the approval required by
> .claude/rules/ledger.md and the ratification of option (a). No agent
> recorded an approval on the owner behalf, and none is claimed. Options (b)
> record a late time_21_dte close at a reconstructed mark and (c) amend H6
> prospectively onto a Schwab-lane evaluator were drafted alongside (a) and
> are not adopted by this append. The reasons the drafting agent gave for
> preferring (a) are in the drafting record and are not attributed to the
> owner. WHAT HAPPENED (Repo-verified 2026-09-15): H6-0001, NVDA 220 strike
> call, expiration 2026-09-18, 1 contract, entered 2026-07-13 at 920.65 USD
> premium; that is a 9.20 USD per-share ask on 100 shares plus 0.65 USD
> commission (arithmetic). Entry receipt reports/h6_forward/2026-07-13.json
> receipt_hash
> cc8ccd80d8fdd4712d0e7fceada160c60dec21341f3bb02a823e9f29e2f2e8c0; book row
> in data/positions/h6_positions.csv. WHY THE REGISTERED EXITS COULD NOT BE
> EVALUATED (Repo-verified): the exits registered at experiments.jsonl seq 6
> are, in substance and with plus and percent spelled out for shell safety,
> close at 21 DTE at conservative fills OR take-profit at plus 100 percent of
> premium, whichever first, with NO stop-loss. Seq 6 also registers a verdict
> rule of 8 completed positions and, separately, a hard kill of 3 consecutive
> calendar months each realizing the full monthly cap as losses; the hard kill
> is not an exit and could not have fired on a single position. The 21 DTE
> date for a 2026-09-18 expiration is 2026-08-28 (arithmetic). The plus 100
> percent take-profit requires exit proceeds of at least 1841.30 USD, which
> under the registered fill model at options_researcher/h6_watch.py lines 440
> to 446 - conservative sell at the bid less the 1 percent SLIPPAGE_HAIRCUT
> floored to the cent, less the 0.65 USD COMMISSION_PER_CONTRACT - is a raw
> bid of about 18.61 USD per share (arithmetic on the 920.65 USD entry cost; 2
> times 920.65 divided by 100 is 18.413, and the conservative fill lifts the
> required bid above that). Both registered exits require an H6 watch receipt,
> and the H6 evaluator rebuilds features from the exact-session ThetaData
> chain. The canonical chain cache ends 2026-07-27 across all names - recorded
> as owner decision OD-2 at facts.log line 19347 (P1_1_PROVIDER_CLOSEOUT
> 2026-07-31: the final canonical chain edge remains 2026-07-27;
> decision-authoritative consumers must fail closed beyond exact cached
> coverage; that decision governs the v1 canonical cache, and facts.log lines
> 19348 to 19350 later approved a separate schema-v2 namespace reaching
> 2026-07-31, which is parked and which no H6 code reads), and re-verified
> against the cache on 2026-09-15 - so no H6 receipt for any session after
> 2026-07-27 can exist. The last H6 watch receipt is
> reports/h6_forward/2026-07-27.json (receipt_hash
> c4b3138dd87053c7bf7b254b236df55b2304b9a5ebfbe056ed8e4739ac23e464), which
> records H6-0001 as action HOLD, dte 53, mark-to-market pnl minus 441.30 USD,
> proceeds 479.35 USD, reason no_exit_trigger, and scores the book at
> completed_positions 0, verdict INSUFFICIENT_SAMPLE, reason requires 8
> completed positions. Minus 441.30 USD is minus 47.93 percent of the 920.65
> USD entry (arithmetic, not a receipt field). WHAT IS AND IS NOT OBSERVED: no
> observation on the registered H6 mark lane - the v1 canonical chain cache at
> .cache/chains, which is the only chain directory the H6 evaluator reads
> (options_researcher/h6_watch.py line 951) - exists for this contract after
> 2026-07-27, which is why neither registered exit could be evaluated. A
> separate owner-approved ThetaData schema-v2 namespace does hold four further
> exact-session chains, through 2026-07-31; it is described below, it is
> parked and excluded from verdict eligibility, and no H6 code reads it, so it
> does not change that conclusion. Off that lane the repository holds three
> further, non-registered observation lanes for this exact contract. First,
> Schwab pre-close captures on 14 capture dates between 2026-08-14 and
> 2026-09-10, each with a committed receipt under reports/schwab_chains/ whose
> names.NVDA status is ok and whose recorded sha256 matches the corresponding
> .cache/schwab_chains parquet on disk (all 14 re-verified on disk
> 2026-09-15). One of those 14 capture dates, 2026-09-07, is a market holiday
> and its row carries a null timestamp and sentinel greeks (iv minus 9.99,
> delta minus 999), so it is an artifact rather than a session; the other 13
> are trading sessions with real timestamps near 19:45 UTC, the single
> exception being 2026-08-19 at 19:49 UTC. Second, intraday chain captures at
> about 09:31, 09:35, 11:00, 13:00 and 15:45 New York time on 15 sessions
> between 2026-08-07 and 2026-09-03, giving 66 observations of this contract,
> each with a committed receipt under reports/intraday_capture/ recording
> names.NVDA status ok and the chain cache path. Those intraday receipts bind
> no sha256, so they are a weaker evidentiary artifact than the Schwab
> receipts, and that difference is stated rather than left for a reader to
> discover. Third, the ThetaData schema-v2 side-by-side backfill namespace
> .cache/chains_v2/od1-2026-08-01, approved by the owner at facts.log lines
> 19348 to 19350 and covering sessions through 2026-07-31, which holds an
> exact-session EOD chain for this contract on 2026-07-27, 07-28, 07-29, 07-30
> and 07-31 at bids of 4.85, 4.80, 3.25, 4.05 and 5.40. Each of those five is
> bound by a sha256 in that namespace _meta/chain_manifest.txt and by a
> per-session attestation, and the read-only audit
> reports/thetadata_v2/2026-08-02-od1-full-audit.md records PASS WITH WARNINGS
> with NVDA not quarantined; all five sha256 were re-verified on disk
> 2026-09-15. That namespace is parked and excluded from verdict eligibility
> by the owner ruling of 2026-08-24, and it is cited here as descriptive
> evidence only, never as a mark source. Taking all four lanes together, 23 of
> the 33 sessions in the window carry at least one observation of this
> contract. Run-verified 2026-09-15; every observation, with its bid and ask,
> its receipt path and, where one exists, its parquet hash, is tabulated in
> the drafting record. None of these off-lane sources is a registered H6 mark
> source; no H6 evaluator exists on the Schwab, intraday or schema-v2 lanes,
> so no receipt was or could be produced under the registered rules and no
> exit is booked from any of them. They are recorded here so that no reader
> concludes the window is evidentially empty. WHAT THOSE OBSERVATIONS SHOW
> (Run-verified 2026-09-15, arithmetic under the registered fill model): on
> the observed pre-close and intraday quotes the plus 100 percent take-profit
> never fired. Across all 84 observed quotes on the three off-lane sources, 66
> intraday, 14 Schwab pre-close and 4 schema-v2 sessions after the canonical
> edge, not one reaches the 1841.30 USD of proceeds the rule requires. The
> best bid observed anywhere is 15.05 on 2026-08-14 at 09:31 New York time, on
> the intraday lane, which is 1488.35 USD of registered conservative-fill
> proceeds - 80.8 percent of the trigger, a gain of plus 61.66 percent against
> a required plus 100 percent. Fifteen of the 66 intraday observations exceed
> the best Schwab pre-close bid, which is 13.50 on 2026-08-14 (1335.35 USD,
> 72.5 percent). On the 2026-08-28 21 DTE date the two lanes captured the
> pre-close seconds apart and disagree slightly: the Schwab capture quotes a
> bid of 5.55, which is 548.35 USD of proceeds and a loss of 372.30 USD, minus
> 40.44 percent of the entry, and the intraday capture of the same session
> quotes 5.50, which is 543.35 USD and a loss of 377.30 USD, minus 40.98
> percent. THESE ARE THE QUOTES THAT WERE CAPTURED: 10 of the 33 sessions in
> the window carry no observation of this contract on any lane - 2026-08-03,
> 08-04, 08-05, 08-06, 08-10, 08-11, 08-21, 08-31, 09-01 and 09-04. Three of
> those matter. 2026-09-04 is the window maximum for the underlying on both
> close and intraday high; it has no Schwab receipt at all, and its intraday
> captures are unobserved for this contract because the intraday chain had
> rolled to the 2026-10-16 monthly expiration from that session onward.
> 2026-08-31 and 2026-09-01 carry committed Schwab receipts recording an
> authentication failure, so they are known-missing rather than merely absent.
> Nothing is asserted here about what the contract was worth on those 10
> sessions. The outage was therefore not costless, and its cost on the
> observed evidence is quantifiable rather than unknown: had the registered
> time close been evaluable on 2026-08-28 it would have valued the position at
> 548.35 USD on the Schwab capture or 543.35 USD on the intraday capture,
> rather than at the expiration value stated below. The cost of the outage on
> this position is therefore that 21 DTE value minus the expiration intrinsic
> value, which is provider-dependent within the 543.35 to 548.35 USD band
> (arithmetic; the 21 DTE figures are proceeds net of the 0.65 USD commission,
> while the expiration intrinsic below is gross). For underlying context only:
> NVDA closed above the 220 strike on 12 of the 33 sessions in the window
> 2026-07-27 to 2026-09-10 inclusive of both endpoint sessions, with a maximum
> close of 230.36 USD and a maximum intraday high of 234.76 USD, both on
> 2026-09-04 (Run-verified 2026-09-15 from the cache file
> .cache/underlying_ohlcv/NVDA.parquet, which is gitignored; its durable
> anchor is the facts.log DATA_PULL_OHLCV 2026-09-15 entry recording NVDA
> rows=2437 at that path, and all 12 closes are reproduced in the drafting
> record). The position is orphaned on the registered lane by the
> data-provider exit: neither registered exit could be evaluated at all under
> the rules as registered, and this fact does not claim the outage was
> costless. LAST VERIFIABLE MARK (Run-verified 2026-09-15): the Schwab
> pre-close capture of 2026-09-10 quotes the NVDA 220 call expiring 2026-09-18
> at bid 3.75 / ask 3.80, delta 0.463, iv 0.33917, open interest 43021, quote
> timestamp 2026-09-10T19:45:33.824Z. Session receipt
> reports/schwab_chains/2026-09-10/preclose.json binds names.NVDA to
> .cache/schwab_chains/NVDA_2026-09-10.parquet at sha256
> 9df5291708fef0d0a6d6485fe5489a793befd9ef905654c62aebfd6f0e542a0f with status
> ok, and its manifest_hash
> 4a4d69702261018660d5ae41734b2086f181c51588397cb7904ff841016c4d63 matches
> reports/schwab_chains/2026-09-10/manifest.json, where files.NVDA carries the
> same sha256; both re-verified on disk 2026-09-15. The mid of 3.775 implies a
> mark of 377.50 USD against the 920.65 USD entry, minus 543.15 USD, minus
> 58.996 percent (arithmetic, not a receipt field), before any exit cost. This
> is a Schwab-lane mark and is NOT a registered H6 mark source; it is recorded
> as the last verifiable observation, never as a fill. DISPOSITION AT
> EXPIRATION (NOT a registered exit): the position was held to its 2026-09-18
> expiration with no exit ever executed. For disclosure purposes only - this
> valuation is recorded in this fact and nowhere else; no book row, receipt,
> or scoreboard carries it - and as a valuation convention adopted by this
> fact and by nothing earlier (Assumption, stated so, because
> experiments.jsonl seq 6 registers no expiry handling at all), the position
> is valued at expiration intrinsic value, defined as max(0, official closing
> price minus 220) times 100 times 1 contract. This is a paper valuation
> convention, not a claim about contract settlement: a listed NVDA call is
> physically settled into 100 shares if exercised, the auto-exercise decision
> belongs to the OCC and not to this fact, and no exercise, assignment, or
> share position is recorded here. NVDA official closing price 2026-09-18:
> <closing price as a number> USD. Source of that closing price: <name the
> source>. Evidence label for that source, which must be exactly one of
> Official-source or Vendor-source: <Official-source or Vendor-source>. Use
> Official-source only for an exchange-published or otherwise official closing
> price, for example the Nasdaq official closing price, and Vendor-source for
> a vendor feed such as the Yahoo EOD path used by
> data.underlying_closes.fetch_underlying_eod_yahoo. Intrinsic value of one
> 220 strike call at that closing price: <intrinsic value as a number> USD
> (equals max(0, closing price minus 220) times 100 times 1, arithmetic). BOOK
> ROW: data/positions/h6_positions.csv row H6-0001 keeps exit_date,
> exit_proceeds, exit_reason and exit_receipt_hash BLANK and is not written by
> this fact. That is deliberate and is what keeps H6 at n equals 0 completed
> positions: the H6 scorer counts completed rows off those columns. Anyone who
> later fills them converts this disclosure into the reconstructed close that
> option (b) would have recorded, which this append does not adopt. STATUS OF
> H6: unchanged. H6 remains INSUFFICIENT_SAMPLE with n equals 0 completed
> positions under the registered rules, because a valuation at expiration is
> not the registered time close at 21 DTE and is not counted as one. The
> registered bar stays 8 completed positions (experiments.jsonl seq 6;
> config.py H6_MIN_COMPLETED_POSITIONS equals 8, Repo-verified). NO
> RETROACTIVE RULE CHANGE: this fact amends nothing, changes no registered
> exit, and creates no precedent for booking a reconstructed close from a
> quote. The one convention it does adopt is the expiration-intrinsic
> valuation stated above, which is prospective-neutral: it values a row the
> registered exits could not reach and does not make that row a completed
> position. The prospective amendment at experiments.jsonl seq 22 (H6_KILL_V2,
> effective for entries on or after 2026-08-03) is untouched and does not
> apply to this row. Registration ref: experiments.jsonl seq 6 (trial_intent,
> hypothesis_id H6, record_hash
> 5d813b8fe0e89f2d04fe41c9b16561e2374ff873d784a3cd9f2c91e4fe52f3cf), amendment
> seq 22 (record_hash
> 4c552641d5a56f96d6e2c12904e7b20467a56bd1c7804d9de18969a3bb548b04). Recording
> note: appended to facts.log per the H10A_RESULT precedent (facts.log line
> 19413) and the METRIC_CORRECTION provenance template (facts.log line 19346).
> facts.log is append-only but not hash-chained and is advisory context, never
> verdict-feeding (ledger/README.md); this fact is descriptive only and feeds
> no verdict.

**Owner ratification: ______**

### 1.5 The append command — Packet 1 (guarded)

Complete the five-step sequence in "Where to append from" first. Then substitute
the four slots — **digits, letters, spaces, dots, slashes, hyphens, colons
only** — and run:

```sh
uv run python -c 'import sys, pathlib, subprocess, hashlib, datetime, zoneinfo, re
from research.facts import append_fact
# ---- the ONLY tree on main today; see the packet section on where to append from ----
BASE = pathlib.Path("/Users/carsynstephenson/options-validator-ops/ledger")
KEY = "H6_0001_UNMARKED_EXPIRY"
TEXT = "H6_0001_UNMARKED_EXPIRY 2026-09-18: H6-0001 reached its 2026-09-18 expiration with no exit ever executed. This fact is appended only after that date has passed; the append command refuses to run before 2026-09-19 00:00 America/New_York. Provenance: agent-drafted 2026-09-15 as option (a) of the three-option disposition packet at reports/2026-09-15-audit-edge-verdict-and-loose-ends.md section 7 (drafting record reports/2026-09-15-audit/H-owner-fact-packets.md, Revision 6). Independent adversarial review rounds 1 to 6, 2026-09-15; receipts reports/2026-09-15-audit/J-fact-packets-adversarial-review.md (Revision 1 text), reports/2026-09-15-audit/L-fact-packets-adversarial-review-round2.md (Revision 2 text), reports/2026-09-15-audit/M-fact-packets-adversarial-review-round3.md (Revision 3 text), reports/2026-09-15-audit/P-fact-packets-adversarial-review-round4.md (Revision 4 text), reports/2026-09-15-audit/Q-fact-packets-adversarial-review-round5.md (Revision 5 text) and reports/2026-09-15-audit/R-fact-packets-adversarial-review-round6.md (this exact text). The owner approves this exact text by reading it and running the append themselves; that act is both the approval required by .claude/rules/ledger.md and the ratification of option (a). No agent recorded an approval on the owner behalf, and none is claimed. Options (b) record a late time_21_dte close at a reconstructed mark and (c) amend H6 prospectively onto a Schwab-lane evaluator were drafted alongside (a) and are not adopted by this append. The reasons the drafting agent gave for preferring (a) are in the drafting record and are not attributed to the owner. WHAT HAPPENED (Repo-verified 2026-09-15): H6-0001, NVDA 220 strike call, expiration 2026-09-18, 1 contract, entered 2026-07-13 at 920.65 USD premium; that is a 9.20 USD per-share ask on 100 shares plus 0.65 USD commission (arithmetic). Entry receipt reports/h6_forward/2026-07-13.json receipt_hash cc8ccd80d8fdd4712d0e7fceada160c60dec21341f3bb02a823e9f29e2f2e8c0; book row in data/positions/h6_positions.csv. WHY THE REGISTERED EXITS COULD NOT BE EVALUATED (Repo-verified): the exits registered at experiments.jsonl seq 6 are, in substance and with plus and percent spelled out for shell safety, close at 21 DTE at conservative fills OR take-profit at plus 100 percent of premium, whichever first, with NO stop-loss. Seq 6 also registers a verdict rule of 8 completed positions and, separately, a hard kill of 3 consecutive calendar months each realizing the full monthly cap as losses; the hard kill is not an exit and could not have fired on a single position. The 21 DTE date for a 2026-09-18 expiration is 2026-08-28 (arithmetic). The plus 100 percent take-profit requires exit proceeds of at least 1841.30 USD, which under the registered fill model at options_researcher/h6_watch.py lines 440 to 446 - conservative sell at the bid less the 1 percent SLIPPAGE_HAIRCUT floored to the cent, less the 0.65 USD COMMISSION_PER_CONTRACT - is a raw bid of about 18.61 USD per share (arithmetic on the 920.65 USD entry cost; 2 times 920.65 divided by 100 is 18.413, and the conservative fill lifts the required bid above that). Both registered exits require an H6 watch receipt, and the H6 evaluator rebuilds features from the exact-session ThetaData chain. The canonical chain cache ends 2026-07-27 across all names - recorded as owner decision OD-2 at facts.log line 19347 (P1_1_PROVIDER_CLOSEOUT 2026-07-31: the final canonical chain edge remains 2026-07-27; decision-authoritative consumers must fail closed beyond exact cached coverage; that decision governs the v1 canonical cache, and facts.log lines 19348 to 19350 later approved a separate schema-v2 namespace reaching 2026-07-31, which is parked and which no H6 code reads), and re-verified against the cache on 2026-09-15 - so no H6 receipt for any session after 2026-07-27 can exist. The last H6 watch receipt is reports/h6_forward/2026-07-27.json (receipt_hash c4b3138dd87053c7bf7b254b236df55b2304b9a5ebfbe056ed8e4739ac23e464), which records H6-0001 as action HOLD, dte 53, mark-to-market pnl minus 441.30 USD, proceeds 479.35 USD, reason no_exit_trigger, and scores the book at completed_positions 0, verdict INSUFFICIENT_SAMPLE, reason requires 8 completed positions. Minus 441.30 USD is minus 47.93 percent of the 920.65 USD entry (arithmetic, not a receipt field). WHAT IS AND IS NOT OBSERVED: no observation on the registered H6 mark lane - the v1 canonical chain cache at .cache/chains, which is the only chain directory the H6 evaluator reads (options_researcher/h6_watch.py line 951) - exists for this contract after 2026-07-27, which is why neither registered exit could be evaluated. A separate owner-approved ThetaData schema-v2 namespace does hold four further exact-session chains, through 2026-07-31; it is described below, it is parked and excluded from verdict eligibility, and no H6 code reads it, so it does not change that conclusion. Off that lane the repository holds three further, non-registered observation lanes for this exact contract. First, Schwab pre-close captures on 14 capture dates between 2026-08-14 and 2026-09-10, each with a committed receipt under reports/schwab_chains/ whose names.NVDA status is ok and whose recorded sha256 matches the corresponding .cache/schwab_chains parquet on disk (all 14 re-verified on disk 2026-09-15). One of those 14 capture dates, 2026-09-07, is a market holiday and its row carries a null timestamp and sentinel greeks (iv minus 9.99, delta minus 999), so it is an artifact rather than a session; the other 13 are trading sessions with real timestamps near 19:45 UTC, the single exception being 2026-08-19 at 19:49 UTC. Second, intraday chain captures at about 09:31, 09:35, 11:00, 13:00 and 15:45 New York time on 15 sessions between 2026-08-07 and 2026-09-03, giving 66 observations of this contract, each with a committed receipt under reports/intraday_capture/ recording names.NVDA status ok and the chain cache path. Those intraday receipts bind no sha256, so they are a weaker evidentiary artifact than the Schwab receipts, and that difference is stated rather than left for a reader to discover. Third, the ThetaData schema-v2 side-by-side backfill namespace .cache/chains_v2/od1-2026-08-01, approved by the owner at facts.log lines 19348 to 19350 and covering sessions through 2026-07-31, which holds an exact-session EOD chain for this contract on 2026-07-27, 07-28, 07-29, 07-30 and 07-31 at bids of 4.85, 4.80, 3.25, 4.05 and 5.40. Each of those five is bound by a sha256 in that namespace _meta/chain_manifest.txt and by a per-session attestation, and the read-only audit reports/thetadata_v2/2026-08-02-od1-full-audit.md records PASS WITH WARNINGS with NVDA not quarantined; all five sha256 were re-verified on disk 2026-09-15. That namespace is parked and excluded from verdict eligibility by the owner ruling of 2026-08-24, and it is cited here as descriptive evidence only, never as a mark source. Taking all four lanes together, 23 of the 33 sessions in the window carry at least one observation of this contract. Run-verified 2026-09-15; every observation, with its bid and ask, its receipt path and, where one exists, its parquet hash, is tabulated in the drafting record. None of these off-lane sources is a registered H6 mark source; no H6 evaluator exists on the Schwab, intraday or schema-v2 lanes, so no receipt was or could be produced under the registered rules and no exit is booked from any of them. They are recorded here so that no reader concludes the window is evidentially empty. WHAT THOSE OBSERVATIONS SHOW (Run-verified 2026-09-15, arithmetic under the registered fill model): on the observed pre-close and intraday quotes the plus 100 percent take-profit never fired. Across all 84 observed quotes on the three off-lane sources, 66 intraday, 14 Schwab pre-close and 4 schema-v2 sessions after the canonical edge, not one reaches the 1841.30 USD of proceeds the rule requires. The best bid observed anywhere is 15.05 on 2026-08-14 at 09:31 New York time, on the intraday lane, which is 1488.35 USD of registered conservative-fill proceeds - 80.8 percent of the trigger, a gain of plus 61.66 percent against a required plus 100 percent. Fifteen of the 66 intraday observations exceed the best Schwab pre-close bid, which is 13.50 on 2026-08-14 (1335.35 USD, 72.5 percent). On the 2026-08-28 21 DTE date the two lanes captured the pre-close seconds apart and disagree slightly: the Schwab capture quotes a bid of 5.55, which is 548.35 USD of proceeds and a loss of 372.30 USD, minus 40.44 percent of the entry, and the intraday capture of the same session quotes 5.50, which is 543.35 USD and a loss of 377.30 USD, minus 40.98 percent. THESE ARE THE QUOTES THAT WERE CAPTURED: 10 of the 33 sessions in the window carry no observation of this contract on any lane - 2026-08-03, 08-04, 08-05, 08-06, 08-10, 08-11, 08-21, 08-31, 09-01 and 09-04. Three of those matter. 2026-09-04 is the window maximum for the underlying on both close and intraday high; it has no Schwab receipt at all, and its intraday captures are unobserved for this contract because the intraday chain had rolled to the 2026-10-16 monthly expiration from that session onward. 2026-08-31 and 2026-09-01 carry committed Schwab receipts recording an authentication failure, so they are known-missing rather than merely absent. Nothing is asserted here about what the contract was worth on those 10 sessions. The outage was therefore not costless, and its cost on the observed evidence is quantifiable rather than unknown: had the registered time close been evaluable on 2026-08-28 it would have valued the position at 548.35 USD on the Schwab capture or 543.35 USD on the intraday capture, rather than at the expiration value stated below. The cost of the outage on this position is therefore that 21 DTE value minus the expiration intrinsic value, which is provider-dependent within the 543.35 to 548.35 USD band (arithmetic; the 21 DTE figures are proceeds net of the 0.65 USD commission, while the expiration intrinsic below is gross). For underlying context only: NVDA closed above the 220 strike on 12 of the 33 sessions in the window 2026-07-27 to 2026-09-10 inclusive of both endpoint sessions, with a maximum close of 230.36 USD and a maximum intraday high of 234.76 USD, both on 2026-09-04 (Run-verified 2026-09-15 from the cache file .cache/underlying_ohlcv/NVDA.parquet, which is gitignored; its durable anchor is the facts.log DATA_PULL_OHLCV 2026-09-15 entry recording NVDA rows=2437 at that path, and all 12 closes are reproduced in the drafting record). The position is orphaned on the registered lane by the data-provider exit: neither registered exit could be evaluated at all under the rules as registered, and this fact does not claim the outage was costless. LAST VERIFIABLE MARK (Run-verified 2026-09-15): the Schwab pre-close capture of 2026-09-10 quotes the NVDA 220 call expiring 2026-09-18 at bid 3.75 / ask 3.80, delta 0.463, iv 0.33917, open interest 43021, quote timestamp 2026-09-10T19:45:33.824Z. Session receipt reports/schwab_chains/2026-09-10/preclose.json binds names.NVDA to .cache/schwab_chains/NVDA_2026-09-10.parquet at sha256 9df5291708fef0d0a6d6485fe5489a793befd9ef905654c62aebfd6f0e542a0f with status ok, and its manifest_hash 4a4d69702261018660d5ae41734b2086f181c51588397cb7904ff841016c4d63 matches reports/schwab_chains/2026-09-10/manifest.json, where files.NVDA carries the same sha256; both re-verified on disk 2026-09-15. The mid of 3.775 implies a mark of 377.50 USD against the 920.65 USD entry, minus 543.15 USD, minus 58.996 percent (arithmetic, not a receipt field), before any exit cost. This is a Schwab-lane mark and is NOT a registered H6 mark source; it is recorded as the last verifiable observation, never as a fill. DISPOSITION AT EXPIRATION (NOT a registered exit): the position was held to its 2026-09-18 expiration with no exit ever executed. For disclosure purposes only - this valuation is recorded in this fact and nowhere else; no book row, receipt, or scoreboard carries it - and as a valuation convention adopted by this fact and by nothing earlier (Assumption, stated so, because experiments.jsonl seq 6 registers no expiry handling at all), the position is valued at expiration intrinsic value, defined as max(0, official closing price minus 220) times 100 times 1 contract. This is a paper valuation convention, not a claim about contract settlement: a listed NVDA call is physically settled into 100 shares if exercised, the auto-exercise decision belongs to the OCC and not to this fact, and no exercise, assignment, or share position is recorded here. NVDA official closing price 2026-09-18: <closing price as a number> USD. Source of that closing price: <name the source>. Evidence label for that source, which must be exactly one of Official-source or Vendor-source: <Official-source or Vendor-source>. Use Official-source only for an exchange-published or otherwise official closing price, for example the Nasdaq official closing price, and Vendor-source for a vendor feed such as the Yahoo EOD path used by data.underlying_closes.fetch_underlying_eod_yahoo. Intrinsic value of one 220 strike call at that closing price: <intrinsic value as a number> USD (equals max(0, closing price minus 220) times 100 times 1, arithmetic). BOOK ROW: data/positions/h6_positions.csv row H6-0001 keeps exit_date, exit_proceeds, exit_reason and exit_receipt_hash BLANK and is not written by this fact. That is deliberate and is what keeps H6 at n equals 0 completed positions: the H6 scorer counts completed rows off those columns. Anyone who later fills them converts this disclosure into the reconstructed close that option (b) would have recorded, which this append does not adopt. STATUS OF H6: unchanged. H6 remains INSUFFICIENT_SAMPLE with n equals 0 completed positions under the registered rules, because a valuation at expiration is not the registered time close at 21 DTE and is not counted as one. The registered bar stays 8 completed positions (experiments.jsonl seq 6; config.py H6_MIN_COMPLETED_POSITIONS equals 8, Repo-verified). NO RETROACTIVE RULE CHANGE: this fact amends nothing, changes no registered exit, and creates no precedent for booking a reconstructed close from a quote. The one convention it does adopt is the expiration-intrinsic valuation stated above, which is prospective-neutral: it values a row the registered exits could not reach and does not make that row a completed position. The prospective amendment at experiments.jsonl seq 22 (H6_KILL_V2, effective for entries on or after 2026-08-03) is untouched and does not apply to this row. Registration ref: experiments.jsonl seq 6 (trial_intent, hypothesis_id H6, record_hash 5d813b8fe0e89f2d04fe41c9b16561e2374ff873d784a3cd9f2c91e4fe52f3cf), amendment seq 22 (record_hash 4c552641d5a56f96d6e2c12904e7b20467a56bd1c7804d9de18969a3bb548b04). Recording note: appended to facts.log per the H10A_RESULT precedent (facts.log line 19413) and the METRIC_CORRECTION provenance template (facts.log line 19346). facts.log is append-only but not hash-chained and is advisory context, never verdict-feeding (ledger/README.md); this fact is descriptive only and feeds no verdict."
CITED = ["reports/2026-09-15-audit-edge-verdict-and-loose-ends.md", "reports/2026-09-15-audit/H-owner-fact-packets.md", "reports/2026-09-15-audit/J-fact-packets-adversarial-review.md", "reports/2026-09-15-audit/L-fact-packets-adversarial-review-round2.md", "reports/2026-09-15-audit/M-fact-packets-adversarial-review-round3.md", "reports/2026-09-15-audit/P-fact-packets-adversarial-review-round4.md", "reports/2026-09-15-audit/Q-fact-packets-adversarial-review-round5.md", "reports/2026-09-15-audit/R-fact-packets-adversarial-review-round6.md", "reports/thetadata_v2/2026-08-02-od1-full-audit.md", "tools/fill_haircut_calibration.py", "reports/fill_calibration/2026-08-24-fill-adversity-context.md", "reports/h6_forward/2026-07-13.json", "reports/h6_forward/2026-07-27.json", "reports/schwab_chains/2026-09-10/preclose.json", "reports/schwab_chains/2026-09-10/manifest.json", "data/positions/h6_positions.csv", "options_researcher/h6_watch.py", "ledger/experiments.jsonl", "ledger/README.md", "config.py"]
TREE = BASE.parent
def git(*a):
    r = subprocess.run(["git", "-C", str(TREE)] + list(a), capture_output=True, text=True)
    return r.returncode, r.stdout.strip(), r.stderr.strip()
ET = zoneinfo.ZoneInfo("America/New_York")
NOW = datetime.datetime.now(ET)
if NOW < datetime.datetime(2026, 9, 19, 0, 0, tzinfo=ET):
    sys.exit("REFUSED: this fact states that H6-0001 reached its 2026-09-18 expiration. It is %s in New York, before 2026-09-19 00:00. Nothing was appended." % NOW.isoformat())
mA = re.search(r"NVDA official closing price 2026-09-18: (.*?) USD\. Source of that closing price: (.*?)\. Evidence label for that source, which must be exactly one of Official-source or Vendor-source: (.*?)\. Use Official-source only", TEXT, re.S)
mB = re.search(r"\. Intrinsic value of one 220 strike call at that closing price: (.*?) USD \(equals max\(0, closing price minus 220\)", TEXT, re.S)
if not mA or not mB:
    sys.exit("REFUSED: the four substitution slots could not be located. Nothing was appended.")
close_s, source_s, label_s = mA.group(1), mA.group(2), mA.group(3)
intrinsic_s = mB.group(1)
if "<" in TEXT or ">" in TEXT:
    sys.exit("REFUSED: unsubstituted placeholder in the fact text. Fill the 2026-09-18 closing price, its source, the evidence label and the intrinsic value first. Nothing was appended.")
for nm, v in ((("closing price"), close_s), (("intrinsic value"), intrinsic_s)):
    if not re.fullmatch(r"[0-9]{1,6}\.[0-9]{2}", v):
        sys.exit("REFUSED: %s slot is %r, which is not a plain number with two decimals. Nothing was appended." % (nm, v))
if label_s not in ("Official-source", "Vendor-source"):
    sys.exit("REFUSED: evidence label is %r; it must be exactly Official-source or Vendor-source. Nothing was appended." % label_s)
exp_intr = round(max(0.0, float(close_s) - 220.0) * 100.0, 2)
if abs(exp_intr - float(intrinsic_s)) > 0.005:
    sys.exit("REFUSED: intrinsic %s is not max(0, %s - 220) times 100, which is %.2f. Nothing was appended." % (intrinsic_s, close_s, exp_intr))
OFFICIAL = ("nasdaq", "nyse", "cboe", "occ", "sec")
if label_s == "Official-source" and not any(k in source_s.lower() for k in OFFICIAL):
    sys.exit("REFUSED: source %r is labelled Official-source but names none of Nasdaq, NYSE, Cboe, OCC or SEC. Use Vendor-source, or name the exchange. Nothing was appended." % source_s)
if len(source_s) < 4 or len(source_s) > 120:
    sys.exit("REFUSED: source slot is %r, which is empty or implausibly long. Nothing was appended." % source_s)
SKEL = re.sub(r"(NVDA official closing price 2026-09-18: ).*?( USD\. Source of that closing price: ).*?(\. Evidence label for that source, which must be exactly one of Official-source or Vendor-source: ).*?(\. Use Official-source only)", r"\1<>\2<>\3<>\4", TEXT, flags=re.S)
SKEL = re.sub(r"(\. Intrinsic value of one 220 strike call at that closing price: ).*?( USD \(equals max\(0, closing price minus 220\))", r"\1<>\2", SKEL, flags=re.S)
if hashlib.sha256(SKEL.encode()).hexdigest() != "b157ac976e18c03b45609e1922d515ecaf24d83905cd91eb5f442e0465920062":
    sys.exit("REFUSED: the reviewed prose of this text has been altered outside the substitution slots. Nothing was appended.")
if not TEXT.startswith(KEY):
    sys.exit("REFUSED: dedupe_prefix is not a prefix of the text. Nothing was appended.")
rc, top, _ = git("rev-parse", "--show-toplevel")
if rc != 0:
    sys.exit("REFUSED: %s is not a git checkout. Nothing was appended." % TREE)
_, url, _ = git("remote", "get-url", "origin")
CANON = "github.com/carsynstephenson16-lang/options-validator"
norm = url.strip()
for pre in ("https://", "http://", "ssh://", "git@"):
    if norm.startswith(pre): norm = norm[len(pre):]
norm = norm.replace("github.com:", "github.com/")
if norm.endswith(".git"): norm = norm[:-4]
if norm != CANON:
    sys.exit("REFUSED: origin is %s, not the options-validator remote. Nothing was appended." % url)
_, branch, _ = git("rev-parse", "--abbrev-ref", "HEAD")
if branch != "main":
    sys.exit("REFUSED: %s is on branch %s, not main. Nothing was appended." % (TREE, branch))
frc, _, ferr = git("fetch", "--quiet", "origin", "main")
if frc != 0:
    sys.exit("REFUSED: could not fetch origin/main (%s). Nothing was appended." % ferr)
_, head, _ = git("rev-parse", "HEAD")
_, upstream, _ = git("rev-parse", "origin/main")
if head != upstream:
    sys.exit("REFUSED: HEAD %s is not origin/main %s. Pull first. Nothing was appended." % (head, upstream))
_, porcelain, _ = git("status", "--porcelain")
if porcelain.strip():
    sys.exit("REFUSED: %s is not clean; git status --porcelain must be empty. Outstanding: %s. Nothing was appended." % (TREE, porcelain.splitlines()[:5]))
_, dirty, _ = git("status", "--porcelain", "--", "ledger/")
if dirty:
    sys.exit("REFUSED: ledger/ has uncommitted local changes in %s (%s). Appending on top of an uncommitted divergence of an append-only file is the hazard this guard exists for. Nothing was appended." % (TREE, dirty))
missing = [c for c in CITED if git("cat-file", "-e", "HEAD:%s" % c)[0] != 0]
if missing:
    sys.exit("REFUSED: these paths are cited by this fact but are not committed on main: %s. Land PR 175 on main first. Nothing was appended." % missing)
RESOLVED = (BASE / "facts.log").resolve()
if not RESOLVED.exists():
    sys.exit("REFUSED: %s does not exist. Nothing was appended." % RESOLVED)
count = lambda: sum(1 for _ in RESOLVED.open(encoding="utf-8", errors="replace"))
print("tree:  ", top, "on", branch, "at", head)
print("target:", RESOLVED)
print("lines before:", count())
append_fact(TEXT, base_dir=str(BASE), dedupe_prefix=KEY)
print("appended under", KEY)
print("lines after: ", count())'
```

**Guard behaviour, Run-verified 2026-09-15 against a stubbed `append_fact` (the
real one was never called).** Re-run for Revision 6 against a fresh clean
synthetic tree (`/tmp/r6/work`, on `main`, at its `origin/main`, all cited paths
committed) as well as the real trees. Sixteen scenarios:

| # | Scenario | Tree | Result |
|---|---|---|---|
| 1 | As shipped, today, slots present | ops | **rc 1** — date gate |
| 2 | Slots filled, still 2026-09-15 | ops | **rc 1** — date gate |
| 3 | Date reached, ops tree as it stands | ops | **rc 1** — *"not clean; porcelain must be empty: `['?? reports/intraday_capture/2026-09-15/']`"* |
| 4 | Pointed at the primary checkout | primary | **rc 1** — *"on branch claude/rest-2026-09-09, not main"* |
| 5 | **ACCEPT**: clean, on `main` at `origin/main`, all cited paths committed, `213.40` / Nasdaq / `Official-source` / `0.00` | clean | **rc 0** — prints tree, branch, commit, target, `lines before`, then calls the stub |
| 6 | Blog string labelled `Official-source` | clean | **rc 1** — *"names none of Nasdaq, NYSE, Cboe, OCC or SEC"* |
| 7 | Intrinsic `9999.00` at close `213.40` | clean | **rc 1** — *"is not max(0, 213.40 - 220) times 100, which is 0.00"* |
| 8 | Close `225.00` with intrinsic `0.00` | clean | **rc 1** — *"… which is 500.00"* |
| 9 | **ACCEPT** with an ITM close: `225.00` / `500.00` | clean | **rc 0** — the recomputation agrees |
| 10 | Label `Blog-source` | clean | **rc 1** — whitelist |
| 11 | Prose tampered (`23 of the 33` → `29 of the 33`) | clean | **rc 1** — skeleton hash |
| 12 | **P-9**: origin is a local path, URL check unpatched | clean | **rc 1** — *"origin is /tmp/r6/upstream, not the options-validator remote"* |
| 13 | Packet 2, same clean tree | clean | **rc 0** |
| 14 | Packet 2, prose tampered (`4` → `9 losses`) | clean | **rc 1** — invariant hash |
| 15 | Packet 2, real ops tree | ops | **rc 1** — porcelain |
| 16 | **Q-6**: the newly cited `reports/thetadata_v2/2026-08-02-od1-full-audit.md` removed from `HEAD` | clean | **rc 1** — *"cited by this fact but are not committed on main: `['reports/thetadata_v2/2026-08-02-od1-full-audit.md']`"* |

*For the accept rows only, the URL constant was replaced with a test sentinel
(the synthetic origin is a local path); the URL check itself ran unpatched in
row 12. Every other check ran unmodified, and the real `append_fact` was never
called.*

**The one unrecoverable mistake:** a placeholder or wrong version appended under
this key burns the key forever. Read the text on screen before pressing Return.

The book row's `exit_*` columns are **not** touched by this fact, and the fact
says so itself.

---

## Packet 2 — H9 receipt full-document hash

### 2.1 What was verified

M re-derived every claim in this fact from `main` and found no error; this is the
third independent reproduction. **The text is appendable exactly as written.**

| Claim | Status |
|---|---|
| `shasum -a 256 reports/h9/receipt.json` = `30df74c4e91e0b23c28d7e70391da6d851feb7b21084bf9ab27ae417a63e7a93` | **Run-verified** |
| `git log --format=%h -1 -- reports/h9/receipt.json` = `d91b1ec`, the only commit it has ever had | **Run-verified** |
| Hash excludes `{"trades","trade_log","board","census"}` | Repo-verified, `tools/h9_run_study.py:169-171` |
| The nine sealed keys, and `sha256(canonical_json(nine))` = `5bea2018…` exactly | **Run-verified ×3** |
| `board` and the 16-row `trades` are outside the seal | **Run-verified** |
| `MIN_LOSSES_FOR_VERDICT = 10` | Repo-verified, `config.py:189` |
| **No verifier anywhere**: `grep receipt_hash options_researcher/h9_*.py` → nothing; the only code reference to `reports/h9/receipt.json` is its writer, `tools/h9_run_study.py:28`; nothing in `tests/` reads it | **Run-verified** |
| `canonical_json(full receipt)` **raises** `ValueError: Out of range float values are not JSON compliant: nan` (`board.return_on_economic_max_loss`) — which is why the remedy must be a file-level sha256 | **Run-verified** |

```sh
uv run python -c 'import json
from research.hashing import canonical_json, sha256_hex
r = json.load(open("reports/h9/receipt.json"))
bulk = {"trades", "trade_log", "board", "census"}
body = {k: v for k, v in r.items() if k not in bulk and k != "receipt_hash"}
print(len(body), sorted(body))
print("recomputed:", sha256_hex(canonical_json(body)))
print("recorded  :", r["receipt_hash"])'
```

### 2.2 Draft fact text — Packet 2 (unchanged since Revision 3.1)

**Byte-identical to the text M reviewed and passed.** Its `M` citation is honest
— round 3 changed nothing in it — and its invariant hash is unchanged at
`c837b27e522f0c9c300e3163985a1b0aab7549dc1cde55baa77b1a7b5dfb10f4`.

> H9_RECEIPT_FULL_DOCUMENT_HASH_V1 2026-09-15: coverage fact for the H9
> receipt, adding a full-document hash where the original hash covered only
> part of the document. Agent-drafted 2026-09-15 (drafting record
> reports/2026-09-15-audit/H-owner-fact-packets.md, Revision 3). Independent
> adversarial review rounds 1 to 3, 2026-09-15; receipts
> reports/2026-09-15-audit/J-fact-packets-adversarial-review.md (Revision 1
> text), reports/2026-09-15-audit/L-fact-packets-adversarial-review-round2.md
> (Revision 2 text) and
> reports/2026-09-15-audit/M-fact-packets-adversarial-review-round3.md (this
> exact text). The owner approves this exact text by reading it and running
> the append themselves; that act is both the approval required by
> .claude/rules/ledger.md and the ratification. No agent recorded an approval
> on the owner behalf, and none is claimed. Source:
> reports/2026-09-15-audit/A-evidence-audit.md section 4 item 1 and
> reports/2026-09-15-audit-edge-verdict-and-loose-ends.md section 4 finding 1.
> WHAT THE ORIGINAL HASH SEALED (Run-verified 2026-09-15): the receipt hash
> recorded in the H9 result fact (facts.log line 17892, H9_RESULT 2026-07-18,
> receipt_hash
> 5bea2018fa204b2b3bfc221fee2b43f669ce9ff5b90270515dbc267084df3c06) is
> computed at tools/h9_run_study.py lines 169 to 171, which exclude the bulk
> keys trades, trade_log, board and census before hashing. It therefore
> attests to nine scalar keys only: study, outcome, n_trades,
> no_trade_log_count, secondary_cohort_informational, spec_sha256, code_sha,
> config_hash, cost_model_hash. It does NOT cover the board, which holds
> expectancy per trade plus 290.32 USD, the CI90, and total pnl 4645.20 USD,
> and it does NOT cover the 16-row trades array. Recomputed independently on
> 2026-09-15 by the drafting agent and again by the adversarial reviewer:
> hashing exactly those nine keys reproduces 5bea2018 exactly. WHAT THIS FACT
> ADDS (Run-verified 2026-09-15): the full file reports/h9/receipt.json has
> sha256 30df74c4e91e0b23c28d7e70391da6d851feb7b21084bf9ab27ae417a63e7a93,
> measured with shasum -a 256, at commit d91b1ec, which is the only commit
> that file has ever had (git log --format=%h -1 -- reports/h9/receipt.json
> returns d91b1ec). From this point a reader can verify the full document by
> recomputing this sha256 and comparing; nothing enforces the comparison, as
> stated below. WHAT THIS FACT DOES NOT DO: it changes no number, no board
> value, no trade row, and no verdict. H9 remains INSUFFICIENT_SAMPLE, 16
> trades with 4 losses against a 10-loss bar, and the one authorized H9 run
> remains SPENT; this fact authorizes no rerun, no refetch and no backfill.
> The known-wrong H9 max_drawdown correction at facts.log line 19346
> (METRIC_CORRECTION 2026-07-31: 361.30 USD as recorded, 718.50 USD when the
> 16 trades stored in the H9 receipt are replayed under the zero-anchored
> entry-date-ordered closed_trade_pnl_drawdown definition of commit 5626c3f -
> expressly NOT a daily-NAV or generic chronological drawdown) is unaffected
> and still stands separately. Nothing here promotes the H9 result. WHAT THIS
> FACT DOES NOT PROTECT: no verifier reads either hash. Re-checked 2026-09-15:
> grep receipt_hash options_researcher/h9_*.py returns nothing, and the only
> code reference to reports/h9/receipt.json anywhere in the repository is its
> writer, tools/h9_run_study.py line 28. The sha256 recorded here is a number
> in an advisory log that nothing automatically checks; its value is that a
> future reader can recompute it, not that any tool will refuse on mismatch.
> RECOMMENDED FORWARD PRACTICE, NOT BINDING BY THIS FACT: future studies
> should seal the whole receipt rather than a subset of its keys. This fact
> cannot impose that - facts.log is advisory and never verdict-feeding
> (ledger/README.md) and no code reads this line. Making it binding requires a
> .cursorrules or .claude/rules entry plus a test, which this fact does not
> perform and does not authorize. Implementation constraint recorded for
> whoever does it: research/hashing.py canonical_json sets allow_nan equals
> False and the H9 receipt bulk section contains NaN
> (board.return_on_economic_max_loss), so a canonical-JSON hash of the whole
> object raises ValueError; a whole-receipt seal must therefore be a sha256 of
> the written file bytes, or the writer must stop emitting NaN. Recording
> note: appended to facts.log per the H10A_RESULT (facts.log line 19413),
> A2_ENTRY_CONVENTION_RATIFIED_V1 (facts.log line 19553) and METRIC_CORRECTION
> (facts.log line 19346) precedents. facts.log is append-only but not
> hash-chained and is advisory context, never verdict-feeding
> (ledger/README.md); this fact is descriptive only and feeds no verdict.

**Owner ratification: ______**

### 2.3 The append command — Packet 2

Same five-step sequence. Re-confirm the two bindings first; if either differs
from `30df74c4…` / `d91b1ec`, **do not append** — a change to that file since
2026-09-15 would itself be the finding:

```sh
shasum -a 256 reports/h9/receipt.json
git log --format=%h -1 -- reports/h9/receipt.json
```

```sh
uv run python -c 'import sys, pathlib, subprocess, hashlib, datetime, zoneinfo, re
from research.facts import append_fact
# ---- the ONLY tree on main today; see the packet section on where to append from ----
BASE = pathlib.Path("/Users/carsynstephenson/options-validator-ops/ledger")
KEY = "H9_RECEIPT_FULL_DOCUMENT_HASH_V1"
TEXT = "H9_RECEIPT_FULL_DOCUMENT_HASH_V1 2026-09-15: coverage fact for the H9 receipt, adding a full-document hash where the original hash covered only part of the document. Agent-drafted 2026-09-15 (drafting record reports/2026-09-15-audit/H-owner-fact-packets.md, Revision 3). Independent adversarial review rounds 1 to 3, 2026-09-15; receipts reports/2026-09-15-audit/J-fact-packets-adversarial-review.md (Revision 1 text), reports/2026-09-15-audit/L-fact-packets-adversarial-review-round2.md (Revision 2 text) and reports/2026-09-15-audit/M-fact-packets-adversarial-review-round3.md (this exact text). The owner approves this exact text by reading it and running the append themselves; that act is both the approval required by .claude/rules/ledger.md and the ratification. No agent recorded an approval on the owner behalf, and none is claimed. Source: reports/2026-09-15-audit/A-evidence-audit.md section 4 item 1 and reports/2026-09-15-audit-edge-verdict-and-loose-ends.md section 4 finding 1. WHAT THE ORIGINAL HASH SEALED (Run-verified 2026-09-15): the receipt hash recorded in the H9 result fact (facts.log line 17892, H9_RESULT 2026-07-18, receipt_hash 5bea2018fa204b2b3bfc221fee2b43f669ce9ff5b90270515dbc267084df3c06) is computed at tools/h9_run_study.py lines 169 to 171, which exclude the bulk keys trades, trade_log, board and census before hashing. It therefore attests to nine scalar keys only: study, outcome, n_trades, no_trade_log_count, secondary_cohort_informational, spec_sha256, code_sha, config_hash, cost_model_hash. It does NOT cover the board, which holds expectancy per trade plus 290.32 USD, the CI90, and total pnl 4645.20 USD, and it does NOT cover the 16-row trades array. Recomputed independently on 2026-09-15 by the drafting agent and again by the adversarial reviewer: hashing exactly those nine keys reproduces 5bea2018 exactly. WHAT THIS FACT ADDS (Run-verified 2026-09-15): the full file reports/h9/receipt.json has sha256 30df74c4e91e0b23c28d7e70391da6d851feb7b21084bf9ab27ae417a63e7a93, measured with shasum -a 256, at commit d91b1ec, which is the only commit that file has ever had (git log --format=%h -1 -- reports/h9/receipt.json returns d91b1ec). From this point a reader can verify the full document by recomputing this sha256 and comparing; nothing enforces the comparison, as stated below. WHAT THIS FACT DOES NOT DO: it changes no number, no board value, no trade row, and no verdict. H9 remains INSUFFICIENT_SAMPLE, 16 trades with 4 losses against a 10-loss bar, and the one authorized H9 run remains SPENT; this fact authorizes no rerun, no refetch and no backfill. The known-wrong H9 max_drawdown correction at facts.log line 19346 (METRIC_CORRECTION 2026-07-31: 361.30 USD as recorded, 718.50 USD when the 16 trades stored in the H9 receipt are replayed under the zero-anchored entry-date-ordered closed_trade_pnl_drawdown definition of commit 5626c3f - expressly NOT a daily-NAV or generic chronological drawdown) is unaffected and still stands separately. Nothing here promotes the H9 result. WHAT THIS FACT DOES NOT PROTECT: no verifier reads either hash. Re-checked 2026-09-15: grep receipt_hash options_researcher/h9_*.py returns nothing, and the only code reference to reports/h9/receipt.json anywhere in the repository is its writer, tools/h9_run_study.py line 28. The sha256 recorded here is a number in an advisory log that nothing automatically checks; its value is that a future reader can recompute it, not that any tool will refuse on mismatch. RECOMMENDED FORWARD PRACTICE, NOT BINDING BY THIS FACT: future studies should seal the whole receipt rather than a subset of its keys. This fact cannot impose that - facts.log is advisory and never verdict-feeding (ledger/README.md) and no code reads this line. Making it binding requires a .cursorrules or .claude/rules entry plus a test, which this fact does not perform and does not authorize. Implementation constraint recorded for whoever does it: research/hashing.py canonical_json sets allow_nan equals False and the H9 receipt bulk section contains NaN (board.return_on_economic_max_loss), so a canonical-JSON hash of the whole object raises ValueError; a whole-receipt seal must therefore be a sha256 of the written file bytes, or the writer must stop emitting NaN. Recording note: appended to facts.log per the H10A_RESULT (facts.log line 19413), A2_ENTRY_CONVENTION_RATIFIED_V1 (facts.log line 19553) and METRIC_CORRECTION (facts.log line 19346) precedents. facts.log is append-only but not hash-chained and is advisory context, never verdict-feeding (ledger/README.md); this fact is descriptive only and feeds no verdict."
CITED = ["reports/2026-09-15-audit/A-evidence-audit.md", "reports/2026-09-15-audit-edge-verdict-and-loose-ends.md", "reports/2026-09-15-audit/H-owner-fact-packets.md", "reports/2026-09-15-audit/J-fact-packets-adversarial-review.md", "reports/2026-09-15-audit/L-fact-packets-adversarial-review-round2.md", "reports/2026-09-15-audit/M-fact-packets-adversarial-review-round3.md", "reports/h9/receipt.json", "tools/h9_run_study.py", "research/hashing.py", "ledger/README.md", "config.py"]
TREE = BASE.parent
def git(*a):
    r = subprocess.run(["git", "-C", str(TREE)] + list(a), capture_output=True, text=True)
    return r.returncode, r.stdout.strip(), r.stderr.strip()
SKEL = TEXT
if hashlib.sha256(SKEL.encode()).hexdigest() != "c837b27e522f0c9c300e3163985a1b0aab7549dc1cde55baa77b1a7b5dfb10f4":
    sys.exit("REFUSED: the reviewed prose of this text has been altered outside the substitution slots. Nothing was appended.")
if not TEXT.startswith(KEY):
    sys.exit("REFUSED: dedupe_prefix is not a prefix of the text. Nothing was appended.")
rc, top, _ = git("rev-parse", "--show-toplevel")
if rc != 0:
    sys.exit("REFUSED: %s is not a git checkout. Nothing was appended." % TREE)
_, url, _ = git("remote", "get-url", "origin")
CANON = "github.com/carsynstephenson16-lang/options-validator"
norm = url.strip()
for pre in ("https://", "http://", "ssh://", "git@"):
    if norm.startswith(pre): norm = norm[len(pre):]
norm = norm.replace("github.com:", "github.com/")
if norm.endswith(".git"): norm = norm[:-4]
if norm != CANON:
    sys.exit("REFUSED: origin is %s, not the options-validator remote. Nothing was appended." % url)
_, branch, _ = git("rev-parse", "--abbrev-ref", "HEAD")
if branch != "main":
    sys.exit("REFUSED: %s is on branch %s, not main. Nothing was appended." % (TREE, branch))
frc, _, ferr = git("fetch", "--quiet", "origin", "main")
if frc != 0:
    sys.exit("REFUSED: could not fetch origin/main (%s). Nothing was appended." % ferr)
_, head, _ = git("rev-parse", "HEAD")
_, upstream, _ = git("rev-parse", "origin/main")
if head != upstream:
    sys.exit("REFUSED: HEAD %s is not origin/main %s. Pull first. Nothing was appended." % (head, upstream))
_, porcelain, _ = git("status", "--porcelain")
if porcelain.strip():
    sys.exit("REFUSED: %s is not clean; git status --porcelain must be empty. Outstanding: %s. Nothing was appended." % (TREE, porcelain.splitlines()[:5]))
_, dirty, _ = git("status", "--porcelain", "--", "ledger/")
if dirty:
    sys.exit("REFUSED: ledger/ has uncommitted local changes in %s (%s). Appending on top of an uncommitted divergence of an append-only file is the hazard this guard exists for. Nothing was appended." % (TREE, dirty))
missing = [c for c in CITED if git("cat-file", "-e", "HEAD:%s" % c)[0] != 0]
if missing:
    sys.exit("REFUSED: these paths are cited by this fact but are not committed on main: %s. Land PR 175 on main first. Nothing was appended." % missing)
RESOLVED = (BASE / "facts.log").resolve()
if not RESOLVED.exists():
    sys.exit("REFUSED: %s does not exist. Nothing was appended." % RESOLVED)
count = lambda: sum(1 for _ in RESOLVED.open(encoding="utf-8", errors="replace"))
print("tree:  ", top, "on", branch, "at", head)
print("target:", RESOLVED)
print("lines before:", count())
append_fact(TEXT, base_dir=str(BASE), dedupe_prefix=KEY)
print("appended under", KEY)
print("lines after: ", count())'
```

No slots and no date gate, so the invariant covers the **whole** text
(Run-verified: `4 losses` → `9 losses` refuses, rc 1). All other guard branches
behave exactly as in §1.5.

---

## 3. Claims not verified, or found wrong

1. **Revision 5 listed four observed sessions as unobserved.** 2026-07-28,
   07-29, 07-30 and 07-31 all carry an owner-approved, sha256-attested
   exact-session chain for this contract in `.cache/chains_v2/od1-2026-08-01/`.
   Counts corrected: **23 of 33 observed (was 19), 10 unobserved (was 14), 84
   off-lane quotes on three lanes (was 80 on two), 86 in-window rows on four
   lanes.** [Q-1]
2. **"The exact-session ThetaData chain" was the wrong name for the registered
   lane** — chains_v2 is also an exact-session ThetaData chain. The fact now
   names **`.cache/chains`** and cites `h6_watch.py:951`. [Q-2]
3. **The OD-2 citation read as self-contradicting** three lines from its own
   supersession. A clause now states that OD-2 governs the v1 canonical cache
   and that 19348–19350 approved a separate, parked namespace. [Q-3]
4. **Intraday capture times were given as exact**; three in-window files are
   `T0936`, `T1549`, `T1101`. Now "at about". [Q-4]
5. **Q's own chains_v2 proceeds are wrong on three rows** — 321.35 / 400.35 /
   534.35 should be **320.35 / 399.35 / 533.35** (`adverse_sell` floors). The
   fact quotes only bids, so it is unaffected; §1.1e carries the corrected
   figures. *This is the first round in which the reviewer's arithmetic, rather
   than the packet's, needed correcting.*
6. **Carried and still true:** the guard fixes from round 4 (P-7 value
   validation, P-8 `cat-file`, P-9 exact URL) all verified closed by Q;
   `.claude/rules/ledger.md`'s "chronological value: $718.50" is still wrong on
   `main`; NVDA `210.96` is reproducible via `.cache/underlying_ohlcv/`, not the
   closes receipt; the round-2 Black-Scholes inference stays withdrawn; the
   "append is the approval" wording is accepted-and-noted.
7. **Nothing was appended, nothing was committed, no ledger-writing tool was
   run** in preparing any revision. All guard testing used a local stub; the
   synthetic trees under `/tmp/r5` and `/tmp/r6` are throwaway and deleted.

---

## 4. Revision 6 changelog, keyed to review Q

| ID | Sev | Change |
|---|---|---|
| **Q-1** | BLOCKER | The fact now discloses **three** off-lane lanes, not two. New third clause: the schema-v2 namespace `.cache/chains_v2/od1-2026-08-01`, *"approved by the owner at facts.log lines 19348 to 19350 and covering sessions through 2026-07-31, which holds an exact-session EOD chain for this contract on 2026-07-27, 07-28, 07-29, 07-30 and 07-31 at bids of 4.85, 4.80, 3.25, 4.05 and 5.40"*, each sha256-bound in `_meta/chain_manifest.txt` and per-session attestations, audited at `reports/thetadata_v2/2026-08-02-od1-full-audit.md` with NVDA not quarantined, **"parked and excluded from verdict eligibility by the owner ruling of 2026-08-24 … cited here as descriptive evidence only, never as a mark source."** Counts corrected throughout: **23 of 33**; **84 observed quotes on the three off-lane sources, 66 intraday, 14 Schwab pre-close and 4 schema-v2 sessions after the canonical edge**; unobserved list **10 dates**. All five rows re-derived and sha256-verified (§1.1e). |
| **Q-2** | MUST | Registered lane renamed precisely: *"the v1 canonical chain cache at .cache/chains, which is the only chain directory the H6 evaluator reads (options_researcher/h6_watch.py line 951)"*, plus *"A separate owner-approved ThetaData schema-v2 namespace does hold four further exact-session chains, through 2026-07-31; it is described below, it is parked and excluded from verdict eligibility, and no H6 code reads it, so it does not change that conclusion."* |
| **Q-3** | MUST | Inside the OD-2 parenthesis: *"; that decision governs the v1 canonical cache, and facts.log lines 19348 to 19350 later approved a separate schema-v2 namespace reaching 2026-07-31, which is parked and which no H6 code reads"*. |
| **Q-4** | SHOULD | *"at about 09:31, 09:35, 11:00, 13:00 and 15:45 New York time"*. |
| **Q-5** | NOTE | No change. Q re-verified that **15.05 remains the global maximum over all 86 rows on all four lanes** (chains_v2 max 5.40), and judged "the best bid observed anywhere" defensible inside its scoping paragraph. |
| **Q-6** | NOTE | `reports/thetadata_v2/2026-08-02-od1-full-audit.md` added to both `CITED` lists, so the guard's `cat-file` check covers it. Verified enforceable: removing it from `HEAD` on the synthetic tree → **rc 1** naming exactly that path (dry-run row 16). The `_meta` manifests are gitignored and are cited via the tracked audit report and the `facts.log` lines, the same pattern already used for `DATA_PULL_OHLCV`. |
| **Q-7** | NOTE | §1.1 framing, §1.1c coverage and the row census all corrected, and §1.1e added with the five chains_v2 rows, their paths and their manifest-bound sha256s — so the fact's *"is tabulated in the drafting record"* clause stays true. |
| **Citation carry-forward** | — | Packet 1 → **rounds 1 to 6**, receipts J, L, M, P, Q and **R** (`…/R-fact-packets-adversarial-review-round6.md`, this exact text); new invariant **`b157ac97…`** (the Revision-6 value `7d6c7ed2…` was superseded by the 6.1 wording fix). **Packet 2 unchanged, byte for byte**; citation stays at rounds 1 to 3 with M as "this exact text" — accurate, and re-confirmed by P and Q; hash stays `c837b27e…`. |
| **Correction to Q** | — | Q's chains_v2 proceeds for bids 3.25 / 4.05 / 5.40 are rounded up; the floor-model values are 320.35 / 399.35 / 533.35. Recorded in §3 item 5 and used in §1.1e. |

| **6.1** | — | Coordinator-directed wording fix, 2026-09-15, applied after Revision 6 was cut and before round 6 reviewed it: the residual the drafting agent flagged. **"Neither off-lane source is a registered H6 mark source; no H6 evaluator exists on the Schwab or intraday lanes"** becomes **"None of these off-lane sources is a registered H6 mark source; no H6 evaluator exists on the Schwab, intraday or schema-v2 lanes"** — "neither" was left over from the two-lane Revision 5 and undercounted after Q-1 added the third. Re-verified that the claim holds for the new lane: `grep -ci chains_v2 options_researcher/h6_watch.py` -> **0**. Nothing else in either text changed; the Packet 1 invariant sha256 was recomputed and both guards re-tested. |

| **6.2** | — | **Packet prose only; fact texts unchanged from 6.1; hashes unchanged.** Round-6 receipt `R` returned Packet 1 **READY WITH FIXES, all non-text**. Applied: **R-1** every prose mention of the Packet 1 invariant now reads `b157ac97…`, the unsourced fourth value that appeared in earlier prose (and reproduced no skeleton and no `sha256(TEXT)` for any revision) is deleted everywhere, quoted nowhere, and `7d6c7ed2…` is recorded as the superseded Revision-6 skeleton; **R-3** `tools/fill_haircut_calibration.py` and `reports/fill_calibration/2026-08-24-fill-adversity-context.md` added to Packet 1 `CITED` (both verified tracked on `origin/main`; `CITED` is not part of `TEXT`, so the hash is untouched); **R-4** manifest count corrected to 4,608 entries plus two header lines; **R-5** §1.2, §1.3(a) and the §1.4 heading brought to the four-lane / 23-of-33 / 84-quote framing; **R-6** and **R-7** recorded in §1.1e as flagged-not-rewritten. **R-2 was deliberately not applied** — the reviewer explicitly recommended against cutting a 6.2 of the *fact text* for it, since that would recompute the hash, invalidate `R` as a review of the appended words, and force a round 7 over a sentence that is already true. |

**Hash discipline (R-1).** The **only** authoritative Packet 1 constant is
`b157ac976e18c03b45609e1922d515ecaf24d83905cd91eb5f442e0465920062`, and it is
the value pinned inside the §1.5 command. Superseded values, recorded so the
history is legible and so nobody re-derives them by accident: `836105dd…`
(Revision 5) and `7d6c7ed2…` (Revision 6, superseded by the 6.1 wording fix). A
fourth value appeared in earlier revisions of this packet's prose and
**reproduced nothing** — not any skeleton, not `sha256(TEXT)` for any revision.
It is deleted rather than quoted here, so that no reader can copy it; that it
existed at all is the reason for the rule in the next sentence. **If the prose and the command ever disagree, the
command is authoritative; do not edit the guard constant to match prose.**

Re-verified after this rewrite: both blockquotes are character-identical to the
text their commands pass to `append_fact`; **Packet 1's skeleton hash is
`b157ac97…` and Packet 2's is `c837b27e…`, both unchanged by Revision 6.2, which
touched only packet prose and the two `CITED` lists**; neither text contains
`'`, `"`, `$`, backtick, `!` or a non-ASCII byte; both
`Owner ratification: ______` lines are blank; and every guard branch was
exercised against a stub, never against the real `append_fact`.
