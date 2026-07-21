# Playbook: Low Original Accuracy

**Symptoms: the model is wrong on the original (unedited) image too often.**

## Actions

1. A model that fails the original question cannot exhibit a meaningful consistency gap.
2. Check task difficulty/ambiguity and parser correctness on original-variant outputs.
3. Confirm the question is answerable from the original image (prompt_answerable review field).
4. Consider per-item conditioning on original-correct items when reporting the gap (document it).

Do not fabricate results to clear this symptom; if the honest outcome is a null
result or an ineligible claim, report it and adjust the protocol, not the numbers.
