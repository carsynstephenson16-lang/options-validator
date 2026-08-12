# H7 Schwab restart machinery — session note

**Status:** BUILD COMPLETE THROUGH PRE-CANARY READINESS / NOT REGISTERED /
NOT ACTIVATED / NOT MERGED.

## Completed

- Preserved August ops evidence on pushed branch
  `evidence/ops-august-2026-08-09` at
  `863175a895b7beaf3f604fc3880c6b69e50a2aa7`.
- Fast-forwarded ops `main` and research `deploy/research` to
  `71e05264447d424622c14b95e5084d893f5133bb`; both validated offline.
- Built the independent durable Schwab full-chain capture, manifest verifier,
  exact-session gate, separate 15:45 LaunchAgent template, new registration
  builder/guarded door, empty ledger namespace, and cached feasibility tool.
- Sunday sentinel invocation refused outside the regular session with exit 1
  before constructing a market-data client.
- Computed 3/1,050 full-stack passes and 3.0 projected entries; no verdict was
  emitted.

## Integrity checkpoints

- Old `ledger/h7_forward/events.jsonl` SHA-256 before/after:
  `6a9bc9820f6afb787683640f188bc4a51c086aa35d6702eb9086ea37bfa070ec`.
- Old `ledger/h7_forward/HEAD` SHA-256 before/after:
  `9ec2a37347346343e62c1af69885964c8d2cd98aa49acd1080f04c6cae380c20`.
- Old store: `VALID records=1 head=a1ea228c2abb`.
- New store: `VerifyResult(valid=True, empty=True, count=0, head=None)`.
- Authority constants remain both `False`; no registration event exists.

## Correction note (2026-08-12, audit M6)

Commit `d77f995` ("docs(h7): record fresh Schwab feasibility") was not
docs-only: it also removed the `feasibility["code_sha"] != evidence["code_commit"]`
equality check from `h7_schwab_window_registration.build_window_registration_event`
(a deliberate loosening — receipts may legitimately predate doc-only commits —
covered by a new test; the receipt's own hash binding via
`_validate_feasibility` is unchanged). Recorded here because the commit label
hid a functional change to registration validation from changelog-level review.

## Pending / stop points

- Backup/restore drill: `BLOCKED_PENDING_MONDAY_CANARY`; there are no live
  `.cache/schwab_chains` bytes to snapshot or restore honestly on Sunday.
- Independent adversarial review: pending orchestrating Claude/Opus; request is
  included in the owner packet.
- Monday live canary, owner decisions, guarded registration, authority flip,
  and merge remain owner-gated and were not performed.
