# M — Round-3 independent adversarial review of the two ledger fact texts

**Target:** `reports/2026-09-15-audit/H-owner-fact-packets.md`, **Revision 3.1**.
**Prior receipts:** `reports/2026-09-15-audit/J-fact-packets-adversarial-review.md`
(round 1, Revision 1 text) and
`reports/2026-09-15-audit/L-fact-packets-adversarial-review-round2.md`
(round 2, Revision 2 text).
**Date:** 2026-09-15. **Worktree:** `.tmp/worktrees/audit-0915`, branch
`claude/audit-2026-09-15`.
**Stance:** show how each text could be lying, over-claiming, pre-deciding, or
unsafe to append. Not a confirmation pass.

**Nothing was appended. Nothing was committed. No ledger-writing tool was
called.** Both guarded programs were executed against a **stubbed**
`append_fact` that captured its arguments and asserted the prefix invariant; the
stub was injected with a single prepended `sys.path.insert` line and the
programs were otherwise byte-identical to the ones in `H`. The packet file was
not edited. The only file created is this one. Two throwaway git clones were
made under `/tmp` and `.tmp/r3/` to attack the lineage guard and were deleted.

---

## §0. Verdicts

### Packet 1 — `H6_0001_UNMARKED_EXPIRY` — **NOT READY**

Rounds 1 and 2 were right that the Revision 2 text was unsafe. Revision 3's fix
to the most consequential of those blockers (**L-2**) replaced a claim that was
*probably true* with one that is **demonstrably false**, and did so because
neither the drafting agent nor the round-2 reviewer looked in the repository's
own Schwab option cache.

- **M-1 (BLOCKER).** The fact asserts *"no option observation of any kind exists
  for this contract between 2026-07-27 and 2026-09-10."* The repository holds
  **fourteen** pre-close captures of exactly that contract (NVDA 220 call,
  expiry 2026-09-18) inside that window, in `.cache/schwab_chains/`, each with a
  committed `status: ok` session receipt in `reports/schwab_chains/` **on
  `main`** — including **2026-08-28, the 21-DTE date the fact singles out as
  unknown**. The fact's own "LAST VERIFIABLE MARK" paragraph cites one member of
  that series while the paragraph above it denies the series exists.
- **M-2 (BLOCKER).** Consequently the take-profit question is **not** UNKNOWN in
  the direction the fact implies. The best bid observed anywhere in the window is
  **13.50** (2026-08-14), worth **1335.35** in registered conservative-fill
  proceeds against the **1841.30** the registered rule requires — **72.5 % of
  the trigger**, never closer. Revision 2's deleted sentence ("never within reach
  of the plus 100 percent take-profit") is the one the evidence supports.
  Round 2's Black-Scholes inference (16.4–17.7, "within 4–8 % of firing") is
  falsified by the actual quotes, which bracket the modelled peak at ~12.
- **M-3 (BLOCKER, both packets).** Six provenance paths cited **inside** the fact
  texts do not exist on `main`, and the guard forces the append to happen on
  `main`.

Every other number, hash, path, line number, `seq` and `record_hash` in the
Packet 1 text reproduced exactly. As in rounds 1 and 2, the failure is evidence
coverage and claim discipline, not arithmetic.

### Packet 2 — `H9_RECEIPT_FULL_DOCUMENT_HASH_V1` — **READY WITH FIXES**

**The Packet 2 fact text may be appended exactly as written** — I re-derived
every one of its claims from `main` and found no error. Its invariant sha256
`c837b27e…` matches the blockquote, and the blockquote is character-identical to
what the command passes. Nothing in this section asks for a word to change, so
the `M` citation inside it remains honest and no round 4 is needed for Packet 2.

Three fixes must land **before** it is run, none of which touch the text:
**M-3** (get the cited receipts onto `main` first), **M-7/M-8** (guard holes),
and **M-6** (both of the packet's recommended append routes are impossible as
written).

---

## §1. Disposition of L-1 … L-14 and the cross-cutting points

