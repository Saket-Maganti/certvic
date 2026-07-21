"""Generate portable, ready-to-paste Kaggle configuration cells and checklists."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from certvic.cvpr.ceiling_common import repository_root
from certvic.cvpr.contracts import load_yaml


PROVIDERS = ("qwen2_5_vl_7b", "internvl_8b", "llava_onevision_7b")
NOTEBOOKS: dict[str, dict[str, Any]] = {
    "00A": {
        "file": "00A_certvic_code_and_environment_smoke.ipynb",
        "datasets": ["certvic-code-bundle", "certvic-offline-wheelhouse"],
        "output": "00A_environment.json",
        "providers": False,
    },
    "00B": {
        "file": "00B_certvic_model_snapshot_smoke.ipynb",
        "datasets": ["certvic-code-bundle", "certvic-offline-wheelhouse", "provider-snapshot"],
        "output": "00B_{provider}_snapshot.json",
        "providers": True,
    },
    "00C2": {
        "file": "00C2_certvic_real_model_two_item_smoke.ipynb",
        "datasets": ["certvic-portable-smoke-bundle", "provider-snapshot"],
        "output": "00C2_{provider}_real_model_smoke.zip",
        "providers": True,
    },
    "confirmatory": {
        "file": "02_qwen_specificity_confirmatory_T4x2.ipynb",
        "datasets": ["certvic-confirmatory-task-bundle", "provider-snapshot"],
        "output": "specificity_confirmatory_cvpr_{provider}_return.zip",
        "providers": True,
    },
    "main": {
        "file": "11_qwen_main_study_T4x2.ipynb",
        "datasets": ["certvic-main-task-bundle", "provider-snapshot"],
        "output": "main_study_cvpr_{provider}_return.zip",
        "providers": True,
    },
    "coco": {
        "file": "21_second_domain_qwen_T4x2.ipynb",
        "datasets": ["certvic-second-domain-task-bundle", "provider-snapshot"],
        "output": "second_domain_cvpr_{provider}_return.zip",
        "providers": True,
    },
}


def _safe_slug(value: str, field: str) -> str:
    if not re.fullmatch(r"[a-zA-Z0-9_.-]+", value):
        raise ValueError(f"{field} contains unsafe characters: {value!r}")
    return value


def generate_config(
    notebook: str,
    *,
    provider: str | None,
    root: str | Path,
) -> dict[str, Any]:
    key = notebook.lower() if notebook.lower() in {"confirmatory", "main", "coco"} else notebook.upper()
    if key not in NOTEBOOKS:
        raise ValueError(f"unsupported notebook family: {notebook}")
    spec = NOTEBOOKS[key]
    if spec["providers"] and provider not in PROVIDERS:
        raise ValueError(f"{notebook} requires --provider in {PROVIDERS}")
    if provider is not None:
        _safe_slug(provider, "provider")
    model: dict[str, Any] = {}
    if provider:
        registry = load_yaml(Path(root) / "configs/models/certvic_cvpr_model_registry.yaml")
        model = registry["models"][provider]
    filename = str(spec["file"])
    if provider:
        prefix = {"qwen2_5_vl_7b": "qwen", "internvl_8b": "internvl", "llava_onevision_7b": "llava"}[provider]
        if key in {"confirmatory", "main", "coco"}:
            candidates = {
                "confirmatory": {
                    "qwen": "02_qwen_specificity_confirmatory_T4x2.ipynb",
                    "internvl": "03_internvl_specificity_confirmatory_T4x2.ipynb",
                    "llava": "04_llava_specificity_confirmatory_T4x2.ipynb",
                },
                "main": {
                    "qwen": "11_qwen_main_study_T4x2.ipynb",
                    "internvl": "12_internvl_main_study_T4x2.ipynb",
                    "llava": "13_llava_main_study_T4x2.ipynb",
                },
                "coco": {
                    "qwen": "21_second_domain_qwen_T4x2.ipynb",
                    "internvl": "22_second_domain_internvl_T4x2.ipynb",
                    "llava": "23_second_domain_llava_T4x2.ipynb",
                },
            }
            filename = candidates[key][prefix]
    output = str(spec["output"]).format(provider=provider or "none")
    return {
        "schema": "certvic.cvpr.kaggle_config.v1",
        "notebook_family": key,
        "notebook_file": filename,
        "provider": provider,
        "model_id": model.get("model_id"),
        "model_commit": model.get("model_commit"),
        "processor_commit": model.get("processor_commit"),
        "required_datasets": spec["datasets"],
        "mount_root": "/kaggle/input",
        "working_root": "/kaggle/working/certvic",
        "environment_variables": {
            "CERTVIC_OFFLINE": "1",
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "TOKENIZERS_PARALLELISM": "false",
        },
        "expected_output_filename": output,
        "handoff_command": (
            f"python3 -m certvic.cvpr.kaggle_config --notebook {notebook} "
            + (f"--provider {provider} " if provider else "")
            + "--out generated_configs"
        ),
        "paper_evidence": False,
        "validation_checklist": [
            "Attach only the listed datasets and disable internet before execution.",
            "Verify every configured model, processor, environment, and permission hash.",
            "Run all notebook cells once in a fresh session without editing frozen values.",
            f"Download {output} and preserve its bytes unchanged for local validation.",
            "Do not treat smoke, planned, or synthetic outputs as paper evidence.",
        ],
    }


def write_config(payload: dict[str, Any], out_dir: str | Path) -> list[Path]:
    destination = Path(out_dir)
    destination.mkdir(parents=True, exist_ok=True)
    stem = f"{payload['notebook_family']}_{payload['provider'] or 'shared'}"
    json_path = destination / f"{stem}.json"
    cell_path = destination / f"{stem}_config_cell.py"
    checklist_path = destination / f"{stem}_checklist.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    compact = json.dumps(payload, sort_keys=True)
    cell_path.write_text(
        "# Ready-to-paste generated cell; contains no secrets or host paths.\n"
        "import json\n"
        f"CERTVIC_CONFIG = json.loads({compact!r})\n"
        "for _key, _value in CERTVIC_CONFIG['environment_variables'].items():\n"
        "    __import__('os').environ[_key] = _value\n",
        encoding="utf-8",
    )
    checklist_path.write_text(
        f"# {payload['notebook_file']} validation checklist\n\n"
        + "\n".join(f"- [ ] {item}" for item in payload["validation_checklist"])
        + "\n",
        encoding="utf-8",
    )
    return [json_path, cell_path, checklist_path]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a portable Kaggle config cell")
    parser.add_argument("--root")
    parser.add_argument("--notebook", required=True)
    parser.add_argument("--provider")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    base = repository_root(args.root)
    payload = generate_config(args.notebook, provider=args.provider, root=base)
    out = Path(args.out)
    if not out.is_absolute():
        out = base / out
    paths = write_config(payload, out)
    print(json.dumps({"generated": [path.relative_to(base).as_posix() for path in paths]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

