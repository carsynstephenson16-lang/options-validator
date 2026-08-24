# Fill-adversity context study

Max as-of session: 2026-08-20.

## Scope and honesty statement

The frozen model charges the quoted half-spread, the configured 1% adverse haircut, and cent rounding. No execution records are present on disk, so the 1% haircut cannot be compared with realized fills. Comparing it with each contract's own quoted spread would be circular because the model already charges that spread. This study describes the model's decomposition and compares the haircut with an independent overnight mid movement; it calibrates nothing.

The overnight movement is absolute rather than directional: a bare chain has no declared position side. Up, down, and flat counts are printed beside each drift table. The drift sample contains contracts admitted at D that remained quoted and fresh at D+1. Contracts that vanish or fail the next-session admission screen drop out. Dropping never-quoted rows removes near-zero movement and can bias drift up, while requiring D+1 presence keeps liquid survivors and can bias it down; the net direction is not determined.

## Decision finding

At least one qualifying bucket is out of scale with the frozen haircut under the declared 2x order-of-magnitude comparison; this is input to a possible future owner amendment.

## Measurement 1 — model decomposition

### Tier 1

Max as-of session: 2026-08-20; n=35216.

| bucket | n | half-spread share p50 | haircut share p50 | cent-rounding share p50 |
|---|---:|---:|---:|---:|
| DTE 0-7; abs-delta 0-0.15 | 189 | INSUFFICIENT (n=189) |  |  |
| DTE 0-7; abs-delta 0.15-0.35 | 231 | 0.666667 | 0.24 | 0.0773684 |
| DTE 0-7; abs-delta 0.35-0.65 | 299 | 0.684211 | 0.266129 | 0.0318182 |
| DTE 0-7; abs-delta 0.65-1.0 | 1800 | 0.645459 | 0.346939 | 0.00502646 |
| DTE 121+; abs-delta 0-0.15 | 2878 | 0.714286 | 0.241463 | 0.0223747 |
| DTE 121+; abs-delta 0.15-0.35 | 4592 | 0.663717 | 0.326345 | 0.00826087 |
| DTE 121+; abs-delta 0.35-0.65 | 7481 | 0.592593 | 0.402899 | 0.00388889 |
| DTE 121+; abs-delta 0.65-1.0 | 6912 | 0.543867 | 0.453955 | 0.00183536 |
| DTE 121+; abs-delta OUT_OF_BAND | 174 | INSUFFICIENT (n=174) |  |  |
| DTE 31-60; abs-delta 0-0.15 | 413 | 0.692308 | 0.207778 | 0.072 |
| DTE 31-60; abs-delta 0.15-0.35 | 513 | 0.714286 | 0.253571 | 0.0217742 |
| DTE 31-60; abs-delta 0.35-0.65 | 643 | 0.643939 | 0.339744 | 0.0134409 |
| DTE 31-60; abs-delta 0.65-1.0 | 848 | 0.592161 | 0.404065 | 0.00296131 |
| DTE 61-120; abs-delta 0-0.15 | 572 | 0.714286 | 0.222361 | 0.0435417 |
| DTE 61-120; abs-delta 0.15-0.35 | 696 | 0.675676 | 0.297964 | 0.0175162 |
| DTE 61-120; abs-delta 0.35-0.65 | 1027 | 0.588235 | 0.400372 | 0.0100806 |
| DTE 61-120; abs-delta 0.65-1.0 | 1435 | 0.575758 | 0.421959 | 0.00230415 |
| DTE 8-30; abs-delta 0-0.15 | 588 | 0.666667 | 0.19 | 0.126 |
| DTE 8-30; abs-delta 0.15-0.35 | 904 | 0.714286 | 0.240765 | 0.0345994 |
| DTE 8-30; abs-delta 0.35-0.65 | 1247 | 0.675676 | 0.296667 | 0.0188312 |
| DTE 8-30; abs-delta 0.65-1.0 | 1762 | 0.659458 | 0.33491 | 0.00448857 |
| DTE 61-120; abs-delta OUT_OF_BAND | 12 | INSUFFICIENT (n=12) |  |  |


### Tier 2

Max as-of session: 2026-07-31; n=2236735.

| bucket | n | half-spread share p50 | haircut share p50 | cent-rounding share p50 |
|---|---:|---:|---:|---:|
| DTE 0-7; abs-delta 0-0.15 | 16147 | 0.5 | 0.166667 | 0.315 |
| DTE 0-7; abs-delta 0.15-0.35 | 17305 | 0.625 | 0.257353 | 0.0833333 |
| DTE 0-7; abs-delta 0.35-0.65 | 24631 | 0.666667 | 0.284091 | 0.0342105 |
| DTE 0-7; abs-delta 0.65-1.0 | 79101 | 0.669643 | 0.316774 | 0.00629371 |
| DTE 121+; abs-delta 0-0.15 | 189778 | 0.636364 | 0.303077 | 0.0351852 |
| DTE 121+; abs-delta 0.15-0.35 | 305605 | 0.555556 | 0.419271 | 0.0122222 |
| DTE 121+; abs-delta 0.35-0.65 | 402110 | 0.526316 | 0.464394 | 0.00670391 |
| DTE 121+; abs-delta 0.65-1.0 | 363462 | 0.537383 | 0.45955 | 0.00281385 |
| DTE 31-60; abs-delta 0-0.15 | 36178 | 0.6 | 0.236154 | 0.115714 |
| DTE 31-60; abs-delta 0.15-0.35 | 41956 | 0.652174 | 0.3035 | 0.0292683 |
| DTE 31-60; abs-delta 0.35-0.65 | 56106 | 0.625 | 0.358047 | 0.0147541 |
| DTE 31-60; abs-delta 0.65-1.0 | 68653 | 0.581395 | 0.412579 | 0.00425532 |
| DTE 61-120; abs-delta 0-0.15 | 53668 | 0.6 | 0.268333 | 0.0808013 |
| DTE 61-120; abs-delta 0.15-0.35 | 64873 | 0.625 | 0.338961 | 0.0220588 |
| DTE 61-120; abs-delta 0.35-0.65 | 89641 | 0.583333 | 0.4 | 0.0115789 |
| DTE 61-120; abs-delta 0.65-1.0 | 91744 | 0.541416 | 0.454316 | 0.00388889 |
| DTE 8-30; abs-delta 0-0.15 | 54267 | 0.6 | 0.208 | 0.165 |
| DTE 8-30; abs-delta 0.15-0.35 | 64749 | 0.666667 | 0.276087 | 0.0431818 |
| DTE 8-30; abs-delta 0.35-0.65 | 98708 | 0.666667 | 0.301695 | 0.0201493 |
| DTE 8-30; abs-delta 0.65-1.0 | 118053 | 0.631868 | 0.359873 | 0.00555556 |


