# Deferred-closeout rulings — 2026-08-28 (owner in-session)

**Context:** the owner directed "finish everything that's deferred" and
ruled each open item via decision prompt. This report is the durable record;
execution artifacts are briefs 32–35 (`docs/superpowers/plans/2026-08-28-*`).

## Rulings

1. **DATA-02 (per-quote age gate): COMMISSION NOW** → brief 32. Warn-first,
   mode-gated; `block_selectable` activation impossible until the owner
   types the threshold (candidates 10/15/20 min in the brief, all
   LLM-proposed, none frozen).
2. **DATA-03 (closes provenance receipt): COMMISSION NOW** → brief 33.
   Additive receipt copying the in-file chain-topup hashing pattern;
   honestly labeled `fetched_frame_sha256` (raw HTTP bytes are not
   retained by the fetcher).
3. **CI: macOS shell job ONLY** → brief 34. repo-rag CI **DECLINED** —
   evidence shown to the owner: the health agent runs and passes (Aug 26:
   848 sources, 0 failures) but the tool has zero consumers; it stays an
   unsupported convenience. Re-open only if something starts depending on
   it.
4. **Ops capture logs (`~/options-validator-ops/.tmp/schwab_chain_capture/`):
   EXPENDABLE — do nothing.** Deliberate ruling; the evidentiary receipts
   and data are protected elsewhere. Do not re-flag.

## Executed same session (no decision needed)

- **SEC-02 close-out:** post-#97 second redeploy run
  (`tools/anti-stranding/install.sh` + kickstart); verified
  `~/bin/repo-reconcile` and `~/.githooks/post-commit` byte-identical to
  origin/main. The ownership gate, gitleaks scan, and born-draft PR
  default are now LIVE on this machine.
- Worktree/draft-PR cleanup sweep and briefs 32–35 review pipeline:
  in flight this session (results recorded in the session artifacts).

## Already closed before this session (verified on main, no action)

DATA-01 (#96, inventory floors live: 90 files/9.7 MB recorded), SEC-01
follow-up (#98 contract pin), SEC-02 code (#97), brief 30 WP-A (#100),
brief 31 digest (#99), pick tracker (#93).

## Still owner-only

- **Schwab token re-auth** by ~2026-08-30 (browser + secret; cannot be
  delegated).
- **H7 bar-7 registration packet** (draft PR #101) — the next big strategy
  decision; gets its own decision package after this closeout lands.
- DSR + robustness-gate instrument-only draft specs (draft PR #114) —
  still awaiting the owner's earlier-requested decision.

---

## Correction + final outcomes appended 2026-08-28 ~14:15 ET (append-only)

**Ruling 1 correction (round-3 review finding F3):** the DATA-02
disposition above ("warn-first, mode-gated" gate) is SUPERSEDED. Two
independent reviews failed that design — round-2 finding N1 proved the
gate has no production surface (`h7_schwab_data_gate.evaluate()` has zero
production callers; the daily gate reads the timestampless v1 cache). The
owner re-ruled in-session ("Report now, gate later"): **the deliverable
NOW is a descriptive daily quote-age sidecar report riding the 15:45
capture (brief 32 rev 4, HANDED OFF after round-3 PASS WITH FIXES); the
BLOCKING gate + owner-typed threshold are a binding requirement of the
future H7 Schwab registration arc** (trigger = the registration event
alone). Threshold evidence recorded for that day: worst SELECTABLE quote
age across all 7 timestamped sessions = 0.61–10.38 min (10-min block ⇒
1-of-7 sessions NO_GO; 15/20-min ⇒ none; n=7, Reviewer-measured
2026-08-28, not owner-typed).

**Final brief pipeline:** 32 rev 4 HANDED OFF (3 review rounds), 33 rev 3
HANDED OFF (2 rounds, M1–M6), 34 rev 2 HANDED OFF (1 round), 35 rev 2
HANDED OFF (1 round). Landing order: 35 before 33; 32 after 33 if it
needs the default-mask accessor.

**Cleanup final tally:** 28 worktrees removed (guard OK before/after
every batch), 22 branches deleted local+remote, 9 stale PRs closed with
recorded reasons, 4 review-cited SHAs preserved on `rescue/*` branches,
789 lines of composite-lane literature rescued into
`reports/literature/2026-08-04-composite-lane/`. Remaining worktrees are
all deliberate: 3 checkouts, the protected H7-packet host, and 4 holding
unlanded unique work.

**Owner list (unchanged owner-only items + new dispositions needed):**
Schwab token re-auth ~08-30; H7 bar-7 packet ruling (PR #101 — note its
§0 precondition table says "all four" over five rows, and it needs a row
for the quote-age gate requirement above); unlanded-unique branches
PR #94 (daily-ritual plist — RECOMMEND LAND: only tracked copy of a
production plist), PR #71 + PR #102 (H7 work — ride the H7 ruling),
PR #103 (A2 battery — needs its own review round), and four old drafts
with unique content needing deliberate disposition (#60 QM-dashboard
July work, #61 branch-hygiene doc, #88 capture-hardening + VST analyst
docs, #115 merge-sweep bundle).
