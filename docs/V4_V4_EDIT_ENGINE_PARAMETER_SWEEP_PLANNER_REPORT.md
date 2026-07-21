# V4 Prompt 07 Report — Edit Engine Parameter Sweep Planner

Implemented `certvic.edit.parameter_sweep` and `certvic.edit.sweep_report`.
Sweep rows are deterministic, capped by `--max-combinations`, and
`SWEEP_PLANNED_ONLY`.