## Measurement 2 — absolute overnight mid drift

### Tier 1

Max as-of session: 2026-08-20; n=10707.

| bucket | n | p50 | p75 | p90 | p95 | p99 |
|---|---:|---:|---:|---:|---:|---:|
| DTE 0-7; abs-delta 0-0.15 | 15 | INSUFFICIENT (n=15) |  |  |  |  |
| DTE 0-7; abs-delta 0.15-0.35 | 42 | INSUFFICIENT (n=42) |  |  |  |  |
| DTE 0-7; abs-delta 0.35-0.65 | 74 | INSUFFICIENT (n=74) |  |  |  |  |
| DTE 0-7; abs-delta 0.65-1.0 | 384 | 0.0314673 | 0.0916767 | 0.183807 | 0.330403 | 0.537364 |
| DTE 121+; abs-delta 0-0.15 | 785 | 0.03 | 0.0489796 | 0.0827463 | 0.124088 | 0.178406 |
| DTE 121+; abs-delta 0.15-0.35 | 1506 | 0.0205901 | 0.0392399 | 0.0798623 | 0.103405 | 0.137335 |
| DTE 121+; abs-delta 0.35-0.65 | 2570 | 0.0130224 | 0.0364146 | 0.0647101 | 0.0800138 | 0.114369 |
| DTE 121+; abs-delta 0.65-1.0 | 2443 | 0.00984043 | 0.0259875 | 0.0444711 | 0.0560417 | 0.104124 |
| DTE 121+; abs-delta OUT_OF_BAND | 56 | INSUFFICIENT (n=56) |  |  |  |  |
| DTE 31-60; abs-delta 0-0.15 | 100 | INSUFFICIENT (n=100) |  |  |  |  |
| DTE 31-60; abs-delta 0.15-0.35 | 156 | INSUFFICIENT (n=156) |  |  |  |  |
| DTE 31-60; abs-delta 0.35-0.65 | 210 | 0.0330108 | 0.0831235 | 0.159364 | 0.189519 | 0.264019 |
| DTE 31-60; abs-delta 0.65-1.0 | 230 | 0.0144329 | 0.040408 | 0.0850819 | 0.098564 | 0.134139 |
| DTE 61-120; abs-delta 0-0.15 | 66 | INSUFFICIENT (n=66) |  |  |  |  |
| DTE 61-120; abs-delta 0.15-0.35 | 126 | INSUFFICIENT (n=126) |  |  |  |  |
| DTE 61-120; abs-delta 0.35-0.65 | 194 | INSUFFICIENT (n=194) |  |  |  |  |
| DTE 61-120; abs-delta 0.65-1.0 | 214 | 0.0123618 | 0.0325932 | 0.0622214 | 0.0768604 | 0.0928814 |
| DTE 8-30; abs-delta 0-0.15 | 146 | INSUFFICIENT (n=146) |  |  |  |  |
| DTE 8-30; abs-delta 0.15-0.35 | 278 | 0.0923259 | 0.169164 | 0.331228 | 0.433297 | 0.575106 |
| DTE 8-30; abs-delta 0.35-0.65 | 448 | 0.0449654 | 0.160051 | 0.274188 | 0.329611 | 0.473058 |
| DTE 8-30; abs-delta 0.65-1.0 | 663 | 0.0196232 | 0.0603359 | 0.132247 | 0.182391 | 0.276865 |
| DTE 61-120; abs-delta OUT_OF_BAND | 1 | INSUFFICIENT (n=1) |  |  |  |  |

Haircut reference: 0.01.

Up/down/flat: {'up': 4926, 'down': 5637, 'flat': 144}. The frozen haircut is shown within the percentile scale above; this is a scale comparison, not fill evidence.

### Tier 2

Max as-of session: 2026-07-31; n=1713323.

