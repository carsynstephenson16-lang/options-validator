# R — Round-6 independent adversarial review of the Packet 1 fact text

**Target:** `reports/2026-09-15-audit/H-owner-fact-packets.md`, **Revision 6.1**,
Packet 1 (`H6_0001_UNMARKED_EXPIRY`).
**Prior receipts:** `Q` (round 5, Rev 5) read in full first; `J`, `L`, `M`, `P`
consulted.
**Packet 2** (`H9_RECEIPT_FULL_DOCUMENT_HASH_V1`) is out of scope except for the
byte-identity confirmation in §0.
**Date:** 2026-09-15. **Worktree:** `.tmp/worktrees/audit-0915`, branch
`claude/audit-2026-09-15`. Repo facts re-derived in the `main` checkout
`/Users/carsynstephenson/options-validator-ops` at `a3745ab` = `origin/main`.
Cache facts re-derived against `/Users/carsynstephenson/options-validator/.cache`
(the ops checkout's `.cache` is a symlink to it — re-confirmed).
**Stance:** show how the Revision 6.1 text could be lying, over-claiming, or
unsafe to append.

**Nothing was appended. Nothing was committed. No ledger-writing tool was
called.** Both guard programs were extracted verbatim from §1.5 / §2.3 and run
only against a **stubbed** `append_fact` that printed its arguments and asserted
the prefix invariant. The packet file was not edited. A throwaway synthetic
repository under `/tmp/r6x` was used for the accept path and deleted. The only
file created is this one.

---

## §0. Verdict

### Packet 1 — `H6_0001_UNMARKED_EXPIRY` — **READY WITH FIXES (non-text only)**

**The Revision 6.1 fact text may be appended as written**, once the sequencing
preconditions in the packet are met (PR 175 on `main`; ops tree clean; date on or
after 2026-09-19). Every number, hash, path, line number, `seq`, date and count
in it reproduced exactly on independent re-derivation. Q-1 through Q-7 are
closed or, for Q-7, closed in the parts the fact depends on.

The fixes are **outside the fact text** and therefore **hash-neutral**:

1. **R-1 (MUST-FIX, drafting record).** The packet states **three different**
   invariant hashes for Packet 1 and **none of the two it advertises is the one
   the guard enforces.** The guard's constant
   `b157ac976e18c03b45609e1922d515ecaf24d83905cd91eb5f442e0465920062` is
   **correct** — independently recomputed from the Revision 6.1 blockquote.
2. **R-3 (SHOULD-FIX, `CITED` list only).** Add the two tracked anchors for the
   2026-08-24 parked ruling, which is otherwise uncitable — it is **not in
   `facts.log`**.
3. **R-5 (NOTE, drafting record).** §1.2, §1.3(a) and the §1.4 heading still
   carry Revision-4/5 framing.

**Round 6 found no fifth observation lane** in the two categories Q's sweep did
not cover (dashboard / composite-cache snapshots, and Obsidian wiki/research
notes) — see §2. The recurring defect that broke rounds 2, 3, 4 and 5 does not
recur in Revision 6.1.

### Packet 2 — byte-identity confirmed

Blockquote **4,638** characters, character-identical to the string its command
passes to `append_fact`; `sha256(TEXT)` =
`c837b27e522f0c9c300e3163985a1b0aab7549dc1cde55baa77b1a7b5dfb10f4`, matching the
pinned constant and the value `M`, `P` and `Q` recorded. Nothing asks for a
character of it to change.

---

## §1. Disposition of Q-1 … Q-7

| ID | Q severity | Disposition | Evidence |
|---|---|---|---|
| **Q-1** — a fourth lane observes four sessions the fact listed as unobserved | BLOCKER | **CLOSED** | The fourth lane is disclosed with its own clause. All five `chains_v2` rows re-derived from disk: bids **4.85 / 4.80 / 3.25 / 4.05 / 5.40**, asks 4.95 / 5.10 / 3.40 / 4.15 / 5.55, timestamps 15:59:56.932 / 15:59:12.172 / 15:59:37.887 / 15:59:13.217 / 15:59:54.734 ET — exact. `shasum -a 256` on disk equals `_meta/chain_manifest.txt` for **all five** (`6760a9ed…`, `2a115885…`, `dda5c750…`, `875dc4c8…`, `cf582959…`). Union coverage recomputed from the 33-session window: **23 observed, 10 unobserved**, list identical to the fact's. Off-lane quotes **66 + 14 + 4 = 84**; in-window rows **1 + 5 + 66 + 14 = 86**; **0 of 86** reach 1,841.30. Global max bid **15.05** (intraday, 2026-08-14 T0931) → 1,488.35 → 80.83 % → +61.66 % — undisturbed. |
| **Q-2** — "the exact-session ThetaData chain" is the wrong name for the registered lane | MUST | **CLOSED** | The fact now says "the v1 canonical chain cache at .cache/chains, which is the only chain directory the H6 evaluator reads (options_researcher/h6_watch.py line 951)". Verified: `h6_watch.py:951` is `chain_dir: Path = Path(".cache/chains")`; `:990-991` raises `FileNotFoundError(f"exact chain missing: {chain_path}")`; `grep -ci chains_v2 options_researcher/h6_watch.py` → **0**; `grep -ci schwab` → **0**; the only two `.cache/chains` occurrences in the file are 951 and the `--chain-dir` default at 1306. The v1 cache's last NVDA session and last session overall are both **2026-07-27** (2,152 NVDA files, 31,367 parquet). See **R-7** for one residual reading. |
| **Q-3** — the OD-2 citation reads as superseded three lines on | MUST | **CLOSED** | The inserted clause is present and verbatim-accurate. `facts.log:19347` contains the quoted OD-2 words exactly ("the final canonical chain edge remains 2026-07-27; decision-authoritative consumers must fail closed beyond exact cached coverage"). 19348 `OD1_SUPERSEDING_DECISION`, 19349 `OD1_V2_PULL_APPROVAL` (through 2026-07-27), 19350 `OD1_V2_EXPANDED_PULL_APPROVAL` (through **2026-07-31**, **18** symbols including NVDA, destination `.cache/chains_v2/od1-2026-08-01`) all verified. `_meta/scope_amendment.json` carries `approval_token OD1-V2-9500-APPROVED`, `end_session 2026-07-31`. |
| **Q-4** — capture times given as exact | SHOULD | **CLOSED** | "at about 09:31, 09:35, 11:00, 13:00 and 15:45 New York time". The in-window outliers `T0936`, `T1101`, `T1549` are covered by "about". |
| **Q-5** — "the best bid observed anywhere" | NOTE | **CLOSED as accepted** | Re-verified global maximum over all **86** in-window rows on all four lanes = **15.05**; chains_v2 max is 5.40. The phrase sits inside its scoping paragraph and is followed by the explicit unobserved-session list. One residual noted as **R-2**, not blocking. |
| **Q-6** — the new evidence was not in `CITED` | NOTE | **CLOSED** | `reports/thetadata_v2/2026-08-02-od1-full-audit.md` is in both `CITED` lists and is **tracked on `main`** (`git cat-file -e HEAD:…` succeeds). Enforcement demonstrated: removing only that path from `HEAD` on the synthetic tree → **rc 1** naming exactly that path (§4 row 19). |
| **Q-7** — the drafting record inherits the error | NOTE | **PARTIAL** | §1.1 framing, §1.1c coverage (23 / 10), the row census (86 / 84) and the new §1.1e are all correct and re-derived. **But** §1.2 still describes the registered lane as "the **exact-session ThetaData chain**" and the evidence as "a **union over both off-lane sources**"; §1.3(a) still says "the **fourteen** off-lane captures"; and the §1.4 heading still reads "**Draft fact text — Packet 1 (Revision 4)**". The fact's own clause "is tabulated in the drafting record" stays **true** (the tabulation lives in §1.1, §1.1b and §1.1e), so this does not block. See **R-5**. |

---

## §2. Spot-check of Q's search coverage — what I checked

Q's sweep was scoped to `/Users/carsynstephenson/options-validator-ops` and its
`.cache`. It enumerated `.cache/**` parquet, `reports/ data/ ledger/ results/
docs/` JSON/JSONL/CSV, all `.md`/`.txt` under `reports/ docs/ wiki/`, and other
binary stores. **It did not walk `.tmp/`**, which is where the dashboard and
composite-cache artifacts actually live. That is the gap I probed.

### (a) Dashboard / live_dashboard / composite_cache snapshot artifacts

| Checked | Method | Result |
|---|---|---|
| `.tmp/` in **both** checkouts — `composite_cache`, `dashboard`, `live_dashboard`, `research`, `research_views`, `daily_ritual`, `intraday_capture`, `schwab_chain_capture`, `controller`, `alignment_check`, `archive`, `redesign-mockups`, … | **1,642** `.json`/`.jsonl`/`.csv`/`.txt`/`.md`/`.html` files enumerated (103 ops + 1,539 primary), excluding `worktrees/`, `uv-cache/`, `__pycache__`; filtered for files containing `NVDA` **and** `2026-09-18` **and** `220` | **13 candidate files**, each opened |
| `…/.tmp/dashboard/attractiveness.html` (ops, written **today** 09:28) | read the rendered H6-0001 block | Names the position — *"NVDA $220.00 call · exp 2026-09-18 · entered 2026-07-13 · **Last mark 2026-07-27 · 36 sessions unmarked**"*. **No bid, no ask, no quote.** It **corroborates** the fact rather than contradicting it |
| `…/.tmp/dashboard/attractiveness.html` (primary), `…/.tmp/archive/brief39-codex-evidence-2026-09-09/*.html` | same | The `2026-09-18` tokens are **other** contracts (SMCI $40 call, CRWV $76 put). No NVDA 220 quote |
| `.tmp/redesign-mockups/{board,board.clean,mock-data}.json`, `option-{a,a-v2,c}.html` | opened | Mock/redesign fixtures; NVDA rows are **235.00 exp 2026-09-16**. No quote for this contract |
| `.tmp/composite_cache/NVDA.parquet` (both checkouts) | schema read | 378 rows, columns `session, atm_iv_near, atm_iv_far, rv, gap, skew_25d` — **aggregated features, no per-contract rows** |
| `.tmp/research/NVDA_features.parquet`, `.tmp/research/attractiveness/NVDA_features.parquet` | schema read | 252 / 2,152 rows, columns `close, rv21, atm_iv, iv_minus_rv, monthly_dte, iv_rank, earnings_week` — **no strike/expiration columns** |
| `docs/reliability/catalog.snapshot.json`, `.tmp/dashboard/picks_snapshot.json` | opened | no NVDA 220 / 2026-09-18 quote |
| `.cache/chains_v2/od1-2026-08-01/raw/greeks_eod/NVDA/`, `raw/open_interest/NVDA/` | listed | 256 sessions each, **last is 2026-07-31** — the raw provider frames behind lane 4, not a separate lane, and they do **not** extend past the approved edge |
| `.cache/market_data` | walked | contains only an **empty** `schwab/` directory — 0 files (Q's "0 files" stands) |
| `.cache/chains/.attestations` | listed | 19 entries, all `*_2026-07-27.json` — consistent with the v1 edge |

**Verdict on (a): no observation lane found.** The only dashboard artifact that
touches this contract states it is **unmarked since 2026-07-27**.

### (b) Obsidian wiki / research notes

| Checked | Method | Result |
|---|---|---|
| `wiki/` + `research/` in the ops checkout | 27 files; `grep -rl '2026-09-18'` | **1 hit**: `wiki/hypotheses.md` |
| `wiki/hypotheses.md:30-43` | read | Prose only — *"one open position, NVDA $220C exp 2026-09-18"*, *"H6-0001 is still open … the newest H6 receipt on disk is `reports/h6_forward/2026-07-27.json` and the close rule has never fired"*. **No quote.** Corroborates the fact |
| `wiki/log.md:148-160` | read | Prose only — *"H6-0001 recorded as open past its 21-DTE rule … newest receipt 2026-07-27"*. No quote |
| Obsidian vault roots on this machine: `options-validator/.obsidian` (vault = the repo, so `wiki/` is covered), `Claude.prod/obsidian` (39 `.md`), `Downloads/options-equity-obsidian` (21 `.md`), `equity-research/wiki` | `grep -rl '2026-09-18'` over each | **zero hits** in all three out-of-repo vaults |

**Verdict on (b): no observation lane found.** Both wiki notes that mention the
position independently state the 2026-07-27 edge.

**I did not repeat the full-cache scan.** I did re-run the four-lane
re-derivation end to end (that is §1/Q-1), and I re-confirmed Q's cache-wide
totals as a cheap cross-check: **48,758** parquet under `.cache`, **2,542**
NVDA-named, **31,367** under `.cache/chains` (the 31,367th is
`.cache/chains/dolthub/SPY_2022-12-30.parquet`).

---

## §3. Re-verification of every other number, hash, path, seq, line and date

All Run-verified 2026-09-15 from `/Users/carsynstephenson/options-validator-ops`
at `a3745ab` = `origin/main`. Fill model:
`proceeds = round(floor(bid × 0.99 × 100)/100 × 100 − 0.65, 2)`
(`h6_watch.py:440-446`, `strategies/base.py:17`, `config.py:94-95`:
`COMMISSION_PER_CONTRACT = 0.65`, `SLIPPAGE_HAIRCUT = 0.01`); trigger
`920.65 × 2 = 1,841.30`.

| Claim in Rev 6.1 | Result |
|---|---|
| entry 920.65 = 9.20 × 100 + 0.65; entry receipt `cc8ccd80d8fdd471…` | **exact** |
| book row `H6-0001,NVDA,220.0,2026-09-18,1,2026-07-13,920.65,cc8ccd80…,,,,` — four blank exit columns | **exact** |
| seq 6 exits verbatim "close at 21 DTE at conservative fills OR take-profit at +100% of premium, whichever first; NO stop-loss"; the fact says "in substance" | **exact** |
| seq 6 verdict rule "after 8 completed positions"; separate "hard kill … 3 consecutive calendar months each realizing the full monthly cap as losses" | **exact** |
| seq 6 registers **no** expiry handling | **exact** — `expiry`/`expiration` appear nowhere in the seq-6 `reason` |
| seq 6 `record_hash 5d813b8fe0e89f2d04fe41c9b16561e2374ff873d784a3cd9f2c91e4fe52f3cf`, ts `2026-07-09T00:50:22.721232+00:00` | **exact** |
| seq 22 `H6_KILL_V2`, `record_hash 4c552641d5a56f96d6e2c12904e7b20467a56bd1c7804d9de18969a3bb548b04`, entries on/after 2026-08-03 | **exact** |
| 21-DTE date 2026-08-28; 2026-07-27 → 2026-09-18 = 53 days | **exact** |
| required proceeds 1,841.30; minimum raw bid 18.61 (`proceeds(18.61)=1,841.35`, `proceeds(18.60)=1,840.35`); `2 × 920.65 ÷ 100 = 18.413` | **exact** |
| `h6_watch.py` lines 440-446 as described (440-443 proceeds, 444 round, 446 `if proceeds >= position.entry_cost * (1.0 + config.H6_TAKE_PROFIT_PCT)`) | **exact** |
| `config.py:347-349` = 1.00 / 21 / 8 | **exact** |
| OD-2 quotation, `facts.log:19347` | **exact** |
| new OD-2 clause: 19348-19350 approved a separate schema-v2 namespace reaching 2026-07-31, parked, no H6 code reads it | **exact** |
| last H6 receipt `reports/h6_forward/2026-07-27.json`, `c4b3138dd87053c7…`, HOLD / dte 53 / pnl −441.30 / proceeds 479.35 / `no_exit_trigger` / `completed_positions 0` / `INSUFFICIENT_SAMPLE` / "requires 8 completed positions" | **exact** |
| `reports/h6_forward/` holds exactly five files ending 2026-07-27 | **exact** |
| −441.30 = −47.93 % of 920.65 | **exact** |
| registered lane: `.cache/chains`, `h6_watch.py` line **951** | **exact** |
| 14 Schwab capture dates 2026-08-14 → 2026-09-10, every receipt tracked on `main`, `names.NVDA.status = ok`, recorded `sha256` == disk | **exact, all 14 re-hashed** |
| 2026-09-07 holiday artifact: `timestamp NaT`, `iv −9.99`, `delta −999.0` | **exact** |
| other 13 near 19:45 UTC, single exception 2026-08-19 at **19:49** UTC | **exact** (`19:49:27.678+00:00`) |
| intraday: 66 observations, 15 sessions, 2026-08-07 → 2026-09-03; **all 66** receipts tracked on `main` with `names.NVDA.status ok` and `chain_cache_path` | **exact** |
| intraday receipts bind **no** `sha256` | **exact** — checked on all 66, zero carry the key |
| chains_v2 clause: namespace path, "facts.log lines 19348 to 19350", "through 2026-07-31", five sessions, bids 4.85 / 4.80 / 3.25 / 4.05 / 5.40, sha256 in `_meta/chain_manifest.txt`, per-session attestation, audit "PASS WITH WARNINGS", NVDA not quarantined | **exact** — attestation `NVDA_2026-07-29.json` binds `dda5c750…`; `data/v2_partition_quarantine.json` holds only AMZN / AVGO / **AMD** at 2025-11-24; the audit report records 4,608 partitions and receipt identity `865024a8…` |
| "Taking all four lanes together, **23 of the 33**" | **exact** |
| "**84** observed quotes … 66 intraday, 14 Schwab pre-close and **4** schema-v2 sessions after the canonical edge"; none reaches 1,841.30 | **exact** — and 0 of all **86** in-window rows |
| best bid **15.05** on 2026-08-14 at 09:31 ET → **1,488.35** → **80.8 %** → **+61.66 %** | **exact** (80.83 %, +61.66 %) |
| **Fifteen** of 66 intraday exceed the best Schwab bid **13.50** (1,335.35, **72.5 %**) | **exact** (15 strictly exceed; 17 are ≥) |
| 2026-08-28 two lanes: Schwab 5.55 → 548.35 → −372.30 → −40.44 %; intraday 5.50 → 543.35 → −377.30 → −40.98 % | **exact** |
| unobserved list — 2026-08-03, 08-04, 08-05, 08-06, 08-10, 08-11, 08-21, 08-31, 09-01, 09-04 — **10** of 33 | **exact, set-identical** |
| 2026-09-04: no Schwab receipt; its four intraday snapshots carry only expiration **2026-10-16**, and every later in-window intraday NVDA file does too | **exact** |
| 2026-08-31 / 2026-09-01 Schwab receipts record auth failure | **exact** (`overall_status: failed`) |
| window 2026-07-27 → 2026-09-10 inclusive = **33** sessions, **12** closes above 220, max close **230.36**, max intraday high **234.76**, both 2026-09-04 | **exact** (21 highs above 220) |
| `.cache/underlying_ohlcv/NVDA.parquet` = **2,437** rows; `facts.log:19621` `DATA_PULL_OHLCV 2026-09-15 … NVDA rows=2437 path=.cache/underlying_ohlcv/NVDA.parquet` | **exact** |
| 2026-09-10 mark: bid 3.75 / ask 3.80, delta 0.463, iv 0.33917, OI 43021, ts `2026-09-10 19:45:33.824+00:00` | **exact** |
| receipt `sha256 9df5291708fe…a0f` == parquet on disk; `manifest_hash 4a4d697022…4d63` == `sha256(canonical_json(manifest − manifest_hash))` and `files.NVDA` carries the same `sha256` | **exact** — the `manifest_hash` derivation re-computed independently (`h6_features.py:212,234-236` convention) |
| mid 3.775 → 377.50 → −543.15 → **−58.996 %** | **exact** |
| `facts.log` lines 17892 / 19346 / 19413 / 19553 valid; file is **19,627** lines on `main` | **exact** |
| `grep -ci schwab options_researcher/h6_watch.py` → 0; `grep -ci chains_v2` → 0 | **exact** |
| `CITED` — 18 paths; 10 tracked on `main` today, the 8 audit receipts absent (expected: PR 175 not landed; the fact's own sequencing covers it) | **exact** |

---

## §4. Guard dry-run (stubbed `append_fact`, never the real one)

**Identity, first.** The Packet 1 blockquote is **15,275** characters and
**character-identical** to the string the command passes to `append_fact`.
`TEXT.startswith(KEY)` holds. The text contains **no** `'`, `"`, `$`, backtick,
`!` or byte above ASCII 126. Applying the guard's two `re.sub` calls yields a
**15,176**-character skeleton whose sha256 is
**`b157ac976e18c03b45609e1922d515ecaf24d83905cd91eb5f442e0465920062`** —
**matching the guard's pinned constant exactly**. Unprotected region: **107**
characters, the four slot values only. Packet 2: blockquote **4,638**
characters, character-identical, `sha256(TEXT)` = `c837b27e…b10f4`.

**Method.** Both guard programs were extracted verbatim from the packet's `sh`
fences. A clean synthetic repository was built at `/tmp/r6x/work` — a real git
checkout on `main`, at its `origin/main`, with **all cited paths committed**.
`BASE` was repointed at that tree; `sys.path` exposed a stub
`research.facts.append_fact` that prints its arguments and asserts the prefix
invariant. Where a scenario required the date gate to be behind us, the single
`if NOW < …` line was flipped to `if False:`. **For the synthetic rows only**,
`CANON` was replaced with a sentinel, because a local bare repo cannot present a
`github.com` URL; the origin check ran **unpatched** in rows 3, 6 and 7 and was
unit-tested separately.

| # | Scenario | Tree | Result |
|---|---|---|---|
| 1 | As shipped, today, placeholders present | ops | **rc 1** — *"It is 2026-09-15T14:01:48…-04:00 in New York, before 2026-09-19 00:00."* |
| 2 | Date gate bypassed, placeholders still present | ops | **rc 1** — *"unsubstituted placeholder in the fact text."* |
| 3 | Slots filled, ops tree as it stands today (origin check **unpatched**, passed) | ops | **rc 1** — *"is not clean … Outstanding: `['?? reports/intraday_capture/2026-09-15/']`"* |
| 4 | Side branch: primary checkout | primary | **rc 1** — *"is on branch claude/rest-2026-09-09, not main."* |
| 5 | Side branch: audit worktree | audit | **rc 1** — *"is on branch claude/audit-2026-09-15, not main."* |
| 6 | Wrong origin, `CANON` unpatched | synthetic | **rc 1** — *"origin is /tmp/r6x/upstream.git, not the options-validator remote."* |
| 7 | **P-9 exploit**: origin `/tmp/r6x/acc/carsynstephenson16-lang/options-validator.git`, `CANON` unpatched | synthetic | **rc 1 — closed.** |
| 8 | Label `Blog-source` | synthetic | **rc 1** — whitelist |
| 9 | **M-7 / P-7 exploit**: `"a blog post I found"` labelled `Official-source` | synthetic | **rc 1 — closed.** *"names none of Nasdaq, NYSE, Cboe, OCC or SEC"* |
| 10 | Intrinsic `9999.00` at close `213.40` | synthetic | **rc 1** — *"which is 0.00"* |
| 11 | Intrinsic `0.00` at ITM close `225.00` | synthetic | **rc 1** — *"which is 500.00"* |
| 12 | Intrinsic `whatever I want` | synthetic | **rc 1** — format |
| 13 | Prose tamper `80.8` → `99.9 percent` | synthetic | **rc 1** — skeleton hash |
| **13b** | **Tamper of the newly edited 6.1 sentence** — revert *"None of these off-lane sources … Schwab, intraday or schema-v2 lanes"* to the Revision-6 *"Neither off-lane source … Schwab or intraday lanes"* | synthetic | **rc 1** — skeleton hash. The invariant is bound to the **6.1** wording, not the 6 wording |
| 13c | Prose tamper `23 of the 33` → `29 of the 33` | synthetic | **rc 1** — skeleton hash |
| 13d | Prose tamper — chains_v2 bid list `… and 5.40` → `… and 18.70` | synthetic | **rc 1** — skeleton hash |
| 14 | `ledger/facts.log` modified | synthetic | **rc 1** — *"Outstanding: `['M ledger/facts.log']`"* |
| 15 | Unrelated untracked file | synthetic | **rc 1** — porcelain |
| 16 | `HEAD` one commit behind `origin/main` | synthetic | **rc 1** — both SHAs printed |
| 17 | **P-8 exploit**: audit receipts on disk, untracked | synthetic | **rc 1 — closed.** porcelain refuses `?? reports/2026-09-15-audit/` |
| 18 | Cited docs absent from `HEAD` **and** disk | synthetic | **rc 1** — names all seven missing audit paths, *"Land PR 175 on main first."* |
| 19 | **Q-6**: only `reports/thetadata_v2/2026-08-02-od1-full-audit.md` removed from `HEAD` | synthetic | **rc 1** — names exactly that path. The new citation is enforced |
| 20 | **ACCEPT** OTM: `213.40` / Nasdaq official closing price / `Official-source` / `0.00` | synthetic | **rc 0** — prints tree, branch, commit, target, `lines before`, calls the stub (`len(text) 15222`, prefix invariant holds), `lines after` |
| 21 | **ACCEPT** ITM: `225.00` / Nasdaq / `Official-source` / `500.00` | synthetic | **rc 0** — recomputation agrees |
| 22 | **ACCEPT** `Vendor-source` with a vendor source string | synthetic | **rc 0** — correct: the label is honest |
| 23 | Packet 2 on the clean synthetic tree | synthetic | **rc 0** |
| 24 | Packet 2 prose tamper (`4` → `9 losses`) | synthetic | **rc 1** — invariant hash |
| 25 | Packet 2 with `tools/h9_run_study.py` and `research/hashing.py` removed from `HEAD` | synthetic | **rc 1** — names both; `cat-file` is live on Packet 2 too |
| 26 | Packet 2 against the real ops tree | ops | **rc 1** — porcelain |

**Origin normaliser, unit-tested separately.** Accepts the four canonical forms
(including the ops tree's actual
`https://github.com/carsynstephenson16-lang/options-validator.git`). Rejects
`/tmp/acc/carsynstephenson16-lang/options-validator.git`,
`https://github.com/evil/carsynstephenson16-lang/…`, `https://notgithub.com/…`,
`https://github.com.evil.io/…` and `https://user:pw@github.com/…`.

**No guard defect found in Revision 6.1.** Q's judgement stands: the guard is the
strongest artifact in the packet, and I could not open a hole in it either.

---

## §5. Findings

### R-1 — **MUST-FIX** (drafting record, non-text). The packet advertises three different invariant hashes, and neither of the two it advertises is the one the guard enforces.

**Exact text, three places:**

> **Packet 1's** text changed, so its citation moves to rounds 1–6 … and its
> invariant hash is recomputed:
> **`7d6c7ed26562b5539ec7ecb2a797fbaa36a55c76883054d2e4886e0184c8b637`**.

> | **Citation carry-forward** | — | … new invariant **`7d6c7ed2…`**.

> Packet 1's new skeleton hash is `09b944ce…`

versus the operative constant inside the §1.5 command:

> `if hashlib.sha256(SKEL.encode()).hexdigest() != "b157ac976e18c03b45609e1922d515ecaf24d83905cd91eb5f442e0465920062":`

**Evidence.** Recomputing the guard's own two `re.sub` calls over the Revision
6.1 blockquote gives **`b157ac97…`** — the guard is **right**. Reconstructing
the pre-6.1 wording (*"Neither off-lane source … Schwab or intraday lanes"*) and
re-hashing gives exactly **`7d6c7ed2…`**, so that value is the **Revision 6**
skeleton, left stale by the 6.1 edit in both places. **`09b944ce…` reproduces
nothing** — not the 6.1 skeleton, not the 6 skeleton, not `sha256(TEXT)` for
either revision. It is an unsourced hash in a document whose whole purpose is to
let the owner verify before an irreversible write, and it sits in the paragraph
that claims *"the Packet 1 invariant sha256 was recomputed"*.

**Why it matters.** The failure mode is not a bad append — the guard refuses on
its own constant and that constant is correct. The failure mode is an owner who
cross-checks the packet's stated hash against the command, finds a mismatch,
cannot tell which is authoritative, and either aborts a correct append or edits
the guard constant to match the stale prose — which would silently disarm the
only protection over 99.3 % of the text.

**Replacement.** In all three places use
`b157ac976e18c03b45609e1922d515ecaf24d83905cd91eb5f442e0465920062`; delete
`09b944ce…`; and state in §4 that `7d6c7ed2…` was the Revision-6 value
superseded by the 6.1 edit, so the number is not simply erased from the record.

### R-2 — **NOTE** (fact text). The scope label on the "WHAT THOSE OBSERVATIONS SHOW" lead sentence still names only two lanes.

**Exact text:**

> on the observed **pre-close and intraday** quotes the plus 100 percent
> take-profit never fired. Across all 84 observed quotes on the **three**
> off-lane sources …

The lead scope phrase is a Revision-5 leftover of exactly the class the 6.1 fix
removed from the "neither" sentence. **It is not false** — on the pre-close and
intraday quotes the take-profit did not fire — and the very next sentence states
the wider scope correctly, and the omitted lane's maximum (5.40) is nowhere near
the trigger, so nothing is hidden. "on the observed off-lane quotes" would be
tidier.

**I do not recommend cutting a Revision 6.2 for it.** The change would recompute
the invariant hash, invalidate this receipt as a review of the appended words,
and require a round 7 — the exact "each revision widens the base and then
re-breaks its own coverage sentence" loop Q named, spent this time on a sentence
that is already true. Recorded so the owner decides with the residual in front
of them.

### R-3 — **SHOULD-FIX** (`CITED` list only — hash-neutral). The 2026-08-24 parked ruling is the one load-bearing claim in the fact with no citable location, and it is **not in `facts.log`**.

**Exact text:**

> That namespace is parked and excluded from verdict eligibility by the **owner
> ruling of 2026-08-24**, and it is cited here as descriptive evidence only,
> never as a mark source.

**Evidence.** `grep -in 'tier-2\|parked' ledger/facts.log` returns **no
2026-08-24 entry**; the ruling exists only as a Python string constant,
`tools/fill_haircut_calibration.py:39-43` (verbatim, verified), with a
supporting tracked report `reports/fill_calibration/2026-08-24-fill-adversity-context.md`
and a parked-namespace row at `docs/provider-transition.md:57`. Every other
load-bearing claim in this fact carries a path, a line number or a hash; this one
carries a date. A 2027 reader following the fact's own standard will look in
`facts.log` and find nothing.

**Mitigation, non-text.** Add `tools/fill_haircut_calibration.py` and
`reports/fill_calibration/2026-08-24-fill-adversity-context.md` to Packet 1's
`CITED` list. Both are **tracked on `main`** (verified), so the guard still
accepts; the `cat-file` check then binds the anchor, and §1.1e already quotes it
verbatim, which is what the fact's "tabulated in the drafting record" clause
points at. `CITED` is not part of `TEXT`, so **the invariant hash does not
change**. Naming the path inside the fact would be better still, but that is a
text change and is not worth a round 7 on its own — see R-2.

### R-4 — **NOTE** (drafting record). `_meta/chain_manifest.txt` entry count is off by the two header lines.

§1.1e says the manifest has **"(4,610 entries)"**. It has 4,610 **lines**, of
which the first two are `# chain-cache-manifest/v2` and
`# legacy-entry-defaults …` → **4,608 entries**, which is also the partition
count the audit report states ("18 symbols × 256 XNYS sessions = 4,608"). Not in
the fact text.

### R-5 — **NOTE** (drafting record). Three passages still carry Revision-4/5 framing.

- §1.2: *"the H6 evaluator rebuilds features from the **exact-session ThetaData
  chain**"* and *"states the off-lane evidence as a **union over both off-lane
  sources**"* — the exact phrasings Q-2 and Q-1 removed from the fact.
- §1.3(a): *"the **fourteen** off-lane captures with what they show"* — now 84
  observations on three lanes.
- §1.4 heading: *"Draft fact text — Packet 1 **(Revision 4)**"* — the text below
  it is Revision 6.1.

The fact's own "is tabulated in the drafting record" clause survives, because the
tabulation lives in §1.1, §1.1b and §1.1e, all of which are correct. This is
Q-7's unfinished half.

### R-6 — **NOTE** (fact text, no change recommended). The manifest tags the five files `usage=verdict-eligible`.

`_meta/chain_manifest.txt` marks each of the five NVDA rows
`schema_version=2  usage=verdict-eligible`, while the fact says the namespace is
"parked and excluded from verdict eligibility". Both are true — the per-file tag
was written at capture time on 2026-08-01, the parking ruling came on 2026-08-24
— and `Q` recorded the tension. A reader who opens the manifest before the ruling
will read a contradiction. Q's own replacement wording omitted the caveat too;
the fact's "never as a mark source" carries the operative restraint. Noted for a
future revision, not worth a text change now.

### R-7 — **NOTE** (fact text, no change recommended). "the only chain directory the H6 evaluator reads (line 951)" points at a default, not an enforcement.

`h6_watch.py:951` is a keyword-argument **default**
(`chain_dir: Path = Path(".cache/chains")`), and `:1306` exposes `--chain-dir` as
an overridable CLI argument with the same default. A reader who opens 951 sees a
default and may ask whether someone could point the evaluator at `chains_v2`.
The load-bearing conclusion does not rest on it: the v1 cache's last session for
every name is **2026-07-27** (independently verified), so no post-07-27 receipt
exists regardless, and `grep -ci chains_v2 options_researcher/h6_watch.py` is 0.
"reads by default" would be marginally more precise.

---

## §6. Wording review

**Are superlatives scoped to observed quotes?** **Yes.** *"on the observed
pre-close and intraday quotes"*, *"Across all 84 observed quotes"*, *"The best
bid observed **anywhere**"* — re-verified as the true global maximum over all 86
in-window rows on all four lanes — followed by *"THESE ARE THE QUOTES THAT WERE
CAPTURED"*, the explicit 10-date list, and *"Nothing is asserted here about what
the contract was worth on those 10 sessions."* One residual scope label at R-2.

**Does it pre-decide?** **No.** `Owner ratification: ______` is blank. The text
says the owner approves by reading it and running the append; options (b) and (c)
are named and *"are not adopted by this append"*; the drafting agent's reasons
are pushed to the drafting record *"and are not attributed to the owner"*.

**Does it legislate?** **No.** `NO RETROACTIVE RULE CHANGE` is present —
*"amends nothing, changes no registered exit, and creates no precedent for
booking a reconstructed close from a quote"* — and the one convention it adopts
is declared prospective-neutral. `RECOMMENDED FORWARD PRACTICE` language is
confined to Packet 2 and is explicitly non-binding there.

**Does it change a registered number?** **No.** H6 stays `INSUFFICIENT_SAMPLE`
at n = 0 against the 8-completed bar (seq 6 and `config.py:349` re-checked); seq
22 is untouched and correctly described as prospective-only; the book row's four
exit columns are verified blank and the fact says they stay blank and why.

**Is the Assumption label on the intrinsic convention intact?** **Yes.** *"as a
valuation convention adopted by this fact and by nothing earlier (Assumption,
stated so, because experiments.jsonl seq 6 registers no expiry handling at
all)"* — and seq 6 does indeed contain no expiry handling (verified: neither
"expiry" nor "expiration" occurs in its `reason`). Backed by *"For disclosure
purposes only - this valuation is recorded in this fact and nowhere else"*, the
physical-settlement / OCC carve-out, and the prospective-neutral clause.

**Does the OD-2 clause say which cache it governs?** **Yes**, and correctly:
*"that decision governs the v1 canonical cache, and facts.log lines 19348 to
19350 later approved a separate schema-v2 namespace reaching 2026-07-31, which is
parked and which no H6 code reads"*. Verified line by line.

**Is "None of these off-lane sources" grammatical and true?** **Yes.** Singular
"is" after "None of these … sources" is standard; the sentence reads cleanly.
True: `grep -ci schwab options_researcher/h6_watch.py` → 0 and
`grep -ci chains_v2` → 0, and no H6 receipt exists on any of the three lanes.

**What could a 2027 reader misread?**

1. **The three conflicting invariant hashes (R-1)** — the packet, not the fact,
   but it is the number the owner is told to trust.
2. **"the owner ruling of 2026-08-24" (R-3)** — locatable only outside
   `facts.log`.
3. **`usage=verdict-eligible` in the manifest (R-6)** — reads against "excluded
   from verdict eligibility" until the reader finds the later ruling.
4. **"line 951" (R-7)** — a default, not an enforcement.
5. **"19:45 UTC"** with no ET translation in a text that otherwise uses New York
   time. Harmless; carried from Q.
6. **"provider-dependent within the 543.35 to 548.35 USD band"** — the sentence
   does define the cost as that value **minus** the expiration intrinsic and
   flags the net-vs-gross asymmetry. Acceptable as written; carried from Q.

---

## §7. What must change before Packet 1 goes to the owner

**Blocking (fact text):** **nothing.**
**Must (drafting record, hash-neutral):** **R-1**.
**Should (`CITED` only, hash-neutral):** **R-3**.
**Note:** **R-2**, **R-4**, **R-5**, **R-6**, **R-7**.

Then the packet's own sequencing applies unchanged: land PR 175 on `main`,
`git pull --ff-only` in `/Users/carsynstephenson/options-validator-ops`, commit
the outstanding `reports/intraday_capture/2026-09-15/` ritual artifact so
porcelain is empty, wait for 2026-09-19, fill the four slots, read the text on
screen, and run the command from that tree.

---

*Nothing in this review was appended to any ledger. No ledger-writing tool was
called; `append_fact` was exercised only against a local stub that wrote nothing.
No commit was made, no packet or ledger file was modified, the synthetic
repository used to exercise the accept path was created under `/tmp` and deleted,
and the only file created is this one.*
