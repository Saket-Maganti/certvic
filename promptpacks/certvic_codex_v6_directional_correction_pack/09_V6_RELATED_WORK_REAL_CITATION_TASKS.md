# CertVIC V6 Prompt — Related Work Real Citation Task Scaffold

Read `00_V6_MASTER_CONTEXT.md` first.

You are correcting project direction, not building generic infrastructure.

Hard constraints:
- Do not initialize git.
- Do not commit or tag.
- Do not use paid APIs.
- Do not use paid cloud.
- Do not download data or weights.
- Do not run GPU jobs.
- Do not run VLM inference.
- Do not fabricate results.
- Do not fabricate citations.
- Do not insert fake paper numbers.
- Do not make evidence claims from mock/smoke/simulated/planned/unreviewed/simple-edit-only artifacts.
- Keep tests local and CPU-only.
- Heavy dependencies must be optional/import-safe.

Do not fabricate citations. Build a citation task system that records what must be searched later.

Create:
- `docs/RELATED_WORK_SEARCH_TASKS.md`
- `paper/related_work_todo.yaml`
- `certvic/paper/related_work_task_audit.py`

Categories:
- counterfactual VQA / edited-image VQA
- VLM robustness and consistency
- image editing for evaluation
- dataset validity / construct validity
- human validation in VLM eval
- confidence sequences / anytime-valid inference
- optional stopping in ML evaluation
- benchmark reproducibility and open models

For each:
- search query
- why it matters
- paper section destination
- required citation count
- risk if missing

Tests:
- every category has tasks
- no fake citation keys
- paper is allowed to contain TODO citations only in draft mode

At the end report:
- files changed
- tests added/updated
- commands added
- docs added
- verification commands run
- whether this prompt passed
- next prompt
