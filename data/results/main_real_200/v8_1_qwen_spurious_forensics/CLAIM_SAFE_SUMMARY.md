# Claim-Safe V8.1 Summary

`paper_evidence=false`

InternVL and LLaVA-OneVision pass the current spurious specificity gate. Qwen fails the current spurious specificity gate at 12/94 = 0.1277 against the unchanged threshold <= 0.10.

Therefore, a clean all-model specificity claim is blocked. The Qwen result can be described only as elevated sensitivity to irrelevant perturbations pending real human review or a preregistered stricter control rerun.

The main update-gap result remains real under its existing artifacts, but it must be interpreted with this specificity limitation. Main-500 should not start until the Qwen spurious failure is resolved or the paper is reframed to exclude clean Qwen specificity.

Claim-valid recompute passes: False
