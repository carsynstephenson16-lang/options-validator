# L — Round-2 independent adversarial review of the two ledger fact texts

**Target:** `reports/2026-09-15-audit/H-owner-fact-packets.md`, **Revision 2**.
**Round-1 receipt:** `reports/2026-09-15-audit/J-fact-packets-adversarial-review.md`
(Packet 1 NOT READY, blockers F-1/F-2; Packet 2 READY WITH FIXES).
**Date:** 2026-09-15. **Worktree:** `.tmp/worktrees/audit-0915`, branch
`claude/audit-2026-09-15`.
**Reviewer stance:** show how each rewritten text could be lying, over-claiming,
pre-deciding, or unsafe to append. Not a confirmation pass.

**Nothing was appended. Nothing was committed. No ledger-writing tool was
called.** Both guarded one-liners were executed against a **stubbed**
`append_fact` that only captured its arguments and asserted the prefix
invariant. The packet file was not edited. The only file created is this one.

---

## §0. Verdicts

### Packet 1 — `H6_0001_UNMARKED_EXPIRY` — **NOT READY**

Round 1's two blockers are genuinely closed. Three new blockers replace them,
none of which round 1 looked for:

- **L-1** the fact states in the past tense an event that is **three days in the
  future** ("the position was held to expiration 2026-09-18"), and the guard —
  which checks for angle brackets, the string `USD`, and the prefix — has **no
  date check** at all;
- **L-2** the sentence *"The position was never within reach of the plus 100
  percent take-profit"* is **not supportable and is probably false**. NVDA closed
  **230.36** on 2026-09-04 (intraday high 234.76) and the 220 call was in the
  money for much of late August and early September. A Black-Scholes estimate at
  the observed highs puts the contract at **16.4–17.7** against an **18.41**
  trigger — within 4–8 percent of firing, on at least four separate sessions. The
  fact would put a false exculpatory claim about the data outage into a permanent
  record;
- **L-3 (cross-cutting)** the pinned append target
  `/Users/carsynstephenson/options-validator/ledger` is **not the `main`
  branch**. It is a worktree checked out on `claude/rest-2026-09-09`, whose
  `facts.log` is **19,610** lines while `main`'s is **19,627** — 17 lines behind,
  not 4 ahead. The packet's item 9 has this backwards, and the guard cannot
  detect it.

Plus three MUST-FIXes (L-4 review-citation misattribution, L-5 the close-price
source slot, L-6 the internal "for book purposes only / book row not written"
contradiction).

Every **number** in the Revision 2 text reproduced exactly, again. As in round 1,
the problem is claim discipline and targeting, not arithmetic.

### Packet 2 — `H9_RECEIPT_FULL_DOCUMENT_HASH_V1` — **READY WITH FIXES**

All three round-1 must-fixes (F-7, F-8, F-9) are closed cleanly and the
replacement wording is faithful to `facts.log:19346` and `ledger/README.md`. The
substance re-reproduced for a third time: nine-key hash `5bea2018…`, file sha256
`30df74c4…`, `d91b1ec` still the only commit, the `NaN` / `allow_nan=False`
finding, and no verifier anywhere in the repo.

Two shared fixes must land first — **L-3** (wrong append target) and **L-4**
(the fact cites review J, which reviewed a *different* text) — plus one residual
over-claim inside the fact (**L-7**, "From this point the full document is
bound", contradicted eleven lines later by the fact's own
`WHAT THIS FACT DOES NOT PROTECT` clause) and one command inconsistency (**L-8**).
With those, it is ready.

---

## §1. Disposition of every round-1 finding

