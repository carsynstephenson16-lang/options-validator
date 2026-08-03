# REGIME-AMI-v1 redundancy-audit receipt

- hypothesis_id: `REGIME-AMI-v1`
- registration: `docs/superpowers/2026-08-03-regime-ami-redundancy-registration.md`
- ledger record present: True
- code SHA: `8a7caada7ce8073ce1adfe390126231b74f64b01`
- timestamp (America/New_York): 2026-08-03T13:52:44.926351-04:00

## Frozen parameters

```json
{
  "window": 63,
  "step": 5,
  "n_clusters": 3,
  "refit_every": 20,
  "min_fit_windows": 24,
  "n_init": 5,
  "seed": 7,
  "symbols": [
    "VST",
    "CEG",
    "MSFT",
    "AMZN"
  ],
  "data_start": "2018-01-01",
  "median_ami_threshold": 0.5,
  "min_included_steps": 100
}
```

## Per-symbol results

| symbol | status | n_labeled | n_included | eligible | as_of | ami | degenerate | note |
|---|---|---|---|---|---|---|---|---|
| VST | OK | 395 | 391 | True | 2026-07-31 | 0.0290 | False |  |
| CEG | OK | 191 | 187 | True | 2026-07-31 | 0.1120 | False |  |
| MSFT | OK | 395 | 391 | True | 2026-07-31 | 0.0300 | False |  |
| AMZN | OK | 395 | 391 | True | 2026-07-31 | 0.0194 | False |  |

- eligible symbols: ['VST', 'CEG', 'MSFT', 'AMZN']
- median AMI: 0.029489362497200425
- **decision: RETAINS_DISTINCT_INFORMATION**

> Descriptive audit of a display-only lane; not a trade verdict. A RETAINS_DISTINCT_INFORMATION result is 'not yet rejected on redundancy', nothing more.

