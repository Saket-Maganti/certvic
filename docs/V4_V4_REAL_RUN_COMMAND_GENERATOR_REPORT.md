# V4 Prompt 01 Report — Real Run Command Generator

Status: implemented.

## Added

- `certvic.commands.command_manifest` defines the V4 stage manifest, safety
  metadata, provider rejection rules, path parameterization, and renderers.
- `certvic.commands.generate_real_run_commands` writes `commands.sh`,
  `commands.md`, `command_manifest.json`, `expected_inputs.md`,
  `expected_outputs.md`, and `resume_notes.md`.
- `tests/test_v4_v4_real_run_command_generator.py` covers generated artifacts,
  stage coverage, safety flags, non-execution markers, provider rejection, path
  anonymization, and heavy-import safety.
- `docs/V4_COMMAND_INDEX.md` records the Prompt 01 commands.

## Commands

```bash
python3 -m certvic.commands.generate_real_run_commands --stage tiny_pilot --out-dir commands/tiny_pilot
python3 -m certvic.commands.generate_real_run_commands --stage main_200 --out-dir commands/main_200
python3 -m certvic.commands.generate_real_run_commands --stage full_2000 --out-dir commands/full_2000
```

Generated bundles now exist at:

- `commands/tiny_pilot/`
- `commands/main_200/`
- `commands/full_2000/`

## Safety

The generator only writes planned command artifacts. It does not execute the
commands it renders, does not download data or weights, does not run GPU jobs,
does not run VLM inference, and does not create evidence claims.

Generated manifests are marked `RUN_COMMANDS_PLANNED_ONLY`.

## Verification

```bash
python3 -m pytest -q tests/test_v4_v4_real_run_command_generator.py
python3 -m pytest -q
python3 -m ruff check certvic/commands tests/test_v4_v4_real_run_command_generator.py
```

Latest local result: focused tests passed, full suite passed (`442 passed`), and
ruff passed for the new code.

## Next Prompt

Prompt 02: Kaggle Notebook Autogenerator.