| bucket | n | p50 | p75 | p90 | p95 | p99 |
|---|---:|---:|---:|---:|---:|---:|
| DTE 0-7; abs-delta 0-0.15 | 6940 | 0.465178 | 0.700875 | 1.88454 | 3.54771 | 11.1001 |
| DTE 0-7; abs-delta 0.15-0.35 | 10705 | 0.493421 | 0.765781 | 1.55097 | 2.60703 | 6.24846 |
| DTE 0-7; abs-delta 0.35-0.65 | 16533 | 0.407143 | 0.674779 | 1.03078 | 1.64498 | 3.41809 |
| DTE 0-7; abs-delta 0.65-1.0 | 49002 | 0.126163 | 0.289039 | 0.535932 | 0.721915 | 1.28993 |
| DTE 121+; abs-delta 0-0.15 | 129420 | 0.0609319 | 0.116564 | 0.191919 | 0.25397 | 0.474334 |
| DTE 121+; abs-delta 0.15-0.35 | 241803 | 0.0553846 | 0.106464 | 0.176892 | 0.234568 | 0.422096 |
| DTE 121+; abs-delta 0.35-0.65 | 322683 | 0.0546595 | 0.104095 | 0.170156 | 0.222934 | 0.388332 |
| DTE 121+; abs-delta 0.65-1.0 | 267386 | 0.0426038 | 0.081761 | 0.134266 | 0.175681 | 0.296669 |
| DTE 31-60; abs-delta 0-0.15 | 27622 | 0.15625 | 0.280702 | 0.448975 | 0.620668 | 1.26484 |
| DTE 31-60; abs-delta 0.15-0.35 | 34771 | 0.159091 | 0.284564 | 0.441748 | 0.582278 | 1.10224 |
| DTE 31-60; abs-delta 0.35-0.65 | 48809 | 0.134191 | 0.239437 | 0.36441 | 0.463174 | 0.787789 |
| DTE 31-60; abs-delta 0.65-1.0 | 52844 | 0.0729968 | 0.141751 | 0.232801 | 0.299334 | 0.484577 |
| DTE 61-120; abs-delta 0-0.15 | 41274 | 0.108 | 0.200412 | 0.32219 | 0.438082 | 0.858428 |
| DTE 61-120; abs-delta 0.15-0.35 | 54084 | 0.107007 | 0.197133 | 0.30597 | 0.39803 | 0.70301 |
| DTE 61-120; abs-delta 0.35-0.65 | 77841 | 0.0935065 | 0.173077 | 0.265432 | 0.334454 | 0.574578 |
| DTE 61-120; abs-delta 0.65-1.0 | 68008 | 0.0597351 | 0.116373 | 0.187401 | 0.239284 | 0.396014 |
| DTE 8-30; abs-delta 0-0.15 | 38164 | 0.252427 | 0.436242 | 0.698503 | 1.13679 | 2.92416 |
| DTE 8-30; abs-delta 0.15-0.35 | 50338 | 0.246377 | 0.445946 | 0.701595 | 1.01618 | 2.15627 |
| DTE 8-30; abs-delta 0.35-0.65 | 80974 | 0.204082 | 0.367816 | 0.568955 | 0.742259 | 1.38983 |
| DTE 8-30; abs-delta 0.65-1.0 | 94122 | 0.103964 | 0.212692 | 0.359003 | 0.469795 | 0.774002 |

Haircut reference: 0.01.

Up/down/flat: {'up': 795271, 'down': 906162, 'flat': 11890}. The frozen haircut is shown within the percentile scale above; this is a scale comparison, not fill evidence.

## Measurement 3 — two-leg net-credit drift (Strategy-A analogue)

### Tier 1

Max as-of session: 2026-08-20; n=3909. One-sided adverse fraction using `A_ENTRY_CREDIT_TOLERANCE`: 0.35558966487592736.

| bucket | n | p50 | p75 | p90 | p95 | p99 | adverse fraction |
|---|---:|---:|---:|---:|---:|---:|---:|
| DTE 0-7; abs-delta 0.35-0.65 | 29 | INSUFFICIENT (n=29) |  |  |  |  |  |
| DTE 0-7; abs-delta 0.65-1.0 | 76 | INSUFFICIENT (n=76) |  |  |  |  |  |
| DTE 121+; abs-delta 0-0.15 | 494 | 0.05 | 0.1 | 0.175 | 0.25875 | 0.35175 | 0.265182 |
| DTE 121+; abs-delta 0.15-0.35 | 794 | 0.1 | 0.25 | 0.5 | 0.675 | 1.17675 | 0.379093 |
| DTE 121+; abs-delta 0.35-0.65 | 1151 | 0.175 | 0.4 | 0.675 | 0.85 | 1.3375 | 0.406603 |
| DTE 121+; abs-delta 0.65-1.0 | 256 | 0.2 | 0.425 | 0.825 | 1.0125 | 1.49 | 0.433594 |
| DTE 31-60; abs-delta 0-0.15 | 46 | INSUFFICIENT (n=46) |  |  |  |  |  |
| DTE 31-60; abs-delta 0.15-0.35 | 74 | INSUFFICIENT (n=74) |  |  |  |  |  |
| DTE 31-60; abs-delta 0.35-0.65 | 107 | INSUFFICIENT (n=107) |  |  |  |  |  |
| DTE 31-60; abs-delta 0.65-1.0 | 57 | INSUFFICIENT (n=57) |  |  |  |  |  |
| DTE 61-120; abs-delta 0-0.15 | 30 | INSUFFICIENT (n=30) |  |  |  |  |  |
| DTE 61-120; abs-delta 0.15-0.35 | 54 | INSUFFICIENT (n=54) |  |  |  |  |  |
| DTE 61-120; abs-delta 0.35-0.65 | 97 | INSUFFICIENT (n=97) |  |  |  |  |  |
| DTE 61-120; abs-delta 0.65-1.0 | 40 | INSUFFICIENT (n=40) |  |  |  |  |  |
| DTE 8-30; abs-delta 0-0.15 | 46 | INSUFFICIENT (n=46) |  |  |  |  |  |
| DTE 8-30; abs-delta 0.15-0.35 | 110 | INSUFFICIENT (n=110) |  |  |  |  |  |
| DTE 8-30; abs-delta 0.35-0.65 | 216 | 0.075 | 0.175 | 0.275 | 0.35 | 0.51375 | 0.333333 |
| DTE 8-30; abs-delta 0.65-1.0 | 220 | 0.15 | 0.275 | 0.5025 | 0.65375 | 1.04525 | 0.363636 |
| DTE 0-7; abs-delta 0-0.15 | 3 | INSUFFICIENT (n=3) |  |  |  |  |  |
| DTE 0-7; abs-delta 0.15-0.35 | 9 | INSUFFICIENT (n=9) |  |  |  |  |  |

