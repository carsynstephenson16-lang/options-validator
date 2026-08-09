# Independent Research Critic Rules

1. Use `America/New_York` for temporal comparisons and bind every audit to the
   producer manifest's `run_id` plus context SHA-256; never use mtime.
2. Prefer canonical repository evidence and independently fetched primary
   sources over aggregators or producer prose.
3. Require exact live-candidate coverage and manifest-bound packet lineage.
4. Require `PJM_BRA_NEXT`, `confirmed: false`, and an official PJM URL for both
   VST and CEG until PJM publishes the exact auction date.
5. Remain read-only and never change research, hypothesis, dashboard, or trade
   state.

Full procedure and source of truth:
`.agents/skills/independent-research-critic/SKILL.md`. When a guardrail
changes, update both files together so they do not drift.
