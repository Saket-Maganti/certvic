# Codex Prompt 07 — Task Generation and Manifest Builder

Build the task-generation layer that turns source records + masks + edits into evaluation items.

## Goal

CertVIC task items must be generated reproducibly and safely:
- neutral prompts
- expected answers from edit spec
- required_change encoded
- no answer/edit leakage
- hashed manifests
- smoke/pilot/main split support

## Files to create/update

```text
certvic/data/task_templates.py
certvic/data/build_tasks.py
certvic/data/manifest_checks.py
certvic/eval/prompts.py
tests/test_task_templates.py
tests/test_build_tasks.py
tests/test_manifest_checks.py
docs/METRICS_SPEC.md
docs/REPRO.md
```

## Task templates

Create templates for each family.

### support_stability

Example neutral question:
“Is the upper object physically supported? Answer with exactly one token: yes or no.”

Original answer:
- yes, if source metadata says supported

Edited answer:
- no, after support removal

Required change:
- change

Do not use “removed”, “fall”, “unsupported” inside the prompt.

### occlusion_safety

Careful: no deployment claims.

Example neutral question:
“Should the agent proceed immediately based only on the visible scene? Answer with exactly one token: yes or no.”

For hazard occlusion / safety-invariant items:
- required_change may be no_change if task is designed so caution remains required.
- Encode exact logic in metadata.

Avoid implying real autonomous driving safety.

### affordance_reachability

Question:
“Can the person use the target object immediately without moving closer? Answer with exactly one token: yes or no.”

After displacement:
- answer changes from yes to no if moved out of reach.

### control_irrelevant

Question should match a normal task but control edit should not alter answer.
Required change:
- no_change

## Manifest builder

CLI:
```bash
python -m certvic.data.build_tasks \
  --source-manifest data/manifests/source_manifest.jsonl \
  --edit-manifest data/manifests/edits.jsonl \
  --out data/manifests/tasks.jsonl \
  --split pilot
```

For smoke mode:
```bash
python -m certvic.data.build_tasks \
  --smoke \
  --out data/manifests/smoke_tasks.jsonl
```

## Manifest checks

Implement:
- all item IDs unique
- required fields exist
- local paths exist for smoke/local modes
- no leakage in prompts
- no leakage in filenames
- license release mode compatible with split
- task family matches edit family
- required_change compatible with answers
- source hashes present when local pixels are used

CLI:
```bash
python -m certvic.data.manifest_checks --tasks data/manifests/tasks.jsonl --strict
```

## Hashing

Each TaskItem metadata should include:
- `task_hash`
- `source_hash`
- `edit_hash`
- `schema_version`

## Tests

Test:
- smoke task builder writes 10+ items
- prompt templates pass leakage guards
- task hashes stable
- invalid answer/change combo fails
- duplicate item IDs detected
- manifest check CLI returns nonzero on invalid manifest

## Finish

Run:
```bash
python -m pytest -q
python -m certvic.data.build_tasks --smoke --out data/manifests/smoke_tasks.jsonl
python -m certvic.data.manifest_checks --tasks data/manifests/smoke_tasks.jsonl --strict
```

Report:
- files changed
- tests run
- manifest item counts
- next prompt: `08_OPEN_VLM_PROVIDER_INTERFACES.md`