| ID | L severity | Disposition | Evidence |
|---|---|---|---|
| **L-1** | BLOCKER (P1) | **CLOSED** | Both halves applied and both work. Text: "reached its 2026-09-18 expiration … This fact is appended only after that date has passed; the append command refuses to run before 2026-09-19 00:00 America/New_York." Guard: real `zoneinfo("America/New_York")` gate. Dry-run today → **rc 1**, `REFUSED: … It is 2026-09-15T12:33:09.289578-04:00 in New York, before 2026-09-19 00:00.` `append_fact` never reached. 2026-09-18 confirmed a Friday; the 2026-09-19 00:00 ET boundary is after that close. |
| **L-2** | BLOCKER (P1) | **OPEN — regressed. See M-1 / M-2.** | The false sentence was removed; the sentence that replaced it is also false, and is false about a larger thing (the existence of evidence rather than its interpretation). The BS figures the packet reproduces are arithmetically right (I reproduce 15.69/17.03, 15.38/16.36, 17.06/17.70 exactly) but empirically wrong by ~45 % against the real quotes. |
| **L-3** | BLOCKER (both) | **PARTIAL.** Guard: CLOSED. Advice: **OPEN — see M-6, M-8, M-9.** | The lineage guard is real and works: primary checkout → `rc 1`, *"is on branch claude/rest-2026-09-09, not main"*; audit worktree → `rc 1`; ops tree on `main` at `origin/main` → `rc 0`, `lines before: 19627`. §3 item 7's numbers are all correct (19,627 / 19,614 / 19,610; `645365b`, `5ff7001`, `6873263` all ancestors of `main`). **But** both routes the packet tells the owner to use are impossible (M-6), the guard passes on a dirty and stale tree (M-8), and it never checks it is even the right repository (M-9). |
| **L-4** | MUST (both) | **CLOSED** | Both texts cite rounds 1 to 3 with all three receipt paths, correctly labelled (J = Revision 1 text, L = Revision 2 text, M = this exact text). The self-reference condition is stated at the top of `H`. For Packet 2 the citation is honest: this round passes its text unchanged. For Packet 1 it is **not**, because this round requires a text change — the citation must move to a round-4 receipt. Separately, all three paths are absent from `main` (M-3). |
| **L-5** | MUST (P1) | **PARTIAL** | The slot now demands an exchange-published source, permits `Official-source` only then, names Yahoo-via-`fetch_underlying_eod_yahoo` as the vendor case, and adds the OCC point. §1.5's claim about the receipt is correct: I read `reports/closes_receipts/2026-09-15/guarded-all-cached.json` on `main` — per symbol it carries only `max_session`, `outcome`, `stored_file`, `stored_file_sha256`, **no price**; `provider` is `data.underlying_closes.fetch_underlying_eod_yahoo`; 25 symbols, `retrieved_utc 2026-09-15T13:24:57Z`. **But the whole slot sits inside the guard's unchecked window** — I demonstrated labelling "a blog post I found" as `Official-source` and still getting `rc 0` (M-7). |
| **L-6** | MUST (P1) | **CLOSED** | Text reads "For disclosure purposes only - this valuation is recorded in this fact and nowhere else; no book row, receipt, or scoreboard carries it -". No longer fights the `BOOK ROW:` clause. |
| **L-7** | SHOULD (P2) | **CLOSED** | "is bound" is gone; replaced by "a reader can verify … nothing enforces the comparison, as stated below." Re-verified the underlying claim on `main`: `grep -rn receipt_hash options_researcher/h9_*.py` → no match (rc 1); the only code reference to `reports/h9/receipt.json` is `tools/h9_run_study.py:28`; nothing in `tests/` references it either. |
| **L-8** | SHOULD (P2) | **CLOSED** | §2.3's orientation block is byte-identical to §1.5's, branch check included. (Both blocks are wrong for a different reason — M-6.) |
| **L-9** | SHOULD (both) | **CLOSED, with a new residue — see M-13.** | The positive form is in both texts. It now asserts that append == approval, which `.claude/rules/ledger.md` orders as two distinct steps. |
| **L-10** | NOTE (P1) | **CLOSED** | "in substance and with plus and percent spelled out for shell safety". §1.1 carries seq 6's exact bytes; I compared them character by character against `ledger/experiments.jsonl` seq 6 `reason` — the quoted string is exact, parenthetical included. |
| **L-11** | NOTE (both) | **CLOSED** | Both phrasings fixed; re-read in context and both are grammatical. |
| **L-12** | NOTE (§3 item 1) | **CLOSED, with a conflation — see M-14.** | `reports/closes_receipts/2026-09-15/guarded-all-cached.json` exists on `main` (25 refreshed, 0 errors) and `.cache/underlying_ohlcv/NVDA.parquet` gives `2026-09-14 → 210.960007`. Both verified. The receipt covers `.cache/underlying/`, a different cache from the one cited. |
| **L-13** | NOTE (§3 item 3) | **CLOSED** | `.claude/rules/ledger.md` on `main` still reads "chronological value: $718.50"; the corrected wording exists only as an uncommitted change in this worktree. The packet says exactly that. |
| **L-14** | NOTE (P1 guard) | **PARTIAL — see M-7.** | The decorative checks are gone and the invariant sha256 is real: I recomputed both and they match the pinned constants (`397d7d54…`, `c837b27e…`), and a mutation outside the placeholders refuses (`12 of the 33 sessions` → `2 of the 33 sessions` → **rc 1**). The substitution character-set warning is present. **But** the implementation leaves a **579-character** window unprotected, not the three placeholder slots it claims to leave. |
| **Cross-cutting: blockquote ≡ command text** | — | **CLOSED (re-verified)** | I extracted both `> ` blockquotes and both `TEXT = "…"` literals programmatically and compared after whitespace normalization: identical for both. Packet 1 = **9,091** chars, Packet 2 = **4,638** chars. Neither contains `'`, `"`, `$`, backtick, `!`, or a byte above ASCII 126. `TEXT.startswith(KEY)` holds for both. |
| **Cross-cutting: invariant hashes** | — | **CLOSED** | P1: `sha256(TEXT.split("NVDA official closing price 2026-09-18:")[0] + "\|" + TEXT.split("BOOK ROW:")[1])` = `397d7d54647ac74f89e89729fb6d4e1a0e5bb8e335c1274088de2e75a744b09e` — matches. P2: `sha256(TEXT)` = `c837b27e522f0c9c300e3163985a1b0aab7549dc1cde55baa77b1a7b5dfb10f4` — matches. Each split marker occurs exactly once. |
| **Cross-cutting: "review the exact text, then approve, then append"** | — | **OPEN (P1), CLOSED (P2)** | Packet 2's text passes this round unchanged, so its `M` citation is true. Packet 1 must change, so its citation becomes a misattribution the moment Revision 4 is cut — the same defect L-4 raised, one round later. |
| **Cross-cutting: provenance paths resolve** | — | **OPEN — M-3 (new; no prior round tested this)** | Six cited paths are absent from `main`, the only tree the guard permits. |
| **Cross-cutting: `append_fact` signature** | — | **CLOSED** | `research/facts.py`: `def append_fact(text: str, base_dir="ledger", *, dedupe_prefix: str \| None = None) -> None`. Both calls match. Neither key exists in `facts.log` in any of the three checkouts, so neither first append can be refused by dedupe. |

---

## §2. New findings

### M-1 — **BLOCKER** (Packet 1). The window the fact calls empty contains fourteen observations of exactly this contract.

**Exact text:**

> WHAT IS UNKNOWN, AND THIS FACT DOES NOT CLAIM OTHERWISE: **no option
> observation of any kind exists for this contract between 2026-07-27 and
> 2026-09-10**, so what the position was worth across that window - **including
> on the 2026-08-28 21-DTE date - is unknown**, and this fact asserts nothing
> about it.

**Evidence.** `.cache/schwab_chains/` (present and byte-identical in both the
primary checkout and the `main` checkout) contains fourteen NVDA pre-close
captures inside that window. Filtering each for `strike == 220.0`,
`right == "C"`, `expiration == 2026-09-18` returns exactly one row per session:

| Session | bid | ask | mid | NVDA close | receipt status |
|---|---|---|---|---|---|
| 2026-08-14 | 13.50 | 13.60 | 13.550 | 225.16 | ok |
| 2026-08-19 | 9.25 | 9.30 | 9.275 | 217.56 | ok |
| 2026-08-20 | 8.55 | 8.65 | 8.600 | 216.85 | ok |
| 2026-08-24 | 4.85 | 4.95 | 4.900 | 208.48 | ok |
| 2026-08-25 | 6.15 | 6.25 | 6.200 | 213.05 | ok |
| 2026-08-26 | 5.05 | 5.10 | 5.075 | 209.66 | ok |
| 2026-08-27 | 12.55 | 12.70 | 12.625 | 227.98 | ok |
| **2026-08-28 (21-DTE date)** | **5.55** | **5.65** | **5.600** | 217.55 | ok |
| 2026-09-02 | 8.60 | 8.70 | 8.650 | 224.41 | ok |
| 2026-09-03 | 11.70 | 11.80 | 11.750 | 228.45 | ok |
| 2026-09-07 † | 12.35 | 12.65 | 12.500 | (Labor Day) | ok |
| 2026-09-08 | 8.50 | 8.60 | 8.550 | 225.73 | ok |
| 2026-09-09 | 6.95 | 7.00 | 6.975 | 223.67 | ok |
| 2026-09-10 | 3.75 | 3.80 | 3.775 | 218.36 | ok |

† 2026-09-07 is Labor Day; that capture carries `timestamp NaT` and sentinel
greeks (`iv -9.99`, `delta -999.0`) and should be treated as an artifact, not a
session. The other thirteen carry real timestamps at ~19:45 UTC (15:45 ET) and
sane greeks, and each has a committed `reports/schwab_chains/<session>/preclose.json`
on `main` with `names.NVDA.status = "ok"` and `overall_status = "ok"`. Two
further sessions (2026-08-31, 2026-09-01) have committed receipts recording an
honest Schwab OAuth failure, and 2026-09-04 has no receipt at all — the series is
a documented, gap-aware capture programme, not a stray file.

