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