### Tier 2

Max as-of session: 2026-07-31; n=543449. One-sided adverse fraction using `A_ENTRY_CREDIT_TOLERANCE`: 0.4683493759304001.

| bucket | n | p50 | p75 | p90 | p95 | p99 | adverse fraction |
|---|---:|---:|---:|---:|---:|---:|---:|
| DTE 0-7; abs-delta 0-0.15 | 2657 | 0.06 | 0.125 | 0.27 | 0.492 | 1.1738 | 0.434701 |
| DTE 0-7; abs-delta 0.15-0.35 | 4354 | 0.165 | 0.325 | 0.625 | 0.93175 | 1.94 | 0.505053 |
| DTE 0-7; abs-delta 0.35-0.65 | 6388 | 0.23 | 0.475 | 0.85 | 1.125 | 1.87695 | 0.463838 |
| DTE 0-7; abs-delta 0.65-1.0 | 10625 | 0.2 | 0.425 | 0.775 | 1.05 | 1.875 | 0.429365 |
| DTE 121+; abs-delta 0-0.15 | 63438 | 0.05 | 0.1 | 0.195 | 0.275 | 0.6 | 0.427441 |
| DTE 121+; abs-delta 0.15-0.35 | 121932 | 0.1 | 0.225 | 0.45 | 0.65 | 1.25 | 0.469155 |
| DTE 121+; abs-delta 0.35-0.65 | 80194 | 0.15 | 0.325 | 0.625 | 0.9 | 1.75 | 0.490685 |
| DTE 31-60; abs-delta 0-0.15 | 13011 | 0.035 | 0.085 | 0.18 | 0.275 | 0.5595 | 0.442933 |
| DTE 31-60; abs-delta 0.15-0.35 | 16418 | 0.125 | 0.275 | 0.5 | 0.7 | 1.2916 | 0.477646 |
| DTE 31-60; abs-delta 0.35-0.65 | 20792 | 0.175 | 0.4 | 0.725 | 0.975 | 1.85 | 0.474558 |
| DTE 61-120; abs-delta 0-0.15 | 20062 | 0.03 | 0.075 | 0.155 | 0.225 | 0.475 | 0.425032 |
| DTE 61-120; abs-delta 0.15-0.35 | 26119 | 0.1 | 0.225 | 0.426 | 0.625 | 1.15 | 0.475516 |
| DTE 61-120; abs-delta 0.35-0.65 | 31877 | 0.15 | 0.35 | 0.625 | 0.875 | 1.525 | 0.487593 |
| DTE 8-30; abs-delta 0-0.15 | 16934 | 0.045 | 0.1 | 0.2 | 0.3 | 0.63335 | 0.479154 |
| DTE 8-30; abs-delta 0.15-0.35 | 22455 | 0.125 | 0.26 | 0.49 | 0.69 | 1.25 | 0.494545 |
| DTE 8-30; abs-delta 0.35-0.65 | 32347 | 0.17 | 0.375 | 0.675 | 0.925 | 1.775 | 0.47213 |
| DTE 8-30; abs-delta 0.65-1.0 | 25142 | 0.2 | 0.425 | 0.725 | 0.975 | 1.8 | 0.464522 |
| DTE 61-120; abs-delta 0.65-1.0 | 10250 | 0.2 | 0.4 | 0.7 | 0.95 | 1.65 | 0.486634 |
| DTE 31-60; abs-delta 0.65-1.0 | 12372 | 0.2 | 0.425 | 0.725 | 0.96125 | 1.70725 | 0.473004 |
| DTE 121+; abs-delta 0.65-1.0 | 6082 | 0.25 | 0.525 | 0.975 | 1.4 | 2.575 | 0.493588 |


The one-sided adverse fraction below uses the configured `A_ENTRY_CREDIT_TOLERANCE` direction and threshold. seq-21's tolerance governs future Strategy A put-credit-spread backtests only (`ledger/experiments.jsonl:22`); the chains measured here are the H7 story-name universe, which seq 21 excludes. This is an analogue computed on a stated spread construction, not a compliance measurement.

## Measurement 4 — touch depth (Tier 2 context)

### Tier 1

Max as-of session: 2026-08-20; n=0. bid_size p50/p90=unavailable/unavailable; ask_size p50/p90=unavailable/unavailable; fraction bid_size >= 1=unavailable; fraction ask_size >= 1=unavailable; size-weighted mean spread fraction=unavailable.

Tier 1 has no touch-size fields; not applicable.

### Tier 2

Max as-of session: 2026-07-31; n=2236735. bid_size p50/p90=46.0/348.0; ask_size p50/p90=45.0/322.0; fraction bid_size >= 1=1.0; fraction ask_size >= 1=1.0; size-weighted mean spread fraction=0.053427568653737746.

