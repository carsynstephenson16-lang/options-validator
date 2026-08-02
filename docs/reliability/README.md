# Reliability checklist profile

This directory vendors version 1 of the five-source portfolio reliability
catalog and maps all 120 items to Options Validator evidence or explicit gaps.
The integration is a read-only advisory layer and adds no runtime dependency.

Run from the repository root:

```bash
.venv/bin/python scripts/reliability_checklist.py audit --format both
```

The lock pins the catalog digest and standards commit. The snapshot is the
immutable input; the profile contains repository-specific mappings and
owner-reviewed priority inputs; the structured receipt records validation
evidence. The reporter verifies relative paths, hashes, symbols, Git ancestry,
mapping completeness, and N/A expiry before calculating results.

The MLTS result preserves the source's 0/1/2 category scoring and minimum-area
score. `STALE` is computed, never authored. No score or priority band can reveal
a holdout, change a verdict, write research state, or approve an experiment.
Explicit owner approval remains mandatory before every experiment or promotion.
