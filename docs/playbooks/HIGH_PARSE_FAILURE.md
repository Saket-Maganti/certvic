# Playbook: High Parse Failure

**Symptoms: a large fraction of model outputs do not parse into a valid answer.**

## Actions

1. Run `certvic.eval.output_triage`; inspect `parse_failure_examples.jsonl` and `suspicious_outputs.csv`.
2. Fix the prompt (answer-format instruction) and/or the parser (strict vs lenient) before trusting scores.
3. Check for refusals and over-long rationales; re-prompt or exclude refusals (they are not a gap).
4. Lower `max_new_tokens` for yes/no tasks; re-run a tiny eval and re-triage.

Do not fabricate results to clear this symptom; if the honest outcome is a null
result or an ineligible claim, report it and adjust the protocol, not the numbers.
