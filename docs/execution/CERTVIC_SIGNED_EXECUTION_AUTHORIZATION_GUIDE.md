
# CertVIC Signed Execution Authorization Guide

Study YAML keeps `execution_allowed=false`. Authority comes only from
`certvic.cvpr.execution_permission.v1`: an expiring, one-run SHA-256 content lock over the strict smoke
gate, canonical final tasks, final review state, task freeze, environment lock, model registry, study
config, and code hash. The notebooks and `after_runs` verify the same permission. Any changed byte,
wrong study, expired artifact, malformed signature, or synthetic permission in a scientific run is
terminal.

```bash
python3 -m certvic.cvpr.execution_gate authorize --study specificity_confirmatory_cvpr   --smoke-gate <GATE.json> --final-task-manifest <TASKS.jsonl>   --final-review-ledger <FINAL_REVIEW.json> --freeze-manifest <FREEZE.json>   --code-hash <SHA256> --environment-lock <LOCK> --model-registry <REGISTRY>   --study-config configs/studies/specificity_confirmatory_cvpr.yaml --out <PERMISSION.json>
python3 -m certvic.cvpr.execution_gate verify --permission <PERMISSION.json>   --study specificity_confirmatory_cvpr
```

Main authorization also requires the signed `certvic.cvpr.confirmatory_outcome.v1` artifact emitted
by successful confirmatory `after_runs`, with `main_go_no_go=GO`. A confirmatory pre-run permission is
not a result and cannot satisfy this prerequisite.