| ID | Round-1 severity | Disposition | Evidence |
|---|---|---|---|
| **F-1** | BLOCKER (P1) | **CLOSED** | Every past-tense owner act is gone. The fact now reads "The owner ratifies option (a) by appending this fact; the act of appending it through research.facts.append_fact IS the ratification and no separate prior approval is claimed here." The "(b) … were both presented and not selected; (b) was declined because …" sentence is deleted; (b)/(c) are named neutrally as "drafted alongside (a) and are not adopted by this append", and the agent's reasons are explicitly "in the drafting record and are not attributed to the owner". Matches the `METRIC_CORRECTION` (`facts.log:19346`) template. See L-9 for one residual wording risk. |
| **F-2** | BLOCKER (P1) | **CLOSED** | Dry-run against a stubbed `append_fact`: as-written → **rc 1**, stderr `REFUSED: unsubstituted placeholder in the fact text…`, `append_fact` never reached. With all three placeholders substituted → **rc 0**, stub called with `dedupe_prefix=H6_0001_UNMARKED_EXPIRY`, prefix assertion passed. The burn-risk paragraph is quoted verbatim in §1.5 and restated in the preamble. |
| **F-3** | MUST-FIX (P1) | **CLOSED** | `EXIT: … settles at intrinsic value` is gone. Replaced by `DISPOSITION AT EXPIRATION (NOT a registered exit)` with the `Assumption` label, the "adopted by this fact and by nothing earlier" clause, and the physical-settlement correction ("a listed NVDA call is physically settled into 100 shares if exercised, and no exercise, assignment, or share position is recorded here"). The closing denial is softened to match. Verified against `experiments.jsonl` seq 6: it registers no expiry handling. See L-6 for a residual internal contradiction in the *wording*, not the substance. |
| **F-4** | MUST-FIX (P1) | **CLOSED** | The `BOOK ROW:` clause is in the fact text, names all four columns, says the blankness is deliberate, and explains the mechanism ("the H6 scorer counts completed rows off those columns"). Verified: `data/positions/h6_positions.csv` row `H6-0001` ends `…,cc8ccd80…,,,,` and `reports/h6_forward/2026-07-27.json` scores `completed_positions: 0`. |
| **F-5** | MUST-FIX (both) | **PARTIAL → see L-4** | Both recording notes now cite a review. But they cite **J**, which reviewed the **Revision 1** text. The rule (`.claude/rules/ledger.md:21-22`) is "independent adversarial review **of the exact text**". The exact text is Revision 2, whose review is *this* file. The citation as written is a misattribution in a permanent record. |
| **F-6** | SHOULD-FIX (P1) | **CLOSED** | Verified on disk: `preclose.json` top-level keys include `names`; `names.NVDA.path` = `.cache/schwab_chains/NVDA_2026-09-10.parquet`, `sha256 9df52917…`, `status "ok"`. `manifest.json` keys are `files, manifest_hash, provider, schema_version, session, session_chain_convention, symbols` — no `names`; `files.NVDA.path` = bare `NVDA_2026-09-10.parquet`, same sha256. Both `manifest_hash` = `4a4d6970…`. `shasum -a 256` of the parquet = `9df52917…`. The fact and the §1.1 table now say exactly this. |
| **F-7** | MUST-FIX (P2) | **CLOSED** | "chronological" is gone. New text: "718.50 USD when H9 16 stored trades are replayed under the zero-anchored entry-date-ordered closed_trade_pnl_drawdown definition of commit 5626c3f - expressly NOT a daily-NAV or generic chronological drawdown". Checked word-for-word against `facts.log:19346`, which says "$718.50 is specifically the implemented entry-date-ordered closed-trade value, not a daily-NAV or generic chronological drawdown" and names commit `5626c3f`. Faithful. |
| **F-8** | MUST-FIX (P2) | **CLOSED** | `FORWARD RULE` → `RECOMMENDED FORWARD PRACTICE, NOT BINDING BY THIS FACT`, with "Making it binding requires a .cursorrules or .claude/rules entry plus a test, which this fact does not perform and does not authorize." Consistent with `ledger/README.md:17-23` ("descriptive research-notes stream, never verdict-feeding… advisory context, not an audit record"). The `allow_nan` constraint is retained as an implementation note. No longer legislates. |
| **F-9** | SHOULD-FIX (P2) | **CLOSED** | "owner-ratified coverage fact" → "coverage fact… Agent-drafted 2026-09-15; independently adversarially reviewed 2026-09-15 (…); the owner ratifies by appending it through research.facts.append_fact, and no prior separate approval is claimed." (Receipt path is wrong — L-4 — but the pre-decided assertion is gone.) |
| **F-10** | SHOULD-FIX (P1) | **CLOSED** | The fact now cites OD-2 at `facts.log:19347` with the quoted wording. Verified verbatim: "OD-2 DECLINE the optional final EOD top-up; … the final canonical chain edge remains 2026-07-27; decision-authoritative consumers must fail closed beyond exact cached coverage". OD-4 in the same line is indeed the ThetaData **access** cutoff of 2026-08-01. Cache re-verified: `~/options-validator/.cache/chains` last three sessions = 2026-07-23, 07-24, **07-27**. |
| **F-11** | SHOULD-FIX (packet) | **CLOSED** | The `Run-verified` definition in the preamble now carves out cache reads. Verified: `.tmp/worktrees/audit-0915/.cache/` contains only an **empty** `chains/`, and `.cache/schwab_chains/` does not exist there. |
| **F-12** | MUST-FIX (both) | **PARTIAL → see L-3** | The `cd`-dependence is genuinely gone: `base_dir` is an absolute `pathlib.Path`, so cwd is irrelevant (dry-run from inside the worktree resolved to `/Users/carsynstephenson/options-validator/ledger/facts.log`). Both commands refuse (rc 1) on a `.tmp/worktrees` path and on a nonexistent path, and print resolved path + line counts before/after. **But the guard proves the wrong thing.** The pinned path is a worktree on branch `claude/rest-2026-09-09`, 17 lines behind `main`. The silent-fork hazard F-12 existed to close has been *relocated*, not closed. |
| **F-13** | NOTE (both) | **CLOSED** | Both facts now say "section 4 item 1". Verified: `A-evidence-audit.md` has `## §4 The three most load-bearing integrity risks` and no `§4.1`; the H9 item is item 1. The hard kill is now named in both the §1.1 table and the Packet 1 fact ("a hard kill of 3 consecutive calendar months each realizing the full monthly cap as losses; the hard kill is not an exit and could not have fired on a single position") — verbatim-equivalent to seq 6's "hard kill regardless: 3 consecutive calendar months each realizing the full monthly cap as losses". |
| **F-14** | NOTE (P1) | **CLOSED** | Both percentages carry "(arithmetic, not a receipt field)". Recomputed: −441.30 / 920.65 = **−47.933%**; (377.50 − 920.65) / 920.65 = **−58.9964%**. `Repo-verified` / `Run-verified` / `Assumption` labels now appear inside the Packet 1 fact text. |
| **F-15** | SHOULD-FIX (P1) | **PARTIAL → see L-5** | A source slot exists and is protected by the `<`/`>` guard. But §1.5's guidance about what to put in it is wrong about what the receipt contains, and the `Official-source` label is not defensible for a Yahoo-derived close. |
| **F-16** | NOTE (both) | **CLOSED** | The incorrect "double quotes inside Python" explanation is deleted. I re-verified both Revision 2 texts programmatically: **zero** occurrences of `'`, `"`, `$`, backtick, `!`, or any byte above ASCII 126. Single-quoted shell passes both byte-for-byte. |
| **Cross-cutting: "rewrite → re-review the exact text → owner appends"** | — | **CLOSED in the packet, OPEN in the facts** | The preamble states the order correctly and says "Do not append straight off this revision." But the fact texts themselves still cite J as their review (L-4). |
| **Cross-cutting: blockquote ≡ one-liner** | — | **CLOSED (re-verified)** | I extracted both `> ` blockquotes and both `TEXT = "…"` literals from the file and compared after whitespace normalization: **identical, `True` for both**. Packet 1 = 6,814 chars, Packet 2 = 4,149 chars. |
| **Cross-cutting: `append_fact` signature** | — | **CLOSED** | `research/facts.py`: `def append_fact(text: str, base_dir="ledger", *, dedupe_prefix: str | None = None) -> None`. Both commands call `append_fact(TEXT, base_dir=str(BASE), dedupe_prefix=KEY)` — positional text, keyword `base_dir`, keyword-only `dedupe_prefix`. Correct. Neither key exists in `facts.log` on any branch (`grep -c` = 0 in the worktree and at `main`), so neither first append can be refused by dedupe. |

