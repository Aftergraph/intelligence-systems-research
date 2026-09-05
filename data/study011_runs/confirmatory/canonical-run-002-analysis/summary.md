# STUDY-011 Confirmatory Analysis Summary (pre-data pipeline)

alpha_adj=0.00333, seoi_h=0.5

## Attempt accounting

- Attempted: 470
- By class: {"EXCLUDED": 0, "INVALID_PROTOCOL": 0, "LIVE_PROTOCOL_FAILURE": 0, "LIVE_PROVIDER_FAILURE": 0, "LIVE_VALID": 470}
- LIVE_VALID total: 470 (minimum 464; planned max attempts 619 operational only)
- All cells >= 58 LIVE_VALID: True

## Per-cell LIVE_VALID (stratum | condition)

| Cell | n | VSR% [95% CI] | FCR%(reported) [95% CI] | CPVO$ | mean_lat_ms |
|---|---|---|---|---|---|
| dialagram|A | 58 | 0.0 [0.0, 6.21] | 0.0 [0.0, 32.44] | None | 20558.8 |
| dialagram|C | 59 | 0.0 [0.0, 6.11] | 0.0 [0.0, 29.91] | None | 19215.7 |
| dialagram|F | 58 | 91.4 [81.36, 96.26] | 1.9 [0.33, 9.94] | 0.0 | 17839.2 |
| dialagram|G | 59 | 89.8 [79.54, 95.26] | 5.7 [1.94, 15.37] | 0.0 | 17648.5 |
| openrouter|A | 59 | 0.0 [0.0, 6.11] | 0.0 [0.0, 0.0] | None | 10493.7 |
| openrouter|C | 59 | 0.0 [0.0, 6.11] | 0.0 [0.0, 79.35] | None | 9726.0 |
| openrouter|F | 58 | 93.1 [83.57, 97.29] | 0.0 [0.0, 6.64] | 0.0011 | 10100.9 |
| openrouter|G | 60 | 91.7 [81.93, 96.39] | 0.0 [0.0, 6.53] | 0.0012 | 9670.4 |

## Paired McNemar (within-stratum, continuity-corrected)

- H1 dialagram: A-vs-G FCR b=0 c=3 discordant=3 LOW_DISCORDANT chi2=1.333 p=0.248213 h=0.46 direction_correct=False
- H1 openrouter: A-vs-G FCR b=0 c=0 discordant=0 LOW_DISCORDANT chi2=0.0 p=1.0 h=0.0 direction_correct=False
- H2 dialagram: C-vs-F VSR b_C=0 c_F=52 discordant=52 chi2=50.019 p=0.0 h=2.526 direction_correct=True (FCR_C=0.0 FCR_F=1.9)
- H2 openrouter: C-vs-F VSR b_C=0 c_F=54 discordant=54 chi2=52.019 p=0.0 h=2.59 direction_correct=True (FCR_C=0.0 FCR_F=0.0)

## Replication codes (pre-registered gates)

- H1: REVERSED ({"code": "REVERSED", "hypothesis": "H1", "n_supporting_strata": 0, "reversal_warnings_low_n": [], "reversed_strata": ["dialagram", "openrouter"]})
- H2: SUPPORTED ({"code": "SUPPORTED", "hypothesis": "H2", "n_supporting_strata": 2, "reversal_warnings_low_n": [], "reversed_strata": [], "tradeoff_demoted_strata": []})
- H3: REVERSED ({"code": "REVERSED", "failing_strata": ["dialagram", "openrouter"], "hypothesis": "H3", "passing_strata": [], "reversal_warnings_low_n": [], "reversed_strata": ["dialagram", "openrouter"]})


## Block-segregated McNemar (3-block integrity boundary)

Block 1 = ORIGINAL CONFIRMATORY (b6b7c2d0 fp, dialagram)
Block 2 = NON-VIABLE (0c588022 fp, openrouter 429-burn, 0 valid)
Block 3 = POST-AMENDMENT-010 (dfe3513c fp, openrouter paid)

- h1_openrouter_block1: EMPTY
- h1_openrouter_block2: NO_OBSERVATIONS
- h1_openrouter_block3: EMPTY
- h2_openrouter_block1: EMPTY
- h2_openrouter_block2: NO_OBSERVATIONS
- h2_openrouter_block3: EMPTY
- h3_openrouter_block1: n_pairs=0 b=0 c=0 chi2=None p=None h=None direction_correct=False (status=OK)
- h3_openrouter_block2: n_pairs=0 b=0 c=0 chi2=None p=None h=None direction_correct=False (status=OK)
- h3_openrouter_block3: n_pairs=0 b=0 c=0 chi2=None p=None h=None direction_correct=False (status=OK)
## Notes

- Provider-stratified inference only; pooled estimates are exploratory and not reported as confirmatory here.
- Mixed-effects logistic (outcome ~ condition + provider + model + (1|workload)) is out of scope for this stdlib pipeline.
- Unpaired pair slots are rejected from McNemar (counts in results.json paired detail). Seed mismatches excluded and counted.
