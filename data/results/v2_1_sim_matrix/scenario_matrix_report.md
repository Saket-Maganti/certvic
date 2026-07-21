# CertVIC V2.1 Simulation Stress Matrix

Status: SIMULATED_ONLY. These are not real data, not VLM outputs, not model evidence, and not paper claims.

- n_items per scenario: 200
- seed: 0
- scenarios: 11
- claim gates blocked all simulated artifacts: True

| scenario | orig acc | consistency | gap | parse fail | control flip | certified | claim blocked |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| perfect_consistent | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | False | True |
| high_accuracy_low_consistency | 0.950 | 0.725 | 0.225 | 0.000 | 0.160 | False | True |
| low_accuracy_high_consistency | 0.710 | 0.725 | -0.015 | 0.000 | 0.340 | False | True |
| spurious_control_flipper | 0.965 | 0.755 | 0.210 | 0.000 | 0.580 | False | True |
| parse_failure_heavy | 0.575 | 0.545 | 0.030 | 0.350 | 0.460 | False | True |
| family_specific_failure | 0.945 | 0.725 | 0.220 | 0.000 | 0.160 | False | True |
| domain_specific_failure | 0.920 | 0.750 | 0.170 | 0.000 | 0.300 | False | True |
| edit_type_specific_failure | 0.975 | 0.775 | 0.200 | 0.000 | 0.180 | False | True |
| small_gap_borderline | 0.685 | 0.730 | -0.045 | 0.000 | 0.320 | False | True |
| null_gap | 0.740 | 0.740 | 0.000 | 0.000 | 0.220 | False | True |
| noisy_realistic_mixed | 0.825 | 0.655 | 0.170 | 0.050 | 0.240 | False | True |

## Interpretation

The matrix exercises metric, certification, reporting, parser-sensitivity, and control-warning surfaces before real runs. It cannot validate ADE20K data quality, edit photorealism, human validity, or VLM behavior.