---

## §2. New findings

### L-1 — **BLOCKER** (Packet 1). The fact asserts, in the past tense, an event that has not happened, and nothing in the guard stops a premature append.

**Exact text:**

> H6_0001_UNMARKED_EXPIRY **2026-09-18**: H6-0001 **reached expiration** with no
> exit ever executed.

and

> DISPOSITION AT EXPIRATION (NOT a registered exit): the position **was held to
> expiration 2026-09-18** with no exit ever executed.

**Evidence.** Today is **2026-09-15**. Expiration is 2026-09-18. The packet's
§1.5 says "Run **on or after the 2026-09-18 close**" — but that is prose in a
working document, and the whole point of the F-2 rewrite was that prose
instructions are not a guard. The guard checks three things: no `<` or `>`,
`TEXT.count("USD") >= 1` (vacuously true — the text contains "USD" 11 times),
and `"2026-09-18" in TEXT` (vacuously true — it is the fact's own date stamp and
the contract's expiration). **Not one of them is a date check.** Dry-run
confirmed: with the placeholders substituted the command exits **rc 0** and calls
`append_fact` today, 2026-09-15.

This is structurally the same defect as F-1, which was a BLOCKER: a fact that
records a past event which has not occurred. F-1 was about an owner's decision;
this is about the market. The remedy is the same shape — make the text true at
the moment it is written, or refuse to write it early.

**Replacement — add to the guard, immediately after the placeholder check:**

```python
import datetime
if datetime.date.today() < datetime.date(2026, 9, 18):
    sys.exit("REFUSED: this fact states that H6-0001 reached expiration on "
             "2026-09-18. Today is earlier than that. Nothing was appended.")
```

Keep the fact text as it is once that guard exists; it then cannot be written
before it is true.

---

### L-2 — **BLOCKER** (Packet 1). "Never within reach of the plus 100 percent take-profit" is unsupportable and probably false.

**Exact text:**

> **The position was never within reach of the plus 100 percent take-profit.** It
> is orphaned by the data-provider exit, not merely late.

**Evidence.** The take-profit trigger is a mark of about **18.41** (+100% of the
9.2065 entry ask; entry_cost 920.65 includes the 0.65 commission). The fact
offers exactly two observations in support: −47.93% on 2026-07-27 and −58.996%
on 2026-09-10. Between those two dates there are **no option observations at all**
— that is the entire premise of the fact. What the repo *does* have is the
underlying (`~/options-validator/.cache/underlying_ohlcv/NVDA.parquet`,
`DATA_PULL_OHLCV 2026-09-15`, 2,437 rows):

| Session | NVDA close | NVDA high |
|---|---|---|
| 2026-08-13 | 225.30 | 227.23 |
| 2026-08-27 | 227.98 | 230.47 |
| 2026-09-04 | **230.36** | **234.76** |
| 2026-09-08 | 225.73 | 233.71 |

The 220 call was **in the money** across late August and early September — it was
never anywhere near "out of reach". A Black-Scholes estimate at each session's
high (r = 4%, σ = 0.35 / 0.40 / 0.45; realised Schwab IV on 09-10 was 0.339, and
IV into that rally would have been higher, not lower) gives a peak contract value
of:

| Session | σ = 0.40 | σ = 0.45 |
|---|---|---|
| 2026-08-13 | 16.0 | **17.03** |
| 2026-08-27 | 15.3 | **16.36** |
| 2026-09-04 | **17.06** | **17.70** |

against an **18.41** trigger — a gap of **4% to 8%**, on four or more separate
sessions. That is squarely "within reach". A slightly higher vol, an intraday
print above the daily high, or one more up-day and the registered take-profit
fires. (Label: **Inference**, model-based, stated as such. I am not claiming it
*did* fire — I am claiming the fact cannot claim it could not.)

There is a second, related distortion. The 21-DTE close date is **2026-08-28**;
on 2026-08-27 NVDA closed 227.98 and the contract modelled at ~15–16, i.e. a loss
near **−40%**, not the −59% the fact's last mark implies. The fact does not claim
otherwise, but the "never within reach / orphaned, not merely late" pairing reads
as *the outage cost nothing*. On the repo's own underlying data, the outage
plausibly cost either a take-profit exit or a materially better time close. That
is the honest finding and it is more useful to a 2027 reader than the current
sentence.

**Replacement:**

> No option observation exists between 2026-07-27 and 2026-09-10, so what the
> position was worth in that window is unknown and this fact asserts nothing
> about it. For context only, and not as a mark: NVDA closed 230.36 on
> 2026-09-04 (Repo-verified, .cache/underlying_ohlcv/NVDA.parquet, refreshed
> 2026-09-15), so the 220 strike was in the money for part of that window and a
> plus 100 percent take-profit at a mark near 18.41 cannot be ruled out on the
> evidence available. The position is orphaned by the data-provider exit: the
> cost of that outage is that neither registered exit could be evaluated at all,
> and this fact does not claim the outage was costless.

---

### L-3 — **BLOCKER** (both). The pinned "main checkout" is not the `main` branch, and item 9 has the drift backwards.

**Exact text (§3 item 9):**

> `wc -l` gives **19,614** lines in this worktree and **19,610** in the main
> checkout (Run-verified 2026-09-15). The four extra lines are automated
> `SCHWAB_CHAIN_CAPTURE` and `DATA_PULL` entries for 2026-09-09 through
> 2026-09-11, **committed on this branch** (`645365b`, `5ff7001`, `6873263`) and
> **not yet in the main checkout's working tree**. … **land this branch first,
> then append**

**Evidence.** Both line counts are right; the interpretation around them is
wrong in three ways.

1. **`git worktree list`** shows `/Users/carsynstephenson/options-validator` is
   itself a worktree, checked out on branch **`claude/rest-2026-09-09`** at
   `a455855`. It is "the main checkout" only in the sense of being the primary
   directory. The `main` **branch** is checked out at
   `/Users/carsynstephenson/options-validator-ops` (`a3745ab`).
2. **The three commits are already on `main`.** `git merge-base --is-ancestor
   6873263 main` → yes, for all three. They are not exclusive to
   `claude/audit-2026-09-15`; that branch simply descends from a point that
   includes them. `main` also carries `a3745ab` (today's ritual).
3. **The real drift is the other way and four times larger.**

   | Tree | `facts.log` lines |
   |---|---|
   | `main` (tip, `a3745ab`) | **19,627** |
   | this audit worktree (`f228894`) | 19,614 |
   | the pinned append target, branch `claude/rest-2026-09-09` | **19,610** |

   The pinned target is **17 lines behind `main`**, not 4 ahead of anything.
   Those 17 lines include today's `DATA_PULL 2026-09-15` (25 ok, 0 fetch errors)
   and eleven `DATA_PULL_OHLCV 2026-09-15` entries.

**Why this is a blocker and not a note.** F-12's whole purpose was to stop a
silent append onto a divergent copy of an append-only log. The guard's only
lineage test is `".tmp/worktrees" in str(RESOLVED)`. The pinned path passes that
test while sitting on a stale non-`main` branch — the exact failure mode,
relocated. The dry-run output proves it: `lines before: 19610`. §1.5's
orientation block does say `git rev-parse --abbrev-ref HEAD # confirm the
intended branch`, but it never names which branch is intended, nothing enforces
it, and **§2.3 drops that line entirely** (see L-8).

The ordering advice is wrong as a consequence. "Land this branch first" does not
move `/Users/carsynstephenson/options-validator` off `claude/rest-2026-09-09`,
so following it literally still appends to the stale tree. And the conflict it
warns about is understated: appending at 19,610 and later reconciling against
`main` at 19,627 is a 17-line tail divergence, not 4.

**Replacement — orientation block (both §1.5 and §2.3):**

```sh
cd /Users/carsynstephenson/options-validator-ops   # the worktree on `main`
git rev-parse --abbrev-ref HEAD                    # must print exactly: main
git pull --ff-only                                 # be at the tip of main
wc -l ledger/facts.log                             # note the count; re-check after
```

**Replacement — guard, in both commands:**

```python
import subprocess
BASE = pathlib.Path("/Users/carsynstephenson/options-validator-ops/ledger")
branch = subprocess.run(["git", "-C", str(BASE.parent), "rev-parse",
                         "--abbrev-ref", "HEAD"],
                        capture_output=True, text=True).stdout.strip()
if branch != "main":
    sys.exit("REFUSED: %s is on branch %r, not main. Nothing was appended."
             % (BASE.parent, branch))
```

**Replacement — §3 item 9, whole paragraph:**

> Three copies of `facts.log` differ and the owner must append to the right one.
> `main` (tip `a3745ab`) has 19,627 lines. This audit worktree has 19,614. The
> primary directory `/Users/carsynstephenson/options-validator` has 19,610 —
> it is a worktree parked on branch `claude/rest-2026-09-09` and is **17 lines
> behind `main`**, not ahead of it. The 2026-09-09/10/11 ritual commits
> (`645365b`, `5ff7001`, `6873263`) are already ancestors of `main`. Append from
> a tree that is on `main` and up to date — `/Users/carsynstephenson/options-validator-ops`
> — or the new line lands on a stale branch and has to be reconciled by hand into
> an append-only file later. Landing the audit branch is a separate concern and
> does not fix this.

*(`options-validator-ops` is skipped by `repo-reconcile`, so the owner commits
and pushes that append himself. Worth one sentence in §1.5.)*

---

### L-4 — **MUST-FIX** (both). Both facts cite a review that did not review them.

**Exact text (Packet 1):**

> Recording note: … **independent adversarial review 2026-09-15, receipt
> reports/2026-09-15-audit/J-fact-packets-adversarial-review.md**.

**Exact text (Packet 2):**

> **independently adversarially reviewed 2026-09-15
> (reports/2026-09-15-audit/J-fact-packets-adversarial-review.md)**

**Evidence.** J reviewed **Revision 1** — J's own §0 says so ("what I reviewed
is the *pre-fix* text") and its cross-cutting note demands a second pass "over
the corrected wording". The packet preamble agrees: "Review J covered the
Revision 1 text." `.claude/rules/ledger.md:21-22` requires "independent
adversarial review **of the exact text**". So each fact, in the permanent record,
names as its review a document that reviewed different words. A 2027 reader who
opens J and diffs it against the fact finds F-1 through F-16 describing text that
is not there.

**Replacement (both facts):**

> independent adversarial review rounds 1 and 2, 2026-09-15; receipts
> reports/2026-09-15-audit/J-fact-packets-adversarial-review.md (Revision 1 text)
> and reports/2026-09-15-audit/L-fact-packets-adversarial-review-round2.md (this
> Revision 2 text).

The self-reference is unavoidable and is the standard resolution: adding the
citation is the only edit after this review, and it is verifiable by diff.
`METRIC_CORRECTION` handles it the lighter way — "independently adversarially
reviewed 2026-07-31", no path — which is also acceptable if the owner prefers it.

---

### L-5 — **MUST-FIX** (Packet 1). The close-price source slot points at a receipt that does not contain a price, and `Official-source` is the wrong label for it.

**Exact text (fact):**

> NVDA official close 2026-09-18: <NVDA 2026-09-18 official close> (source:
> <closes receipt path or named official source>, **Official-source**).

**Exact text (§1.5):**

> If that receipt exists for 2026-09-18, **put its path in the source slot**.

**Evidence.** I read the receipt. `reports/closes_receipts/2026-09-15/guarded-all-cached.json`
records, per symbol, only:

```json
"NVDA": {"max_session": "2026-09-14", "outcome": "refreshed",
         "stored_file": ".cache/underlying/NVDA.parquet",
         "stored_file_sha256": "5140617d386deac426bf173542bfea27604ec2b4d23cf5bb5de4ae7ea9b0b8e6"}
```

**No price.** The number lives in `.cache/underlying/NVDA.parquet`, which is
gitignored — the same durability problem F-10 was raised to fix, reintroduced in
the one slot the whole disposition rests on. A 2027 reader following the cited
path finds a sha256 of a file that is not in the repo.

Second: the receipt's provider is `data.underlying_closes.fetch_underlying_eod_yahoo`
— Yahoo. `.cursorrules` (lines 83-86) requires the label to be honest and says
"Never cite blogs … for assignment, margin, fills, or fees when an official
source exists." A Yahoo EOD close is a **vendor** close. For an expiring listed
option it is also not the figure that governs anything: auto-exercise is decided
by OCC against the exchange closing price, not by a vendor feed. Labelling it
`Official-source` overstates it.

Third, smaller: §1.5 cites `reports/closes_receipts/2026-09-11/` as its
Repo-verified example. That run recorded **25 fetch errors and 0 successes** —
every symbol failed with a DNS error. It is the worst available example of the
mechanism working. Today's 2026-09-15 receipt (25 ok, 0 errors, on `main`) is the
right one to cite.

**Replacement (fact):**

> NVDA official close 2026-09-18: <close in USD> (Vendor-source, Yahoo EOD via
> data.underlying_closes.fetch_underlying_eod_yahoo; provenance receipt
> reports/closes_receipts/2026-09-18/guarded-all-cached.json, which records
> outcome and stored_file_sha256 <sha256> for .cache/underlying/NVDA.parquet but
> does not itself carry the price; the price is read from that gitignored
> parquet. This is a vendor close, not an exchange or OCC settlement price, and
> no exercise or settlement decision is recorded by this fact.)

**Replacement (§1.5):** say that the receipt is a provenance record, that the
owner must copy the `stored_file_sha256` into the slot alongside the path, and
that the price itself comes from the gitignored parquet.

---

### L-6 — **MUST-FIX** (Packet 1). "For book purposes only" and "not written by this fact" contradict each other.

**Exact text:**

> **For book purposes only**, and as a valuation convention adopted by this fact
> and by nothing earlier (Assumption, stated so), the position is valued at
> expiration intrinsic value…

then, ~90 words later:

> BOOK ROW: data/positions/h6_positions.csv row H6-0001 keeps exit_date,
> exit_proceeds, exit_reason and exit_receipt_hash BLANK and **is not written by
> this fact**.

**Evidence.** Both sentences are individually correct and both are needed. Read
together they tell a 2027 reader that a valuation exists "for the book" and that
the book does not contain it. The reader's natural next move is to go look for it
in `h6_positions.csv`, not find it, and conclude one of the two sentences is a
mistake — which is precisely the confusion F-4 was raised to prevent.

**Replacement:** change "For book purposes only" to **"For disclosure purposes
only — this valuation is recorded in this fact and nowhere else; no book row,
receipt, or scoreboard carries it —"**. One phrase, and the two clauses stop
fighting.

---

### L-7 — **SHOULD-FIX** (Packet 2). "From this point the full document is bound" is an over-claim the same fact retracts eleven lines later.

**Exact text:**

> …the full file reports/h9/receipt.json has sha256 30df74c4… at commit d91b1ec…
> **From this point the full document is bound.**

versus, in the same fact:

> WHAT THIS FACT DOES NOT PROTECT: no verifier reads either hash. … The sha256
> recorded here is a number in an advisory log that nothing automatically checks;
> its value is that a future reader can recompute it, not that any tool will
> refuse on mismatch.

**Evidence.** I re-confirmed the second clause: `grep -rn "receipt_hash"
options_researcher/h9_*.py` → nothing; the only file in the repo that references
`reports/h9/receipt.json` in code is its writer, `tools/h9_run_study.py:28`
(`RECEIPT_PATH`). Nothing binds anything. The `DOES NOT PROTECT` clause is the
honest one; "is bound" is the leftover of the Revision 1 framing and it is the
sentence a skimming reader will carry away. This is the same species as F-8 —
asserting enforcement an advisory log cannot deliver.

**Replacement:** "From this point a reader can verify the full document by
recomputing this sha256 and comparing; nothing enforces the comparison (see
below)."

---

### L-8 — **SHOULD-FIX** (Packet 2, §2.3). The two orientation blocks are not the same, and the one that matters is missing a line.

§1.5 has four commands: `cd`, `git rev-parse --show-toplevel`, **`git rev-parse
--abbrev-ref HEAD`**, `wc -l`. §2.3 says "Orient first, **exactly as in §1.5**"
and then prints only three — the branch check is dropped. Given L-3, the branch
check is the single most load-bearing line in the block. Make the two blocks
byte-identical and use the L-3 replacement for both.

---

### L-9 — **SHOULD-FIX** (both). "No separate prior approval is claimed here" reads as an admission that the rule's approval step was skipped.

**Exact text (Packet 1):** "the act of appending it through
research.facts.append_fact **IS the ratification and no separate prior approval
is claimed here**." (Packet 2 carries the same clause.)

**Evidence.** `.claude/rules/ledger.md:21-22` sets the order as "independent
adversarial review of the exact text, **then owner approval, then append**" —
three steps, approval distinct from and prior to the append. The fact's clause
collapses two of them and then explicitly disclaims the middle one. A 2027
auditor reading the rule and then the fact can reasonably conclude the rule was
not followed.

The substance is fine — the owner reading the text and running the command
himself *is* approval. The wording just describes it in the negative. Note that
the precedent the packet leans on, `A2_ENTRY_CONVENTION_RATIFIED_V1`
(`facts.log:19553`), carries a positive token: `owner-approved 2026-08-31
source=reports/2026-08-31-a2-entry-convention-ratification-receipt.md`.

**Replacement (both facts):**

> The owner approves this exact text by reading it and running the append
> himself; that act is both the approval required by .claude/rules/ledger.md and
> the ratification. No agent recorded an approval on the owner behalf, and none
> is claimed.

---

### L-10 — **NOTE** (Packet 1). "Verbatim" is claimed for a transliterated quote.

**Exact text:** "the exits registered at experiments.jsonl seq 6 are,
**verbatim**, close at 21 DTE at conservative fills OR take-profit at plus 100
percent of premium, whichever first, with NO stop-loss."

Seq 6 reads: `"Exit: close at 21 DTE at conservative fills OR take-profit at
+100% of premium, whichever first; NO stop-loss (H1 evidence: stops were the loss
engine)."` The `+`, `%`, and `;` were transliterated (correctly — the text must
stay shell-safe) and the parenthetical was dropped. The meaning is exact; the
word "verbatim" is not. Say "in substance, with plus and percent spelled out for
shell safety" — a one-word-level fix in a document that is otherwise fastidious.

### L-11 — **NOTE** (both). Stripped apostrophes have produced two ungrammatical phrases.

"**The drafting agent reasons** for preferring (a)" (Packet 1) and "when **H9 16
stored trades** are replayed" (Packet 2). Both are casualties of the no-`'`
constraint. Rewrite around the possessive: "The reasons the drafting agent gave
for preferring (a)…" and "when the 16 trades stored in the H9 receipt are
replayed…".

### L-12 — **NOTE** (packet §3, item 1). The "NOT VERIFIED" entry is now stale.

§3 item 1 says NVDA's $210.96 close on 2026-09-14 is unverifiable because "the
latest closes receipt is `reports/closes_receipts/2026-09-11/`". As of today
`main` carries `reports/closes_receipts/2026-09-15/guarded-all-cached.json`
(25 ok, 0 errors), and `.cache/underlying/NVDA.parquet` — refreshed at
2026-09-15T13:25 UTC — has `2026-09-14 → 210.960007`. The number is now
reproducible in-repo. Keeping it out of the fact is still the right call (it is
context, not evidence), but the stated reason is no longer true. This is the same
stale-vantage-point problem as L-3: the packet was written from a worktree that
predates today's ritual.

### L-13 — **NOTE** (packet §3, item 3). The rules-file fix the packet defers has already been made.

§3 item 3 says correcting `.claude/rules/ledger.md`'s "chronological value:
$718.50" is "out of scope here". `git diff .claude/rules/ledger.md` in this
worktree shows it **has** been corrected (uncommitted) to "the zero-anchored,
entry-date-ordered closed-trade value is $718.50 (a closed-trade drawdown, NOT a
daily-NAV or generic chronological drawdown — `METRIC_CORRECTION`, facts.log
2026-08-01)". Update the item to "done on this branch, uncommitted" so nobody
does it twice.

### L-14 — **NOTE** (Packet 1, guard). Two guard clauses are decorative, and substitution can reintroduce a shell hazard.

`TEXT.count("USD") < 1` (the text contains "USD" 11 times) and `"2026-09-18" not
in TEXT` (it is the fact's own date stamp) cannot fail for any plausible edit.
They cost nothing but they create false confidence that "the text still looks
like the reviewed fact" is being checked; it is not. A real check would be a
length assertion plus a sha256 of the reviewed text with the three placeholders
blanked.

More importantly: the packet verifies the *current* text is free of `'`, `$`,
backtick and `!` — but the owner is about to **edit** it. Pasting a path or a
note containing `'` breaks the single-quoted shell program, and `$` or a backtick
would be expanded. Add one line to §1.5: *"When you substitute, use only digits,
letters, spaces, dots, slashes, hyphens and colons. Never paste a character that
is not on that list — an apostrophe or a dollar sign will break or silently alter
the command."*

---

## §3. Direct answers to the questions asked

**Q2 — every number re-verified.** All of them reproduced. Independently
re-derived today, in this worktree: `experiments.jsonl` seq 6 (`trial_intent`,
`H6`, `record_hash 5d813b8f…`, ts `2026-07-09T00:50:22.721232+00:00`), the exit
prose, the 8-completed bar, the hard kill; seq 22 (`H6_KILL_V2`,
`record_hash 4c552641…`, "entries on or after 2026-08-03", "Existing H6 rows
retain v1"); the `h6_positions.csv` row byte-for-byte with four blank exit
columns; `cc8ccd80…` as the 07-13 `receipt_hash`; `reports/h6_forward/` = exactly
five files ending 07-27; the 07-27 receipt's `action HOLD, dte 53, pnl -441.3,
proceeds 479.35, reason no_exit_trigger` and `completed_positions 0 /
INSUFFICIENT_SAMPLE / "requires 8 completed positions"` and
`receipt_hash c4b3138d…`; `config.py:347-349` (exactly those three constants on
exactly those lines) and `config.py:189 MIN_LOSSES_FOR_VERDICT = 10`;
`tools/h9_run_study.py:169-171` (169 `bulk = …`, 170-171 the hash call);
`shasum -a 256 reports/h9/receipt.json = 30df74c4…`; `d91b1ec` still the only
commit for that file; the nine-key set and **`sha256_hex(canonical_json(nine))` =
`5bea2018fa204b2b3bfc221fee2b43f669ce9ff5b90270515dbc267084df3c06`, matching the
recorded value**; `board.expectancy_per_trade 290.32499…`, `CI90 [27.82187…,
574.4625…]`, `total_pnl 4645.1999…`, `n_trades 16`, `n_losses 4`;
`canonical_json(full receipt)` → `ValueError: Out of range float values are not
JSON compliant: nan` from `board.return_on_economic_max_loss`; `facts.log` lines
17892, 19346, 19347, 19413, 19553 all carry the cited records **and carry them at
the same line numbers in `main` and in the primary checkout**; the Schwab 09-10
NVDA 220 C 2026-09-18 row (bid 3.75, ask 3.80, delta 0.463, iv 0.33917, OI 43021,
ts `2026-09-10T19:45:33.824000+00:00`); the parquet sha256 `9df52917…` and the
`preclose.json` / `manifest.json` structure; 21-DTE = 2026-08-28 (a Friday);
07-27 → 09-18 = 53 days; −47.933% and −58.9964%.

**Discrepancies, all of them:** three, all in the packet's prose rather than in
the fact texts — **L-3** (19,610 vs 19,627; "main checkout" is a worktree on
`claude/rest-2026-09-09`; the three commits are already on `main`), **L-12**
(the 09-15 closes receipt now exists and `210.96` is reproducible), **L-13** (the
rules-file correction is already made). **No number, hash, path, line number,
seq or `record_hash` inside either fact text is wrong.**

**Q3 — attacking the guarded one-liners.** All executed against a stub. Packet 1:
as-written → **rc 1**, `REFUSED: unsubstituted placeholder…`, `append_fact` never
reached; substituted → **rc 0**, stub called with the right `base_dir` and
`dedupe_prefix`, prefix assertion passed. Both packets: `base_dir` redirected
under `.tmp/worktrees` → **rc 1**; `base_dir` nonexistent → **rc 1**. Text passed
is **character-identical** to the blockquote for both (6,814 and 4,149 chars).
`dedupe_prefix` is a prefix of the text in both and neither key exists in
`facts.log` on any branch. Neither text contains `'`, `"`, `$`, backtick, `!`, or
a non-ASCII byte, so single-quoted `sh`/`zsh` passes both through byte-for-byte.
The real `append_fact` signature is
`append_fact(text, base_dir="ledger", *, dedupe_prefix=None)` and both calls
match it. **Three gaps remain: no date check (L-1), no branch check (L-3), and
two vacuous sanity checks plus an unguarded substitution step (L-14).**

**Q4 — does either text still pre-decide, legislate, change a number, or deny a
convention it introduces?** Owner pre-decision: **no** — F-1 and F-9 are cleanly
closed; the residue is only the negative phrasing in L-9. Legislating from an
advisory log: **no** — F-8 is closed and the new clause explicitly disclaims the
power. Changing a registered number or verdict: **no** — H6 stays
INSUFFICIENT_SAMPLE at n = 0 against the 8-completed bar, H9 stays
INSUFFICIENT_SAMPLE at 16 trades / 4 losses against 10, the one H9 run stays
SPENT, seq 22 is untouched, no board value or trade row moves. Denying a
convention it introduces: **no** — F-3 is closed; the fact now names the
expiration-intrinsic valuation as a convention it adopts, labels it
`Assumption`, and corrects the physical-settlement point. The sentences that
still need to go are **L-2** (a false empirical claim), **L-1** (a past-tense
future event) and **L-7** ("From this point the full document is bound").

**Q5 — item 9 and the ordering advice.** Line counts verified: 19,614 in the
worktree, 19,610 in the primary checkout. The **interpretation is wrong** and
the advice does not solve the problem it names — see **L-3**. Correct advice:
append from a tree that is on `main` and up to date
(`/Users/carsynstephenson/options-validator-ops`), with a branch check in the
guard. Landing the audit branch is a separate concern.

**Q6 — what a 2027 reader would misread.** (i) That the outage was costless and
the position was hopeless throughout — L-2 is the correction, and it is the most
consequential item in this review. (ii) That a valuation exists "for the book"
which the book does not contain — L-6. (iii) That review J examined these words
— L-4. (iv) That the cited closes receipt contains the closing price, and that a
Yahoo EOD print is an official settlement price — L-5. (v) That the full H9
document is now protected — L-7. (vi) That the rule's separate owner-approval
step was skipped — L-9. (vii) That "verbatim" means byte-exact — L-10. (viii)
That `/Users/carsynstephenson/options-validator` is the canonical `facts.log` —
L-3, which a 2027 reader inherits as an unexplained gap in the log's tail.

---

## §4. What must change before each packet goes to the owner

**Packet 1 (all required):** L-1 date guard · L-2 replace the "never within
reach" sentence · L-3 repoint and branch-guard the append · L-4 fix the review
citation · L-5 fix the source slot and its label · L-6 "for disclosure purposes
only". Then L-9, L-10, L-11, L-14.

**Packet 2 (all required):** L-3 · L-4 · L-7. Then L-8, L-9, L-11.

**Sequencing.** `.claude/rules/ledger.md` requires review of the **exact** text.
These fixes change the text, so a Revision 3 needs one short confirming pass —
ideally a diff-only check that nothing beyond the listed items moved, rather than
a full round 3.

---

*Nothing in this review was appended to any ledger. No ledger-writing tool was
called. `append_fact` was exercised only against a local stub that captured its
arguments and asserted the prefix invariant. No commit was made, the packet file
was not modified, and the only file created is this one.*
