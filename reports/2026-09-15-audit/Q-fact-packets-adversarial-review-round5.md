# Q — Round-5 independent adversarial review of the Packet 1 fact text

**Target:** `reports/2026-09-15-audit/H-owner-fact-packets.md`, **Revision 5**,
Packet 1 (`H6_0001_UNMARKED_EXPIRY`).
**Prior receipts:** `J` (round 1, Rev 1), `L` (round 2, Rev 2),
`M` (round 3, Rev 3.1), `P` (round 4, Rev 4) — all in this directory. `P` was
read in full first; `J`, `L`, `M` were consulted.
**Packet 2** (`H9_RECEIPT_FULL_DOCUMENT_HASH_V1`) is out of scope except for the
byte-identity confirmation in §0.
**Date:** 2026-09-15. **Worktree:** `.tmp/worktrees/audit-0915`, branch
`claude/audit-2026-09-15`. Repo facts re-derived in the `main` checkout
`/Users/carsynstephenson/options-validator-ops` at `a3745ab` = `origin/main`.
**Stance:** show how the Revision 5 text could be lying, over-claiming, or unsafe
to append. Not a confirmation pass.

**Nothing was appended. Nothing was committed. No ledger-writing tool was
called.** Both guard programs were executed only against a **stubbed**
`append_fact` that printed its arguments and asserted the prefix invariant. The
packet file was not edited. A throwaway synthetic repository under `/tmp/r5x`
was used to exercise the accept path. The only file created is this one.

---

## §0. Verdict

### Packet 1 — `H6_0001_UNMARKED_EXPIRY` — **NOT READY**

**The Packet 1 fact text must NOT be appended as written.** A **fourth**
committed-and-attested observation lane exists, and Revision 5's coverage
paragraph is falsified by it in the most direct way possible: the fact names
**2026-07-28, 07-29, 07-30 and 07-31** in an explicit list of sessions that
"carry no observation of this contract **on any lane**", and
`.cache/chains_v2/od1-2026-08-01/` holds a **ThetaData exact-session EOD chain
for each of those four sessions**, each containing exactly one NVDA 220 call
expiring 2026-09-18, each hash-bound in a manifest and an attestation, produced
under an **owner-approved pull recorded in `facts.log` three lines below the
line the fact itself cites**. See **Q-1**.

This is round 2, 3, 4 and now 5 finding the same paragraph wrong for the same
reason: a statement true of the lanes the drafter happened to look at, promoted
into a statement about the record.

**Every other number in Revision 5 reproduced exactly** — all 66 intraday
observations, all 14 Schwab captures, the 15.05 / 1,488.35 / 80.8 % / +61.66 %
headline, the 15-of-66 count, 0-of-80 reaching the trigger, the two 08-28
values, the 08-19 19:49 UTC outlier, the "no sha256" property of intraday
receipts, the 09-04 roll to 2026-10-16, the 08-31 / 09-01 auth-failure receipts,
every hash, `seq`, `record_hash`, path, line number and date. The guard is
materially stronger than Revision 4's: **P-7, P-8 and P-9 are all closed**, and
the invariant hash `836105dd…` and both blockquote identities reproduce exactly.
The failure is evidence coverage, again, and nothing else.

Because the text must change, the invariant hash must be recomputed against
Revision 6, and this receipt reviewed words that will not be the words appended
— the `L-4` / `M` / `P` carry-forward defect, one round later.

### Packet 2 — byte-identity confirmed

The Packet 2 blockquote is **4,638 characters** and **character-identical** to
the string its command passes to `append_fact`;
`sha256(TEXT)` = `c837b27e522f0c9c300e3163985a1b0aab7549dc1cde55baa77b1a7b5dfb10f4`,
matching the pinned constant and the hashes `M` and `P` recorded. **Byte-identical
to what `P` reviewed.** Nothing here asks for a character of it to change. Its
guard was dry-run and behaves correctly (§4, rows 24–25).

---

## §1. The exhaustive search for further observation lanes

Scope: **any** observation of the NVDA **220 strike call expiring 2026-09-18**
with a session date in **2026-07-27 … 2026-09-10**, anywhere in
`/Users/carsynstephenson/options-validator-ops` or its `.cache`.

**First structural finding:** `.cache` in the ops checkout is a **symlink** to
`/Users/carsynstephenson/options-validator/.cache`. All three checkouts share
one cache; there is no second cache to miss.

### What was searched