| bucket | n | spread fraction p50 |
|---|---:|---:|
| DTE 0-7; abs-delta 0-0.15 | 16147 | 0.0634921 |
| DTE 0-7; abs-delta 0.15-0.35 | 17305 | 0.0492611 |
| DTE 0-7; abs-delta 0.35-0.65 | 24631 | 0.0465116 |
| DTE 0-7; abs-delta 0.65-1.0 | 79101 | 0.0423892 |
| DTE 121+; abs-delta 0-0.15 | 189778 | 0.0421941 |
| DTE 121+; abs-delta 0.15-0.35 | 305605 | 0.0268666 |
| DTE 121+; abs-delta 0.35-0.65 | 402110 | 0.0227038 |
| DTE 121+; abs-delta 0.65-1.0 | 363462 | 0.0233918 |
| DTE 31-60; abs-delta 0-0.15 | 36178 | 0.0518135 |
| DTE 31-60; abs-delta 0.15-0.35 | 41956 | 0.0431655 |
| DTE 31-60; abs-delta 0.35-0.65 | 56106 | 0.0346657 |
| DTE 31-60; abs-delta 0.65-1.0 | 68653 | 0.0281974 |
| DTE 61-120; abs-delta 0-0.15 | 53668 | 0.0465116 |
| DTE 61-120; abs-delta 0.15-0.35 | 64873 | 0.0371747 |
| DTE 61-120; abs-delta 0.35-0.65 | 89641 | 0.0291971 |
| DTE 61-120; abs-delta 0.65-1.0 | 91744 | 0.0238372 |
| DTE 8-30; abs-delta 0-0.15 | 54267 | 0.0571429 |
| DTE 8-30; abs-delta 0.15-0.35 | 64749 | 0.0483092 |
| DTE 8-30; abs-delta 0.35-0.65 | 98708 | 0.0444444 |
| DTE 8-30; abs-delta 0.65-1.0 | 118053 | 0.0351129 |


Quoted size is not fill evidence; it bounds 1-lot plausibility only. Owner ruling 2026-08-24: Tier-2 chains_v2 read-only access is approved for this descriptive study; the namespace remains parked and excluded from verdict eligibility.

## Data quality and source lineage

Tier-2 staleness filtering keeps timestamps on the row's session date between 09:30 and 16:15 ET. Rows dropped at each stage and sessions losing more than half their admitted rows are listed in the receipt. The Tier-2 full-audit warning profile is consumed and warning counts are recorded per used session. Missing Tier-1 raw closes exclude the affected session from moneyness tables; no interpolation is performed.

## What this is not

This is not fill evidence, not a recommendation, not a re-scoring of any registered result, and not applicable to any registered result. It does not change the frozen fill model, a strategy, a score, a ledger, authority, the paper book, or an order path.

## Appendix

Symbol breakdowns are appendix-only and use the same floor and absolute
overnight-drift definition; headline tables remain pooled across symbols.

### Tier 1

Max as-of session: 2026-08-20; symbol breakdown is appendix-only.

