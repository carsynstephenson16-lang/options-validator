# Owner decision record — ritual switch-on D-1 … D-4 (2026-08-14, evening)

**Owner wording (in-session, 2026-08-14 evening):** "go ahead with D-1 through
D-4, implement the switch-on."

The decisions below adopt the recommendations presented in
`docs/superpowers/plans/2026-08-14-11-ritual-switch-on-rev2-spec.md` §12 and
relayed to the owner in the same session via
`reports/2026-08-14-owner-decision-package.md` Group 1. Provenance for this
record: owner-directed in-session 2026-08-14; recorded by the implementing
session per the owner-delegated standing 2026-07-25 (recording only — the
decisions themselves are the owner's, given above in the owner's words).

## Decisions

### D-1 — Hypothesis fence: **F1**

No hypothesis lane (H5/H6/H8/H10, steps 10–14) runs under data-tier
authority. All are chain-starved at the 2026-07-27 cache edge; F2 would
produce only DATA_GAP records, and F3 would append starved observations to a
registered hypothesis's record under an authority tier that asserts no
exact-session data.

### D-2 — Flip `ritual_data_phase_active` to True: **YES**

The switch-on itself. Asserts only that the owner authorizes the daily
non-verdict-bearing data/display phase to run from cached data — nothing
about a live source, nothing about H7. Executed as a separate one-line commit
after the implementation passes independent adversarial review, with the
provenance comment specified in spec §11.7.

### D-3 — Capture-wrapper alignment-gate relaxation: **YES**

`tools/schwab_chain_capture.sh` tolerates evidence-only divergence: every
commit in `origin/main..HEAD` must touch only evidence allow-list paths, else
refuse as today. Preserves the gate's purpose (no unreviewed *code* runs
unattended) while ensuring a transient push failure can no longer cost an
irreplaceable 15:45 capture.

### D-4 — `exact_session_source_active` honesty bar: **S1 ratified**

Three consecutive scheduled trading sessions with offline-verifying preclose
receipts (full registered watch universe), no forced-capture marker in the
span, and the LaunchAgent loaded with last exit 0 — per spec §7 as restated
in artifact-measurable terms. The "three consecutive" threshold remains
LLM-proposed in provenance; the owner's go-ahead ratifies it for this bar.

**OPEN sub-fork (deliberately not decided here):** S1 condition 3
(unattended-vs-manual provenance) requires the owner to choose **3a** (add an
`invocation_source` field to the capture receipt — a hashed
`options_researcher/` change, to be batched per spec §11) or **3b** (drop the
condition, rely on conditions 1, 2 and 5). The owner's directive did not name
either. This fork blocks nothing today — the bar is only consulted before a
future `exact_session_source_active` flip — and MUST be resolved by the owner
before that flip. Until then the bar is S1-with-condition-3-unresolved.

## Explicitly still open (not covered by the directive)

- **D-6** (intra-day "ops is behind" detection: scheduled check / manual
  habit / accept risk). Docs land with rules R1+R2 recorded and D-6 noted as
  pending.
- **D-4 sub-fork 3a/3b** (above).
- Everything in decision-package Groups 2–3 (variant pick, registration
  authorization, `h7_active`) — untouched by this record.