| Store | Enumerated | Method | Contract found in-window |
|---|---|---|---|
| All parquet under `.cache/**` | **48,758** files | full enumeration; every NVDA-named file (**2,542**) opened and filtered on `strike == 220.0 & right == C & expiration == 2026-09-18`; 2,539 carry a chain schema, 3 do not, **0 read errors** | **86 rows**, 4 lanes |
| `.cache/chains` (v1, registered) | 31,367 parquet | last NVDA session **2026-07-27**, last session overall **2026-07-27** | **1** (07-27) |
| `.cache/chains_v2/od1-2026-08-01` | 13,824 parquet | last session overall **2026-07-31** | **5** (07-27 … 07-31) — **see Q-1** |
| `.cache/intraday` | 1,751 parquet | 105 NVDA files in-window | **66** on 15 sessions |
| `.cache/schwab_chains` | 210 parquet | 14 NVDA files in-window | **14** on 14 capture dates |
| `.cache/future_tickers` | 1,536 parquet, 1,537 json | symbols are CLSK, ET, HYLN, INTC, MU, NBIS — **no NVDA** | none |
| `.cache/underlying`, `underlying.backup-2026-08-20`, `underlying_ohlcv` | 70 parquet | underlying OHLCV only, no option rows | none |
| `.cache/market_data` | **0 files** | empty | none |
| `reports/`, `data/`, `ledger/`, `results/`, `docs/` — every `.json`, `.jsonl`, `.csv` | **523** files | full text scan requiring `NVDA` **and** `2026-09-18` **and** a `220` token in the same file → 12 candidates, each opened | none new |
| `reports/live_probe/*.json` (9 files) | all | schema-only Schwab entitlement probes; `probe_symbol` is **VST**; no NVDA quotes | none |
| `reports/pick_tracker/dryrun/**` (outcomes + `events.jsonl`) | all | NVDA candidates are 232.50 / 235.00 / 230.00 / 225.00 exp 2026-09-09 / 09-16 / 09-23 / 10-09, and one **220 call expiring 2026-09-11** — a different contract | none |
| `reports/chain_consistency/*.json` (4) | all | 220 tokens are other expirations (08-24, 08-28, 2027-01-15) and puts | none |
| `reports/h7_receipts/**/source_health/*.json` | all | no 220 strike | none |
| `reports/intraday_capture/**`, `reports/schwab_chains/**`, `reports/h6_forward/**` | all | the receipts for the lanes already disclosed | already counted |
| `.md` / `.txt` across `reports/`, `docs/`, `wiki/` | all | 4 files name the contract; all prose (`H6-0001 NVDA $220 call, expiry 2026-09-18`), **no quote** | none |
| Other binary stores (`*.db`, `*.sqlite*`, `*.duckdb`, `*.feather`, `*.h5`, `*.pkl`, `*.npz`, `*.xlsx`) | whole tree | only `.lumibot/memory/*/memory.sqlite` (0 occurrences of `2026-09-18`), `.serena` symbol caches, and `.venv` test fixtures | none |

**Symbol-attribution check.** Chain parquets are symbol-per-file; a sample of 60
non-NVDA files confirms some carry a `symbol` column and none mixes symbols.
Attribution by filename is therefore sound for this cache layout.

### What was found

| Lane | rows | sessions | first → last | max bid | proceeds | % of 1,841.30 |
|---|---|---|---|---|---|---|
| `.cache/chains` (v1, registered) | 1 | 1 | 2026-07-27 | 4.85 | 479.35 | 26.0 % |
| **`.cache/chains_v2/od1-2026-08-01`** | **5** | **5** | **2026-07-27 → 2026-07-31** | **5.40** | **534.35** | **29.0 %** |
| `.cache/intraday` | 66 | 15 | 2026-08-07 → 2026-09-03 | **15.05** | **1,488.35** | **80.8 %** |
| `.cache/schwab_chains` | 14 | 14 | 2026-08-14 → 2026-09-10 | 13.50 | 1,335.35 | 72.5 % |

**0 of 86 reach the 1,841.30 trigger.** The fact's *conclusion* survives intact;
its *coverage arithmetic* does not.

---

## §2. Findings

### Q-1 — **BLOCKER** (fact text). A fourth committed, owner-approved, hash-attested lane observes this contract on four sessions the fact lists as unobserved.

**Exact text (two places):**

> Taking all three lanes together, 19 of the 33 sessions in the window carry at
> least one observation of this contract.

> THESE ARE THE QUOTES THAT WERE CAPTURED: 14 of the 33 sessions in the window
> carry no observation of this contract on any lane - 2026-07-28, 07-29, 07-30,
> 07-31, 08-03, 08-04, 08-05, 08-06, 08-10, 08-11, 08-21, 08-31, 09-01 and
> 09-04.

**Evidence.** `.cache/chains_v2/od1-2026-08-01/` holds ThetaData schema-v2 EOD
chains for NVDA on **2026-07-27, 07-28, 07-29, 07-30 and 07-31**, each with
exactly one row at `strike 220.0, right C, expiration 2026-09-18`:

| Session | bid | ask | quote timestamp | registered proceeds | % of trigger |
|---|---|---|---|---|---|
| 2026-07-27 | 4.85 | 4.95 | 2026-07-27 15:59:56.932 −04:00 | 479.35 | 26.0 % |
| **2026-07-28** | **4.80** | 5.10 | 2026-07-28 15:59:12.172 −04:00 | 474.35 | 25.8 % |
| **2026-07-29** | **3.25** | 3.40 | 2026-07-29 15:59:37.887 −04:00 | 321.35 | 17.5 % |
| **2026-07-30** | **4.05** | 4.15 | 2026-07-30 15:59:13.217 −04:00 | 400.35 | 21.7 % |
| **2026-07-31** | **5.40** | 5.55 | 2026-07-31 15:59:54.734 −04:00 | 534.35 | 29.0 % |

The 07-27 row is **bid 4.85 / ask 4.95, identical to the v1 registered chain**,
so the v2 namespace is a verified drop-in superset of v1 at the boundary, not a
different measurement.

