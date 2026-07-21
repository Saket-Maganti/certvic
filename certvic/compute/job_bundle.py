"""Core free-compute job-bundle builder (V3 prompt 03).

A *bundle* is a directory of text files describing exactly how to run one stage
on a free GPU session and how to resume it if the session dies. It contains no
pixels, no credentials, and no paid endpoints, and it is never executed here.

Bundles are emitted by the Kaggle and Colab packagers; this module holds the
shared job specs, path anonymization, the safety scan, and the writer.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from certvic.hashing import sha256_file
from certvic.io import write_json

EVIDENCE_STATUS = "JOB_PLANNED_ONLY"

JOB_TYPES = ("diffusion_tiny", "diffusion_200", "vlm_tiny", "vlm_200", "ablations", "reports_only")

# Markers that must never appear in a bundle (credentials / paid endpoints).
FORBIDDEN_MARKERS = (
    "api_key", "apikey", "secret_key", "bearer ", "authorization:", "sk-",
    "openai.com", "anthropic.com/v1", "api.openai", "x-api-key",
    "aws_secret", "gcp_key", "paid", "credit_card",
)

# Templated job specs. {config}/{tasks}/{edit_plan}/{out_dir} are filled from
# args; ROOT-like values stay as <PLACEHOLDER> on purpose.
def _job_specs(config: str, scale: int | None) -> dict:
    n = str(scale) if scale else "200"
    return {
        "diffusion_tiny": {
            "description": "Generate a tiny batch of photorealistic diffusion-inpaint edits on a free GPU.",
            "stage": "edit_generation",
            "heavy": True,
            "scale": 20,
            "preflight": [
                f"python3 -m certvic.edit.diffusion_preflight --edit-plan data/manifests/pilot_edit_plan.jsonl --engine diffusers_inpaint_optional --config {config} --weights-dir <WEIGHTS_DIR> --check-gpu",
            ],
            "commands": [
                "python3 -m certvic.edit.generate_edits --edit-plan data/manifests/pilot_edit_plan.jsonl "
                "--out-dir data/edits/ade20k_tiny_pilot --out-manifest data/manifests/pilot_generated_edits.jsonl "
                "--rejected-out data/manifests/pilot_generated_edits_rejected.jsonl "
                "--summary-out data/results/tiny_edit_generation_summary.json --max-items 20 --mode diffusers_inpaint --seed 0",
                "python3 -m certvic.provenance.run_ledger add --stage edit_generation --run-id diffusion_tiny "
                "--inputs data/manifests/pilot_edit_plan.jsonl --outputs data/manifests/pilot_generated_edits.jsonl "
                f"--config {config} --evidence-status REAL_EVIDENCE",
            ],
            "expected_inputs": [
                "data/manifests/pilot_edit_plan.jsonl",
                "<ADE20K_ROOT> (local source pixels; not in bundle)",
                "<WEIGHTS_DIR> (pre-downloaded diffusion weights; not in bundle)",
            ],
            "expected_outputs": [
                "data/edits/ade20k_tiny_pilot/ (edited images)",
                "data/manifests/pilot_generated_edits.jsonl",
                "data/results/tiny_edit_generation_summary.json",
            ],
        },
        "diffusion_200": {
            "description": "Generate ~200 photorealistic diffusion-inpaint edits, sharded across free GPU sessions.",
            "stage": "edit_generation",
            "heavy": True,
            "scale": 200,
            "preflight": [
                f"python3 -m certvic.edit.diffusion_preflight --edit-plan data/manifests/pilot_edit_plan.jsonl --engine diffusers_inpaint_optional --config {config} --weights-dir <WEIGHTS_DIR> --check-gpu",
            ],
            "commands": [
                "# Use the diffusion job queue to shard and resume (see docs/DIFFUSION_JOB_QUEUE.md once built).",
                "python3 -m certvic.edit.generate_edits --edit-plan data/manifests/pilot_edit_plan.jsonl "
                "--out-dir data/edits/ade20k_pilot --out-manifest data/manifests/pilot_generated_edits.jsonl "
                "--rejected-out data/manifests/pilot_generated_edits_rejected.jsonl "
                "--summary-out data/results/edit_generation_summary.json --max-items 200 --mode diffusers_inpaint --seed 0",
            ],
            "expected_inputs": [
                "data/manifests/pilot_edit_plan.jsonl",
                "<ADE20K_ROOT> (local source pixels; not in bundle)",
                "<WEIGHTS_DIR> (pre-downloaded diffusion weights; not in bundle)",
            ],
            "expected_outputs": [
                "data/edits/ade20k_pilot/ (edited images)",
                "data/manifests/pilot_generated_edits.jsonl",
            ],
        },
        "vlm_tiny": {
            "description": "Run open-local VLM inference + scoring on a tiny reviewed task set.",
            "stage": "vlm_inference",
            "heavy": True,
            "scale": 20,
            "preflight": [
                f"python3 -m certvic.eval.vlm_preflight --config {config} --tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl --provider qwen2_5_vl_7b --check-gpu",
            ],
            "commands": [
                f"python3 -m certvic.pipeline.run_tiny_eval --config {config} "
                "--tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl --provider qwen2_5_vl_7b "
                "--out-dir data/results/tiny_eval_qwen --max-items 20",
            ],
            "expected_inputs": [
                "data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl",
                "edited + original images referenced by the tasks (local)",
                "<MODEL_WEIGHTS> (open-local VLM; not in bundle)",
            ],
            "expected_outputs": [
                "data/results/tiny_eval_qwen/ (predictions, scores, summary)",
            ],
        },
        "vlm_200": {
            "description": "Run open-local VLM inference on ~200 tasks with resume + sharding, then score.",
            "stage": "vlm_inference",
            "heavy": True,
            "scale": 200,
            "preflight": [
                f"python3 -m certvic.eval.vlm_preflight --config {config} --tasks data/manifests/tasks.jsonl --provider qwen2_5_vl_7b --check-gpu",
            ],
            "commands": [
                "python3 -m certvic.eval.run_eval --config {cfg} --tasks data/manifests/tasks.jsonl "
                "--out data/predictions/run_qwen.jsonl --provider qwen2_5_vl_7b --run-id qwen_200 "
                "--max-items 200 --num-shards 4 --shard-index 0".replace("{cfg}", config),
                "python3 -m certvic.metrics.score_predictions --tasks data/manifests/tasks.jsonl "
                "--preds data/predictions/run_qwen.jsonl --out-scores data/results/qwen_pair_scores.jsonl "
                "--out-summary data/results/qwen_summary.json",
            ],
            "expected_inputs": [
                "data/manifests/tasks.jsonl",
                "edited + original images referenced by the tasks (local)",
                "<MODEL_WEIGHTS> (open-local VLM; not in bundle)",
            ],
            "expected_outputs": [
                "data/predictions/run_qwen.jsonl (resumable, sharded)",
                "data/results/qwen_pair_scores.jsonl",
                "data/results/qwen_summary.json",
            ],
        },
        "ablations": {
            "description": "Run baseline/ablation conditions (text-only, caption-only, original-only) on a free GPU.",
            "stage": "ablation",
            "heavy": True,
            "scale": int(n) if n.isdigit() else 200,
            "preflight": [
                f"python3 -m certvic.eval.vlm_preflight --config {config} --tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl --provider qwen2_5_vl_7b --check-gpu",
            ],
            "commands": [
                f"python3 -m certvic.eval.run_ablations --tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl --out-dir data/results/ablations --max-items {n} --seed 0",
            ],
            "expected_inputs": [
                "data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl",
            ],
            "expected_outputs": [
                "data/results/ablations/ (ablation predictions + report)",
            ],
        },
        "reports_only": {
            "description": "CPU-only: rebuild reports from existing predictions/scores. No GPU, no model.",
            "stage": "report",
            "heavy": False,
            "scale": None,
            "preflight": [
                "python3 -m pytest -q",
            ],
            "commands": [
                "python3 -m certvic.reporting.build_report --tasks data/manifests/tasks.jsonl "
                "--scores data/results/pair_scores.jsonl --preds data/predictions/run.jsonl "
                "--out-dir data/results/report --alpha 0.05 --gap-threshold 0.05",
            ],
            "expected_inputs": [
                "data/manifests/tasks.jsonl",
                "data/results/pair_scores.jsonl",
                "data/predictions/run.jsonl",
            ],
            "expected_outputs": [
                "data/results/report/ (markdown + figures)",
            ],
        },
    }


def anonymize(text: str) -> str:
    """Collapse home / private absolute paths to a single ``<LOCAL_PATH>`` token."""
    home = str(Path.home())
    # Scrub the whole private path (prefix + remainder), not just the prefix, so
    # no private subdirectory name leaks through.
    out = re.sub(re.escape(home) + r"[^\s\"']*", "<LOCAL_PATH>", text)
    out = re.sub(r"/(Users|home|root|mnt|media)/[^\s\"']*", "<LOCAL_PATH>", out)
    return out


def _scan_forbidden(texts: list[str]) -> list[str]:
    hits: list[str] = []
    for text in texts:
        low = text.lower()
        for marker in FORBIDDEN_MARKERS:
            if marker in low:
                hits.append(marker)
    return sorted(set(hits))


def build_bundle(
    job: str,
    *,
    config: str,
    out_dir: str,
    platform: str = "kaggle",
    scale: int | None = None,
    anonymize_paths: bool = True,
    platform_notes: list[str] | None = None,
) -> dict:
    if job not in JOB_TYPES:
        raise ValueError(f"unknown job type '{job}'; expected one of {JOB_TYPES}")

    spec = _job_specs(config, scale)[job]
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    def maybe(text: str) -> str:
        return anonymize(text) if anonymize_paths else text

    commands = [maybe(c) for c in spec["commands"]]
    preflight = [maybe(c) for c in spec["preflight"]]

    # Safety scan: no credentials / paid endpoints in any emitted text.
    forbidden = _scan_forbidden(commands + preflight + spec["expected_inputs"] + spec["expected_outputs"] + [spec["description"]])

    files: dict[str, str] = {}

    files["README.md"] = _render_readme(job, spec, platform, platform_notes or [], commands, preflight)
    files["commands.sh"] = _render_sh("Run commands", commands)
    files["preflight.sh"] = _render_sh("Preflight (no heavy work)", preflight)
    files["expected_inputs.md"] = _render_list("Expected inputs", spec["expected_inputs"])
    files["expected_outputs.md"] = _render_list("Expected outputs", spec["expected_outputs"])
    files["ZERO_COST_POLICY.txt"] = (
        "This job uses only free Kaggle/Colab GPU, open models, and user-supplied local data.\n"
        "No paid APIs, paid cloud, paid datasets, paid annotation, or paid tracking.\n"
        "No credentials and no private pixels are included in this bundle.\n"
    )

    for name, content in files.items():
        (out / name).write_text(content, encoding="utf-8")

    file_manifest = {
        name: sha256_file(out / name) for name in sorted(files)
    }

    manifest = {
        "bundle": "certvic_free_compute_job",
        "job": job,
        "platform": platform,
        "stage": spec["stage"],
        "heavy_gpu_required": spec["heavy"],
        "scale": scale if scale is not None else spec["scale"],
        "config": config,
        "anonymized": anonymize_paths,
        "evidence_status": EVIDENCE_STATUS,
        "n_commands": len(commands),
        "files": sorted(files),
        "file_hashes": file_manifest,
        "forbidden_markers_found": forbidden,
        "safe": not forbidden,
        "executed": False,
        "downloads_attempted": False,
        "paid_services": False,
        "evidence_claims_made": False,
        "generated": date.today().isoformat(),
    }
    write_json(out / "manifest.json", manifest)
    if forbidden:
        raise ValueError(f"bundle contains forbidden markers: {forbidden}")
    return manifest


def _render_readme(job, spec, platform, platform_notes, commands, preflight) -> str:
    lines = [
        f"# CertVIC free-compute bundle: `{job}` ({platform})",
        "",
        spec["description"],
        "",
        f"- Stage: `{spec['stage']}`",
        f"- GPU required: {spec['heavy']}",
        f"- Evidence status: `{EVIDENCE_STATUS}` (planning artifact; not evidence)",
        "",
        "## Zero-cost policy",
        "",
        "Free GPU + open models + user-supplied local data only. No paid services, no",
        "credentials, no private pixels in this bundle. This bundle is not executed here.",
        "",
        "## Platform notes",
        "",
        *[f"- {n}" for n in platform_notes],
        "",
        "## 1. Preflight (no heavy work)",
        "",
        "```bash",
        *preflight,
        "```",
        "",
        "## 2. Run",
        "",
        "```bash",
        *commands,
        "```",
        "",
        "## 3. Resume",
        "",
        "Free sessions die often. Re-running the commands resumes from existing outputs:",
        "generation skips items whose output already exists, `run_eval` resumes from its",
        "JSONL + run manifest, and sharded runs continue at the next incomplete shard.",
        "After each session, record outputs with `certvic.provenance.run_ledger add` so",
        "progress is hash-tracked across sessions.",
        "",
        "See `expected_inputs.md` / `expected_outputs.md` and `manifest.json`.",
        "",
    ]
    return "\n".join(lines)


def _render_sh(title: str, commands: list[str]) -> str:
    body = "\n".join(commands) if commands else "echo 'no commands'"
    return f"#!/usr/bin/env bash\nset -euo pipefail\n# {title}\n\n{body}\n"


def _render_list(title: str, items: list[str]) -> str:
    return "\n".join([f"# {title}", "", *[f"- `{i}`" for i in items], ""])
