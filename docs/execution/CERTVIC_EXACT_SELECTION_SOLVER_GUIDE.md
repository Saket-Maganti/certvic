# Exact Selection Solver Guide

`candidate_selection` jointly solves primary and reserve marginal quotas using deterministic exact
backtracking. It supports answer, size, position, complexity, engine, difficulty, source, and duplicate
group constraints. Outputs include `FEASIBLE_SELECTION_FOUND` or `NO_FEASIBLE_SELECTION_EXISTS`,
visited states, achieved counts, objective values, and a conflict certificate. A heuristic shortage is
never treated as proof of infeasibility.
