"""
metrics.py -- the SCOREBOARD.

Answers "does this strategy have positive expectancy after costs?" and, just as
importantly, refuses to answer when the sample is too thin to mean anything.

Design principle (the load-bearing one): in a high-win-rate short-vol strategy a
long string of wins is EXPECTED and proves nothing -- the rare losses decide
whether the edge is real. So the verdict gates on the number of LOSSES, not the
number of trades, and the headline metric is expectancy-per-trade with a
confidence interval, not a point estimate or a flattering win rate.

Input: a list of closed trades. Each trade is a dict with at least:
    pnl              net profit/loss in $ AFTER all costs (commission + slippage)
    capital_at_risk  $ tied up (defined-risk max loss) while the trade was open
Optionally:
    is_win           bool; if present, must agree with pnl > 0
    economic_max_loss margin + round-trip commissions; secondary diagnostic only

Run a demo:  python metrics.py
"""
from __future__ import annotations

from datetime import date

import numpy as np

import config


def _as_date(x):
    if isinstance(x, date):
        return x
    if isinstance(x, str):
        try:
            return date.fromisoformat(x)
        except ValueError as exc:
            raise ValueError(f"invalid ISO date: {x!r}") from exc
    raise ValueError(f"expected ISO date string or date object, got {type(x).__name__}")


def _iso_week_key(d):
    iso = _as_date(d).isocalendar()
    return (iso[0], iso[1])  # (ISO year, ISO week)


def _build_week_cohorts(entry_dates, pnls):
    """Group PnLs into cohorts keyed by ISO week of entry, ordered chronologically.

    Weekly cohorts keep same-week trades across all names as one INDIVISIBLE unit
    (the cross-sectional axis); the block bootstrap over the ordered cohort
    sequence handles the serial axis (Task 12)."""
    if config.COHORT_GRANULARITY != "week":
        raise ValueError(f"unsupported COHORT_GRANULARITY: {config.COHORT_GRANULARITY!r}")
    order = sorted(range(len(entry_dates)), key=lambda i: _as_date(entry_dates[i]))
    groups = {}
    keys_in_order = []
    for i in order:
        k = _iso_week_key(entry_dates[i])
        if k not in groups:
            groups[k] = []
            keys_in_order.append(k)
        groups[k].append(float(pnls[i]))
    return [np.array(groups[k], dtype=float) for k in keys_in_order]


def _block_lengths(n_cohorts):
    """Frozen, theory-anchored mean block lengths (in cohorts): round(c*n^(1/3)),
    deduped, clamped to 2 <= L <= n_cohorts-1. Empty if n_cohorts < 3 (no valid
    block) -> the caller returns INSUFFICIENT SAMPLE / no verdict."""
    if n_cohorts < 3:
        return []
    lengths = set()
    for c in config.BOOTSTRAP_BLOCK_CONSTANTS:
        L = int(round(c * n_cohorts ** config.BOOTSTRAP_BLOCK_EXPONENT))
        L = max(2, min(L, n_cohorts - 1))
        lengths.add(L)
    return sorted(lengths)


def _resample_block(cohorts, n_target, block_len, rng):
    """Circular block bootstrap over the ordered cohort sequence. Accumulates
    contiguous blocks of whole cohorts (with wraparound) until >= n_target trades,
    then returns the mean PnL per trade of the resample."""
    n = len(cohorts)
    acc = []
    total = 0
    while total < n_target:
        start = int(rng.integers(n))
        for j in range(block_len):
            c = cohorts[(start + j) % n]
            acc.append(c)
            total += len(c)
            if total >= n_target:
                break
    return float(np.concatenate(acc).mean())


def _resample_stationary(cohorts, n_target, block_len, rng):
    """Stationary bootstrap (Politis-Romano): geometric block length with mean
    `block_len` (p = 1/block_len), over the same cohort sequence."""
    n = len(cohorts)
    p = 1.0 / block_len
    acc = []
    total = 0
    idx = int(rng.integers(n))
    while total < n_target:
        c = cohorts[idx]
        acc.append(c)
        total += len(c)
        if rng.random() < p:
            idx = int(rng.integers(n))
        else:
            idx = (idx + 1) % n
    return float(np.concatenate(acc).mean())


def _ci_one(cohorts, n_target, block_len, method, n_boot, rng, lo, hi):
    fn = _resample_block if method == "block" else _resample_stationary
    means = np.empty(n_boot)
    for i in range(n_boot):
        means[i] = fn(cohorts, n_target, block_len, rng)
    return float(np.percentile(means, lo)), float(np.percentile(means, hi))


def _ci_from_cohorts(cohorts, n_target, n_boot, lo, hi, seed):
    """Widest CI across ALL (method, block_len) combinations: min lower bound,
    max upper bound. No configuration can be selected because it flatters."""
    Ls = _block_lengths(len(cohorts))
    if not Ls:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    los, his = [], []
    for method in ("block", "stationary"):
        for L in Ls:
            lo_b, hi_b = _ci_one(cohorts, n_target, L, method, n_boot, rng, lo, hi)
            los.append(lo_b)
            his.append(hi_b)
    return (min(los), max(his))


