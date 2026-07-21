"""Focused evidence-boundary guard for the Kaggle execution pack."""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path
from typing import Any

from certvic.cvpr.kaggle_bundle import verify_bundle
from certvic.cvpr.notebook_builder import NOTEBOOKS


FORBIDDEN_LOCAL_SUFFIXES = {".whl", ".safetensors", ".pt", ".pth", ".ckpt", ".bin"}


def guard(root: str | Path) -> dict[str, Any]:
    base = Path(root)
    errors: list[str] = []
    bundle_rows = []
    for path in sorted((base / "kaggle_uploads/00_code").glob("*.zip")):
        result = verify_bundle(path)
        bundle_rows.append({"path": str(path.relative_to(base)), "passed": result["passed"]})
        if not result["passed"]:
            errors.append(f"invalid local bundle: {path.name}")
            continue
        with zipfile.ZipFile(path) as archive:
            forbidden = [
                name for name in archive.namelist()
                if Path(name).suffix.lower() in FORBIDDEN_LOCAL_SUFFIXES
            ]
            if forbidden:
                errors.append(f"fabricated/external binary class in {path.name}: {forbidden[:5]}")
            for name in archive.namelist():
                if Path(name).suffix.lower() not in {".json", ".jsonl", ".ipynb"}:
                    continue
                text = archive.read(name).decode("utf-8", errors="ignore")
                if '"paper_evidence": true' in text.lower():
                    errors.append(f"paper_evidence=true in local pack: {path.name}:{name}")
                if '"human_reviewed": true' in text.lower():
                    errors.append(f"human_reviewed=true in local pack: {path.name}:{name}")
    notebook_root = base / "notebooks/kaggle/cvpr"
    observed = {path.name for path in notebook_root.glob("*.ipynb")}
    if observed != set(NOTEBOOKS):
        errors.append("canonical notebook set differs from 16-runbook contract")
    for path in sorted(notebook_root.glob("*.ipynb")):
        text = path.read_text().lower()
        if '"paper_evidence": true' in text or "internet enabled" in text:
            errors.append(f"notebook evidence/network boundary violation: {path.name}")
    import yaml

    for relative in (
        "configs/studies/main_study_cvpr.yaml", "configs/studies/second_domain_cvpr.yaml"
    ):
        value = yaml.safe_load((base / relative).read_text())
        if value.get("execution_allowed") is not False:
            errors.append(f"execution_allowed must remain false: {relative}")
        if value.get("paper_evidence") is not False:
            errors.append(f"paper_evidence must remain false: {relative}")
    return {
        "schema": "certvic.kaggle.claim_guard.v1",
        "passed": not errors,
        "errors": errors,
        "bundles": bundle_rows,
        "notebooks": len(observed),
        "paper_evidence": False,
        "genuine_human_reviewed_true_count": 0,
        "main_execution_allowed": False,
        "coco_execution_allowed": False,
        "v2_30_role": "RETROSPECTIVE_SENSITIVITY",
        "external_model_weight_bytes_fabricated": False,
        "external_wheel_bytes_fabricated": False,
        "real_provider_outputs_fabricated": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--out")
    args = parser.parse_args(argv)
    result = guard(args.root)
    if args.out:
        path = Path(args.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

