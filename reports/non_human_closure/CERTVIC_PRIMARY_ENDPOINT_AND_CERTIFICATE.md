# Primary endpoint and certificate

`semantic_update_success` requires: original correct, edited correct, changed gold, and a model answer
that changes to the edited gold. `irrelevant_flip` requires unchanged gold and a changed normalized
answer. A never-updating model therefore receives zero relevant successes and cannot pass.

The primary fixed-sample certificate passes only when the one-sided exact lower bound for update
success is at least 0.50 and the one-sided exact upper bound for irrelevant flips is at most 0.10.
Familywise alpha 0.05 is Bonferroni-allocated over three models by two gates (1/120 per bound). Missing,
abstaining, and parser-failed relevant rows fail responsiveness; corresponding irrelevant rows count
as flips. The old accuracy-minus-change gap is secondary descriptive output only.
