# Descriptive tradability profile. Reads ALL cached years incl. post-2022 (disclosed research look; see facts.log H3-era pivot note). No P&L is computed.

import glob
import os
import sys
from datetime import date as _date
from datetime import datetime

import pandas as pd

from options_researcher.chains import puts_in_window


def profile_symbol(symbol, cache_dir):
    """Profile tradability for a single symbol."""
    pattern = os.path.join(cache_dir, f"{symbol}_*.parquet")
    files = sorted(glob.glob(pattern))

    if not files:
        print(f"{symbol}: NO CACHED DATA\n")
        return

    # Parse dates from filenames
    file_dates = []
    for f in files:
        basename = os.path.basename(f)
        date_str = basename.split("_")[1].replace(".parquet", "")
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            file_dates.append((date_obj, f))
        except ValueError:
            pass

    if not file_dates:
        print(f"{symbol}: NO VALID DATES\n")
        return

    file_dates.sort()

    # Sample every 5th trading day
    sampled_files = [f for i, (_, f) in enumerate(file_dates) if i % 5 == 0]

    # Aggregate by calendar year
    year_stats = {}

    for file_path in sampled_files:
        basename = os.path.basename(file_path)
        date_str = basename.split("_")[1].replace(".parquet", "")
        file_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        year = file_date.year

        # Read parquet
        try:
            df = pd.read_parquet(file_path)
        except Exception as e:
            print(f"WARN unreadable cache file skipped: {file_path}: {e}",
                  file=sys.stderr)
            continue

        # Filter to PUTs with valid quotes inside the 25-60 DTE window
        win = puts_in_window(df, _date.fromisoformat(date_str), 25, 60)

        if win.empty:
            continue

        # Get expiration nearest to 37 DTE (intentionally nearest-37-DTE,
        # NOT nearest-monthly -- this profiler is the weekly-fragmentation
        # detector)
        win = win.copy()
        win['dte_diff'] = abs(win['dte'] - 37)
        nearest_exp = win.loc[win['dte_diff'].idxmin(), 'exp_date']

        # Filter to that expiration
        df_exp = win[win['exp_date'] == nearest_exp].copy()

        if df_exp.empty:
            continue

        # Find ATM row (|delta| closest to 0.50)
        df_exp['abs_delta_diff'] = abs(abs(df_exp['delta']) - 0.50)
        atm_idx = df_exp['abs_delta_diff'].idxmin()
        atm_row = df_exp.loc[atm_idx]

        # Compute atm_spread_pct
        mid = (atm_row['bid'] + atm_row['ask']) / 2
        if mid <= 0:
            continue
        atm_spread_pct = (atm_row['ask'] - atm_row['bid']) / mid * 100

        atm_oi = atm_row['open_interest']
        atm_iv = atm_row['iv']
        atm_strike = atm_row['strike']

        # Grid step: median difference between consecutive unique strikes within 10% of atm_strike
        lower_bound = atm_strike * 0.90
        upper_bound = atm_strike * 1.10
        nearby_strikes = sorted(df_exp[(df_exp['strike'] >= lower_bound) & (df_exp['strike'] <= upper_bound)]['strike'].unique())

        if len(nearby_strikes) > 1:
            diffs = [nearby_strikes[i+1] - nearby_strikes[i] for i in range(len(nearby_strikes) - 1)]
            grid_step = pd.Series(diffs).median()
        else:
            grid_step = 0

        # Count liquid strikes
        df_exp_mid = df_exp.copy()
        df_exp_mid['mid'] = (df_exp_mid['bid'] + df_exp_mid['ask']) / 2
        df_exp_mid = df_exp_mid[df_exp_mid['mid'] > 0]
        df_exp_mid['spread_pct'] = (df_exp_mid['ask'] - df_exp_mid['bid']) / df_exp_mid['mid']
        n_liquid = len(df_exp_mid[(df_exp_mid['open_interest'] >= 100) & (df_exp_mid['spread_pct'] <= 0.10)])

        # Record stats
        if year not in year_stats:
            year_stats[year] = {
                'count': 0,
                'spreads': [],
                'ois': [],
                'ivs': [],
                'grid_steps': [],
                'liquidities': []
            }

        year_stats[year]['count'] += 1
        year_stats[year]['spreads'].append(atm_spread_pct)
        year_stats[year]['ois'].append(atm_oi)
        year_stats[year]['ivs'].append(atm_iv)
        year_stats[year]['grid_steps'].append(grid_step)
        year_stats[year]['liquidities'].append(n_liquid)

    # Print table
    print(f"\n{symbol}")
    print("-" * 100)
    print(f"{'Year':<6} {'Sampled Days':<15} {'Median Spread %':<18} {'Median OI':<15} {'Median IV':<15} {'Median Grid':<15} {'Median Liquid':<15}")
    print("-" * 100)

    for year in sorted(year_stats.keys()):
        stats = year_stats[year]
        if stats['count'] == 0:
            continue

        median_spread = pd.Series(stats['spreads']).median()
        median_oi = pd.Series(stats['ois']).median()
        median_iv = pd.Series(stats['ivs']).median()
        median_grid = pd.Series(stats['grid_steps']).median()
        median_liquid = pd.Series(stats['liquidities']).median()

        print(f"{year:<6} {stats['count']:<15} {median_spread:<18.2f} {median_oi:<15.0f} {median_iv:<15.4f} {median_grid:<15.2f} {median_liquid:<15.1f}")

    # Summary
    print("\nSUMMARY:")

    # First year with spread <= 10% AND oi >= 100
    first_year_good = None
    for year in sorted(year_stats.keys()):
        stats = year_stats[year]
        median_spread = pd.Series(stats['spreads']).median()
        median_oi = pd.Series(stats['ois']).median()
        if median_spread <= 10.0 and median_oi >= 100:
            first_year_good = year
            break

    if first_year_good:
        print(f"  First year with spread <= 10% AND OI >= 100: {first_year_good}")
    else:
        print(f"  First year with spread <= 10% AND OI >= 100: NONE")

    # Most recent grid step
    if year_stats:
        most_recent_year = max(year_stats.keys())
        median_grid_recent = pd.Series(year_stats[most_recent_year]['grid_steps']).median()
        print(f"  Most recent year ({most_recent_year}) median grid step: {median_grid_recent:.2f}")

    # Total sampled days
    total_days = sum(stats['count'] for stats in year_stats.values())
    print(f"  Total sampled days with usable expiration: {total_days}")


def main():
    repo_root = "/Users/carsynstephenson/Downloads/options-validator"
    cache_dir = os.path.join(repo_root, ".cache", "chains")

    if not os.path.isdir(cache_dir):
        print(f"ERROR: cache dir not found: {cache_dir}")
        sys.exit(1)

    for symbol in ["VST", "CEG", "MSFT", "AMZN"]:
        profile_symbol(symbol, cache_dir)


if __name__ == "__main__":
    main()
