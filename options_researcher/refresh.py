"""options_researcher/refresh.py -- one-command data + research refresh.

Steps run IN ORDER and fail LOUDLY (a dead fetch must never let stale data
masquerade as fresh): 1) chains: cache_runner both windows for the universe
(skip-if-cached), 2) closes: fetch_underlying_eod per symbol from the last
cached date, 3) features: features.build_all(), 4) studies: the three
study mains. Each step returns a small dict merged into the printed
what-changed summary.
"""
from __future__ import annotations


def run_refresh(steps=None) -> dict:
    """Execute (name, fn) steps in order; return {name: result}. Injectable
    for tests; default_steps() wires the real pipeline."""
    summary: dict = {}
    for name, fn in (steps if steps is not None else default_steps()):
        print(f"refresh: {name} ...", flush=True)
        summary[name] = fn()
        print(f"refresh: {name} -> {summary[name]}", flush=True)
    return summary


def default_steps():
    import config
    from data import cache_runner
    from data.underlying_closes import fetch_underlying_eod_yahoo
    from options_researcher import features
    from options_researcher.studies import (covered_call_income,
                                            earnings_behavior,
                                            iv_vs_realized)

    def chains():
        a = cache_runner.cache_in_sample()
        b = cache_runner.cache_oos_blind()
        return {"in_sample": a, "oos_blind": b}

    def closes():
        # Yahoo = level-exact primary (validated $0.0000 vs true closes,
        # facts.log UNDERLYING_CLOSES_YAHOO); parity builder remains a
        # cross-check tool, not a refresh step.
        return {symbol: fetch_underlying_eod_yahoo(symbol)
                for symbol in config.UNIVERSE}

    def feats():
        features.build_all()
        return {"symbols": len(config.UNIVERSE)}

    def studies():
        iv_vs_realized.main()
        earnings_behavior.main()
        covered_call_income.main()
        return {"studies": 3}

    return [("chains", chains), ("closes", closes),
            ("features", feats), ("studies", studies)]


if __name__ == "__main__":
    run_refresh()