**This is not a stray file.** Its provenance is stronger than the intraday
lane's:

- **sha256 verified on disk for all five**, matching
  `_meta/chain_manifest.txt` and `_meta/artifact_manifest.jsonl`
  (e.g. 07-29 → `dda5c7501b1f427b…`).
- Per-session attestation at `_meta/attestations/NVDA_2026-07-29.json`:
  `schema thetadata-v2-partition-attestation/v1`, `provider ThetaData`,
  `status COMPLETE`, `audit.verdict "PASS WITH WARNINGS"`,
  `captured_at_utc 2026-08-01T20:04:43Z`, and raw provider frames bound as well
  (`raw/greeks_eod/NVDA/2026-07-29.parquet`,
  `raw/open_interest/NVDA/2026-07-29.parquet`).
- The manifest tags each file `usage=verdict-eligible`.
- **Owner-approved in `facts.log`, three and four lines below the line this fact
  cites:**
  - line **19348** `OD1_SUPERSEDING_DECISION 2026-08-01` — supersedes OD-1's
    decline with APPROVE for a v2 backfill;
  - line **19349** `OD1_V2_PULL_APPROVAL 2026-08-01` — 2025-07-25 → 2026-07-27;
  - line **19350** `OD1_V2_EXPANDED_PULL_APPROVAL 2026-08-01` — expanded to
    **2026-07-31**, 18 symbols including NVDA, destination
    `.cache/chains_v2/od1-2026-08-01`.
  - `_meta/scope_amendment.json` records `approval_token OD1-V2-9500-APPROVED`,
    `end_session 2026-07-31`.
- A **tracked** audit report on `main`,
  `reports/thetadata_v2/2026-08-02-od1-full-audit.md`: *"PASS WITH WARNINGS /
  DATA QUALITY ACCEPTABLE WITH QUARANTINES"*, 0 effective blockers, 4,608
  partitions, receipt identity `865024a8…`. NVDA is **not** in the quarantine
  list (`data/v2_partition_quarantine.json` holds only AMZN / AVGO / AMD for
  2025-11-24).

**The one qualification, which the replacement must carry.** A later owner
ruling parks the namespace: `tools/fill_haircut_calibration.py:39-43` —
*"Owner ruling 2026-08-24: Tier-2 chains_v2 read-only access is approved for
this descriptive study; the namespace remains parked and excluded from verdict
eligibility."* So chains_v2 is **not** verdict-eligible today despite the
per-file tag, and the tool refuses it without `--allow-parked-chains-v2`. That
makes it exactly the right kind of evidence for a **descriptive disclosure
fact** — read-approved, parked, non-verdict-feeding — and exactly the wrong kind
of evidence to omit from one.

**Why this is a blocker.** The fact's stated purpose for the off-lane paragraph
is *"so that no reader concludes the window is evidentially empty"*, and it then
publishes a **list of specific dates** asserting emptiness on four dates where
an owner-approved ThetaData capture of this exact contract exists. A 2027 reader
who reads `facts.log` sequentially hits the contradicting approval **three lines
after** the line this fact cites for its own premise. Both the count (19 → 23)
and the list (14 → 10) are wrong in a permanent append-only record.

**Also affected, same finding:**

- > Off that lane the repository holds **two** further, non-registered
  > observation lanes for this exact contract.

  Three.

- > Across all **80** observed quotes on the **two** off-lane sources, 66
  > intraday and 14 Schwab pre-close, not one reaches the 1841.30 USD of
  > proceeds the rule requires.

  84 on three (66 intraday + 14 Schwab + 4 post-edge chains_v2), or 85 counting
  the chains_v2 07-27 duplicate of the registered mark. Still **0 reach the
  trigger** — verified over all 86 in-window rows.

- > Nothing is asserted here about what the contract was worth on those **14**
  > sessions.

  Ten.

**Replacement wording** — replace the sentence beginning *"Off that lane the
repository holds two further…"* through *"…Taking all three lanes together, 19
of the 33 sessions…"*, and the `THESE ARE THE QUOTES THAT WERE CAPTURED`
sentence, with:

> Off that lane the repository holds three further, non-registered observation
> lanes for this exact contract. First, Schwab pre-close captures on 14 capture
> dates between 2026-08-14 and 2026-09-10, each with a committed receipt under
> reports/schwab_chains/ whose names.NVDA status is ok and whose recorded sha256
> matches the corresponding .cache/schwab_chains parquet on disk (all 14
> re-verified on disk 2026-09-15). One of those 14 capture dates, 2026-09-07, is
> a market holiday and its row carries a null timestamp and sentinel greeks (iv
> minus 9.99, delta minus 999), so it is an artifact rather than a session; the
> other 13 are trading sessions with real timestamps near 19:45 UTC, the single
> exception being 2026-08-19 at 19:49 UTC. Second, intraday chain captures at
> about 09:31, 09:35, 11:00, 13:00 and 15:45 New York time on 15 sessions
> between 2026-08-07 and 2026-09-03, giving 66 observations of this contract,
> each with a committed receipt under reports/intraday_capture/ recording
> names.NVDA status ok and the chain cache path. Those intraday receipts bind no
> sha256, so they are a weaker evidentiary artifact than the Schwab receipts,
> and that difference is stated rather than left for a reader to discover.
> Third, the ThetaData schema-v2 side-by-side backfill namespace
> .cache/chains_v2/od1-2026-08-01, approved by the owner at facts.log lines
> 19348 to 19350 and covering sessions through 2026-07-31, which holds an
> exact-session EOD chain for this contract on 2026-07-27, 07-28, 07-29, 07-30
> and 07-31 at bids of 4.85, 4.80, 3.25, 4.05 and 5.40. Each of those five is
> bound by a sha256 in that namespace _meta/chain_manifest.txt and by a
> per-session attestation, and the read-only audit
> reports/thetadata_v2/2026-08-02-od1-full-audit.md records PASS WITH WARNINGS
> with NVDA not quarantined; all five sha256 were re-verified on disk
> 2026-09-15. That namespace is parked and excluded from verdict eligibility by
> the owner ruling of 2026-08-24, and it is cited here as descriptive evidence
> only, never as a mark source. Taking all four lanes together, 23 of the 33
> sessions in the window carry at least one observation of this contract.

