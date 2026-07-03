"""
analysis/power_check.py -- power/size study of the VERDICT PATH itself.

Before paying for data, answer a blunter question than feasibility: if Strategy A
had a real edge of plausible size, could the frozen verdict machinery even SEE
it -- and how often does it certify a PASS when there is NO edge at all? A
harness that cannot detect a plausible edge, or that false-PASSes well above its
nominal rate, must be known to do so BEFORE the first registered run, not after.

This study is SYNTHETIC: it measures the instrument, not the strategy. It never
touches market data (so it cannot touch the OOS holdout) and it goes through the
repo's real, frozen CI machinery -- metrics._build_week_cohorts and
metrics._ci_from_cohorts, widest envelope, PASS iff CI90 lower bound > 0 -- with
the scoreboard's verdict gates replicated in classify() (kept honest by
tests/test_power_check.py against scoreboard()).

Generative model (per-trade PnL in width units, W = A_SPREAD_WIDTH * 100 $):
- 5 symbols, one open position per symbol, sequential re-entry; holds 2-5 weeks
  (a mix of profit-target early exits and 7-DTE closes). ASSUMPTION.
- Weekly market factor; a trade's systematic draw is the normalized mean of the
  factor over its holding weeks (overlap => serial dependence), with
  CROSS_A2 = 0.85 systematic variance share. The resulting PnL-level
  correlation is MEASURED by measure_dependence() and printed -- it lands at
  ~1.5 effective bets across the 5 names, matching config's concentration flag.
- P(loss) = 0.25 (short-vol shape). ASSUMPTION.
- Win = A_PROFIT_TARGET * assumed credit (+noise); loss = -A_STOP_LOSS * assumed
  credit (+noise; the 2x-credit stop). Credit = ASSUMED_CREDIT_FRAC of width,
  same assumption feasibility.py uses until real chains replace it.
- The whole distribution is shifted so the true mean equals the edge under test.

Findings are recorded in
docs/superpowers/specs/2026-07-02-pre-registration-design-decisions.md.

Run from the repo root:
    python analysis/power_check.py --quick   # smoke (~seconds, noisy)
    python analysis/power_check.py           # full study (~40 min, reproducible)
"""
import os
import sys
from datetime import date, timedelta

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config  # noqa: E402
from analysis.feasibility import ASSUMED_CREDIT_FRAC  # noqa: E402
from metrics import _build_week_cohorts, _ci_from_cohorts  # noqa: E402

# ---- strategy-shaped parameters: sourced from config, never re-invented ------
W = config.A_SPREAD_WIDTH * 100.0          # $ per width unit, 1 contract
CREDIT_FRAC = ASSUMED_CREDIT_FRAC          # same assumption as feasibility.py
WIN_MEAN = config.A_PROFIT_TARGET * CREDIT_FRAC     # +50% of credit captured
LOSS_MEAN = -config.A_STOP_LOSS * CREDIT_FRAC       # 2x-credit stop
N_SYMBOLS = len(config.UNIVERSE)

# ---- study assumptions (documented above; not config knobs) ------------------
CROSS_A2 = 0.85        # latent systematic variance share; PnL corr is measured
P_LOSS = 0.25
WIN_SD, LOSS_SD = 0.02, 0.12
BASE_MEAN = (1 - P_LOSS) * WIN_MEAN + P_LOSS * LOSS_MEAN
Z_CRIT = -0.6744897501960817               # Phi^-1(P_LOSS)
HOLD_CHOICES = np.array([2, 3, 4, 5])      # weeks
HOLD_PROBS = np.array([0.25, 0.30, 0.25, 0.20])

# Edges under test, as fractions of W: $0 (size), then plausible -> implausible.
EDGE_FRACS = (0.0, 0.02, 0.05, 0.10)

# Windows. IS is derived from config. BOTH OOS window candidates are kept so the
# blind pre-registration choice between them stays reproducible; the extended
# window was adopted into config.BACKTEST_END on 2026-07-02, decided BLIND
# (no post-IN_SAMPLE_END market data fetched or opened).
def _weeks(a, b):
    return (date.fromisoformat(b) - date.fromisoformat(a)).days // 7


SCENARIOS = [
    (f"IS {config.BACKTEST_START[:4]}-{config.IN_SAMPLE_END[:4]}",
     _weeks(config.BACKTEST_START, config.IN_SAMPLE_END),
     date.fromisoformat(config.BACKTEST_START)),
    ("OOS 2023..2024-12-31", _weeks("2023-01-02", "2024-12-31"), date(2023, 1, 2)),
    ("OOS 2023..2026-06-30", _weeks("2023-01-02", "2026-06-30"), date(2023, 1, 2)),
]


def _pnl_from_z(z, rng):
    if z < Z_CRIT:
        return LOSS_MEAN + LOSS_SD * rng.standard_normal()
    return WIN_MEAN + WIN_SD * rng.standard_normal()


def simulate_trades(n_weeks, start_monday, edge_w, rng):
    """One simulated trade history. Returns (entry_dates_iso, pnls_dollars)."""
    factors = rng.standard_normal(n_weeks + 8)
    a = np.sqrt(CROSS_A2)
    entries, pnls = [], []
    for _ in range(N_SYMBOLS):
        week = int(rng.integers(0, 3))
        while week < n_weeks:
            hold = int(rng.choice(HOLD_CHOICES, p=HOLD_PROBS))
            f_window = factors[week:week + hold].mean() * np.sqrt(hold)  # ~N(0,1)
            z = a * f_window + np.sqrt(1 - CROSS_A2) * rng.standard_normal()
            pnl_w = _pnl_from_z(z, rng) + edge_w - BASE_MEAN
            entries.append((start_monday + timedelta(weeks=week)).isoformat())
            pnls.append(pnl_w * W)
            week += hold + 1
    return entries, pnls


