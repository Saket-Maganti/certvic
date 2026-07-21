# V8 Mechanism Probe Report

`status=complete` `evidence_status=DIAGNOSTIC_NON_EVIDENCE` `paper_evidence=false`

Mechanism probes are diagnostic only. The blocked two-image `original_vs_edited` family is excluded.

| provider | family | rows | raw parse | decision parse | decision accuracy | target mention | false target mention |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `qwen2_5_vl_7b` | context_suppression | 91 | 1.0 | 1.0 | 0.2637 | None | None |
| `qwen2_5_vl_7b` | object_list | 91 | 1.0 | 0.0 | None | 0.4176 | 0.4176 |
| `qwen2_5_vl_7b` | region_focused | 91 | 1.0 | 1.0 | 0.2967 | None | None |
| `qwen2_5_vl_7b` | two_step | 91 | 1.0 | 0.022 | 0.0 | None | None |
| `internvl_8b` | context_suppression | 91 | 1.0 | 1.0 | 0.2418 | None | None |
| `internvl_8b` | object_list | 91 | 1.0 | 0.0 | None | 0.6813 | 0.6813 |
| `internvl_8b` | region_focused | 91 | 1.0 | 1.0 | 0.3846 | None | None |
| `internvl_8b` | two_step | 91 | 1.0 | 0.011 | 0.0 | None | None |
| `llava_onevision_7b` | context_suppression | 91 | 1.0 | 1.0 | 0.1429 | None | None |
| `llava_onevision_7b` | object_list | 91 | 1.0 | 0.0 | None | 0.5714 | 0.5714 |
| `llava_onevision_7b` | region_focused | 91 | 1.0 | 1.0 | 0.1648 | None | None |
| `llava_onevision_7b` | two_step | 91 | 1.0 | 0.033 | 0.3333 | None | None |

## Integrity

- `qwen2_5_vl_7b`: rows=364 expected=364 provider_ok=True duplicates=0
- `internvl_8b`: rows=364 expected=364 provider_ok=True duplicates=0
- `llava_onevision_7b`: rows=364 expected=364 provider_ok=True duplicates=0

## Limits

- Diagnostic-only, not paper evidence.
- `original_vs_edited` remains SPEC_BLOCKED until the two-image interface exists.