and

> THESE ARE THE QUOTES THAT WERE CAPTURED: 10 of the 33 sessions in the window
> carry no observation of this contract on any lane - 2026-08-03, 08-04, 08-05,
> 08-06, 08-10, 08-11, 08-21, 08-31, 09-01 and 09-04. Three of those matter.
> [unchanged through] … known-missing rather than merely absent. Nothing is
> asserted here about what the contract was worth on those 10 sessions.

and, in the `WHAT THOSE OBSERVATIONS SHOW` paragraph:

> Across all 84 observed quotes on the three off-lane sources, 66 intraday, 14
> Schwab pre-close and 4 schema-v2 sessions after the canonical edge, not one
> reaches the 1841.30 USD of proceeds the rule requires.

### Q-2 — **MUST-FIX** (fact text). "the exact-session ThetaData chain" is the wrong name for the lane the fact means.

**Exact text:**

> no observation on the registered H6 mark lane - **the exact-session ThetaData
> chain** - exists for this contract after 2026-07-27, which is why neither
> registered exit could be evaluated.

**Evidence.** `.cache/chains_v2/od1-2026-08-01` **is** an exact-session
ThetaData chain, from the same provider, with the same normalized 20-column
schema, and it does hold this contract on 07-28 through 07-31. What is actually
true is narrower and verifiable: the H6 evaluator's chain directory is
`options_researcher/h6_watch.py:951`, `chain_dir: Path = Path(".cache/chains")`,
and it requires an exact-session file (`:990-991`,
`raise FileNotFoundError(f"exact chain missing: {chain_path}")`). The **v1
canonical cache** ends 2026-07-27 for NVDA and for every name (Run-verified).
The v2 namespace is a different directory the evaluator never reads.

As written the sentence is falsifiable by one `ls`. **Replacement:**

> no observation on the registered H6 mark lane - the v1 canonical chain cache
> at .cache/chains, which is the only chain directory the H6 evaluator reads
> (options_researcher/h6_watch.py line 951) - exists for this contract after
> 2026-07-27, which is why neither registered exit could be evaluated. A
> separate owner-approved ThetaData schema-v2 namespace does hold four further
> exact-session chains, through 2026-07-31; it is described below, it is parked
> and excluded from verdict eligibility, and no H6 code reads it, so it does not
> change that conclusion.

### Q-3 — **MUST-FIX** (fact text). The OD-2 citation is true but is read out of context three lines from its own supersession.

**Exact text:**

> The canonical chain cache ends 2026-07-27 across all names - recorded as owner
> decision OD-2 at facts.log line 19347 (P1_1_PROVIDER_CLOSEOUT 2026-07-31: the
> final canonical chain edge remains 2026-07-27; …)

**Evidence.** The quoted clause is verbatim and the line number is right
(Run-verified). But `facts.log` line **19348**, timestamped ~16.5 hours later,
opens *"OWNER DECISION: supersede the 2026-07-31 OD-1 DECLINE with APPROVE…"*,
and 19350 approves the pull **through 2026-07-31**. A reader who checks 19347
and reads on finds what looks like a direct contradiction of the sentence that
cited it. The fix is one clause, not a retraction: OD-2 governs the **canonical
v1 cache**, and the supersession created a **separate, parked** namespace.

**Replacement:** after *"…fail closed beyond exact cached coverage)"*, insert:

> ; that decision governs the v1 canonical cache, and facts.log lines 19348 to
> 19350 later approved a separate schema-v2 namespace reaching 2026-07-31, which
> is parked and which no H6 code reads

### Q-4 — **SHOULD-FIX** (fact text). The intraday capture times are given as exact and three of the 105 files are not.

**Exact text:** *"intraday chain captures at 09:31, 09:35, 11:00, 13:00 and
15:45 New York time"*.

In-window NVDA intraday filenames include `T0936` (2026-08-19), `T1549`
(2026-08-19) and `T1101` (2026-08-24). "at about 09:31, 09:35, 11:00, 13:00 and
15:45" removes the discrepancy at no cost. (Included in the Q-1 replacement.)

### Q-5 — **NOTE** (fact text). "The best bid observed anywhere."

