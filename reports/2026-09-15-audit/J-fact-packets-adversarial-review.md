# J — Independent adversarial review of the two drafted ledger fact texts

**Target:** `reports/2026-09-15-audit/H-owner-fact-packets.md`
**Reviewer stance:** show how each fact text could be lying, over-claiming,
pre-deciding, or unsafe to append. Not a confirmation pass.
**Date:** 2026-09-15. **Worktree:** `.tmp/worktrees/audit-0915`, branch
`claude/audit-2026-09-15`.
**Nothing was appended. Nothing was committed. The packet file was not edited.
`append_fact` was never called for real — the two one-liners were executed
against a stubbed `append_fact` that only captured its arguments.**

Rules checked against: `.claude/rules/ledger.md`, `.cursorrules` (claim
discipline, vocabulary discipline), `CLAUDE.md` (owner owns the numbers and the
ratifications), and the three cited `ledger/facts.log` precedents —
19413 `H10A_RESULT`, 19553 `A2_ENTRY_CONVENTION_RATIFIED_V1`, and the failure
mode at 19511 `A2_ENTRY_CONVENTION_CORRECTION_V1`. A fourth precedent,
19346 `METRIC_CORRECTION`, turns out to be the most load-bearing one and the
packet does not cite it.

---

## §0. Re-verification sweep — every number, hash, path, line, seq and date

All re-run independently on 2026-09-15. "OK" = reproduced exactly.

### Packet 1 (H6)

| Packet claim | Result |
|---|---|
| `experiments.jsonl` seq 6, `entry_type trial_intent`, `hypothesis_id H6`, `record_hash 5d813b8f…`, timestamp `2026-07-09T00:50:22.721232+00:00` | OK (`record_hash 5d813b8fe0e89f2d04fe41c9b16561e2374ff873d784a3cd9f2c91e4fe52f3cf`) |
| Registered exit prose: "close at 21 DTE at conservative fills OR take-profit at +100% of premium, whichever first; NO stop-loss" | OK, verbatim in seq 6 `reason` |
| Reject after 8 completed if CI90 upper < 0; continue if CI90 lower > 0 | OK |
| seq 22 `H6_KILL_V2`, 2026-08-02, prospective for entries on/after 2026-08-03, existing rows keep v1 | OK (`record_hash 4c552641…`, timestamp `2026-08-02T20:08:45.166385+00:00`) |
| Position row `H6-0001,NVDA,220.0,2026-09-18,1,2026-07-13,920.65,cc8ccd80…` with four blank exit columns | OK, byte-for-byte |
| `cc8ccd80d8fdd4712d0e7fceada160c60dec21341f3bb02a823e9f29e2f2e8c0` = `receipt_hash` of `reports/h6_forward/2026-07-13.json` | OK |
| `reports/h6_forward/` holds exactly 07-13, 07-22, 07-23, 07-24, 07-27 | OK |
| 07-27 receipt: `H6-0001` `action HOLD, dte 53, pnl -441.3, proceeds 479.35, reason no_exit_trigger`; score `completed_positions 0, verdict INSUFFICIENT_SAMPLE, reason "requires 8 completed positions"`; `receipt_hash c4b3138d…` | OK, all six fields |
| Canonical chain cache last session 2026-07-27 across all names, NVDA included | OK **in the main checkout** — see F-11 |
| 21-DTE date = 2026-08-28; 07-27 → 09-18 is 53 calendar days | OK (2026-08-28 is a Friday; 53 days) |
| `config.py:347-349` = `H6_TAKE_PROFIT_PCT 1.00`, `H6_CLOSE_AT_DTE 21`, `H6_MIN_COMPLETED_POSITIONS 8` | OK, exact line numbers |
| Schwab 09-10 NVDA 220C exp 2026-09-18: bid 3.75 / ask 3.80, delta 0.463, iv 0.33917, OI 43021, ts `2026-09-10T19:45:33.824Z` | OK, single matching row (index 268) |
| Parquet sha256 `9df5291708fef0d0a6d6485fe5489a793befd9ef905654c62aebfd6f0e542a0f` matches the receipt binding | OK on disk; **but see F-6 for where that hash actually lives** |
| mid 3.775 → $377.50 vs $920.65 = −$543.15 = −59.0% | OK (−58.9964%) |
| −$441.30 = −47.9% of $920.65 | OK (−47.93%) |

### Packet 2 (H9)

