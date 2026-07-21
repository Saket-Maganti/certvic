# CertVIC CPU Ready for GPU Handoff

All locally available CPU nodes are complete or precisely blocked by external bytes, GPU returns, genuine human review, or an upstream gate.

## Resume

```bash
python3 scripts/run_all_cpu_workflows.py --resume
```

The first authorized Kaggle wave is defined in `CERTVIC_FIRST_GPU_WAVE_HANDOFF.md`. 00C2 is not authorized by this Phase B handoff.

## Current external provisioning gate

Provision the Linux CPython 3.10 wheelhouse and all three immutable snapshot ZIPs, then run 00A and the three isolated 00B validations. Missing external bytes are not local CPU failures.

## Evidence boundary

- Frozen V1: Qwen 12/94, InternVL 1/94, LLaVA 3/94.
- Threshold: observed spurious flip rate <= 0.10; Qwen fails V1.
- V2-30 remains retrospective; confirmatory remains prospective and zero-overlap with V1.
- Main and COCO remain blocked; `paper_evidence=false`.
- Genuine `human_reviewed=true` count remains zero for the prospective workflow.

PHASE_B_ALL_AVAILABLE_CPU_RUNS_COMPLETE  
PRE_GPU_CPU_CLOSURE_COMPLETE  
FIRST_KAGGLE_WAVE_READY