Scoped correctly — the sentence sits inside a paragraph headed *"on the observed
pre-close and intraday quotes"*, and the gaps are named two sentences later. Once
the Q-1 counts are corrected it is defensible. Re-verified: the global maximum
over all 86 in-window rows on all four lanes is **15.05**, intraday,
2026-08-14T09:31 ET, and the chains_v2 additions (max 5.40) do not disturb it.
The phrase should still say "on the observed quotes" rather than "anywhere";
"observed anywhere" already does most of that work, so this is a NOTE, not a
MUST.

### Q-6 — **NOTE** (fact text). The `CITED` list does not include the new evidence.

If the Q-1 replacement lands, the fact will cite
`reports/thetadata_v2/2026-08-02-od1-full-audit.md` and `facts.log` lines
19348–19350. The audit report **is tracked on `main`** today
(`git cat-file -e HEAD:…` succeeds), so adding it to `CITED` costs nothing and
makes the guard's `cat-file` check cover it. The `_meta` manifest and
attestations live beside the gitignored cache and cannot be cited as paths —
cite the tracked audit report and the `facts.log` lines instead, exactly as the
fact already does for `.cache/underlying_ohlcv/NVDA.parquet` via the
`DATA_PULL_OHLCV` anchor.

### Q-7 — **NOTE** (packet prose, §1.1c). The drafting record inherits the same error.

§1.1c ("Coverage: 19 of 33 sessions observed, 14 unobserved") and §1.1's "two
off-lane sources" framing must be corrected alongside the fact text, and the
chains_v2 rows tabulated, or the fact's clause *"is tabulated in the drafting
record"* becomes false.

---

## §3. Disposition of P-1 … P-14