| Packet claim | Result |
|---|---|
| `shasum -a 256 reports/h9/receipt.json` = `30df74c4e91e0b23c28d7e70391da6d851feb7b21084bf9ab27ae417a63e7a93` | OK |
| `git log --format=%h -1 -- reports/h9/receipt.json` = `d91b1ec` | OK; also `git log --all` → one commit; `git show d91b1ec:…` hashes to `30df74c4…`; working tree clean |
| Hash excludes `{"trades","trade_log","board","census"}` at `tools/h9_run_study.py:169-171` | OK, exact line numbers (169 `bulk = …`, 170-171 the `sha256_hex(canonical_json(...))` call) |
| Nine sealed keys: `code_sha, config_hash, cost_model_hash, n_trades, no_trade_log_count, outcome, secondary_cohort_informational, spec_sha256, study` | OK |
| **Recomputed by me:** `sha256_hex(canonical_json(nine keys))` = `5bea2018fa204b2b3bfc221fee2b43f669ce9ff5b90270515dbc267084df3c06` | **OK — reproduces the recorded hash exactly** |
| `5bea2018…` is the hash in `ledger/facts.log:17892` (`H9_RESULT 2026-07-18`) | OK |
| `board` holds `expectancy_per_trade` 290.32499…, `expectancy_CI90` [27.82, 574.46], `total_pnl` 4645.1999…; `trades` has 16 rows; both outside the seal | OK (`+290.32` / `4645.20` are correct roundings) |
| `canonical_json` on the full document raises `ValueError: Out of range float values are not JSON compliant: nan` | OK — `board.return_on_economic_max_loss` is `NaN`; `research/hashing.py` sets `allow_nan=False` |
| H9 = INSUFFICIENT_SAMPLE, 16 trades, 4 losses, 10-loss bar (`config.py:189 MIN_LOSSES_FOR_VERDICT = 10`) | OK |

### Discrepancies found in the sweep

Only three, all small, all listed as findings below: **F-6** (manifest key name),
**F-11** (which checkout the cache claim was verified in), **F-13** (`§4.1` is
cited but memo A has no `§4.1` heading). Every hash, every number, every seq,
every line number and every date in both fact texts reproduced. The
recomputation in §2.1 of the packet is honest and I got the same answer.

### Mechanical equivalence of blockquote and one-liner

Both `python -c` blocks were parsed and executed against a stubbed
`append_fact`. For each packet the text passed to `append_fact` is
**character-identical** to the reviewed blockquote after whitespace
normalization. P1 = 4,117 chars, P2 = 2,705 chars. So reviewing the blockquote
is equivalent to reviewing what would be appended. That part of the packet is
sound.

---

## §1. Findings

### F-1 — BLOCKER (Packet 1). The fact asserts an owner decision that has not happened, in the past tense, and its own cited source says the opposite.

**Exact text at issue:**

> Owner ratification: option (a) of the 2026-09-15 disposition packet (…) **was
> presented to the owner with all three options and the owner selected (a)**, let
> it expire and append a disclosure fact.

and later:

> Options (b) … and (c) … **were both presented and not selected**; (b) **was
> declined because** … and (c) governs future entries only …

**Evidence.** The cited source, `reports/2026-09-15-audit-edge-verdict-and-loose-ends.md`
§7, is titled "H6-0001 disposition packet (**owner ruling needed** before Friday)"
and its options table is headed "**owner picks; nothing pre-filled**". The
packet's own §1.3 marks (a) "**RECOMMENDED**" and §1.4 leaves the ratification
line blank (`**Owner ratification: ______**`). So at drafting time the selection
had not been made, the drafting agent recommended it, and the fact text records
it as an accomplished owner act with the agent's reasons attributed to the owner.

