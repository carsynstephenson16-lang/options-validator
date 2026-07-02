# Seed hygiene: `hash()`-derived seeds made a Monte Carlo study irreproducible

**One line:** a power study seeded with Python's builtin `hash((label, edge))`
produced numbers that changed on every process start (PYTHONHASHSEED string
randomization), and single-run cells swung by up to ±13pp -- caught only
because a fresh-context auditor re-ran the script and got different results.

**Why it mattered:** the study's headline numbers (false-PASS rate, power at
plausible edges) feed a real spending decision, in a repo whose entire
identity is frozen reproducible verdicts. Publishing 1pp-precision numbers
from an irreproducible run would have been exactly the kind of quiet
dishonesty the project exists to catch. The v1 numbers were retracted.

**Rules adopted (now in analysis/power_check.py):**
- Never seed from builtin `hash()` of strings; use explicit integers /
  `np.random.SeedSequence([...])` with stable components.
- Keep the data-generation stream and the bootstrap stream SEPARATE.
- Report Monte Carlo proportions with Wilson intervals, never bare
  percentages from ~30 reps.
- Have someone (or a fresh agent) RE-RUN the script before its numbers are
  cited anywhere; "same command, same output" is part of done.