| ID | P severity | Disposition | Evidence |
|---|---|---|---|
| **P-1** — stated maximum falsified by the intraday lane | BLOCKER | **CLOSED** | The 13.50 / 72.5 % claim is gone. Independently re-derived from `.cache/intraday`: **66** observations, **15** sessions, 2026-08-07 → 2026-09-03; global best **15.05** at 2026-08-14 tag `0931` → `floor(15.05×0.99×100)/100×100 − 0.65` = **1,488.35** = **80.83 %** of 1,841.30 = **+61.66 %** on the 920.65 entry. Exact to the cent. Top six reproduce: 15.05, 14.75, 14.60, 14.40, 14.35, 14.30. |
| **P-2** — off-lane disclosure omits a whole lane | BLOCKER | **OPEN (recurred at the next lane)** | The intraday lane is now disclosed correctly, with its five earlier sessions. But a **fourth** lane is still omitted, and four of its sessions are affirmatively listed as unobserved. See **Q-1**. |
| **P-3** — "anywhere in the window" / "never close to firing" | MUST | **PARTIAL** | "was never close to firing" is deleted; the numbers carry the claim; the gap paragraph is present and its three load-bearing sessions are named correctly (09-04 window max on close **230.36** and high **234.76**, no Schwab receipt, intraday rolled to 2026-10-16 — all re-verified; 08-31 and 09-01 receipts read `overall_status: failed`, *"Refresh token is invalid, expired or revoked"*). **But the count and the list are wrong** — 23 / 10, not 19 / 14. See **Q-1**. |
| **P-4** — "14 sessions" then one is not a session | MUST | **CLOSED** | Now "14 **capture dates**", with 2026-09-07 explicitly called an artifact and the other 13 called trading sessions. Re-verified: 2026-09-07 is absent from the OHLCV parquet; its row carries `timestamp NaT`, `iv −9.99`, `delta −999.0`. |
| **P-5** — "next best" ranking skipped the artifact | SHOULD | **CLOSED (superseded)** | The P-1 rewrite removed the ranking sentence. No gap remains. |
| **P-6** — 21-DTE value is provider-dependent | SHOULD | **CLOSED** | Both values are now given and both re-derived exactly: Schwab **5.55 → 548.35 → −372.30 → −40.44 %**; intraday preclose **5.50 → 543.35 → −377.30 → −40.98 %**. The outage cost is stated as a **543.35–548.35 band**, and the net-vs-gross asymmetry against the expiration intrinsic is flagged in the text. |
| **P-7** — M-7 exploit not closed; guard table wrong | MUST (guard) | **CLOSED** | Dry-run rows 8–12: `Blog-source` → rc 1; **blog string labelled `Official-source` → rc 1** (*"names none of Nasdaq, NYSE, Cboe, OCC or SEC"*); intrinsic `9999.00` at close `213.40` → rc 1 (*"which is 0.00"*); intrinsic `0.00` at close `225.00` → rc 1 (*"which is 500.00"*); non-numeric intrinsic → rc 1. §1.5's guard-behaviour table now records the Revision-4 row as having been **wrong**, which it was. |
| **P-8** — provenance check tested the disk, not `main` | MUST (guard) | **CLOSED** | The porcelain carve-out is gone (`porcelain.strip()` must be empty) **and** the check is now `git cat-file -e HEAD:<path>`. Dry-run row 19: six cited docs present on disk and untracked → rc 1 at the porcelain gate; row 20, with them removed from disk and from `HEAD` → rc 1 naming all seven missing paths. The exploit has no route left. |
| **P-9** — origin check was a bare suffix match | SHOULD (guard) | **CLOSED** | Dry-run row 7, unpatched: origin `/tmp/r5x/acc/carsynstephenson16-lang/options-validator.git` → **rc 1**. The normaliser was additionally unit-tested: it accepts the four canonical forms (including the ops tree's actual `https://github.com/carsynstephenson16-lang/options-validator.git`) and rejects the local path, `…/evil/carsynstephenson16-lang/…`, `notgithub.com/…` and `github.com.evil.io/…`. |
| **P-10** — porcelain parsing is positional | NOTE | **CLOSED (moot)** | `ln[3:]` is gone with the carve-out; the guard now requires porcelain to be **entirely empty**, so no parsing happens. |
| **P-11** — fill model is not at line 446 | NOTE | **CLOSED** | Text now cites "lines 440 to 446". Re-verified: 440-443 is the `proceeds` computation, 444 the `round`, 446 the threshold test `if proceeds >= position.entry_cost * (1.0 + config.H6_TAKE_PROFIT_PCT):`. |
| **P-12** — `h7-forward-operations.md` line range | NOTE | **CLOSED** | Packet prose now cites `191-195`. |
| **P-13** — "near 19:45 UTC" outlier | NOTE | **CLOSED** | The text now names it: *"the single exception being 2026-08-19 at 19:49 UTC"*. Re-verified: that row's timestamp is `2026-08-19 19:49:27.678000+00:00`. |
| **P-14** — the two receipt types are not equally strong | NOTE | **CLOSED** | The text states it. Re-verified against `reports/intraday_capture/2026-08-28/preclose.json`: `names.NVDA` keys are `atm_iv, chain_cache_path, chain_contracts_admitted, chain_contracts_total, greeks_note, iv_label, iv_rank_preview, iv_source, min_spread_pct_observed, monthly_expiration, open_interest_asof, spot_ask, spot_bid, spot_mid, spot_source, spot_ts, status, symbol` — **no `sha256`**. |

---

## §4. Re-verification of the Revision 5 numbers

All Run-verified 2026-09-15 from `/Users/carsynstephenson/options-validator-ops`
at `a3745ab` = `origin/main`. Fill model:
`proceeds = round(floor(bid × 0.99 × 100)/100 × 100 − 0.65, 2)`;
trigger `920.65 × 2 = 1,841.30`.

| Claim in Rev 5 | Result |
|---|---|
| 66 intraday observations on 15 sessions, 2026-08-07 → 2026-09-03 | **exact** |
| best bid 15.05 at 2026-08-14 09:31 ET → 1,488.35 → 80.8 % → +61.66 % | **exact** (80.83 %, +61.66 %) |
| 15 of the 66 intraday observations exceed 13.50 | **exact** |
| best Schwab pre-close bid 13.50 → 1,335.35 → 72.5 % | **exact** (72.52 %) |
| 0 of 80 reach 1,841.30 | **exact** — and 0 of all **86** in-window rows on all four lanes |
| 14 Schwab capture dates, 2026-08-14 → 2026-09-10, all `status ok`, all sha256 matching disk | **exact** |
| 2026-09-07 holiday artifact: null timestamp, iv −9.99, delta −999 | **exact** |
| 2026-08-19 Schwab timestamp 19:49 UTC | **exact** (19:49:27.678 UTC) |
| 08-28 two values 548.35 / 543.35, −40.44 % / −40.98 % | **exact** |
| intraday receipts bind no sha256 | **exact** |
| 2026-09-04: no Schwab receipt; intraday parquets contain only expiration 2026-10-16 | **exact** (four snapshots 0931/0935/1100/1300, all `['2026-10-16']`) |
| 2026-08-31 and 2026-09-01 Schwab receipts record auth failure | **exact** (`overall_status: failed`, `invalid_grant`) |
| window = 33 sessions, 12 closes above 220, max close 230.36 and max high 234.76 both 2026-09-04 | **exact** (21 highs above 220) |
| `.cache/underlying_ohlcv/NVDA.parquet` = 2,437 rows; `facts.log:19621` `DATA_PULL_OHLCV 2026-09-15 … rows=2437` | **exact** |
| **union 19 of 33 sessions** | **WRONG — 23 of 33.** 19 is correct only if chains_v2 is excluded. **Q-1** |
| **14 unobserved sessions, list as given** | **WRONG — 10.** 07-28, 07-29, 07-30, 07-31 are observed. **Q-1** |
| seq 6 `H6`, `record_hash 5d813b8fe0e89f2d…`, ts `2026-07-09T00:50:22.721232+00:00` | **exact** |
| seq 22 `record_hash 4c552641d5a56f96…` | **exact** |
| `h6_positions.csv` row `H6-0001,NVDA,220.0,2026-09-18,1,2026-07-13,920.65,cc8ccd80…,,,,` — four blank exit columns | **exact** |
| entry receipt `cc8ccd80d8fdd471…`; last receipt `c4b3138dd87053c7…` with HOLD / dte 53 / pnl −441.3 / proceeds 479.35 / `no_exit_trigger`; score `completed_positions 0`, `INSUFFICIENT_SAMPLE`, *"requires 8 completed positions"* | **exact** |
| `reports/h6_forward/` holds exactly five files ending 2026-07-27 | **exact** |
| `config.py:347-349` = 1.00 / 21 / 8 | **exact** |
| `h6_watch.py` lines 440-446 as described | **exact** |
| `grep -ci schwab options_researcher/h6_watch.py` → 0 | **exact** |
| required proceeds 1,841.30, minimum raw bid 18.61, `2 × 920.65 ÷ 100 = 18.413` | **exact** |
| −441.30 = −47.93 % of 920.65; mid 3.775 → 377.50 → −543.15 → −58.996 % | **exact** |
| 2026-09-10 row: bid 3.75 / ask 3.80, delta 0.463, iv 0.33917, OI 43021, ts `2026-09-10T19:45:33.824Z`; receipt sha256 `9df5291708fe…a0f`, `manifest_hash 4a4d697022…4d63` | **exact** |
| `facts.log` lines 17892 / 19346 / 19347 / 19413 / 19553 valid; file is 19,627 lines on `main` | **exact** |
| 21-DTE date 2026-08-28; 2026-07-27 → 2026-09-18 = 53 days | **exact** |

---

## §5. Wording review

**Are superlatives scoped to observed quotes?** Mostly yes, and the scoping is a
genuine improvement on Revision 4: the paragraph opens *"on the observed
pre-close and intraday quotes"*, says *"Across all 80 observed quotes"*, and
follows with *"THESE ARE THE QUOTES THAT WERE CAPTURED"* and an explicit
statement that nothing is asserted about the unobserved sessions. The remaining
defect is not scoping but **arithmetic**: the scope itself is described wrongly
(Q-1). "The best bid observed anywhere" survives verification but would read
better as "the best bid on any observed quote" (Q-5).

**Does it pre-decide?** **No.** `Owner ratification: ______` is blank; the text
says the owner approves by reading and running the append; options (b) and (c)
are named and explicitly *"not adopted by this append"*; the drafting agent's
preference is pushed to the drafting record *"and are not attributed to the
owner"*. Unchanged from Revision 4, which `P` cleared.

**Does it legislate?** **No.** `NO RETROACTIVE RULE CHANGE` is present and
explicit — *"amends nothing, changes no registered exit, and creates no
precedent for booking a reconstructed close from a quote"*.

**Does it change a registered number?** **No.** H6 stays `INSUFFICIENT_SAMPLE`
at n = 0 against the 8-completed bar (seq 6 and `config.py:349` re-checked); seq
22 is untouched and correctly described as prospective-only; the book row's four
exit columns are verified blank and the fact says they stay blank and why.

**Is the Assumption label on the intrinsic convention intact?** **Yes.** The
text carries *"as a valuation convention adopted by this fact and by nothing
earlier (Assumption, stated so, because experiments.jsonl seq 6 registers no
expiry handling at all)"*, plus *"For disclosure purposes only - this valuation
is recorded in this fact and nowhere else; no book row, receipt, or scoreboard
carries it"*, the physical-settlement / OCC auto-exercise carve-out, and the
prospective-neutral clause. Adequate; no change needed.

**What could a 2027 reader misread?**

1. **The unobserved-session list (Q-1).** The worst case: a reader runs one
   filter over `.cache/chains_v2` and finds the fact asserting emptiness on four
   dates it can quote bids for. Blocking.
2. **"the exact-session ThetaData chain" (Q-2)** reads as "ThetaData has nothing
   after 07-27", which is false for this cache.
3. **The OD-2 citation (Q-3)** looks superseded three lines later unless the
   fact says which cache OD-2 governs.
4. **"provider-dependent within the 543.35 to 548.35 USD band."** A reader may
   take this as the outage cost itself; the sentence does define it as *that
   value minus the expiration intrinsic*, and flags the net-vs-gross asymmetry.
   Acceptable as written.
5. **"19:45 UTC"** with no ET translation, in a text that otherwise uses New
   York time. Harmless; noted.

---

## §6. Guard dry-run (stubbed `append_fact`, never the real one)

**Identity, first.** The Packet 1 blockquote is **13,766 characters** and
**character-identical** to the string the command passes to `append_fact`.
`TEXT.startswith(KEY)` holds. The text contains **no** `'`, `"`, `$`, backtick,
`!` or byte above ASCII 126. Applying the guard's two `re.sub` calls yields a
**13,667**-character skeleton whose sha256 is
**`836105dd729cfc935af68eae532af5ea0d708c884ee221ad5df3b5b5edef5fa3`** —
**matching the pinned constant exactly**. Unprotected region: **107 characters**,
the four slot values only. Packet 2: blockquote **4,638** characters,
character-identical, `sha256(TEXT)` =
`c837b27e522f0c9c300e3163985a1b0aab7549dc1cde55baa77b1a7b5dfb10f4`.

**Method.** The guard program was extracted verbatim from §1.5 and run under a
`sys.path` shim exposing a stub `research.facts.append_fact` that prints its
arguments and asserts the prefix invariant. A clean synthetic repository was
built at `/tmp/r5x/work` — a real git checkout on `main`, at its `origin/main`,
with **all sixteen cited paths committed**. Where a scenario required the date
gate to be behind us, the single `if NOW < …` line was flipped to `if False:`;
everything else ran unmodified. **For the accept rows only**, `CANON` was
replaced with the synthetic origin sentinel, because a local bare repo cannot
present a `github.com` URL without also rewriting `git remote get-url`; the
origin check itself was exercised **unpatched** in rows 6 and 7 and unit-tested
separately.

| # | Scenario | Tree | Result |
|---|---|---|---|
| 1 | As shipped, today, placeholders present | ops | **rc 1** — *"It is 2026-09-15T13:34:50…-04:00 in New York, before 2026-09-19 00:00."* |
| 2 | Date gate bypassed, placeholders still present | ops | **rc 1** — *"unsubstituted placeholder in the fact text."* |
| 3 | Slots filled, ops tree as it stands today | ops | **rc 1** — *"is not clean; git status --porcelain must be empty. Outstanding: `['?? reports/intraday_capture/2026-09-15/']`"* |
| 4 | Side branch: primary checkout | primary | **rc 1** — *"is on branch claude/rest-2026-09-09, not main."* |
| 5 | Side branch: audit worktree | audit | **rc 1** — *"is on branch claude/audit-2026-09-15, not main."* |
| 6 | Wrong origin, `CANON` unpatched | synthetic | **rc 1** — *"origin is /tmp/r5x/upstream.git, not the options-validator remote."* |
| 7 | **P-9 exploit**: local path ending `carsynstephenson16-lang/options-validator.git`, `CANON` unpatched | synthetic | **rc 1 — closed.** |
| 8 | Label `Blog-source` | synthetic | **rc 1** — whitelist |
| 9 | **M-7 / P-7 exploit**: `"a blog post I found"` labelled `Official-source` | synthetic | **rc 1 — closed.** *"names none of Nasdaq, NYSE, Cboe, OCC or SEC"* |
| 10 | Intrinsic `9999.00` at close `213.40` | synthetic | **rc 1** — *"which is 0.00"* |
| 11 | Intrinsic `0.00` at ITM close `225.00` | synthetic | **rc 1** — *"which is 500.00"* |
| 12 | Intrinsic `whatever I want` | synthetic | **rc 1** — format |
| 13 | Prose tamper (`80.8` → `99.9 percent`) | synthetic | **rc 1** — skeleton hash mismatch |
| 17 | `ledger/facts.log` modified | synthetic | **rc 1** — *"Outstanding: `['M ledger/facts.log']`"* |
| 18 | Unrelated untracked file | synthetic | **rc 1** — porcelain |
| 19 | **P-8 exploit**: six provenance docs on disk, untracked | synthetic | **rc 1 — closed.** porcelain refuses the untracked paths |
| 20 | Cited docs absent from `HEAD` and disk | synthetic | **rc 1** — *"cited by this fact but are not committed on main … Land PR 175 on main first."* |
| 21 | `HEAD` one commit behind `origin/main` | synthetic | **rc 1** — both SHAs printed |
| 14 / 23 | **ACCEPT** OTM: `213.40` / Nasdaq official closing price / `Official-source` / `0.00` | synthetic | **rc 0** — prints tree, branch, commit, target, `lines before`, calls the stub, `lines after` |
| 15 | **ACCEPT** ITM: `225.00` / Nasdaq / `Official-source` / `500.00` | synthetic | **rc 0** — recomputation agrees |
| 16 | **ACCEPT** `Vendor-source` with a vendor source string | synthetic | **rc 0** — correct: the label is honest |
| 24 | Packet 2 guard, cited paths not all in the stub tree | synthetic | **rc 1** — *"not committed on main: ['reports/2026-09-15-audit/A-evidence-audit.md', 'tools/h9_run_study.py', 'research/hashing.py']"* — the `cat-file` check is live on Packet 2 too |
| 25 | Packet 2 prose tamper (`4` → `9 losses`) | synthetic | **rc 1** — invariant hash |

**Origin normaliser, unit-tested separately.** Accepts
`https://github.com/carsynstephenson16-lang/options-validator{,.git}`,
`git@github.com:…`, `ssh://git@github.com/…` — the ops tree's actual origin is
the first of these. Rejects `/tmp/acc/carsynstephenson16-lang/options-validator.git`,
`https://github.com/evil/carsynstephenson16-lang/options-validator.git`,
`https://notgithub.com/…` and `https://github.com.evil.io/…`.

**No guard defect found in Revision 5.** The guard is now, in my judgement, the
strongest artifact in the packet. Every hole `M` and `P` opened is closed, and
I could not open a new one.

---

## §7. What must change before Packet 1 goes to the owner

**Blocking (fact text — a Revision 6 is required):** **Q-1**, **Q-2**, **Q-3**.
**Should:** **Q-4**.
**Note:** **Q-5**, **Q-6**, **Q-7** (the drafting record must be corrected
alongside the text, or the fact's "tabulated in the drafting record" clause
becomes false).
**Guard:** nothing. Recompute the invariant hash against Revision 6 and move the
fact's own review citation from `Q` to a round-6 receipt.

Everything `P` raised that could be closed by Revision 5 was closed correctly,
and every figure Revision 5 added is exact to the cent. The reason this is round
5 and not the last round is unchanged from round 4: each revision widens the
evidence base by one lane and then asserts coverage over it.

---

*Nothing in this review was appended to any ledger. No ledger-writing tool was
called; `append_fact` was exercised only against a local stub. No commit was
made, no packet or ledger file was modified, the synthetic repository used to
exercise the accept path was created under `/tmp` and touches nothing in the
project, and the only file created is this one.*
