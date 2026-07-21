"""Generate Colab fallback notebooks without executing GPU work."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from certvic.notebooks.notebook_cells import checklist, code_cell, make_notebook, markdown_cell, write_notebook

COLAB_JOBS = {
    "diffusion_tiny": [
        "python3 -m certvic.edit.engines --edit-plan data/manifests/pilot_edit_plan.jsonl --out-dir /content/certvic_outputs/edits --out-manifest /content/certvic_outputs/pilot_generated_edits.jsonl --rejected-out /content/certvic_outputs/pilot_generated_rejected.jsonl --summary-out /content/certvic_outputs/pilot_generation_summary.json --engine diffusers_inpaint_optional --max-items 20 --seed 0 --resume --fail-fast",
    ],
    "vlm_tiny": [
        "python3 -m certvic.eval.run_eval --config configs/kaggle_open_vlm.yaml --tasks data/manifests/pilot_eval_tasks_reviewed.jsonl --out /content/certvic_outputs/qwen_tiny.jsonl --provider qwen2_5_vl_7b --run-id colab_qwen_tiny --max-items 20 --shard-index 0 --num-shards 1 --strict-leakage --evidence-run --fail-fast",
    ],
}


def build_notebook(job: str) -> dict:
    if job not in COLAB_JOBS:
        raise ValueError(f"unknown Colab job '{job}'; expected one of {sorted(COLAB_JOBS)}")
    cells = [
        markdown_cell(
            "## Colab setup checklist\n\n"
            "- Drive mount is disabled by default; upload or mount only after review.\n"
            "- Use a user-managed model cache. CertVIC does not auto-download weights.\n"
            "- CPU setup cells are safe; GPU commands are commented."
        ),
        code_cell(
            "from pathlib import Path\n"
            "OUT = Path('/content/certvic_outputs')\n"
            "OUT.mkdir(parents=True, exist_ok=True)\n"
            "print('Drive mount disabled by default. No GPU work executed.')"
        ),
    ]
    for command in COLAB_JOBS[job]:
        cells.append(markdown_cell("## Planned Colab command\n\nUncomment only after inputs/cache exist."))
        cells.append(code_cell("# " + command))
    return make_notebook(f"CertVIC Colab {job}", cells)


def write_colab_notebook(job: str, out: str) -> dict:
    out_path = Path(out)
    write_notebook(out_path, build_notebook(job))
    aux = {
        "README.md": "# CertVIC Colab Fallback\n\nGenerated notebook only; no execution happened.\n",
        "colab_setup_checklist.md": checklist(
            "Colab Setup Checklist",
            [
                "Drive mount remains disabled until manually needed",
                "Model cache path is mounted or uploaded by the user",
                "No automatic downloads are enabled",
                "GPU cells remain commented before manual review",
            ],
        ),
    }
    for name, text in aux.items():
        (out_path.parent / name).write_text(text, encoding="utf-8")
    return {"job": job, "out": str(out_path), "files": sorted([out_path.name, *aux]), "executed": False}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build a CertVIC Colab notebook")
    parser.add_argument("--job", required=True, choices=sorted(COLAB_JOBS))
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    print(json.dumps(write_colab_notebook(args.job, args.out), sort_keys=True))


if __name__ == "__main__":
    main()