def measure_dependence(n_pairs=200_000, seed=99):
    """Measured PnL correlation of two fully-overlapping trades sharing a factor
    window, and the implied effective-bet count across the universe."""
    rng = np.random.default_rng(seed)
    a = np.sqrt(CROSS_A2)
    f = rng.standard_normal(n_pairs)
    p1, p2 = np.empty(n_pairs), np.empty(n_pairs)
    for i in range(n_pairs):
        z1 = a * f[i] + np.sqrt(1 - CROSS_A2) * rng.standard_normal()
        z2 = a * f[i] + np.sqrt(1 - CROSS_A2) * rng.standard_normal()
        p1[i] = _pnl_from_z(z1, rng)
        p2[i] = _pnl_from_z(z2, rng)
    rho = float(np.corrcoef(p1, p2)[0, 1])
    n_eff = N_SYMBOLS / (1 + (N_SYMBOLS - 1) * rho)
    return rho, n_eff


def classify(n_losses, n_cohorts, ci_lo, ci_hi):
    """Mirror of scoreboard()'s verdict gates, in the same precedence order.
    Kept honest by tests against the real scoreboard."""
    if n_losses < config.MIN_LOSSES_FOR_VERDICT:
        return "INSUFF"
    if n_cohorts < 3:
        return "INSUFF"
    if ci_lo > 0:
        return "PASS"
    if ci_hi < 0:
        return "FAIL"
    return "NO-EDGE"


def wilson(k, n, z=1.96):
    """Wilson score interval for a binomial proportion."""
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, center - half), min(1.0, center + half)


def run_scenario(cell_id, label, n_weeks, start, edge_w, reps, n_boot):
    counts = {"PASS": 0, "FAIL": 0, "NO-EDGE": 0, "INSUFF": 0}
    widths, n_trades_all, n_losses_all = [], [], []
    for r in range(reps):
        data_rng = np.random.default_rng(np.random.SeedSequence([1234, cell_id, r]))
        entries, pnls = simulate_trades(n_weeks, start, edge_w, data_rng)
        n_losses = int((np.asarray(pnls) < 0).sum())
        cohorts = _build_week_cohorts(entries, pnls)
        if classify(n_losses, len(cohorts), 0.0, 0.0) == "INSUFF":
            counts["INSUFF"] += 1
            continue
        boot_seed = 777_000_000 + cell_id * 1_000_000 + r  # stream != data stream
        lo, hi = _ci_from_cohorts(cohorts, len(pnls), n_boot, 5, 95, seed=boot_seed)
        counts[classify(n_losses, len(cohorts), lo, hi)] += 1
        widths.append(hi - lo)
        n_trades_all.append(len(pnls))
        n_losses_all.append(n_losses)
    w_lo, w_hi = wilson(counts["PASS"], reps)
    med_w = float(np.median(widths)) if widths else float("nan")
    print(f"{label:22s} edge=${edge_w * W:6.2f} | "
          f"trades~{int(np.median(n_trades_all)) if n_trades_all else 0:4d} "
          f"losses~{int(np.median(n_losses_all)) if n_losses_all else 0:3d} | "
          f"PASS {counts['PASS']}/{reps} = {counts['PASS'] / reps:5.1%} "
          f"[Wilson95 {w_lo:5.1%}..{w_hi:5.1%}]  "
          f"NO-EDGE {counts['NO-EDGE'] / reps:5.1%}  "
          f"FAIL {counts['FAIL'] / reps:5.1%}  "
          f"INSUFF {counts['INSUFF'] / reps:4.1%} | med CI width ${med_w:6.2f}",
          flush=True)


def run(quick=False):
    reps_size, boot_size = (8, 100) if quick else (120, 2000)
    reps_pow, boot_pow = (6, 100) if quick else (50, 1000)
    rho, n_eff = measure_dependence(n_pairs=20_000 if quick else 200_000)
    print("=" * 78)
    print("POWER/SIZE STUDY of the frozen verdict path (synthetic; measures the")
    print("instrument, not the strategy; no market data touched)")
    print("=" * 78)
    print(f"measured fully-overlapping PnL correlation {rho:.3f} -> "
          f"~{n_eff:.2f} effective bets across {N_SYMBOLS} names "
          f"(config flags ~1.5)")
    print("PASS rule: widest-envelope 90% CI lower bound > 0 (metrics.py, frozen)")
    if quick:
        print("QUICK MODE: numbers are smoke-level noisy; run full for the record")
    print(flush=True)
    cell_id = 0
    for edge_w in EDGE_FRACS:
        is_size_row = edge_w == 0.0
        reps = reps_size if is_size_row else reps_pow
        n_boot = boot_size if is_size_row else boot_pow
        tag = "SIZE (false-PASS rate)" if is_size_row else "POWER"
        print(f"-- {tag}: true edge ${edge_w * W:.2f}/trade, reps={reps}, "
              f"n_boot={n_boot} --", flush=True)
        for label, n_weeks, start in SCENARIOS:
            run_scenario(cell_id, label, n_weeks, start, edge_w, reps, n_boot)
            cell_id += 1
        print(flush=True)
    print("Reading this: if PASS at $0 edge is materially above ~5%, the CI90")
    print("undercovers under this dependence; if PASS at a plausible edge is not")
    print("far above the $0 row, the harness cannot discriminate that edge --")
    print("an honest NO-EDGE is then the EXPECTED verdict, and a PASS is weak")
    print("evidence on its own. Neither is a reason to loosen anything; it is")
    print("what this experiment, at this concentration, can honestly resolve.")


if __name__ == "__main__":
    run(quick="--quick" in sys.argv[1:])