| symbol / DTE band | n | p50 | p75 | p90 | p95 | p99 |
|---|---:|---:|---:|---:|---:|---:|
| AMD; DTE 0-7 | 103 | INSUFFICIENT (n=103) |  |  |  |  |
| AMD; DTE 121+ | 1233 | 0.00569777 | 0.01093 | 0.018263 | 0.0251734 | 0.0384396 |
| AMD; DTE 31-60 | 126 | INSUFFICIENT (n=126) |  |  |  |  |
| AMD; DTE 61-120 | 100 | INSUFFICIENT (n=100) |  |  |  |  |
| AMD; DTE 8-30 | 200 | 0.0122325 | 0.0550749 | 0.122313 | 0.192824 | 0.347701 |
| AMZN; DTE 0-7 | 71 | INSUFFICIENT (n=71) |  |  |  |  |
| AMZN; DTE 121+ | 709 | 0.0584718 | 0.0853659 | 0.119778 | 0.141961 | 0.179946 |
| AMZN; DTE 31-60 | 76 | INSUFFICIENT (n=76) |  |  |  |  |
| AMZN; DTE 61-120 | 62 | INSUFFICIENT (n=62) |  |  |  |  |
| AMZN; DTE 8-30 | 124 | INSUFFICIENT (n=124) |  |  |  |  |
| AVGO; DTE 0-7 | 37 | INSUFFICIENT (n=37) |  |  |  |  |
| AVGO; DTE 121+ | 742 | 0.00945215 | 0.0163132 | 0.0310431 | 0.0418118 | 0.0602934 |
| AVGO; DTE 31-60 | 55 | INSUFFICIENT (n=55) |  |  |  |  |
| AVGO; DTE 61-120 | 44 | INSUFFICIENT (n=44) |  |  |  |  |
| AVGO; DTE 8-30 | 120 | INSUFFICIENT (n=120) |  |  |  |  |
| CEG; DTE 0-7 | 1 | INSUFFICIENT (n=1) |  |  |  |  |
| CEG; DTE 121+ | 83 | INSUFFICIENT (n=83) |  |  |  |  |
| CEG; DTE 61-120 | 8 | INSUFFICIENT (n=8) |  |  |  |  |
| CEG; DTE 8-30 | 15 | INSUFFICIENT (n=15) |  |  |  |  |
| CRWV; DTE 0-7 | 40 | INSUFFICIENT (n=40) |  |  |  |  |
| CRWV; DTE 121+ | 586 | 0.0386167 | 0.0528927 | 0.0672456 | 0.0765073 | 0.0941361 |
| CRWV; DTE 31-60 | 74 | INSUFFICIENT (n=74) |  |  |  |  |
| CRWV; DTE 61-120 | 42 | INSUFFICIENT (n=42) |  |  |  |  |
| CRWV; DTE 8-30 | 161 | INSUFFICIENT (n=161) |  |  |  |  |
| ET; DTE 121+ | 11 | INSUFFICIENT (n=11) |  |  |  |  |
| ET; DTE 31-60 | 1 | INSUFFICIENT (n=1) |  |  |  |  |
| IREN; DTE 0-7 | 19 | INSUFFICIENT (n=19) |  |  |  |  |
| IREN; DTE 121+ | 178 | INSUFFICIENT (n=178) |  |  |  |  |
| IREN; DTE 31-60 | 35 | INSUFFICIENT (n=35) |  |  |  |  |
| IREN; DTE 61-120 | 43 | INSUFFICIENT (n=43) |  |  |  |  |
| IREN; DTE 8-30 | 123 | INSUFFICIENT (n=123) |  |  |  |  |
| MSFT; DTE 0-7 | 49 | INSUFFICIENT (n=49) |  |  |  |  |
| MSFT; DTE 121+ | 1007 | 0.00610128 | 0.0156913 | 0.0296495 | 0.0405271 | 0.0760962 |
| MSFT; DTE 31-60 | 91 | INSUFFICIENT (n=91) |  |  |  |  |
| MSFT; DTE 61-120 | 89 | INSUFFICIENT (n=89) |  |  |  |  |
| MSFT; DTE 8-30 | 153 | INSUFFICIENT (n=153) |  |  |  |  |
| NOW; DTE 0-7 | 32 | INSUFFICIENT (n=32) |  |  |  |  |
| NOW; DTE 121+ | 331 | 0.045 | 0.0598988 | 0.0775194 | 0.0894895 | 0.104299 |
| NOW; DTE 31-60 | 21 | INSUFFICIENT (n=21) |  |  |  |  |
| NOW; DTE 61-120 | 30 | INSUFFICIENT (n=30) |  |  |  |  |
| NOW; DTE 8-30 | 98 | INSUFFICIENT (n=98) |  |  |  |  |
| NVDA; DTE 0-7 | 72 | INSUFFICIENT (n=72) |  |  |  |  |
| NVDA; DTE 121+ | 1213 | 0.0223015 | 0.0311818 | 0.0484653 | 0.0678954 | 0.102419 |
| NVDA; DTE 31-60 | 121 | INSUFFICIENT (n=121) |  |  |  |  |
| NVDA; DTE 61-120 | 66 | INSUFFICIENT (n=66) |  |  |  |  |
| NVDA; DTE 8-30 | 242 | 0.0793672 | 0.118208 | 0.1405 | 0.149529 | 0.180487 |
| PLTR; DTE 0-7 | 62 | INSUFFICIENT (n=62) |  |  |  |  |
| PLTR; DTE 121+ | 763 | 0.00740741 | 0.0156139 | 0.0294812 | 0.0406978 | 0.0514214 |
| PLTR; DTE 31-60 | 77 | INSUFFICIENT (n=77) |  |  |  |  |
| PLTR; DTE 61-120 | 58 | INSUFFICIENT (n=58) |  |  |  |  |
| PLTR; DTE 8-30 | 178 | INSUFFICIENT (n=178) |  |  |  |  |
| SMCI; DTE 0-7 | 27 | INSUFFICIENT (n=27) |  |  |  |  |
| SMCI; DTE 121+ | 274 | 0.0100577 | 0.0195244 | 0.0326313 | 0.0467391 | 0.0627497 |
| SMCI; DTE 31-60 | 3 | INSUFFICIENT (n=3) |  |  |  |  |
| SMCI; DTE 61-120 | 44 | INSUFFICIENT (n=44) |  |  |  |  |
| SMCI; DTE 8-30 | 71 | INSUFFICIENT (n=71) |  |  |  |  |
| TEM; DTE 121+ | 33 | INSUFFICIENT (n=33) |  |  |  |  |
| TEM; DTE 31-60 | 3 | INSUFFICIENT (n=3) |  |  |  |  |
| TEM; DTE 61-120 | 1 | INSUFFICIENT (n=1) |  |  |  |  |
| TEM; DTE 8-30 | 6 | INSUFFICIENT (n=6) |  |  |  |  |
| USAR; DTE 121+ | 82 | INSUFFICIENT (n=82) |  |  |  |  |
| USAR; DTE 8-30 | 27 | INSUFFICIENT (n=27) |  |  |  |  |
| VST; DTE 0-7 | 2 | INSUFFICIENT (n=2) |  |  |  |  |
| VST; DTE 121+ | 115 | INSUFFICIENT (n=115) |  |  |  |  |
| VST; DTE 31-60 | 13 | INSUFFICIENT (n=13) |  |  |  |  |
| VST; DTE 61-120 | 14 | INSUFFICIENT (n=14) |  |  |  |  |
| VST; DTE 8-30 | 17 | INSUFFICIENT (n=17) |  |  |  |  |

### Tier 2

Max as-of session: 2026-07-31; symbol breakdown is appendix-only.