The mids track the underlying coherently (227.98 close → 12.625 at 22 DTE;
217.55 close → 5.600 the next session), so these are genuine quotes, not stale
bytes.

**Why this is a blocker.** Three things follow, and all three are load-bearing:

1. The quoted sentence is **false as written**, in a permanent append-only
   record, about the existence of evidence. That is worse than the Revision 2
   sentence L-2 removed, which was merely a wrong interpretation.
2. It is **self-contradicting within the same fact**. Eighty words later the
   fact says *"the Schwab pre-close capture of 2026-09-10 quotes the NVDA 220
   call expiring 2026-09-18 at bid 3.75 / ask 3.80"* and cites
   `reports/schwab_chains/2026-09-10/preclose.json`. That receipt is the last
   of a sixteen-session series the preceding paragraph denies exists. A 2027
   reader who opens the cited directory sees the other fifteen immediately.
3. The defensible version of this claim is **lane-scoped**, and the fact already
   knows the distinction — it says elsewhere *"This is a Schwab-lane mark and is
   NOT a registered H6 mark source."* What is true is that **no
   registered-lane (ThetaData chain) observation** exists after 2026-07-27, which
   is what OD-2 at `facts.log:19347` actually establishes and what I re-verified
   (`.cache/chains` last sessions 2026-07-22/23/24/**27**). The fact generalised
   a true statement about one lane into a false statement about all evidence.

**Replacement wording:**

> WHAT IS AND IS NOT OBSERVED: no observation on the registered H6 mark lane -
> the exact-session ThetaData chain - exists for this contract after 2026-07-27,
> which is why neither registered exit could be evaluated. Off that lane the
> repository does hold Schwab pre-close captures of this exact contract on 13
> sessions between 2026-08-14 and 2026-09-10, each with a committed session
> receipt under reports/schwab_chains/. These are not a registered H6 mark
> source and no exit is booked from them; they are recorded here so that no
> reader concludes the window is evidentially empty.

### M-2 — **BLOCKER** (Packet 1). On the observations that exist, the take-profit was never close, and the outage's cost is measurable rather than UNKNOWN.

**Exact text:**

> whether the plus 100 percent take-profit near 18.41 USD would have fired is
> **UNKNOWN on the available evidence - it is not ruled out**, and any statement
> that the position was out of reach throughout would be false.

and

> The position is orphaned by the data-provider exit: the cost of that outage is
> that neither registered exit could be evaluated at all, and **this fact does
> not claim the outage was costless**.

**Evidence.** The registered rule (`options_researcher/h6_watch.py:446`) is
`proceeds >= entry_cost * (1 + H6_TAKE_PROFIT_PCT)` with
`proceeds = adverse_sell(bid) * 100 - 0.65` and
`adverse_sell(p) = floor(p * 0.99 * 100)/100` (`strategies/base.py:17`,
`SLIPPAGE_HAIRCUT = 0.01`, `COMMISSION_PER_CONTRACT = 0.65`). Required proceeds:
**1841.30**. Applying it to the real bids:

| Session | bid | registered proceeds | P&L | % of entry | take-profit? |
|---|---|---|---|---|---|
| 2026-08-14 (best) | 13.50 | 1335.35 | +414.70 | **+45.04 %** | no |
| 2026-08-27 | 12.55 | 1241.35 | +320.70 | +34.83 % | no |
| **2026-08-28 (21-DTE)** | 5.55 | **548.35** | **−372.30** | **−40.44 %** | no |
| 2026-09-03 | 11.70 | 1157.35 | +236.70 | +25.71 % | no |
| 2026-09-10 | 3.75 | 370.35 | −550.30 | −59.77 % | no |

The best level reached in the entire window is **72.5 %** of the trigger
(1335.35 / 1841.30) — a gain of +45 % against a required +100 %. Not "within
4–8 % of firing". Round 2's Black-Scholes estimate is the source of that error:
it modelled the *intraday high* at an assumed σ of 0.45, whereas the captures
bracket the modelled 2026-09-04 peak of 17.70 at **11.75 (09-03)** and
**8.55 (09-08)**. The model overstated by roughly 45 %.

Two consequences:

- **"it is not ruled out" is wrong.** On the repository's own option data the
  take-profit was never within 27 percentage points of firing. Revision 2's
  deleted sentence was closer to the truth than Revision 3's replacement.
- **The outage's cost is a number, not an unknown.** A 21-DTE close on
  2026-08-28 would have realised **−372.30 (−40.44 %)**. The last mark implies
  **−550.30 (−59.77 %)**. The outage cost approximately **178.00**, and saying so
  is both more useful and more honest than UNKNOWN.

**Replacement wording:**

> On the Schwab captures described above the plus 100 percent take-profit was
> never approached: the highest bid observed in the window, 13.50 on 2026-08-14,
> corresponds to 1335.35 USD of registered conservative-fill proceeds against
> the 1841.30 USD the rule requires, or 72.5 percent of the trigger. On the
> 2026-08-28 21-DTE date the bid was 5.55, which under the registered fill model
> is 548.35 USD of proceeds and a loss of 372.30 USD, minus 40.44 percent
> (arithmetic). The outage was therefore not costless: had the registered time
> close been evaluable it would on this off-lane evidence have booked a loss
> near 40 percent rather than the near 60 percent the last mark implies. These
> figures are off the registered mark lane and no exit is booked from them.

### M-3 — **BLOCKER** (both packets). Six provenance paths cited inside the fact texts do not exist on `main`, and the guard forces the append onto `main`.

**Exact text (Packet 1):** "the three-option disposition packet at
**reports/2026-09-15-audit-edge-verdict-and-loose-ends.md** section 7 (drafting
record **reports/2026-09-15-audit/H-owner-fact-packets.md**, Revision 3) …
receipts **…/J-…**, **…/L-…** and **…/M-…**".
**Exact text (Packet 2):** "Source: **reports/2026-09-15-audit/A-evidence-audit.md**
section 4 item 1 and **reports/2026-09-15-audit-edge-verdict-and-loose-ends.md**
section 4 finding 1."

**Evidence.** Checked with `git cat-file -e origin/main:<path>`:

| Path | on the audit branch | on `origin/main` |
|---|---|---|
| `reports/2026-09-15-audit-edge-verdict-and-loose-ends.md` | tracked (`f228894`) | **absent** |
| `reports/2026-09-15-audit/A-evidence-audit.md` | tracked | **absent** |
| `reports/2026-09-15-audit/H-owner-fact-packets.md` | **untracked** | **absent** |
| `reports/2026-09-15-audit/J-fact-packets-adversarial-review.md` | **untracked** | **absent** |
| `reports/2026-09-15-audit/L-fact-packets-adversarial-review-round2.md` | **untracked** | **absent** |
| `reports/2026-09-15-audit/M-fact-packets-adversarial-review-round3.md` | does not exist until this file is written; untracked | **absent** |

`git merge-base --is-ancestor f228894 origin/main` → **no**; the audit branch has
not landed. Every *evidence* path in both texts (`reports/h6_forward/*`,
`reports/schwab_chains/2026-09-10/*`, `data/positions/h6_positions.csv`,
`reports/h9/receipt.json`, `tools/h9_run_study.py`, `config.py`,
`ledger/experiments.jsonl`, `ledger/README.md`, `.claude/rules/ledger.md`) **is**
on `main` and verified. It is precisely the provenance chain — source memo,
drafting record, all three review receipts — that is missing.

Meanwhile the guard *requires* `branch == main` and `HEAD == origin/main`. So the
command, working exactly as designed, produces a permanent ledger line in a tree
where none of its six provenance citations resolve. `.claude/rules/ledger.md`
requires "independent adversarial review of the exact text, then owner approval,
then append"; a receipt that is not in the repository is not evidence that step
happened.

This is L-4 one level up, and no prior round tested it. Note the irony: L-3
correctly demolished Revision 2's "land this branch first, then append" as a
non-solution to the *stale tree* problem, and Revision 3 removed the landing step
entirely — but landing the branch is now **required**, for a different reason.

**Fix — sequencing only; no word of either fact text changes.** Before either
append: commit `G`, `H`, `I`, `J`, `K`, `L`, `M`, `N` under
`reports/2026-09-15-audit/`; land `claude/audit-2026-09-15` on `main`; then in
the append tree `git pull --ff-only` and confirm all six paths resolve at
`origin/main` before running the command. **Recommended guard addition** (also no
text change):

```python
TOP = pathlib.Path(top)
for rel in ["reports/2026-09-15-audit-edge-verdict-and-loose-ends.md",
            "reports/2026-09-15-audit/A-evidence-audit.md",
            "reports/2026-09-15-audit/H-owner-fact-packets.md",
            "reports/2026-09-15-audit/J-fact-packets-adversarial-review.md",
            "reports/2026-09-15-audit/L-fact-packets-adversarial-review-round2.md",
            "reports/2026-09-15-audit/M-fact-packets-adversarial-review-round3.md"]:
    if not (TOP / rel).exists():
        sys.exit("REFUSED: %s is cited by this fact but is not in this tree. "
                 "Land the audit branch on main first. Nothing was appended." % rel)
```

(Packet 2 cites four of the six; list only the ones its own text names.)

### M-4 — **MUST-FIX** (Packet 1). The 18.41 figure has a wrong derivation and understates the registered trigger.

**Exact text:**

> The plus 100 percent take-profit corresponds to a mark near 18.41 USD per
> share **(arithmetic on the 9.20 USD entry ask)**.

**Evidence.** 2 × 9.20 = **18.40**, not 18.41. The figure 18.41 is
2 × (920.65 / 100) = 18.413 — i.e. it is derived from the **entry cost including
the 0.65 commission**, which the same sentence's companion clause explicitly
separates from the ask. The stated derivation does not produce the stated number.

Worse, "a mark near 18.41 per share" is not what the rule tests. Per
`h6_watch.py:440-446` the rule tests conservative-fill **proceeds**:
`floor(bid × 0.99 × 100)/100 × 100 − 0.65 ≥ 1841.30`, i.e. a raw **bid** of
**≈ 18.61**, and a mid higher still by half the spread. In a passage whose entire
purpose is to say how near the trigger came, the fact understates the bar by
~1.1 % on the bid and presents it as a "mark". The direction of the error is the
same as M-2's: it flatters the "not ruled out" conclusion.

**Replacement:**

> The plus 100 percent take-profit requires exit proceeds of at least 1841.30
> USD, which under the registered fill model (conservative sell at the bid less
> the 1 percent slippage haircut, less 0.65 USD commission) is a raw bid of about
> 18.61 USD per share (arithmetic on the 920.65 USD entry cost).

### M-5 — **MUST-FIX** (Packet 1). "The closes are reproduced in the drafting record" is false.

**Exact text:**

> (Repo-verified 2026-09-15 from .cache/underlying_ohlcv/NVDA.parquet, sha256
> c4c36936…, which is gitignored; **the closes are reproduced in the drafting
> record**).

**Evidence.** The drafting record names **four** of the twelve above-220 closes
(230.36, 225.30, 227.98, 228.45) in §1.1 and §1.2. It does not reproduce the
other eight. Since the parquet is gitignored and its sha256 is bound nowhere in
the repository (see M-10), that clause is the fact's *only* durability promise
for the 12-of-33 claim — and it does not hold.

**Fix that does not change the fact text:** add the full table to `H` §1.1, which
makes the sentence true. The twelve sessions with a close above 220 in
2026-07-27 … 2026-09-10 inclusive are: 08-07 223.96, 08-12 224.09, 08-13 225.30,
08-14 225.16, 08-17 225.01, 08-27 227.98, 08-31 220.78, 09-02 224.41,
09-03 228.45, 09-04 230.36, 09-08 225.73, 09-09 223.67. (Packet 1 is NOT READY
for other reasons, so in practice this will be folded into Revision 4.)

### M-6 — **MUST-FIX** (packet prose, both). Both append routes the packet recommends are impossible, and the command ships pointing at a directory that cannot be created.

**Exact text (§"Where to append from", and the orientation block in both §1.5 and §2.3):**

> - **Check out `main` there**, `git pull --ff-only` … or
> - **Make a fresh worktree** — `git worktree add .tmp/worktrees/facts-append main`

**Evidence.** `main` is already checked out at
`/Users/carsynstephenson/options-validator-ops` (`git worktree list`). Git
refuses to check out a branch twice:

- `git switch --no-guess main` in `/Users/carsynstephenson/options-validator` →
  `fatal: 'main' is already checked out at '/Users/carsynstephenson/options-validator-ops'`
  (run today; the primary tree was left on `claude/rest-2026-09-09`, unchanged).
- `git worktree add <path> main` on an exact throwaway analogue →
  `fatal: 'main' is already checked out at …`.

So the owner following the packet hits `fatal:` twice, and the `BASE` line the
command ships with points at
`/Users/carsynstephenson/options-validator/.tmp/worktrees/facts-append/ledger`,
a directory the shipped instruction cannot produce. Dry-run as-shipped confirms
it: Packet 2 → **rc 1**, *"…/facts-append is not a git checkout."*

`git worktree add --detach … main` is not an escape: the guard tests
`rev-parse --abbrev-ref HEAD == "main"`, and a detached worktree prints `HEAD`.

**The only route that works today is `/Users/carsynstephenson/options-validator-ops`**
— the one the packet presents as a grudging third option. It is on `main` at
`origin/main`, and both commands return **rc 0** against it. The packet's own
caveat is correct and verified: `~/bin/repo-reconcile` line 67 sets
`"$HOME/options-validator-ops"|"$HOME/options-validator-research") ro=1`, and
line 98 leaves uncommitted changes on a `main` checkout alone ("needs you"), so
nothing will commit or push the evidence commit for the owner.

**Replacement — both orientation blocks:**

```sh
cd /Users/carsynstephenson/options-validator-ops   # the only tree on `main`
git rev-parse --abbrev-ref HEAD                    # must print exactly: main
git pull --ff-only                                 # be at the tip of main
wc -l ledger/facts.log                             # note the count; re-check after
```

and set `BASE = pathlib.Path("/Users/carsynstephenson/options-validator-ops/ledger")`.
Add one sentence: repo-reconcile treats this tree as read-only and skips `main`,
so the owner commits and pushes the evidence commit by hand.

### M-7 — **MUST-FIX** (Packet 1 guard). The invariant hash leaves 579 characters unprotected, not three placeholder slots — and the unprotected region is the one L-5 exists to protect.

**Exact text (guard):**

```python
if hashlib.sha256((TEXT.split("NVDA official closing price 2026-09-18:")[0] + "|"
                 + TEXT.split("BOOK ROW:")[1]).encode()).hexdigest() != "397d7d54…":
```

**Evidence.** Everything between those two markers is excluded — **579 of 9,091
characters, 6.4 % of the fact** — not just the three `<…>` slots. That region
contains the entire `Official-source` / `Vendor-source` labelling instruction,
the named Yahoo vendor path, and the intrinsic-value formula. Demonstrated
(stubbed, `rc 0`): I replaced the whole span with

> NVDA official closing price 2026-09-18: 213.40 USD (source: a blog post I found;
> Official-source). Intrinsic value of one 220 strike call at that closing price:
> 9999.00 USD (equals whatever I want).

and the guard **passed**, calling `append_fact` with the right prefix. Citing a
blog as `Official-source` is the exact thing `.cursorrules` forbids and L-5 was
raised to prevent, and an unconstrained intrinsic value defeats the fact's only
arithmetic check. The guard advertises "any edit outside the three placeholder
slots refuses"; it does not.

**Replacement — hash the fixed prose *between* the slots too, not just around
them** (no fact-text change; only the pinned constant moves):

```python
import re
SKEL = re.sub(r"(NVDA official closing price 2026-09-18: ).*?( \(source: ).*?(\)\. Intrinsic value of one 220 strike call at that closing price: ).*?( \(equals)",
              r"\1<>\2<>\3<>\4", TEXT, flags=re.S)
```
then hash `SKEL` in full. Simpler and just as good: keep the three original
placeholder strings in a list, `TEXT.replace(ph, "<>")` for each, and hash the
result — that protects 100 % of the reviewed prose and still permits exactly the
three substitutions.

### M-8 — **MUST-FIX** (both guards). The lineage rule passes on a stale tree with an uncommitted local edit to `facts.log`.

**Evidence.** The rule is sound on the axis it tests. `git fetch --quiet origin
main` does update `refs/remotes/origin/main` (the clone carries the standard
`+refs/heads/*:refs/remotes/origin/*` refspec, verified), so a tree rolled back
behind its own origin is caught: I rolled a clone back three commits, forced
`origin/main` to match, and the guard still refused —
*"REFUSED: HEAD 3537ca7… is not origin/main a3745ab…"*. Good.

But the rule tests HEAD against **whatever `origin` happens to be**, and never
looks at the working tree. Demonstration (stubbed): a checkout at `/tmp/ov-stale`
on a branch named `main`, equal to *its own* `origin/main`, whose `origin` is a
stale local repository 17 lines behind the real `main`, **and with an
uncommitted appended line in `ledger/facts.log`** → Packet 2 returned **rc 0**:

```
tree:   /private/tmp/ov-stale on main at 3537ca7269e820785a27f7eb6cc067bb9f6d39f4
target: /private/tmp/ov-stale/ledger/facts.log
lines before: 19611
```

The only signal the owner gets is the printed `lines before:` count being 19,611
instead of ≥ 19,627 — an eyeball check, which is precisely what F-12 and L-3
decided was insufficient.

The dirty-tree half is not hypothetical. `~/bin/repo-reconcile` line 98
explicitly **leaves uncommitted changes on a `main` checkout alone**, so an
un-rescued dirty `ledger/facts.log` on the append tree is a state the daily job
is designed to produce and preserve.

**Replacement (both commands), immediately after the `HEAD == origin/main` check:**

```python
_, dirty, _ = git("status", "--porcelain", "--", "ledger/facts.log")
if dirty:
    sys.exit("REFUSED: ledger/facts.log has uncommitted local changes in %s (%s). "
             "Appending on top of an uncommitted divergence of an append-only file "
             "is the hazard this guard exists for. Nothing was appended." % (TREE, dirty))
```

### M-9 — **SHOULD-FIX** (both guards). The guard never checks it is in the right repository.

Nothing compares `git remote get-url origin` to
`https://github.com/carsynstephenson16-lang/options-validator.git` (verified as
the real remote). Any checkout on a branch called `main`, at its own
`origin/main`, containing a `ledger/facts.log`, is accepted. Combined with M-8
this is how the `/tmp/ov-stale` attack succeeded. One line closes it:

```python
_, url, _ = git("remote", "get-url", "origin")
if not url.endswith("carsynstephenson16-lang/options-validator.git"):
    sys.exit("REFUSED: origin is %s, not the options-validator remote. Nothing was appended." % url)
```

### M-10 — **SHOULD-FIX** (Packet 1). `Repo-verified` is the wrong label for a gitignored file, and the sha256 cited is bound nowhere.

**Exact text:** "(**Repo-verified** 2026-09-15 from .cache/underlying_ohlcv/NVDA.parquet,
sha256 c4c36936…, **which is gitignored**…)".

The packet's own preamble defines **Repo-verified** as "read out of a file in
this repo; path given" and carves cache reads out of **Run-verified** precisely
because they are not in the repo. §1.1 labels this same row **Run-verified**. The
fact text uses the other label, for a file it simultaneously describes as
gitignored. Pick one; `Run-verified (cache)` is the honest one.

Second, `grep -rl c4c36936…` across the whole `main` checkout returns **nothing**:
no receipt, no facts.log line binds that hash. The durable anchor that *does*
exist is `facts.log`'s `DATA_PULL_OHLCV 2026-09-15: Yahoo OHLCV refresh NVDA
rows=2437 path=.cache/underlying_ohlcv/NVDA.parquet` — and the file does have
exactly **2,437** rows (verified). Cite that instead of, or alongside, an
unanchored sha256. (Note the line number for it sits in the divergent tail —
cite it by key and date, not by line.)

### M-11 — **SHOULD-FIX** (Packet 1). "12 of the 33 sessions" mixes an exclusive and an inclusive reading of the same window in consecutive sentences.

"no option observation … **between** 2026-07-27 and 2026-09-10" reads
exclusively (there are marks on both endpoints). "12 of the **33** sessions in
that window" is the **inclusive** count. Strictly between the marks there are
**31** sessions. The numerator is robust — 12 either way, since neither endpoint
closes above 220 — but a 2027 reader recomputing the denominator gets 31 and
concludes the fact is wrong. **Fixable without touching the fact text:** §1.1 of
`H` already defines the window as "Between the two marks (2026-07-27 →
2026-09-10) there are 33 sessions"; add "inclusive of both endpoint sessions" so
the drafting record the fact cites settles it. (For the record, the inclusive
counts are 33 sessions, 12 closes above 220, 21 highs above 220; exclusive, 31 /
12 / 20.)

### M-12 — **NOTE** (packet prose). The Black-Scholes "reproduces exactly" claim is slightly overstated, and the inference itself is now falsified.

§1.1 says "The round-2 reviewer's figures reproduce **exactly**." I reproduce
H's own figures exactly (2026-08-13: 15.69 / 17.03; 08-27: 15.38 / 16.36; 09-04:
17.06 / 17.70, r = 4 %, calendar-day T, S = session high). But L's σ = 0.40 value
for 2026-08-13 was **16.0**, not 15.69 — one of eight figures differs by 2 %, and
H silently corrected it while claiming exact reproduction. Cosmetic in itself;
listed because §1.1 leans on that reproduction as corroboration. M-2 supersedes
the whole exercise: the real quotes put the modelled peak ~45 % too high. The
Inference label and the decision to keep these numbers out of the fact were both
correct.

### M-13 — **NOTE** (both). The L-9 rewrite now asserts an interpretation of the rule rather than admitting a gap.

`.claude/rules/ledger.md` orders three steps: "independent adversarial review of
the exact text, **then owner approval, then append**". The texts now say the
append *is* the approval. L-9 moved this from a negative admission to a positive
assertion, which is better reading but makes the fact argue with the rule in the
permanent record. The substance is fine — the owner reading the text and running
the command genuinely is approval — and the A2 precedent at `facts.log:19553`
(`owner-approved 2026-08-31 source=<receipt path>`) would need a separate receipt
to imitate, i.e. a text change. **Acceptable as-is**; noted so nobody is
surprised by it in 2027.

### M-14 — **NOTE** (packet §3 item 1). Two different caches are presented as one.

`reports/closes_receipts/2026-09-15/guarded-all-cached.json` records
`stored_file: .cache/underlying/NVDA.parquet`, sha256 `5140617d…`. The packet
cites it in the same breath as `.cache/underlying_ohlcv/NVDA.parquet`
(sha256 `c4c36936…`) — a different file, refreshed by a different producer
(`DATA_PULL_OHLCV` vs `data.recent_topup.refresh_closes_guarded`), with **no**
receipt covering it. Both files exist and both figures verify; the receipt just
does not cover the parquet the packet leans on. Packet prose only.

### M-15 — **NOTE** (both). How the evidence commit gets pushed is not actually settled.

The packet says the owner "pushes themselves". Verified: `repo-reconcile` skips
`main`/`master`/`deploy/*` for rescue-commits (line 98), pushes (line 142) and
PRs (line 174), and skips the ops and research checkouts entirely (lines 67,
90-92, 265). So nothing automatic will move it — correct. But the guard requires
being **on `main` at `origin/main`**, so the resulting commit sits on `main`
locally, and `git push origin main` bypasses the PR-and-green-checks flow the
automerge machinery assumes, and may be refused by branch protection. Worth one
sentence: after the append, `git switch -c claude/facts-append-2026-09-19`,
commit there, push, and let the normal flow land it. The guard's precondition was
satisfied at append time regardless.

### M-16 — **NOTE**. The five `facts.log` line numbers are valid in every checkout, and the fact should *not* qualify them.

Lines **17892**, **19346**, **19347**, **19413** and **19553** carry exactly the
cited records in all three trees — `main` (19,627 lines), the primary checkout on
`claude/rest-2026-09-09` (19,610) and this audit worktree (19,614). The three
copies diverge only in the tail above 19,553, so every cited line is below the
divergence point. Because `facts.log` is append-only, earlier line numbers can
never move. **The fact texts should stay as they are and should not name a
checkout** — adding a qualifier would imply a fragility that does not exist, and
would itself go stale. (I re-read each line in full on `main`: the OD-2 quotation
in Packet 1 and the `METRIC_CORRECTION` paraphrase in Packet 2 are both faithful
to the source, including "the final canonical chain edge remains 2026-07-27;
decision-authoritative consumers must fail closed beyond exact cached coverage"
and the "expressly NOT a daily-NAV or generic chronological drawdown" gloss. OD-4
in line 19347 is indeed the ThetaData **access** cutoff of 2026-08-01, as the
packet says.)

---

## §3. Direct answers to the questions asked

**Q2 — every number, hash, path, line number, `seq`, `record_hash` and date,
re-derived.** Independently re-derived today. Unless marked, verified in the
`main` checkout `/Users/carsynstephenson/options-validator-ops` at `a3745ab` =
`origin/main`.

*Packet 1.* `experiments.jsonl` seq 6: `entry_type trial_intent`,
`hypothesis_id H6`, `timestamp 2026-07-09T00:50:22.721232+00:00`,
`record_hash 5d813b8f…` — all exact; the seq 6 exit sentence quoted in §1.1
matches byte for byte including the parenthetical; the 8-completed verdict rule
and the separate 3-consecutive-month hard kill are both present as described.
Seq 22: `H6_KILL_V2`, `record_hash 4c552641…`, "effective only for H6 entries on
or after 2026-08-03", "Existing H6 rows retain v1" — exact. `h6_positions.csv`
row: `H6-0001,NVDA,220.0,2026-09-18,1,2026-07-13,920.65,cc8ccd80…,,,,` — four
blank exit columns confirmed against the header
(`exit_date,exit_proceeds,exit_reason,exit_receipt_hash`). `reports/h6_forward/`
holds exactly five files, 07-13 / 07-22 / 07-23 / 07-24 / 07-27.
`2026-07-13.json receipt_hash = cc8ccd80d8fdd4712d0e7fceada160c60dec21341f3bb02a823e9f29e2f2e8c0`.
`2026-07-27.json receipt_hash = c4b3138dd87053c7bf7b254b236df55b2304b9a5ebfbe056ed8e4739ac23e464`,
`exits[0] = {action HOLD, dte 53, pnl -441.3, proceeds 479.35, reason
no_exit_trigger, position_id H6-0001}`, `score = {completed_positions 0,
verdict INSUFFICIENT_SAMPLE, reason "requires 8 completed positions"}`.
`config.py:347-349` = `H6_TAKE_PROFIT_PCT 1.00` / `H6_CLOSE_AT_DTE 21` /
`H6_MIN_COMPLETED_POSITIONS 8`, exactly those lines. Dates: 2026-09-18 is a
Friday; 2026-07-27 → 2026-09-18 = **53** days, matching the receipt's `dte`;
2026-09-18 − 21 days = **2026-08-28**, also a Friday. Arithmetic:
−441.30 / 920.65 = **−47.933 %**; (377.50 − 920.65)/920.65 = **−58.9964 %**;
mid (3.75+3.80)/2 = 3.775 → 377.50. Schwab 09-10 row: bid 3.75, ask 3.80,
delta 0.463, iv 0.33917, open_interest 43021, timestamp
`2026-09-10 19:45:33.824000+00:00` — exact. Bindings: `preclose.json` has a
`names` key, `names.NVDA.path = .cache/schwab_chains/NVDA_2026-09-10.parquet`,
`sha256 9df5291708fef0d0a6d6485fe5489a793befd9ef905654c62aebfd6f0e542a0f`,
`status ok`; `manifest.json` has `files` and **no** `names`, `files.NVDA.path`
is the bare filename with the same sha256; both `manifest_hash
4a4d69702261018660d5ae41734b2086f181c51588397cb7904ff841016c4d63`;
`shasum -a 256` of the parquet reproduces `9df52917…`. Chain cache last sessions
2026-07-22/23/24/**27**.

*The NVDA OHLCV parquet.* `/Users/carsynstephenson/options-validator-ops/.cache/underlying_ohlcv/NVDA.parquet`
— sha256 **`c4c36936dac20a948a21e6add93606ffe6b89e8a5f50242c42985c5aef783b93`**,
**2,437** rows. The primary checkout's copy is byte-identical (same sha256), so
the packet's "cache reads resolve to `~/options-validator/.cache/`" carve-out is
harmless here. Window 2026-07-27 … 2026-09-10 **inclusive**: 33 sessions, **12**
closes above 220, 21 highs above 220, max close **230.36** and max high
**234.76**, both 2026-09-04 — all confirmed. Strictly between: 31 / 12 / 20
(**M-11**). Spot checks confirmed: 225.30 on 08-13, 227.98 on 08-27, 228.45 on
09-03. `2026-09-14 → 210.960007` confirmed.

*The 18.41 arithmetic.* 2 × (920.65/100) = **18.413**; 2 × 9.20 = **18.40**. The
fact's stated derivation does not yield its stated number, and the registered
trigger is a bid of ≈ **18.61**, not a mark of 18.41 — **M-4**.

*Packet 2.* `shasum -a 256 reports/h9/receipt.json` =
`30df74c4e91e0b23c28d7e70391da6d851feb7b21084bf9ab27ae417a63e7a93`.
`git log --format=%h -1 -- reports/h9/receipt.json` = `d91b1ec`, and
`git log --all` shows that is the only commit the file has ever had (2026-07-18).
`tools/h9_run_study.py:28` is `RECEIPT_PATH = Path("reports/h9/receipt.json")`;
lines **169-171** are the `bulk = {"trades","trade_log","board","census"}`
exclusion and the two-line `sha256_hex(canonical_json(...))` call — exactly as
cited. The nine sealed keys are `code_sha, config_hash, cost_model_hash,
n_trades, no_trade_log_count, outcome, secondary_cohort_informational,
spec_sha256, study`, and hashing exactly those nine **reproduces
`5bea2018fa204b2b3bfc221fee2b43f669ce9ff5b90270515dbc267084df3c06`**, matching
the value recorded in the receipt and in `facts.log:17892`. `board` carries
`expectancy_per_trade 290.32499…`, `expectancy_CI90 [27.82187…, 574.4625…]`,
`total_pnl 4645.1999…`, `n_trades 16`, `n_losses 4`, and
`return_on_economic_max_loss = NaN`; `trades` has 16 rows; both are outside the
seal. `canonical_json(full receipt)` raises
`ValueError: Out of range float values are not JSON compliant: nan` — the
packet's "it raises, it does not merely differ" correction stands.
`config.py:189` = `MIN_LOSSES_FOR_VERDICT = 10`.
`grep -rn receipt_hash options_researcher/h9_*.py` → no match; the only code
reference to `reports/h9/receipt.json` anywhere is `tools/h9_run_study.py:28`
(the other hits are `ledger/facts.log`, `wiki/`, `docs/` and `reports/` prose);
nothing in `tests/` reads it either. `A-evidence-audit.md` has `## §4 The three
most load-bearing integrity risks` and no `§4.1`, so "section 4 item 1" is right.

*facts.log line numbers.* See **M-16** — all five valid in all three checkouts;
no qualifier needed.

**Discrepancies found, in full:** M-1 and M-2 (false claims inside the Packet 1
fact text); M-3 (six provenance paths absent from `main`, both packets); M-4
(18.41 derivation and trigger level); M-5 ("the closes are reproduced in the
drafting record"); M-6 (both recommended routes impossible); M-10 (label and
unanchored sha256); M-11 (33 vs 31); M-12 and M-14 (packet prose only).
**No hash, `seq`, `record_hash`, line number or receipt path in either fact text
is wrong.**

**Q3 — dry-running both guarded commands against a stubbed `append_fact`.**
All rc values observed, `append_fact` never real:

| Scenario | Result |
|---|---|
| P1 as shipped, 2026-09-15, placeholders present | **rc 1** — date gate: *"It is 2026-09-15T12:33:09…-04:00 in New York, before 2026-09-19 00:00."* |
| P1, date gate satisfied, placeholders still present | **rc 1** — *"unsubstituted placeholder in the fact text."* |
| P1, substituted, tree on `main` at `origin/main` | **rc 0** — `tree: …ops on main at a3745ab…`, `lines before: 19627`, stub called with `dedupe_prefix=H6_0001_UNMARKED_EXPIRY`, prefix assertion passed |
| P1, substituted, primary checkout | **rc 1** — *"is on branch claude/rest-2026-09-09, not main."* |
| P1, substituted, tampered outside placeholders (`12 of the 33` → `2 of the 33`) | **rc 1** — invariant sha256 mismatch |
| **P1, substituted, whole source/intrinsic span rewritten** | **rc 0 — PASSES. See M-7.** |
| P2 as shipped (`facts-append` does not exist) | **rc 1** — *"is not a git checkout."* |
| P2, tree on `main` at `origin/main` | **rc 0** — `lines before: 19627` |
| P2, primary checkout / audit worktree | **rc 1** — branch check |
| P2, tampered text (`4 losses` → `9 losses`) | **rc 1** — invariant sha256 mismatch |
| **P2, stale wrong-origin tree on `main`, `facts.log` dirty** | **rc 0 — PASSES. See M-8/M-9.** |

Invariant hashes: P1 `397d7d54647ac74f89e89729fb6d4e1a0e5bb8e335c1274088de2e75a744b09e`
and P2 `c837b27e522f0c9c300e3163985a1b0aab7549dc1cde55baa77b1a7b5dfb10f4`, both
recomputed from the blockquotes and both matching the pinned constants. Both
blockquotes are **character-identical** to what the commands pass (9,091 and
4,638 characters). Neither text contains `'`, `"`, `$`, backtick, `!` or a
non-ASCII byte. Both `TEXT.startswith(KEY)`. Each split marker occurs exactly
once in the P1 text.

**Q4 — pre-decision, legislating, changed numbers, unguarded future tense,
unknowable claims.**

- *A decision the owner has not made?* **No.** Both texts condition approval on
  the owner running the append. Options (b) and (c) are named neutrally and the
  agent's reasons are pushed to the drafting record. One residue, **M-13**.
- *Legislating from an advisory log?* **No.** Packet 2's `RECOMMENDED FORWARD
  PRACTICE, NOT BINDING BY THIS FACT` disclaims it explicitly. Packet 1's
  expiration-intrinsic convention is labelled `Assumption`, scoped to "this fact
  and nowhere else", and paired with `NO RETROACTIVE RULE CHANGE`. Adequate.
- *Changing a registered number or verdict?* **No.** H6 stays
  `INSUFFICIENT_SAMPLE` at n = 0 against the 8-completed bar (seq 6 and
  `config.py:349` both re-checked); seq 22 untouched; H9 stays
  `INSUFFICIENT_SAMPLE`, 16 trades / 4 losses against
  `MIN_LOSSES_FOR_VERDICT = 10` (`config.py:189`), one run SPENT; no board value
  or trade row moves.
- *A future event stated as past, unguarded?* **No — closed.** The date gate is
  real and refused today at rc 1, and the text says so itself.
- *Knowledge about 2026-07-27 → 2026-09-10 it cannot have?* **The opposite, and
  it is a blocker.** The fact claims an *absence* of knowledge that it does not
  have grounds for. Offending sentences, quoted:

  > "no option observation of any kind exists for this contract between
  > 2026-07-27 and 2026-09-10"

  > "what the position was worth across that window - including on the
  > 2026-08-28 21-DTE date - is unknown, and this fact asserts nothing about it"

  > "whether the plus 100 percent take-profit near 18.41 USD would have fired is
  > UNKNOWN on the available evidence - it is not ruled out"

  All three are contradicted by fourteen captures of exactly this contract held
  in the repository, with committed receipts on `main`. See M-1, M-2.

  One further sentence is now wrong for the same reason, in the packet's §1.3
  rather than the fact: *"every close must cite a watch receipt and none for
  2026-08-28 can be produced — the chain stops at 07-27 and the H6 evaluator has
  no Schwab data path."* The second clause is true and is the real obstacle
  (`grep schwab options_researcher/h6_watch.py` → nothing). The first
  overstates: the **data** for 2026-08-28 exists with a committed `status: ok`
  receipt; what is missing is an evaluator wired to that lane. This makes
  option (c) considerably more live than the packet presents it, and it should
  be corrected before the owner chooses between (a), (b) and (c).

**Q5 — is the lineage rule sound?** On the axis it tests, yes, and the `fetch`
is what makes it work (verified: `git fetch origin main` does update
`refs/remotes/origin/main`, so a locally rolled-back tree is caught). It is
strictly stronger than the directory test, and the packet's stated deviation from
a blanket `.tmp/worktrees` refusal is correctly reasoned and correctly
documented. **But it can be satisfied by a stale or wrong tree** — demonstrated
at rc 0 against a checkout on a branch named `main`, equal to its own
`origin/main`, whose origin is not this repository and whose `ledger/facts.log`
carried an uncommitted edit (**M-8**, **M-9**). **The advice on which checkout to
use is wrong** — both recommended routes are impossible because `main` is already
checked out at `options-validator-ops`, which is the only tree that works
(**M-6**). **The read-only claim about the ops checkout is correct** — verified
at `~/bin/repo-reconcile:67` (`ro=1`) and `:98` (uncommitted changes on a `main`
checkout are left alone) — so the owner really must commit and push by hand; but
how to push a commit made directly on `main` is not addressed (**M-15**).

**Q6 — what a 2027 reader would misread.**
(i) That the 2026-07-27 → 2026-09-10 window is evidentially empty, when the
repository holds fourteen quotes of the contract — and that the take-profit might
have fired, when the best observed level was 72.5 % of the trigger (**M-1**,
**M-2**). This is the most consequential item in this review, as L-2 was in the
last.
(ii) That the fact's provenance can be checked, when none of the six cited
documents is in the tree the fact was appended to (**M-3**).
(iii) That the take-profit trigger was a mark of 18.41 derived from the 9.20 ask,
when it was conservative-fill proceeds of 1841.30, i.e. a bid near 18.61
(**M-4**).
(iv) That the twelve above-220 closes are recoverable from the drafting record
(**M-5**).
(v) That a gitignored parquet's sha256 is verifiable against something in the
repository (**M-10**).
(vi) That the window is 33 sessions when the preceding sentence defines it
exclusively at 31 (**M-11**).
(vii) That the rule's separate owner-approval step was performed as the rule
words it (**M-13**).
(viii) That `git worktree add .tmp/worktrees/facts-append main` is a command they
can run (**M-6**).

---

## §4. What must change before each packet goes to the owner

**Packet 1 — NOT READY.** Blocking: **M-1**, **M-2** (false claims in the fact
text), **M-3** (provenance), **M-4**, **M-5**. M-1, M-2, M-4 and M-5 all require
the fact text to change, so **the Packet 1 text must not be appended as-is**. A
Revision 4 is needed, the invariant sha256 `397d7d54…` must be recomputed against
it, and the review citation inside the fact must move from `M` to a round-4
receipt — this file reviewed words that will not be the words appended. Also
apply M-7, M-10, M-11 and the §1.3 option-(b) correction in Q4 above; M-6, M-8
and M-9 are shared with Packet 2. The owner should re-read §1.3 before choosing
between (a), (b) and (c): the discovery in M-1 changes the trade-off.

**Packet 2 — READY WITH FIXES. The fact text may be appended exactly as written.**
Nothing in this review asks for a character of it to change, so the invariant hash
`c837b27e…` stands and the `M` citation inside it is accurate. Before running it:

1. **M-3** — commit the `reports/2026-09-15-audit/` documents and land
   `claude/audit-2026-09-15` on `main`, then confirm
   `reports/2026-09-15-audit/A-evidence-audit.md`,
   `reports/2026-09-15-audit-edge-verdict-and-loose-ends.md`,
   `…/H-owner-fact-packets.md`, `…/J-…`, `…/L-…` and `…/M-…` all resolve in the
   append tree. Optionally add the path-existence guard clause.
2. **M-6** — set `BASE` to `/Users/carsynstephenson/options-validator-ops/ledger`
   and replace both orientation blocks; the shipped `facts-append` route cannot
   be created.
3. **M-8** and **M-9** — add the dirty-tree and origin-URL checks.
4. Re-run the two re-confirmation commands in §2.3 (`shasum -a 256
   reports/h9/receipt.json` → `30df74c4…`, `git log --format=%h -1` → `d91b1ec`);
   both still hold today.

None of 1–4 alters a character of the Packet 2 fact text.

---

*Nothing in this review was appended to any ledger. No ledger-writing tool was
called; `append_fact` was exercised only against a local stub that captured its
arguments and asserted the prefix invariant. No commit was made, no packet or
ledger file was modified, the throwaway clones used to attack the lineage guard
were deleted, and the only file created is this one.*
