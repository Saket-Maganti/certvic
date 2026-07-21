"""Command manifests for V4 real-run execution planning.

This module renders shell commands and metadata only. It never executes commands,
downloads data/model weights, runs GPU jobs, or runs VLM inference.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from certvic.hashing import stable_record_hash
from certvic.providers.registry import PAID_PROVIDER_NAMES, provider_metadata

EVIDENCE_STATUS = "RUN_COMMANDS_PLANNED_ONLY"
ADE20K_PLACEHOLDER = "<ADE20K_ROOT>"
MODEL_CACHE_PLACEHOLDER = "<MODEL_CACHE_ROOT>"
DEFAULT_PROVIDERS = ("qwen2_5_vl_7b", "internvl_8b", "llava_onevision_7b")
FORBIDDEN_PROVIDER_MARKERS = (
    "anthropic",
    "azure",
    "claude",
    "gemini",
    "gpt",
    "openai",
    "paid",
)


@dataclass(frozen=True)
class StageSpec:
    stage: str
    scale: int
    max_items: int
    num_shards: int
    out_label: str
    description: str


STAGE_SPECS: dict[str, StageSpec] = {
    "tiny_pilot": StageSpec(
        stage="tiny_pilot",
        scale=20,
        max_items=20,
        num_shards=2,
        out_label="tiny_real_pilot",
        description="Tiny ADE20K/diffusion/open-VLM pilot with dry-run first.",
    ),
    "main_200": StageSpec(
        stage="main_200",
        scale=200,
        max_items=200,
        num_shards=4,
        out_label="main_real_200",
        description="Main-pilot 200 item execution plan.",
    ),
    "full_2000": StageSpec(
        stage="full_2000",
        scale=2000,
        max_items=2000,
        num_shards=12,
        out_label="full_real_2000",
        description="Full 2k study execution plan, heavily sharded for free GPU sessions.",
    ),
}
SUPPORTED_STAGES = tuple(STAGE_SPECS)


def build_command_manifest(
    stage: str,
    *,
    ade20k_root: str = ADE20K_PLACEHOLDER,
    model_cache_root: str = MODEL_CACHE_PLACEHOLDER,
    providers: list[str] | tuple[str, ...] | None = None,
    anonymize_paths: bool = True,
) -> dict:
    """Build a non-executed command manifest for a real-run stage."""
    if stage not in STAGE_SPECS:
        raise ValueError(f"unknown stage '{stage}'; expected one of {sorted(STAGE_SPECS)}")
    provider_list = _validate_providers(providers or DEFAULT_PROVIDERS)
    spec = STAGE_SPECS[stage]
    ade_root = _parameterize_path(ade20k_root, ADE20K_PLACEHOLDER, anonymize_paths)
    model_root = _parameterize_path(model_cache_root, MODEL_CACHE_PLACEHOLDER, anonymize_paths)
    commands = _commands_for_stage(spec, ade_root, model_root, provider_list)
    manifest = {
        "manifest": "certvic_v4_real_run_commands",
        "stage": stage,
        "description": spec.description,
        "generated_date": date.today().isoformat(),
        "scale": spec.scale,
        "max_items": spec.max_items,
        "num_shards": spec.num_shards,
        "providers": list(provider_list),
        "provider_metadata": {p: provider_metadata(p) for p in provider_list},
        "commands": commands,
        "n_commands": len(commands),
        "required_inputs": _required_inputs(spec, ade_root, model_root),
        "expected_outputs": _expected_outputs(spec),
        "resume_notes": _resume_notes(spec),
        "safety": {
            "executed": False,
            "downloads_attempted": False,
            "gpu_required_for_generation": False,
            "vlm_inference_run": False,
            "paid_services": False,
            "evidence_claims_made": False,
            "planned_artifacts_evidence_status": EVIDENCE_STATUS,
            "private_paths_anonymized": anonymize_paths,
        },
    }
    manifest["command_manifest_sha256"] = stable_record_hash(
        {
            "stage": manifest["stage"],
            "scale": manifest["scale"],
            "providers": manifest["providers"],
            "commands": manifest["commands"],
            "safety": manifest["safety"],
        }
    )
    return manifest


def commands_sh(manifest: dict) -> str:
    """Render a shell script from a command manifest."""
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
        f"# CertVIC V4/V6 real-run command index: {manifest['stage']}",
        "# Generated for later execution; generation itself executed nothing.",
        "# Do not run this file wholesale. Use staged scripts and gate reports.",
        "# Planned command artifacts are non-evidence.",
        "",
        'if [[ "${CERTVIC_RUN_ALL_DANGEROUS_STAGES:-0}" != "1" ]]; then',
        '  echo "Refusing to run all stages in one blind script."',
        '  echo "Use staged scripts, inspect gates, and only then run VLM stages."',
        '  echo "Override only with CERTVIC_RUN_ALL_DANGEROUS_STAGES=1 after manual review."',
        "  exit 2",
        "fi",
        "",
    ]
    for entry in manifest["commands"]:
        lines.append(f"# [{entry['id']}] {entry['title']}")
        if entry.get("notes"):
            lines.append(f"# {entry['notes']}")
        lines.append(entry["command"])
        lines.append("")
    return "\n".join(lines)


def staged_scripts(manifest: dict) -> dict[str, str]:
    """Render V6 staged scripts for the tiny-pilot command sequence."""
    by_id = {entry["id"]: entry for entry in manifest["commands"]}

    def script(title: str, entries: list[str], extra_comments: list[str] | None = None) -> str:
        lines = [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            "",
            f"# {title}",
            "# Generated command plan only; review paths before execution.",
            "# No paid APIs, paid cloud, downloads, or evidence claims are authorized here.",
        ]
        for comment in extra_comments or []:
            lines.append(f"# {comment}")
        lines.append("")
        for command_id in entries:
            entry = by_id[command_id]
            lines.extend([f"# [{entry['id']}] {entry['title']}", f"# {entry['notes']}", entry["command"], ""])
        return "\n".join(lines)

    return {
        "commands/tiny_pilot/01_cpu_readiness.sh": script(
            "Stage 01: CPU readiness only",
            ["v3_gate", "study_plan"],
            ["CPU-only. Stop after this stage and inspect reports."],
        ),
        "commands/tiny_pilot/02_dry_run_only.sh": script(
            "Stage 02: ADE20K dry-run only",
            ["tiny_pilot_dry_run"],
            ["Dry-run must pass before any edit generation."],
        ),
        "commands/tiny_pilot/03_generate_edits_only.sh": script(
            "Stage 03: generate edits only",
            ["tiny_pilot_execute", "diffusion_queue", "diffusion_resume_status", "gpu_edit_generation", "quality_gate"],
            ["Free-GPU edit generation only. Do not run VLM inference in this stage."],
        ),
        "commands/tiny_pilot/04_detectability_gate_only.sh": script(
            "Stage 04: detectability gate only",
            ["quality_gate"],
            ["Run edit detectability and tiny-pilot go/no-go before VLM inference."],
        ),
        "commands/tiny_pilot/05_vlm_eval_only_AFTER_GATES.sh": script(
            "Stage 05: VLM eval only AFTER gates",
            ["review_batches", "model_matrix", "vlm_dry_run_one_shard", "vlm_execute_one_shard", "score_predictions", "triage_outputs", "build_report"],
            ["Only run after detectability, visual quality, review, and certificates pass."],
        ),
    }


def commands_md(manifest: dict) -> str:
    lines = [
        f"# V4 Real-Run Commands — {manifest['stage']}",
        "",
        manifest["description"],
        "",
        "**Generation status:** no commands executed; this file is run-later infrastructure.",
        "",
        "| # | Command | Evidence status | Notes |",
        "| --- | --- | --- | --- |",
    ]
    for i, entry in enumerate(manifest["commands"], start=1):
        command = entry["command"].replace("|", "\\|")
        notes = entry.get("notes", "").replace("|", "\\|")
        lines.append(f"| {i} | `{command}` | {entry['evidence_status']} | {notes} |")
    lines.append("")
    return "\n".join(lines)


def expected_inputs_md(manifest: dict) -> str:
    lines = [
        f"# Expected Inputs — {manifest['stage']}",
        "",
        "All paths are user-provided or generated locally. No downloads are attempted here.",
        "",
    ]
    lines.extend(f"- `{item}`" for item in manifest["required_inputs"])
    lines.append("")
    return "\n".join(lines)


def expected_outputs_md(manifest: dict) -> str:
    lines = [
        f"# Expected Outputs — {manifest['stage']}",
        "",
        "Outputs are expected after the user executes the generated commands.",
        "Planned outputs and dry-run outputs are not paper evidence.",
        "",
    ]
    lines.extend(f"- `{item}`" for item in manifest["expected_outputs"])
    lines.append("")
    return "\n".join(lines)


def resume_notes_md(manifest: dict) -> str:
    lines = [
        f"# Resume Notes — {manifest['stage']}",
        "",
        "Re-run the same command after interruption unless a command explicitly says otherwise.",
        "Avoid `--overwrite` unless you are intentionally replacing a bad partial artifact.",
        "",
    ]
    lines.extend(f"- {note}" for note in manifest["resume_notes"])
    lines.append("")
    return "\n".join(lines)


def _commands_for_stage(
    spec: StageSpec,
    ade20k_root: str,
    model_cache_root: str,
    providers: tuple[str, ...],
) -> list[dict]:
    result_dir = f"data/results/{spec.out_label}"
    pred_root = f"data/predictions/{spec.out_label}"
    task_path = f"{result_dir}/pilot_eval_tasks_reviewed.jsonl"
    provider_args = " ".join(providers)
    first_provider = providers[0]
    commands = [
        _cmd(
            "v3_gate",
            "Confirm the V3 final gate is green",
            "python3 -m certvic.v3.final_pre_real_run_audit "
            "--out docs/V3_FINAL_PRE_REAL_RUN_AUDIT_REPORT.md "
            "--json-out data/results/v3_final_pre_real_run_audit.json",
            "AUDIT_ONLY",
            "CPU-only audit; creates no evidence.",
        ),
        _cmd(
            "study_plan",
            "Render the main-study dry-run plan",
            "python3 -m certvic.pipeline.main_study_dry_run "
            f"--scale {spec.scale} --out-dir data/results/main_study_dry_run_{spec.scale}",
            "PLAN_ONLY",
            "Command planning only; no GPU/VLM execution.",
        ),
        _cmd(
            "tiny_pilot_dry_run",
            "Inspect ADE20K and build local dry-run state",
            "python3 -m certvic.pipeline.run_tiny_pilot "
            f"--config configs/real_pilot_ade20k.yaml --ade20k-root {ade20k_root} "
            f"--out-dir {result_dir} --max-items {spec.max_items} --seed 0 --dry-run",
            "PIPELINE_NON_EVIDENCE",
            "Safety flag `--dry-run` must pass before running the non-dry-run command.",
        ),
        _cmd(
            "tiny_pilot_execute",
            "Run the bounded pilot pipeline",
            "python3 -m certvic.pipeline.run_tiny_pilot "
            f"--config configs/real_pilot_ade20k.yaml --ade20k-root {ade20k_root} "
            f"--out-dir {result_dir} --max-items {spec.max_items} --seed 0",
            "PIPELINE_NON_EVIDENCE",
            "Resume by re-running; stage_status.json skips completed stages unless `--force`.",
        ),
        _cmd(
            "diffusion_queue",
            "Build the resumable diffusion queue",
            "python3 -m certvic.edit.job_queue build "
            f"--edit-plan {result_dir}/pilot_edit_plan.jsonl "
            f"--out {result_dir}/diffusion_job_queue.jsonl --shards {spec.num_shards}",
            "JOB_PLANNED_ONLY",
            "Queue building only.",
        ),
        _cmd(
            "diffusion_resume_status",
            "Compute diffusion resume worklist",
            "python3 -m certvic.edit.diffusion_resume "
            f"--queue {result_dir}/diffusion_job_queue.jsonl "
            f"--generated {result_dir}/pilot_generated_edits.jsonl "
            f"--out {result_dir}/diffusion_resume.jsonl",
            "JOB_PLANNED_ONLY",
            "Use this before each free-GPU session.",
        ),
        _cmd(
            "gpu_edit_generation",
            "Generate photorealistic edits on free GPU",
            "python3 -m certvic.edit.engines "
            f"--edit-plan {result_dir}/pilot_edit_plan.jsonl "
            f"--out-dir data/edits/{spec.out_label} "
            f"--out-manifest {result_dir}/pilot_generated_edits.jsonl "
            f"--rejected-out {result_dir}/pilot_generated_rejected.jsonl "
            f"--summary-out {result_dir}/pilot_generation_summary.json "
            "--engine diffusers_inpaint_optional "
            f"--max-items {spec.max_items} --seed 0 --resume --fail-fast",
            "GENERATED_EDIT_ONLY",
            "Runs only when the user executes it on free GPU with local/cached weights.",
        ),
        _cmd(
            "quality_gate",
            "Build quality and detectability reports",
            "python3 -m certvic.edit.quality_report "
            f"--generated-manifest {result_dir}/pilot_generated_edits.jsonl "
            f"--rejected {result_dir}/pilot_generated_rejected.jsonl "
            f"--out-dir {result_dir}/tiny_edit_quality_report",
            "QUALITY_ONLY",
            "Quality gates do not create evidence claims.",
        ),
        _cmd(
            "review_batches",
            "Create human review batches",
            "python3 -m certvic.validation.review_batches "
            f"--tasks {result_dir}/pilot_eval_tasks_tiny.jsonl "
            f"--out-dir data/annotations/{spec.out_label}_review_batches "
            "--reviewers reviewer_a reviewer_b --overlap-rate 0.2",
            "HUMAN_REVIEWED_NON_EVIDENCE",
            "Reviewer IDs are placeholders; paid annotation is not required.",
        ),
        _cmd(
            "model_matrix",
            "Plan the open-local VLM matrix",
            "python3 -m certvic.eval.run_matrix_planner "
            f"--tasks {task_path} --providers {provider_args} "
            f"--out-dir {result_dir}/model_run_matrix --config configs/kaggle_open_vlm.yaml "
            f"--pred-root {pred_root} --max-items {spec.max_items} --num-shards {spec.num_shards}",
            "RUN_MATRIX_PLANNED_ONLY",
            "Planning only; no inference.",
        ),
        _cmd(
            "vlm_dry_run_one_shard",
            "Dry-run one VLM shard before real inference",
            "python3 -m certvic.eval.run_eval "
            f"--config configs/kaggle_open_vlm.yaml --tasks {task_path} "
            f"--out {pred_root}/{first_provider}_shard0.jsonl --provider {first_provider} "
            f"--run-id {spec.stage}_{first_provider}_shard0 "
            f"--max-items {spec.max_items} --shard-index 0 --num-shards {spec.num_shards} "
            "--dry-run --strict-leakage --fail-fast",
            "PREFLIGHT_ONLY",
            "Safety flags included; dry-run must pass before dropping `--dry-run`.",
        ),
        _cmd(
            "vlm_execute_one_shard",
            "Execute one evidence-eligible open-local VLM shard",
            "python3 -m certvic.eval.run_eval "
            f"--config configs/kaggle_open_vlm.yaml --tasks {task_path} "
            f"--out {pred_root}/{first_provider}_shard0.jsonl --provider {first_provider} "
            f"--run-id {spec.stage}_{first_provider}_shard0 "
            f"--max-items {spec.max_items} --shard-index 0 --num-shards {spec.num_shards} "
            "--strict-leakage --evidence-run --fail-fast",
            "REAL_EVIDENCE_AFTER_EXECUTION",
            "Resume is default because completed task keys are skipped by the runner.",
        ),
        _cmd(
            "score_predictions",
            "Score merged predictions",
            "python3 -m certvic.metrics.score_predictions "
            f"--tasks {task_path} --preds {pred_root}/merged.jsonl "
            f"--out-scores {result_dir}/pair_scores.jsonl "
            f"--out-summary {result_dir}/score_summary.json",
            "REAL_EVIDENCE_AFTER_EXECUTION",
            "Only valid after real open-local predictions exist.",
        ),
        _cmd(
            "triage_outputs",
            "Triage parse/output quality",
            "python3 -m certvic.eval.output_triage "
            f"--preds {pred_root}/merged.jsonl --tasks {task_path} "
            f"--out-dir {result_dir}/output_triage",
            "QUALITY_ONLY",
            "Inspect before trusting gaps.",
        ),
        _cmd(
            "build_report",
            "Build report artifacts without paper-number injection",
            "python3 -m certvic.reporting.build_v2_report "
            f"--tasks {task_path} --preds {pred_root}/merged.jsonl "
            f"--scores {result_dir}/pair_scores.jsonl --out-dir {result_dir}/v2_report",
            "REPORT_ONLY",
            "Paper claims still require claim gates and future result lockfiles.",
        ),
    ]
    if model_cache_root != MODEL_CACHE_PLACEHOLDER:
        commands.insert(
            2,
            _cmd(
                "model_cache_note",
                "Record user-managed model cache root",
                f"printf '%s\\n' '{model_cache_root}' > {result_dir}/MODEL_CACHE_ROOT.txt",
                "LOCAL_NOTE_ONLY",
                "No downloads; this records a local/cache path placeholder for later scripts.",
            ),
        )
    return commands


def _cmd(command_id: str, title: str, command: str, evidence_status: str, notes: str) -> dict:
    return {
        "id": command_id,
        "title": title,
        "command": command,
        "evidence_status": evidence_status,
        "notes": notes,
    }


def _required_inputs(spec: StageSpec, ade20k_root: str, model_cache_root: str) -> list[str]:
    return [
        f"{ade20k_root} (local ADE20K root; never downloaded by CertVIC)",
        f"{model_cache_root} (user-managed local/open model cache)",
        "free Kaggle or Colab GPU session for edit generation and open-local VLM inference",
        f"human review capacity for up to {spec.max_items} reviewed items",
        "configs/real_pilot_ade20k.yaml",
        "configs/kaggle_open_vlm.yaml",
    ]


def _expected_outputs(spec: StageSpec) -> list[str]:
    result_dir = f"data/results/{spec.out_label}"
    pred_root = f"data/predictions/{spec.out_label}"
    return [
        f"{result_dir}/stage_status.json",
        f"{result_dir}/pilot_generated_edits.jsonl",
        f"{result_dir}/tiny_edit_quality_report/",
        f"{result_dir}/model_run_matrix/",
        f"{pred_root}/",
        f"{result_dir}/pair_scores.jsonl",
        f"{result_dir}/output_triage/",
        f"{result_dir}/v2_report/",
    ]


def _resume_notes(spec: StageSpec) -> list[str]:
    result_dir = f"data/results/{spec.out_label}"
    return [
        f"`{result_dir}/stage_status.json` lets `run_tiny_pilot` skip completed stages.",
        "`certvic.edit.engines --resume` skips already generated/rejected edit IDs.",
        "`certvic.eval.run_eval` skips completed task keys by default.",
        "`certvic.edit.diffusion_resume` should be rerun after each interrupted GPU session.",
        "Do not delete partial JSONL outputs until merge/dedup/recovery tools have inspected them.",
    ]


def _validate_providers(providers: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    cleaned = tuple(str(p).strip() for p in providers if str(p).strip())
    if not cleaned:
        raise ValueError("at least one provider is required")
    rejected: list[str] = []
    for provider in cleaned:
        lower = provider.lower()
        meta = provider_metadata(provider)
        if provider in PAID_PROVIDER_NAMES:
            rejected.append(provider)
            continue
        if any(marker in lower for marker in FORBIDDEN_PROVIDER_MARKERS):
            rejected.append(provider)
            continue
        if meta.get("provider_type") == "free_tier_reference":
            rejected.append(provider)
    if rejected:
        raise ValueError(
            "paid or non-core providers are not allowed in V4 real-run commands: "
            + ", ".join(sorted(rejected))
        )
    return cleaned


def _parameterize_path(path: str, placeholder: str, anonymize: bool) -> str:
    if not path:
        return placeholder
    if path == placeholder:
        return path
    if not anonymize:
        return path
    expanded = Path(path).expanduser()
    if expanded.is_absolute() or str(path).startswith("~"):
        return placeholder
    return path