This is not identical to the A2 failure mode — there, the *agent* appended the
approval record (`facts.log:19511`: "appended by the implementing agent … no
committed owner-approval receipt exists … That line is VOID as an approval
record"). Here the owner runs the command himself. But the structural defect the
A2 correction actually punishes is named in its own words: "**the agent wrote
its own gate input**." A pre-filled "the owner selected (a)" is an agent-written
gate input that the owner's keystroke merely blesses. And the H10A precedent the
packet says it follows is *not* this shape: H10A's ratification clause was
written **after** the owner selected "Write it today" in-session, and it names
the date, the setting, and the walkthrough that preceded it.

The correct in-repo template is `METRIC_CORRECTION` (`facts.log:19346`), which
the packet does not cite:

> Provenance: agent-drafted under owner direction 2026-07-30; independently
> adversarially reviewed 2026-07-31; append remains owner-gated and must use
> `research.facts.append_fact`.

That clause claims nothing about a selection. It is true whether or not the
owner ever appends, and it is still true the moment he does.

**Replacement wording.** Replace the entire "Owner ratification: …" clause with:

> Provenance: agent-drafted 2026-09-15 as option (a) of the three-option
> disposition packet at reports/2026-09-15-audit-edge-verdict-and-loose-ends.md
> section 7 (drafting record reports/2026-09-15-audit/H-owner-fact-packets.md,
> independent adversarial review reports/2026-09-15-audit/J-fact-packets-adversarial-review.md).
> The owner ratifies option (a) by appending this fact; the act of appending it
> through research.facts.append_fact IS the ratification and no separate prior
> approval is claimed here. Options (b) record a late time_21_dte close at a
> reconstructed mark and (c) amend H6 prospectively onto a Schwab-lane evaluator
> were drafted alongside (a) and are not adopted by this append. The drafting
> agent's stated reasons for preferring (a) are in the drafting record and are
> not attributed to the owner.

And delete the later "were both presented and not selected; (b) was declined
because …" sentence entirely — it is superseded by the clause above and is the
part that puts the agent's reasoning in the owner's mouth.

With that change the fact is self-certifying: appending it is the decision, and
a 2027 reader is told exactly that, rather than being told about a meeting that
may never have occurred.

---

### F-2 — BLOCKER (Packet 1). The placeholders can be appended literally, and the `dedupe_prefix` then makes the damage permanent.

**Exact text at issue:**

> NVDA official close 2026-09-18: `<NVDA 2026-09-18 close>`. Intrinsic value of
> one 220 strike call at that close: `<intrinsic>`.

**Evidence.** `research/facts.py::append_fact` validates exactly one thing: that
`dedupe_prefix` is a non-empty prefix of `text`. It does not inspect the body.
I confirmed by stubbed dry-run that the one-liner as written passes
`"… close: <NVDA 2026-09-18 close>. … : <intrinsic>. …"` straight through. A
copy-paste-and-run before substitution appends a fact with literal angle
brackets into an **append-only, never-edited** log.

The `dedupe_prefix` then turns a slip into a permanent one. From `facts.py`:

```python
if payload.rstrip("\n") == text:
    return
raise RuntimeError(
    "append_fact dedupe refused: an existing fact shares "
    f"prefix {dedupe_prefix!r} but its payload differs; "
    "refusing to silently skip a divergent anchor"
)
```

Once the placeholder version is on disk, **every** later attempt to append the
corrected text under `dedupe_prefix="H6_0001_UNMARKED_EXPIRY"` raises. The key
is burned. Recovery requires a second fact under a different key
(`H6_0001_UNMARKED_EXPIRY_V2`) plus a correction fact voiding the first — i.e.
the A2 remediation dance, for a typo. The packet presents `dedupe_prefix` as the
safety feature ("the safe way to make a re-run harmless"); for this packet it is
also the trap, and the packet does not say so.

**Replacement.** Do not ship a bare `append_fact(...)` one-liner for Packet 1.
Ship a guarded one that refuses on any unsubstituted placeholder, and state the
burn risk in §1.5:

```sh
uv run python -c 'import sys
from research.facts import append_fact
TEXT = "…full fact text…"
KEY = "H6_0001_UNMARKED_EXPIRY"
if "<" in TEXT or ">" in TEXT:
    sys.exit("REFUSED: unsubstituted placeholder in the fact text. "
             "Fill the 2026-09-18 close and the intrinsic value first. "
             "Nothing was appended.")
if TEXT.count("USD") < 1 or "2026-09-18" not in TEXT:
    sys.exit("REFUSED: text does not look like the reviewed fact.")
append_fact(TEXT, dedupe_prefix=KEY)
print("appended under", KEY)'
```

Add to §1.5, verbatim: *"If a placeholder version is ever appended under this
key, the key is burned — `append_fact` will raise on every corrected re-append
and `facts.log` is never edited. Check the text on screen before pressing
Return."*

---

### F-3 — MUST-FIX (Packet 1). "Settles at intrinsic value" is an unregistered exit convention stated as a property of the contract, in a fact that claims to add no exit convention.

**Exact text at issue:**

> EXIT: the position was held to expiration and **settles at intrinsic value**.
> … NO RETROACTIVE RULE CHANGE: this fact amends nothing, changes no registered
> exit, **adds no new exit convention** …

**Evidence.** Registration seq 6 names exactly two exits and no expiry handling
at all: "close at 21 DTE at conservative fills OR take-profit at +100% of
premium, whichever first; NO stop-loss." Expiry settlement is not among them —
the registration simply assumes the 21-DTE close always fires. So "settles at
intrinsic value" is a **new rule being introduced by this fact** for how an
H6 row that reaches expiration is valued. The fact's own closing clause denies
doing that. The two sentences cannot both be true.

Second problem, and it matters because the owner is a beginner in options
mechanics: a listed NVDA equity call is **physically settled**, not cash
settled. An in-the-money call held through expiration is auto-exercised into 100
shares (about $22,000 of stock at a $220 strike), not paid out as cash equal to
intrinsic value. "Settles at intrinsic value" is a **paper-book modelling
convention**, and a reasonable one, but it is a convention — under `.cursorrules`
claim discipline it is an **Assumption**, and the text labels it as nothing.

**Replacement wording.** Change the `EXIT:` block to:

> DISPOSITION AT EXPIRATION (NOT a registered exit): the position was held to
> expiration 2026-09-18 with no exit ever executed. For book purposes only, and
> as a valuation convention adopted by this fact and by nothing earlier
> (Assumption, stated so), the position is valued at expiration intrinsic value,
> defined as max(0, official close minus 220) times 100 times 1 contract. This
> is a paper-book valuation convention, not a claim about contract settlement: a
> listed NVDA call is physically settled into 100 shares if exercised, and no
> exercise, assignment, or share position is recorded here.

And soften the closing denial to be accurate:

> NO RETROACTIVE RULE CHANGE: this fact amends nothing, changes no registered
> exit, and creates no precedent for booking a reconstructed close from a
> quote. The one convention it does adopt is the expiration-intrinsic valuation
> stated above, which is prospective-neutral: it values a row the registered
> exits could not reach and does not make that row a completed position.

---

### F-4 — MUST-FIX (Packet 1). The fact is silent on whether the book row's exit columns get written; §1.5 says one thing and the fact says another.

**Evidence.** The fact text says "EXIT: … settles at intrinsic value" and, sixty
words later, "H6 remains INSUFFICIENT_SAMPLE with n equals 0 completed
positions." Those coexist only if `data/positions/h6_positions.csv` keeps
`exit_date`, `exit_proceeds`, `exit_reason` and `exit_receipt_hash` **blank**,
because the scorer counts completed rows off those columns (verified: the 07-27
receipt scores `completed_positions: 0` against the row with four blank exit
fields). The packet knows this — §1.5 says "The position row's `exit_*` columns
are … **not** touched by this fact" — but that sentence lives in the packet, not
in the fact, and the packet is a working document while the fact is the
permanent record. A 2027 reader sees an "EXIT:" heading and a blank CSV row and
cannot tell which is the mistake.

**Replacement — add to the fact text, immediately after the disposition block:**

> BOOK ROW: data/positions/h6_positions.csv row H6-0001 keeps exit_date,
> exit_proceeds, exit_reason and exit_receipt_hash BLANK and is not written by
> this fact. That is deliberate and is what keeps H6 at n equals 0 completed
> positions: the H6 scorer counts completed rows off those columns. Anyone who
> later fills them converts this disclosure into the reconstructed close that
> option (b) was rejected for.

---

### F-5 — MUST-FIX (both). Neither fact cites an independent adversarial review, which `.claude/rules/ledger.md` requires and which the two strongest precedents both carry.

**Evidence.** `.claude/rules/ledger.md`: "a correction fact requires:
**independent adversarial review of the exact text**, then owner approval, then
append." `METRIC_CORRECTION` records "independently adversarially reviewed
2026-07-31"; `A2_ENTRY_CONVENTION_CORRECTION_V1` records "after independent
adversarial review (finding 7, round-1 review; governance analysis, round-2
review)"; `H10A_RESULT` records "adversarially reviewed rounds 1-2 (receipt
reports/2026-08-15-monday-ship-adversarial-review-receipt.md)". Packet 2 is
plainly a coverage/correction fact. Packet 1 corrects the record about a
position whose registered exit did not fire. Neither draft names a review.

**Replacement.** Both facts' recording notes gain:
`independent adversarial review 2026-09-15, receipt
reports/2026-09-15-audit/J-fact-packets-adversarial-review.md` — and the texts
must be re-reviewed after the F-1/F-3/F-4/F-7/F-8 rewrites, because what I
reviewed is the *pre-fix* text and the rule is review **of the exact text**.

---

### F-6 — SHOULD-FIX (Packet 1). The manifest key cited does not exist; the binding actually lives in `preclose.json`.

**Exact text at issue (packet §1.1, and loosely in the fact):** "`manifest.json`
`names.NVDA.sha256`"; fact text: "manifest reports/schwab_chains/2026-09-10/manifest.json
binding `.cache/schwab_chains/NVDA_2026-09-10.parquet` at sha256 9df5…".

**Evidence.** `manifest.json` top-level keys are
`files, manifest_hash, provider, schema_version, session, session_chain_convention, symbols`.
There is no `names`. `manifest.json → files.NVDA` carries `path:
"NVDA_2026-09-10.parquet"` — a bare filename, not `.cache/schwab_chains/…`.
The `names` key and the full `.cache/schwab_chains/NVDA_2026-09-10.parquet`
path live in **`preclose.json`**. Both files carry the same sha256 `9df5…`, and
`preclose.json.manifest_hash` equals `manifest.json.manifest_hash`
(`4a4d6970…`), so the claim is true — it just points at the wrong file for the
path binding.

**Replacement (fact text):**

> … session receipt reports/schwab_chains/2026-09-10/preclose.json, which binds
> names.NVDA to .cache/schwab_chains/NVDA_2026-09-10.parquet at sha256
> 9df5291708fef0d0a6d6485fe5489a793befd9ef905654c62aebfd6f0e542a0f (status ok),
> and whose manifest_hash 4a4d69702261018660d5ae41734b2086f181c51588397cb7904ff841016c4d63
> matches reports/schwab_chains/2026-09-10/manifest.json, where files.NVDA
> carries the same sha256. Both re-verified on disk 2026-09-15.

Fix the §1.1 table row to say `files.NVDA.sha256` / `preclose.json names.NVDA`.

---

### F-7 — MUST-FIX (Packet 2). "Chronological" contradicts the correction fact it is citing.

**Exact text at issue:**

> The known-wrong H9 max_drawdown correction (METRIC_CORRECTION, 361.30 USD
> stated, **718.50 USD chronological**) is unaffected and still stands
> separately.

**Evidence.** `facts.log:19346` says the opposite in so many words: "$718.50 is
specifically the **implemented entry-date-ordered closed-trade** value, **not a
daily-NAV or generic chronological drawdown**", and separately notes that
aggregating by `exit_fill_session` yields $572.20. Writing "chronological" into
a new permanent fact re-introduces exactly the imprecision the correction was
appended to kill, and it makes the new fact a *mis-citation* of the old one.
(`.claude/rules/ledger.md` carries the same drift — "chronological value:
$718.50" — which is presumably where it was picked up. The rule file is wrong
too, but a new fact should not propagate it.)

**Replacement:**

> The known-wrong H9 max_drawdown correction at facts.log line 19346
> (METRIC_CORRECTION 2026-07-31: 361.30 USD as recorded, 718.50 USD when H9's 16
> stored trades are replayed under the zero-anchored entry-date-ordered
> closed_trade_pnl_drawdown definition of commit 5626c3f — expressly NOT a
> daily-NAV or generic chronological drawdown) is unaffected and still stands
> separately.

*Separately and out of scope for this packet: `.claude/rules/ledger.md` should
have its "chronological value: $718.50" wording corrected the same way. That is
a rules-file edit, not a fact append.*

---

### F-8 — MUST-FIX (Packet 2). "FORWARD RULE" makes a fact prescriptive, which `ledger/README.md` says facts cannot be, and which the fact's own last sentence denies.

**Exact text at issue:**

> **FORWARD RULE: future studies seal the whole receipt, not a subset of its
> keys.** … Recording note: … this fact is **descriptive only** and feeds no
> verdict.

**Evidence.** `ledger/README.md`: `facts.log` is "a descriptive research-notes
stream, **never verdict-feeding**", "Treat it as advisory context, not an audit
record", and "Any decision that freezes a number … belongs in the **chained**
ledger … with `facts.log` at most carrying a pointer to it." A standing
engineering rule about how all future receipts are hashed is a decision that
binds future code. It cannot be set by an unchained, unverified, advisory log
line — and nothing reads `facts.log` to enforce it, so in practice this sentence
is a rule that does not exist. Meanwhile the fact ends by calling itself
descriptive only. Both cannot hold.

There is also a real precedent for the right mechanism: the A2 correction did
**not** rely on a fact to enforce anything — it shipped code
(`options_researcher/a2_runner.py validate_governance`) and used the fact as the
pointer.

**Replacement:**

> RECOMMENDED FORWARD PRACTICE, NOT BINDING BY THIS FACT: future studies should
> seal the whole receipt rather than a subset of its keys. This fact cannot
> impose that — facts.log is advisory and never verdict-feeding
> (ledger/README.md) and no code reads this line. Making it binding requires a
> .cursorrules or .claude/rules entry plus a test, which this fact does not
> perform and does not authorize. Implementation constraint recorded for whoever
> does it: research/hashing.py canonical_json sets allow_nan equals False and the
> H9 receipt bulk section contains NaN (board.return_on_economic_max_loss), so a
> canonical-JSON hash of the whole object raises ValueError; a whole-receipt seal
> must therefore be a sha256 of the written file bytes, or the writer must stop
> emitting NaN.

**Answer to the question as asked:** no, the owner may not set that rule by
fact. He can *record the intent* by fact; the rule itself has to live in
`.cursorrules` / `.claude/rules/ledger.md` with a test, or it is decoration.

---

### F-9 — SHOULD-FIX (Packet 2). "Owner-ratified" in the opening clause is the same pre-decided assertion as F-1, milder.

**Exact text:** "H9_RECEIPT_FULL_DOCUMENT_HASH_V1 2026-09-15: **owner-ratified**
coverage fact for the H9 receipt…"

At drafting time it was not ratified; the packet's own ratification line is
blank. Same fix, same shape as F-1, and it is worth noting that the tight
precedent the packet says it follows —
`A2_ENTRY_CONVENTION_RATIFIED_V1` — carries `owner-approved 2026-08-31
source=reports/2026-08-31-a2-entry-convention-ratification-receipt.md`: a date
**and** a receipt path. This draft has neither.

**Replacement opening clause:**

> H9_RECEIPT_FULL_DOCUMENT_HASH_V1 2026-09-15: coverage fact for the H9 receipt,
> adding a full-document seal where the original seal covered only part of the
> document. Agent-drafted 2026-09-15; independently adversarially reviewed
> 2026-09-15 (reports/2026-09-15-audit/J-fact-packets-adversarial-review.md);
> the owner ratifies by appending it through research.facts.append_fact, and no
> prior separate approval is claimed.

---

### F-10 — SHOULD-FIX (Packet 1). The chain-cache claim cites only a gitignored directory; a durable, owner-approved citation exists and is not used.

**Exact text:** "the canonical chain cache ends 2026-07-27 across all names, so
no receipt for any session after 2026-07-27 can exist."

**Evidence.** True — I reproduced it — but `.cache/` is gitignored, so in 2027
this is unfalsifiable from the repo. The durable citation already exists:
`facts.log:19347` (`P1_1_PROVIDER_CLOSEOUT 2026-07-31`), **OD-2**: "the final
canonical chain edge remains 2026-07-27; decision-authoritative consumers must
fail closed beyond exact cached coverage", and it ends "Owner approved this P1.1
provider-closeout append on 2026-07-31." (Note: memo A and `H10A_RESULT` both
attribute the chain edge to **OD-4**; OD-4 in that same line is the ThetaData
*access* cutoff. The chain-edge sentence is OD-2. Cite OD-2.)

