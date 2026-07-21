# CertVIC Kaggle Runtime Estimates

These are planning ranges, not observed runtimes. Dual-GPU notebook-hours are wall time; individual T4 GPU-hours are approximately twice dual-T4 wall time. CPU packaging/import is 0.1-1.0 hours per return. Human review is external and must be estimated only after real generated-item counts and rater calibration. Recalibrate only from non-evidence 00C2 runtime manifests.

- `00A_certvic_code_and_environment_smoke.ipynb`: 10-20 min; 0.2-0.4 h; N/A.
- `00B_certvic_model_snapshot_smoke.ipynb`: 15-30 min/provider; 0 GPU-h; 2-8 GB RAM.
- `00C1_certvic_mock_adapter_smoke.ipynb`: 2-5 min; 0.05 h; N/A.
- `00C2_certvic_real_model_two_item_smoke.ipynb`: 15-45 min/provider; 0.25-0.75 h/provider; 12-15 GB.
- `01_specificity_confirmatory_generation_T4x2.ipynb`: 2-5 h; 4-10 T4-h; 8-14 GB/GPU.
- `02_qwen_specificity_confirmatory_T4x2.ipynb`: 2-5 h; 4-10 T4-h; 12-15 GB/GPU.
- `03_internvl_specificity_confirmatory_T4x2.ipynb`: 3-7 h; 6-14 T4-h; 14-16 GB/GPU.
- `04_llava_specificity_confirmatory_T4x2.ipynb`: 2-5 h; 4-10 T4-h; 12-15 GB/GPU.
- `10_main_study_generation_T4x2.ipynb`: 4-10 h (8-18 h reserve); 8-20 T4-h; 10-15 GB/GPU.
- `11_qwen_main_study_T4x2.ipynb`: 5-10 h; 10-20 T4-h; 12-15 GB/GPU.
- `12_internvl_main_study_T4x2.ipynb`: 8-16 h; 16-32 T4-h; 14-16 GB/GPU.
- `13_llava_main_study_T4x2.ipynb`: 5-10 h; 10-20 T4-h; 12-15 GB/GPU.
- `20_second_domain_generation_T4x2.ipynb`: 2-5 h; 4-10 T4-h; 10-15 GB/GPU.
- `21_second_domain_qwen_T4x2.ipynb`: 1-2 h; 2-4 T4-h; 12-15 GB/GPU.
- `22_second_domain_internvl_T4x2.ipynb`: 1.5-3 h; 3-6 T4-h; 14-16 GB/GPU.
- `23_second_domain_llava_T4x2.ipynb`: 1-2 h; 2-4 T4-h; 12-15 GB/GPU.