def _dependence_aware_ci(entry_dates, pnls, n_boot=None, lo=5, hi=95, seed=42):
    """Verdict CI: weekly-cohort block bootstrap + stationary cross-check over a
    shared frozen block-length envelope, reporting the widest CI."""
    n_boot = n_boot or config.BOOTSTRAP_SAMPLES
    cohorts = _build_week_cohorts(entry_dates, pnls)
    return _ci_from_cohorts(cohorts, len(pnls), n_boot, lo, hi, seed)


def iid_expectancy_ci(pnls, n_boot=None, lo=5, hi=95, seed=42):
    """EXPLICIT, opt-in IID resample -- for the demo/illustration ONLY. NEVER
    called by scoreboard(): a silent IID fallback is the integrity hole this
    module exists to close."""
    n_boot = n_boot or config.BOOTSTRAP_SAMPLES
    if len(pnls) < 2:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    means = np.empty(n_boot)
    for i in range(n_boot):
        means[i] = rng.choice(pnls, size=len(pnls), replace=True).mean()
    return (float(np.percentile(means, lo)), float(np.percentile(means, hi)))


def _validated_arrays(trades):
    pnls = []
    wins = []
    losses = []
    capital_at_risk = []
    economic_max_loss = []
    entry_dates = []
    saw_economic_max_loss = False
    missed_economic_max_loss = False

    for idx, trade in enumerate(trades):
        missing = {"pnl", "capital_at_risk", "entry_date", "symbol"} - trade.keys()
        if missing:
            raise ValueError(f"trade {idx} missing required field(s): {sorted(missing)}")

        if not isinstance(trade["symbol"], str) or not trade["symbol"].strip():
            raise ValueError(f"trade {idx} has empty symbol")
        try:
            entry_date = _as_date(trade["entry_date"])
        except (ValueError, TypeError):
            raise ValueError(
                f"trade {idx} has unparseable entry_date: {trade['entry_date']!r}")

        pnl = float(trade["pnl"])
        car = float(trade["capital_at_risk"])
        if not np.isfinite(pnl):
            raise ValueError(f"trade {idx} has non-finite pnl: {trade['pnl']!r}")
        if not np.isfinite(car) or car <= 0:
            raise ValueError(
                f"trade {idx} has invalid capital_at_risk: {trade['capital_at_risk']!r}"
            )
        inferred_win = pnl > 0
        if "is_win" in trade and bool(trade["is_win"]) != inferred_win:
            raise ValueError(
                f"trade {idx} has is_win inconsistent with net pnl: "
                f"{trade['is_win']!r} vs {trade['pnl']!r}"
            )
        if "economic_max_loss" in trade:
            saw_economic_max_loss = True
            eml = float(trade["economic_max_loss"])
            if not np.isfinite(eml) or eml <= 0:
                raise ValueError(
                    f"trade {idx} has invalid economic_max_loss: "
                    f"{trade['economic_max_loss']!r}"
                )
            if eml < car:
                raise ValueError(
                    f"trade {idx} has economic_max_loss below capital_at_risk: "
                    f"{trade['economic_max_loss']!r} < {trade['capital_at_risk']!r}"
                )
            economic_max_loss.append(eml)
        else:
            missed_economic_max_loss = True

        pnls.append(pnl)
        wins.append(inferred_win)
        losses.append(pnl < 0)
        capital_at_risk.append(car)
        entry_dates.append(entry_date)

    if saw_economic_max_loss and missed_economic_max_loss:
        raise ValueError("economic_max_loss must be supplied on every trade or none")

    return (
        np.array(pnls, dtype=float),
        np.array(wins, dtype=bool),
        np.array(losses, dtype=bool),
        np.array(capital_at_risk, dtype=float),
        np.array(economic_max_loss, dtype=float) if saw_economic_max_loss else None,
        entry_dates,
    )


def _max_drawdown(pnls):
    """Max drawdown ($) on the cumulative trade-by-trade equity curve."""
    if len(pnls) == 0:
        return 0.0
    equity = np.cumsum(pnls)
    running_max = np.maximum.accumulate(equity)
    return float((running_max - equity).max())