**Replacement:** "… the canonical chain cache ends 2026-07-27 across all names
— recorded as owner decision OD-2 in facts.log line 19347
(P1_1_PROVIDER_CLOSEOUT 2026-07-31: 'the final canonical chain edge remains
2026-07-27'), and re-verified against the cache on 2026-09-15 — so no receipt
for any session after 2026-07-27 can exist."

---

### F-11 — SHOULD-FIX (packet §1.1, not the fact text). The "Run-verified in this worktree" label is wrong for the cache rows.

`.tmp/worktrees/audit-0915/.cache/chains/` is **empty**, and
`.cache/schwab_chains/` does not exist in the worktree at all. Both cache checks
(and mine) necessarily read `~/options-validator/.cache/…`, i.e. the main
checkout. The packet's global claim that Run-verified means "in the worktree
`audit-0915`" is therefore false for those rows. Harmless to the fact text;
misleading to a re-verifier. Amend the evidence-label definition to "in the
worktree, except cache reads, which resolve to the main checkout
`~/options-validator/.cache/` because `.cache/` is not populated in worktrees."

---

### F-12 — MUST-FIX (both, §1.5 / §2.3). "From the repo root" is ambiguous and this session is living proof.

`append_fact` defaults to `base_dir="ledger"`, resolved **relative to the current
working directory**. This worktree contains a full `ledger/facts.log`
(19,614 lines). Running either one-liner from `.tmp/worktrees/audit-0915` would
append to the **worktree's** copy — a silent fork of an append-only log, on a
branch, with no error and no output. Both one-liners print nothing on success,
so there is no signal to notice it by.

**Replacement — prepend to both commands and say it in prose:**

```sh
cd /Users/carsynstephenson/options-validator          # the MAIN checkout, not a worktree
git rev-parse --show-toplevel                          # must print exactly that path
git rev-parse --abbrev-ref HEAD                        # confirm the intended branch
wc -l ledger/facts.log                                 # note the count; re-check after
```

and add `print("appended under", KEY)` to the command (already folded into the
F-2 replacement) so a successful append is visible.

---

### F-13 — NOTE (both). Two citation nits.

- Both facts cite "reports/2026-09-15-audit/A-evidence-audit.md **section 4.1**".
  That file has `## §4 The three most load-bearing integrity risks` and no
  `§4.1` heading; the H9 item is **§4 item 1**. The `§4.1` form was inherited
  from the loose-ends table. Cite "memo A §4, item 1".
- Packet 1's §1.1 row for seq 6 summarizes the verdict rule as the CI90 bar only
  and omits the co-registered hard kill ("3 consecutive calendar months each
  realizing the full monthly cap as losses"). The fact text omits it too. Not
  wrong — the hard kill is not an exit and cannot have fired on a single
  position — but a 2027 reader reconstructing "the registered rules" from this
  fact alone would be missing one. One clause fixes it.

---

### F-14 — NOTE (Packet 1). Derived percentages are presented at the same level as receipt-bound numbers.

"minus 441.30 USD (minus 47.9 percent)" and "minus 543.15 USD or minus 59.0
percent": the dollar figures are receipt-bound / quote-bound; the percentages
are my-and-the-drafter's arithmetic against the $920.65 entry and appear in no
artifact. Both reproduce exactly (−47.93%, −58.996%). Under `.cursorrules` claim
discipline these should be marked. Cheapest fix: "(minus 47.9 percent of the
920.65 USD entry, arithmetic, not a receipt field)".

More generally: **Packet 1's fact text carries zero `.cursorrules` evidence
labels** (Packet 2 carries one, "Run-verified 2026-09-15"). Adding
Repo-verified / Run-verified / Official-source markers to the load-bearing
claims in Packet 1 would bring it in line with the rule and with
`METRIC_CORRECTION`'s style.

---

### F-15 — SHOULD-FIX (Packet 1). The closing price the whole exit rests on has no source slot.

The fact will state an NVDA official close and an intrinsic value derived from
it, and then says "the exit is settlement arithmetic on a public closing price"
— without naming the source of that price. `.cursorrules` requires the label
(**Official-source**) and an official source where one exists. §1.5 discusses
`reports/closes_receipts/<date>/guarded-all-cached.json` but that guidance is
not in the fact. Relatedly, memo A's own §3 flags `NVDA closed $210.96 on
2026-09-14` as unverifiable in-repo (latest closes receipt is
`reports/closes_receipts/2026-09-11/`) — the packet correctly keeps that number
out of the fact; it should apply the same rigour to the number it *does* put in.

**Replacement — extend the disposition block:**

> NVDA official close 2026-09-18: <close> (source: <reports/closes_receipts/2026-09-18/guarded-all-cached.json,
> or the named official source if that receipt does not exist>, Official-source).
> Intrinsic value of one 220 strike call at that close: <intrinsic>
> (= max(0, close − 220) × 100 × 1, arithmetic).

The guard in F-2 already refuses on any remaining `<`, which now also protects
the source slot.

---

### F-16 — NOTE. The packet's own shell-quoting rationale is self-contradictory, though the commands are in fact safe.

The preamble says the `$` signs "are not expanded by zsh" because the fact text
is in double quotes **inside Python**; §1.5 then says the `$` signs "have been
spelled out as `USD` … so that no shell expansion is possible." Both
explanations are offered, and the first one is wrong: the entire `python -c`
program sits inside **single** shell quotes, so nothing would be expanded
regardless. And there are no `$` characters in either fact text at all.

I verified the commands are genuinely safe: neither contains `'`, `$`, a
backtick, `!`, a newline, or any non-ASCII character, so single-quoted `sh`/`zsh`
passes both through byte-for-byte. Keep the commands; delete the first
explanation.

---

## §2. Direct answers to the seven questions

**1. Numbers, hashes, paths, lines, seqs, dates.** Every one reproduced. I
recomputed the nine-key hash myself and got `5bea2018…`, matching the recorded
value; the nine-key set is exactly as stated. Discrepancies: F-6
(`manifest.json` has `files`, not `names`, and a bare filename path — the
binding with the full path is in `preclose.json`), F-11 (cache rows were
Run-verified in the main checkout, not the worktree as the label claims), F-13
(`memo A §4.1` does not exist; it is `§4` item 1). Nothing else. No number in
either fact text is wrong.

**2. Does either text assert owner approval or a selection not yet made?** Yes,
both. Packet 1 states "the owner selected (a)" and attributes decline reasons
for (b) and (c) to him; Packet 2 opens "owner-ratified". Is "the owner ratifies
by running it" an acceptable template? **Not as written.** A fact that says "was
presented … and the owner selected" asserts a *past event* — a meeting, an
options walkthrough, a choice — that running the command does not retroactively
make true, and it contradicts its own cited source ("owner ruling needed …
nothing pre-filled"). It does not repeat the A2 failure mode exactly (the owner,
not an agent, would press Return) but it repeats its core defect, which the A2
correction names as "the agent wrote its own gate input." The fix is not to
remove owner authority from the record but to state it in the form that is true
at every moment: *the owner ratifies by appending; appending is the
ratification; no prior approval is claimed.* Exact wording in F-1 and F-9.

**3. Does the H6 text quietly change H6's state or create a reconstructed-close
precedent?** It does not change n, the bar, or the verdict — all three are
stated correctly and I verified each against the 07-27 receipt, seq 6, and
`config.py:349`. It does not create a reconstructed-close precedent; it
explicitly refuses one, and correctly explains why (b) was refusable. **But** it
is silent on the book row's blank exit columns, which is the only thing
mechanically holding n at 0 (F-4). And "settles at intrinsic value" **is not an
exit under the registered rules** — seq 6 has no expiry handling whatsoever —
so it is a new valuation convention the fact introduces while claiming in the
same paragraph to add none (F-3). The text is honest that it is not a
`time_21_dte` close; it is not honest that it is adding a convention at all, and
it presents a paper-book modelling choice as a property of a physically-settled
listed option.

**4. Does the H9 text change a number, a verdict, or authorize anything?** No to
all three, and it says so explicitly and accurately: no number, no board value,
no trade row, no verdict; H9 stays INSUFFICIENT_SAMPLE; the one run stays SPENT;
no rerun, refetch, or backfill. I verified each against the receipt, the board,
`facts.log:17892`, and `.claude/rules/ledger.md`'s one-run clause. The
`FORWARD RULE` sentence is the exception: it *is* an attempt to set policy, it
contradicts the fact's own "descriptive only" closing clause, and per
`ledger/README.md` it cannot bind anything from `facts.log`. **The owner may not
set that rule by fact.** It belongs in `.cursorrules` / `.claude/rules/ledger.md`
with a test; the fact may record the intent and point at it (F-8).

**5. Are the two append one-liners safe?** Mechanically, yes: correct signature
(`append_fact(text, base_dir="ledger", *, dedupe_prefix=...)`), `dedupe_prefix`
is a valid non-empty prefix of `text` in both, no shell metacharacters that
survive single quoting, and — verified by stubbed dry-run — the text passed is
character-identical to the reviewed blockquote in both packets. I did **not**
call the real `append_fact`. Three real hazards remain: no accidental-write
guard on the placeholders (F-2), silent writes to a worktree's `facts.log` if
`cd` is wrong (F-12), and no success output at all, so the owner gets no
confirmation either way (F-2/F-12 replacements add `print`).

**6. Can the owner append literal placeholders?** **Yes, trivially.**
`append_fact` inspects nothing but the prefix; I confirmed the placeholder text
passes straight through. And `dedupe_prefix` makes it unrecoverable under that
key — every corrected re-append raises `RuntimeError`, and `facts.log` is never
edited. Guard proposed in F-2: the one-liner refuses and exits non-zero if `<`
or `>` is present, plus a sanity check that the text looks like the reviewed
fact, plus a success `print`.

**7. What a 2027 reader would still need.** (i) The review receipt — neither
fact names one, though the rule and all three precedents require it (F-5).
(ii) A durable citation for the 2026-07-27 chain edge; `.cache/` is gitignored,
but `facts.log:19347` OD-2 says it and is owner-approved (F-10). (iii) A source
for the closing price the entire H6 exit rests on (F-15). (iv) The statement
that the book row stays blank, which is what makes "n = 0" verifiable (F-4).
(v) The co-registered H6 hard-kill clause, omitted from the summary of "the
registered rules" (F-13). (vi) For Packet 2, precise language about $718.50 so
the new fact does not mis-cite the correction it points at (F-7). (vii) A
pointer to the fact that there is still **no verifier CLI** for `receipt_hash`
anywhere in the repo (memo A §4: `grep receipt_hash options_researcher/h9_*.py`
→ nothing) — the new full-file hash is a number in an advisory log that nothing
checks, and the fact would read as stronger protection than it is unless it says
so.

---

## §3. Verdicts

### Packet 1 — `H6_0001_UNMARKED_EXPIRY` — **NOT READY**

Two BLOCKERs. The fact asserts a past owner selection that has not happened and
that its own cited source calls "owner ruling needed … nothing pre-filled"
(F-1) — the defect the `A2_ENTRY_CONVENTION_CORRECTION_V1` precedent exists to
punish, in a softer form. And the unguarded one-liner will cheerfully append
literal `<NVDA 2026-09-18 close>` into an append-only log, after which the
`dedupe_prefix` blocks every correction under that key forever (F-2). Three
MUST-FIXes on top: the unacknowledged new valuation convention presented as a
contract property (F-3), the missing statement that the book row stays blank
(F-4), and the missing review citation (F-5), plus the `cd` hazard (F-12).

Every *number* in it is correct — I re-derived all of them. The problem is
governance and safety, not arithmetic. With F-1 through F-5, F-10, F-12 and
F-15 applied and the revised text re-reviewed, this becomes a good fact and
option (a) remains the right disposition on the merits.

### Packet 2 — `H9_RECEIPT_FULL_DOCUMENT_HASH_V1` — **READY WITH FIXES**

No BLOCKERs. The substance is sound and independently reproduced: the nine-key
recomputation gives `5bea2018…` exactly, the file hash is `30df74c4…`, `d91b1ec`
is the only commit in the repo's history for that file and its blob still hashes
to `30df74c4…` with a clean tree, and the fact changes no number and authorizes
nothing. The `NaN` / `allow_nan=False` observation is a genuine strengthening of
memo A and belongs in the record.

Three things must change before it goes in: "chronological" mis-cites
`METRIC_CORRECTION`, which explicitly rules that word out (F-7); the
`FORWARD RULE` clause tries to legislate from an advisory log and contradicts
the fact's own closing sentence (F-8); and the opening "owner-ratified" asserts
a ratification that has not occurred, without the date-and-receipt token its own
cited precedent carries (F-9, F-5). Add the `cd`-to-main-checkout guard (F-12)
and fix the `§4.1` citation (F-13), and it is ready.

### Cross-cutting

Neither packet should be appended in the order the packet implies. The sequence
that satisfies `.claude/rules/ledger.md` is: **rewrite → re-review the exact
rewritten text → owner appends.** What I reviewed is the pre-fix text, and the
rule is review *of the exact text*. A second, short pass over the corrected
wording closes that loop.

---

*Nothing in this review was appended to any ledger. No ledger-writing tool was
called. `append_fact` was exercised only against a local stub that captured its
arguments. No commit was made and the packet file was not modified. The only
file created is this one.*
