"""Generate Kaggle-ready notebooks without executing GPU work."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from certvic.notebooks.notebook_cells import checklist, code_cell, make_notebook, markdown_cell, write_notebook

KAGGLE_JOBS = {
    "diffusion_tiny": {
        "title": "CertVIC Kaggle Diffusion Tiny",
        "commands": [
            "python3 -m certvic.edit.diffusion_resume --queue data/manifests/diffusion_job_queue.jsonl --generated data/manifests/pilot_generated_edits.jsonl --out data/manifests/diffusion_resume.jsonl",
            "python3 -m certvic.edit.engines --edit-plan data/manifests/pilot_edit_plan.jsonl --out-dir /kaggle/working/edits --out-manifest /kaggle/working/pilot_generated_edits.jsonl --rejected-out /kaggle/working/pilot_generated_rejected.jsonl --summary-out /kaggle/working/pilot_generation_summary.json --engine diffusers_inpaint_optional --max-items 20 --seed 0 --resume --fail-fast",
        ],
    },
    "vlm_200": {
        "title": "CertVIC Kaggle VLM 200",
        "commands": [
            "python3 -m certvic.eval.run_matrix_planner --tasks /kaggle/input/certvic-tasks/pilot_eval_tasks_reviewed.jsonl --providers qwen2_5_vl_7b internvl_8b llava_onevision_7b --out-dir /kaggle/working/model_run_matrix --config configs/kaggle_open_vlm.yaml --pred-root /kaggle/working/predictions --max-items 200 --num-shards 4",
            "python3 -m certvic.eval.run_eval --config configs/kaggle_open_vlm.yaml --tasks /kaggle/input/certvic-tasks/pilot_eval_tasks_reviewed.jsonl --out /kaggle/working/predictions/qwen_shard0.jsonl --provider qwen2_5_vl_7b --run-id kaggle_qwen_shard0 --max-items 200 --shard-index 0 --num-shards 4 --strict-leakage --evidence-run --fail-fast",
        ],
    },
}


def build_notebook(job: str) -> dict:
    if job not in KAGGLE_JOBS:
        raise ValueError(f"unknown Kaggle job '{job}'; expected one of {sorted(KAGGLE_JOBS)}")
    spec = KAGGLE_JOBS[job]
    cells = [
        markdown_cell(
            "## Setup checklist\n\n"
            "- Attach CertVIC code as a Kaggle input dataset or upload a source archive.\n"
            "- Attach ADE20K/task manifests and model caches as read-only Kaggle inputs.\n"
            "- Keep internet off unless you intentionally prepared a free public cache path.\n"
            "- Never paste credentials into this notebook."
        ),
        code_cell(
            "from pathlib import Path\n"
            "WORK = Path('/kaggle/working')\n"
            "WORK.mkdir(parents=True, exist_ok=True)\n"
            "print('GPU execution is user-triggered only; this cell is CPU-safe.')"
        ),
    ]
    for command in spec["commands"]:
        cells.append(markdown_cell("## Planned command\n\nThis cell is intentionally commented. Review before running."))
        cells.append(code_cell("# Resume-safe command; uncomment in Kaggle only after inputs are mounted.\n# " + command))
    cells.append(markdown_cell("## Output policy\n\nCopy only manifests/reports back. Do not redistribute ADE20K pixels."))
    return make_notebook(spec["title"], cells)


def write_kaggle_notebook(job: str, out: str) -> dict:
    notebook = build_notebook(job)
    out_path = Path(out)
    write_notebook(out_path, notebook)
    aux = {
        "README.md": (
            f"# {KAGGLE_JOBS[job]['title']}\n\n"
            "Generated notebook only; no execution happened. Use free Kaggle GPU manually.\n"
        ),
        "inputs_checklist.md": checklist(
            "Kaggle Inputs Checklist",
            [
                "CertVIC code attached",
                "Task/edit manifests attached",
                "User-managed model cache attached",
                "No credentials or paid endpoints",
            ],
        ),
        "outputs_checklist.md": checklist(
            "Kaggle Outputs Checklist",
            [
                "Prediction/edit JSONL copied from /kaggle/working",
                "Summary JSON/Markdown copied",
                "No nonredistributable pixels exported",
            ],
        ),
    }
    for name, text in aux.items():
        (out_path.parent / name).write_text(text, encoding="utf-8")
    return {"job": job, "out": str(out_path), "files": sorted([out_path.name, *aux]), "executed": False}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build a CertVIC Kaggle notebook")
    parser.add_argument("--job", required=True, choices=sorted(KAGGLE_JOBS))
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    print(json.dumps(write_kaggle_notebook(args.job, args.out), sort_keys=True))


if __name__ == "__main__":
    main()