def scoreboard(trades, label="strategy"):
    pnls, wins, losses, cap, economic_max_loss, entry_dates = _validated_arrays(trades)
    n = len(trades)
    n_win, n_loss = int(wins.sum()), int(losses.sum())

    win_pnls, loss_pnls = pnls[wins], pnls[losses]
    rets = pnls / cap

    expectancy = float(pnls.mean()) if n else 0.0
    cohorts = _build_week_cohorts(entry_dates, pnls)
    n_cohorts = len(cohorts)
    ci_lo, ci_hi = _ci_from_cohorts(cohorts, n, config.BOOTSTRAP_SAMPLES, 5, 95, seed=42)

    mean_r = float(rets.mean()) if n else 0.0
    std_r = float(rets.std(ddof=1)) if n > 1 else 0.0
    downside = rets[rets < 0]
    dstd = float(downside.std(ddof=1)) if len(downside) > 1 else 0.0
    economic_return = (
        float(pnls.sum() / economic_max_loss.mean())
        if economic_max_loss is not None and economic_max_loss.mean()
        else float("nan")
    )
    # ---- verdict gates on LOSSES and on COHORTS, not trades -----------------
    if n_loss < config.MIN_LOSSES_FOR_VERDICT:
        verdict = (f"INSUFFICIENT SAMPLE ({n_loss} losses; need "
                   f">= {config.MIN_LOSSES_FOR_VERDICT}). Ratios below are NOT reliable.")
    elif n_cohorts < 3:
        verdict = (f"INSUFFICIENT SAMPLE ({n_cohorts} entry-week cohorts; need >= 3 "
                   "to form a dependence-aware CI). No verdict.")
    elif ci_lo > 0:
        verdict = "PASS -- expectancy positive after costs (CI above zero)"
    elif ci_hi < 0:
        verdict = "FAIL -- expectancy negative after costs (CI below zero)"
    else:
        verdict = "NO EDGE -- expectancy indistinguishable from zero after costs"

    return {
        "label": label,
        "n_trades": n, "n_wins": n_win, "n_losses": n_loss,
        "win_rate": (n_win / n) if n else 0.0,
        "expectancy_per_trade": expectancy,
        "expectancy_CI90": (ci_lo, ci_hi),
        "avg_win": float(win_pnls.mean()) if n_win else 0.0,
        "avg_loss": float(loss_pnls.mean()) if n_loss else 0.0,
        "worst_loss": float(loss_pnls.min()) if n_loss else 0.0,
        "total_pnl": float(pnls.sum()),
        "max_drawdown": _max_drawdown(pnls),
        "sharpe_per_trade": (mean_r / std_r) if std_r else float("nan"),
        "sortino_per_trade": (mean_r / dstd) if dstd else float("nan"),
        "capital_efficiency": float(pnls.sum() / cap.mean()) if cap.mean() else float("nan"),
        "return_on_economic_max_loss": economic_return,
        "verdict": verdict,
    }


def print_scoreboard(s):
    lo, hi = s["expectancy_CI90"]
    print("=" * 70)
    print(f"SCOREBOARD -- {s['label']}")
    print("=" * 70)
    print(f"  trades                {s['n_trades']}  "
          f"(wins {s['n_wins']} / losses {s['n_losses']})")
    print(f"  win rate              {s['win_rate']:.1%}   <- seductive, read LAST")
    print(f"  EXPECTANCY / trade    ${s['expectancy_per_trade']:.2f}  "
          f"(90% CI ${lo:.2f} .. ${hi:.2f})   <- the headline")
    print(f"  avg win / avg loss    ${s['avg_win']:.2f} / ${s['avg_loss']:.2f}")
    print(f"  worst single loss     ${s['worst_loss']:.2f}")
    print(f"  total P&L             ${s['total_pnl']:.2f}")
    print(f"  max drawdown          ${s['max_drawdown']:.2f}")
    print(f"  Sharpe (per-trade)    {s['sharpe_per_trade']:.2f}   (NOT annualized)")
    print(f"  Sortino (per-trade)   {s['sortino_per_trade']:.2f}   (NOT annualized)")
    print(f"  capital efficiency    {s['capital_efficiency']:.2%}  "
          f"(total P&L / avg capital at risk)")
    economic = s["return_on_economic_max_loss"]
    if np.isfinite(economic):
        print(f"  economic max-loss ret {economic:.2%}  "
              f"(total P&L / avg economic max loss)")
    else:
        print("  economic max-loss ret n/a    (economic_max_loss not supplied)")
    print("-" * 70)
    print(f"  VERDICT: {s['verdict']}")
    print("=" * 70)


def _demo():
    """Synthetic illustration: a high win rate that ISN'T edge.

    35 small wins, then a handful of large losses -- the classic short-vol
    shape. Shows how the win rate flatters while expectancy tells the truth,
    and how the verdict refuses to certify a thin loss sample.
    """
    rng = np.random.default_rng(7)
    base = date(2020, 1, 6).toordinal()  # Monday
    symbols = config.UNIVERSE
    trades = [{"pnl": float(rng.normal(45, 8)), "capital_at_risk": 350.0,
               "entry_date": date.fromordinal(base + i * 3).isoformat(),
               "symbol": symbols[i % len(symbols)]}
              for i in range(35)]
    trades += [{"pnl": float(rng.normal(-300, 40)), "capital_at_risk": 350.0,
                "entry_date": date.fromordinal(base + 120 + i * 3).isoformat(),
                "symbol": symbols[i % len(symbols)]}
               for i in range(6)]
    print_scoreboard(scoreboard(trades, label="DEMO put credit spread (synthetic)"))
    print("\nNote: ~85% win rate, but only 6 losses -- below the verdict floor,")
    print("so the harness refuses to certify it. The expectancy is already")
    print("negative; more losses would let the CI decide honestly.")


if __name__ == "__main__":
    _demo()
