# CertVIC Main Exact Selection Guide

Main primary and reserve rows are solved jointly. The config freezes exact family, category, answer
transition, size, position, complexity, difficulty, engine, question-template, edit-magnitude, and
source-diversity targets plus the same-stratum replacement key. The deterministic backtracker uses
pruning, memoization, state/time limits, and seeded ordering. On a resource limit it invokes pinned
SciPy MILP when available and records `FEASIBLE_SELECTION_FOUND`, `NO_FEASIBLE_SELECTION_EXISTS`,
`SOLVER_RESOURCE_LIMIT`, or `OPTIONAL_SOLVER_UNAVAILABLE`. Greedy partial assignment is prohibited.
`main_solver_report.json` records constraints, counts, objective, states, runtime, and fallback.