| symbol / DTE band | n | p50 | p75 | p90 | p95 | p99 |
|---|---:|---:|---:|---:|---:|---:|
| AMD; DTE 0-7 | 12681 | 0.242312 | 0.534483 | 0.857637 | 1.42233 | 5.51724 |
| AMD; DTE 121+ | 122045 | 0.0639513 | 0.123288 | 0.205503 | 0.281304 | 0.537568 |
| AMD; DTE 31-60 | 19129 | 0.130769 | 0.262112 | 0.431745 | 0.614703 | 1.32687 |
| AMD; DTE 61-120 | 26179 | 0.0996051 | 0.192223 | 0.305387 | 0.427711 | 0.839457 |
| AMD; DTE 8-30 | 39052 | 0.200659 | 0.390336 | 0.623869 | 0.913775 | 2.34188 |
| AMZN; DTE 0-7 | 8273 | 0.189189 | 0.453416 | 0.761217 | 1.02896 | 2.9527 |
| AMZN; DTE 121+ | 127291 | 0.0464576 | 0.0878574 | 0.147905 | 0.198483 | 0.376221 |
| AMZN; DTE 31-60 | 15506 | 0.107914 | 0.211397 | 0.344582 | 0.445577 | 0.826348 |
| AMZN; DTE 61-120 | 24759 | 0.0795713 | 0.149626 | 0.251748 | 0.331387 | 0.624765 |
| AMZN; DTE 8-30 | 23954 | 0.159407 | 0.315145 | 0.522516 | 0.703012 | 1.48289 |
| AVGO; DTE 0-7 | 6940 | 0.211857 | 0.441991 | 0.744578 | 1.02987 | 3.03589 |
| AVGO; DTE 121+ | 81700 | 0.0542795 | 0.104089 | 0.167306 | 0.221521 | 0.375682 |
| AVGO; DTE 31-60 | 12055 | 0.111322 | 0.211573 | 0.342762 | 0.444931 | 0.788825 |
| AVGO; DTE 61-120 | 19561 | 0.0867925 | 0.165127 | 0.263403 | 0.347826 | 0.598529 |
| AVGO; DTE 8-30 | 23431 | 0.166667 | 0.318961 | 0.51938 | 0.687252 | 1.46687 |
| BE; DTE 0-7 | 2488 | 0.150704 | 0.294261 | 0.589296 | 0.977249 | 2.2677 |
| BE; DTE 121+ | 18355 | 0.0752972 | 0.139922 | 0.221707 | 0.28291 | 0.475116 |
| BE; DTE 31-60 | 5497 | 0.124204 | 0.226012 | 0.358652 | 0.458274 | 0.777971 |
| BE; DTE 61-120 | 9308 | 0.097561 | 0.175059 | 0.271276 | 0.350327 | 0.666064 |
| BE; DTE 8-30 | 6034 | 0.150338 | 0.279052 | 0.448838 | 0.639127 | 1.24898 |
| CEG; DTE 0-7 | 280 | 0.16345 | 0.304123 | 0.459096 | 0.594571 | 1.55834 |
| CEG; DTE 121+ | 3746 | 0.0661628 | 0.122738 | 0.188475 | 0.241489 | 0.395283 |
| CEG; DTE 31-60 | 1798 | 0.130638 | 0.239469 | 0.351114 | 0.4451 | 0.795303 |
| CEG; DTE 61-120 | 2797 | 0.110664 | 0.200495 | 0.310077 | 0.382745 | 0.611989 |
| CEG; DTE 8-30 | 1042 | 0.169338 | 0.32157 | 0.49964 | 0.648355 | 1.26026 |
| CRWV; DTE 0-7 | 4831 | 0.26087 | 0.526145 | 0.843103 | 1.25815 | 2.7367 |
| CRWV; DTE 121+ | 33200 | 0.066565 | 0.119718 | 0.183742 | 0.232942 | 0.376912 |
| CRWV; DTE 31-60 | 7932 | 0.1337 | 0.236151 | 0.35443 | 0.463019 | 0.796711 |
| CRWV; DTE 61-120 | 12122 | 0.103926 | 0.182482 | 0.27145 | 0.348743 | 0.620162 |
| CRWV; DTE 8-30 | 12807 | 0.199413 | 0.363285 | 0.559405 | 0.735456 | 1.44053 |
| ET; DTE 0-7 | 139 | INSUFFICIENT (n=139) |  |  |  |  |
| ET; DTE 121+ | 1964 | 0.0302269 | 0.0581866 | 0.0913079 | 0.117117 | 0.184816 |
| ET; DTE 31-60 | 246 | 0.0609153 | 0.115803 | 0.205825 | 0.266089 | 0.357143 |
| ET; DTE 61-120 | 342 | 0.0539589 | 0.110606 | 0.162581 | 0.203644 | 0.303781 |
| ET; DTE 8-30 | 244 | 0.0817463 | 0.144651 | 0.231173 | 0.318596 | 0.525969 |
| HIMS; DTE 0-7 | 1953 | 0.233184 | 0.458824 | 0.737645 | 1.17662 | 3.25211 |
| HIMS; DTE 121+ | 11230 | 0.0522986 | 0.0983934 | 0.157407 | 0.208007 | 0.318779 |
| HIMS; DTE 31-60 | 5125 | 0.113946 | 0.198319 | 0.312457 | 0.421076 | 0.663828 |
| HIMS; DTE 61-120 | 6763 | 0.0836653 | 0.148734 | 0.228313 | 0.301468 | 0.481732 |
| HIMS; DTE 8-30 | 7691 | 0.172107 | 0.309222 | 0.496552 | 0.690543 | 1.27138 |
| IREN; DTE 0-7 | 3046 | 0.272727 | 0.57024 | 0.869826 | 1.30862 | 2.56134 |
| IREN; DTE 121+ | 15678 | 0.0786876 | 0.141404 | 0.20738 | 0.260443 | 0.376452 |
| IREN; DTE 31-60 | 5521 | 0.135338 | 0.248497 | 0.354749 | 0.463221 | 0.698722 |
| IREN; DTE 61-120 | 7799 | 0.109827 | 0.193768 | 0.279466 | 0.363731 | 0.530376 |
| IREN; DTE 8-30 | 8233 | 0.214724 | 0.393023 | 0.589436 | 0.752435 | 1.26701 |
| MSFT; DTE 0-7 | 8824 | 0.264449 | 0.550838 | 0.871371 | 1.39892 | 4.39754 |
| MSFT; DTE 121+ | 118991 | 0.0522667 | 0.0986661 | 0.160123 | 0.207763 | 0.398841 |
| MSFT; DTE 31-60 | 18505 | 0.119086 | 0.225118 | 0.353479 | 0.464166 | 0.896517 |
| MSFT; DTE 61-120 | 27342 | 0.0863636 | 0.162235 | 0.249502 | 0.317933 | 0.681006 |
| MSFT; DTE 8-30 | 27829 | 0.177799 | 0.339827 | 0.546096 | 0.728778 | 1.59455 |
| NOW; DTE 0-7 | 1542 | 0.314206 | 0.55 | 0.900616 | 1.5903 | 3.31008 |
| NOW; DTE 121+ | 16871 | 0.0760234 | 0.142857 | 0.222474 | 0.284524 | 0.524343 |
| NOW; DTE 31-60 | 4267 | 0.141176 | 0.252841 | 0.378294 | 0.493421 | 0.888306 |
| NOW; DTE 61-120 | 6910 | 0.106321 | 0.195639 | 0.293526 | 0.370231 | 0.666225 |
| NOW; DTE 8-30 | 5265 | 0.21 | 0.379433 | 0.592851 | 0.846814 | 1.66667 |
| NVDA; DTE 0-7 | 14096 | 0.18459 | 0.484998 | 0.794998 | 1.12063 | 3.3185 |
| NVDA; DTE 121+ | 224878 | 0.0440415 | 0.084134 | 0.137871 | 0.180233 | 0.290168 |
| NVDA; DTE 31-60 | 32432 | 0.111319 | 0.219738 | 0.358962 | 0.460993 | 0.789211 |
| NVDA; DTE 61-120 | 43135 | 0.0777027 | 0.151025 | 0.254753 | 0.329747 | 0.563911 |
| NVDA; DTE 8-30 | 44957 | 0.160767 | 0.328767 | 0.538485 | 0.701256 | 1.49054 |
| PLTR; DTE 0-7 | 10625 | 0.226324 | 0.524664 | 0.818774 | 1.25391 | 3.90904 |
| PLTR; DTE 121+ | 125436 | 0.0479188 | 0.0935156 | 0.157407 | 0.206269 | 0.318875 |
| PLTR; DTE 31-60 | 18124 | 0.105774 | 0.214778 | 0.364225 | 0.47804 | 0.842361 |
| PLTR; DTE 61-120 | 24981 | 0.0787825 | 0.15503 | 0.257545 | 0.332209 | 0.526883 |
| PLTR; DTE 8-30 | 36737 | 0.168216 | 0.336957 | 0.552853 | 0.75239 | 1.6884 |
| SMCI; DTE 0-7 | 4152 | 0.207101 | 0.463311 | 0.746137 | 1.21334 | 2.96868 |
| SMCI; DTE 121+ | 31993 | 0.0550239 | 0.110874 | 0.192857 | 0.26846 | 0.5265 |
| SMCI; DTE 31-60 | 7895 | 0.104895 | 0.207317 | 0.353446 | 0.487628 | 0.9635 |
| SMCI; DTE 61-120 | 13215 | 0.0829016 | 0.165264 | 0.281531 | 0.388801 | 0.683298 |
| SMCI; DTE 8-30 | 13064 | 0.160494 | 0.306896 | 0.521739 | 0.749038 | 1.71517 |
| TEM; DTE 0-7 | 829 | 0.231076 | 0.435897 | 0.716884 | 1.04822 | 2.49302 |
| TEM; DTE 121+ | 5006 | 0.0573854 | 0.1 | 0.168421 | 0.226396 | 0.378378 |
| TEM; DTE 31-60 | 2228 | 0.121744 | 0.21992 | 0.329424 | 0.422627 | 0.825171 |
| TEM; DTE 61-120 | 3408 | 0.0917814 | 0.162019 | 0.245334 | 0.323832 | 0.671095 |
| TEM; DTE 8-30 | 2694 | 0.199798 | 0.326923 | 0.488734 | 0.677651 | 1.52218 |
| UBER; DTE 0-7 | 1704 | 0.261569 | 0.490334 | 0.780596 | 1.25492 | 2.72922 |
| UBER; DTE 121+ | 14903 | 0.0489396 | 0.0869565 | 0.142202 | 0.184073 | 0.304334 |
| UBER; DTE 31-60 | 3990 | 0.111315 | 0.198876 | 0.318527 | 0.40949 | 0.776209 |
| UBER; DTE 61-120 | 7021 | 0.0810811 | 0.14881 | 0.233227 | 0.298701 | 0.500771 |
| UBER; DTE 8-30 | 7099 | 0.17301 | 0.314784 | 0.496672 | 0.64415 | 1.21546 |
| USAR; DTE 0-7 | 303 | 0.206349 | 0.41304 | 0.755897 | 1.08222 | 2.06593 |
| USAR; DTE 121+ | 2474 | 0.0838781 | 0.15 | 0.22934 | 0.299005 | 0.443213 |
| USAR; DTE 31-60 | 1097 | 0.143713 | 0.253731 | 0.366024 | 0.505506 | 0.820378 |
| USAR; DTE 61-120 | 1080 | 0.112075 | 0.190651 | 0.309106 | 0.393948 | 0.695758 |
| USAR; DTE 8-30 | 1057 | 0.188889 | 0.333333 | 0.536842 | 0.747183 | 1.53215 |
| VST; DTE 0-7 | 474 | 0.166058 | 0.321582 | 0.59422 | 0.947869 | 1.66945 |
| VST; DTE 121+ | 5531 | 0.0710498 | 0.117901 | 0.172012 | 0.213242 | 0.346797 |
| VST; DTE 31-60 | 2699 | 0.139932 | 0.229316 | 0.330434 | 0.41743 | 0.73163 |
| VST; DTE 61-120 | 4485 | 0.110497 | 0.185504 | 0.271919 | 0.325907 | 0.540242 |
| VST; DTE 8-30 | 2408 | 0.165975 | 0.297015 | 0.455083 | 0.581455 | 1.0554 |


Exceedance fractions are appendix-only and must not be read as headline findings. They are saturated in the available dollar-priced option data: a one-cent dollar threshold is often one tick, so its fraction is a tick-size artifact. Tier 1 `|Δmid|/mid > haircut`: 65.8%. Tier 2 `|Δmid|/mid > haircut`: 91.6%. Tier 1 `|Δmid| > $0.01`: 98.1%; Tier 2 `|Δmid| > $0.01`: 98.9%.

Receipt hash: 5c52893cae57260820e60a5a2e74e7358aa9f3b0169ed6bcd528dce18d09b971.
