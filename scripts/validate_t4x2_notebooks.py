"""CPU-only static validation for the runnable CertVIC T4x2 VLM notebooks."""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from certvic.eval.parse import DIAGNOSTIC_ANSWER_FORMATS  # noqa: E402


FAKE_OUTPUT_RE = re.compile(r"(?:fake|mock|fixture)[_-]?(?:prediction|preds?|results?)", re.I)
DEFAULT_NOTEBOOKS = sorted(
    {
        *ROOT.glob("notebooks/kaggle/vlm_*_T4x2_parallel.ipynb"),
        *ROOT.glob("notebooks/kaggle/vlm_*_spurious_v2_T4x2.ipynb"),
    }
)
PROVIDERS = ("qwen2_5_vl_7b", "internvl_8b", "llava_onevision_7b")


def _notebook_text(nb) -> str:
    return "\n".join(str(cell.get("source", "")) for cell in nb.cells)


def _required(text: str, needle: str, errors: list[str], label: str | None = None) -> None:
    if needle not in text:
        errors.append(f"missing {label or needle}")


def _validate_one(path: Path) -> dict:
    errors: list[str] = []
    try:
        nb = nbformat.read(path, as_version=4)
        nbformat.validate(nb)
    except Exception as exc:
        return {"path": str(path), "passed": False, "errors": [f"nbformat: {exc}"]}
    text = _notebook_text(nb)
    code_cells = [cell for cell in nb.cells if cell.cell_type == "code"]
    for index, cell in enumerate(code_cells):
        if cell.get("outputs"):
            errors.append(f"code cell {index} contains saved outputs")
        try:
            ast.parse(cell.source)
        except SyntaxError as exc:
            errors.append(f"code cell {index} syntax error: {exc.msg} line {exc.lineno}")

    private_unix_home = "/" + "Users" + "/"
    private_windows_home = "\\" + "Users" + "\\"
    if private_unix_home in text or private_windows_home in text:
        errors.append("private absolute path")
    if FAKE_OUTPUT_RE.search(text):
        errors.append("fake/mock/fixture prediction generation language")
    provider_hits = [provider for provider in PROVIDERS if f'PROVIDER = "{provider}"' in text]
    if len(provider_hits) != 1:
        errors.append(f"expected exactly one provider constant, found {provider_hits}")

    for needle, label in (
        ("torch.cuda.device_count()", "GPU inventory"),
        ("CUDA_VISIBLE_DEVICES=0", "GPU0 wiring"),
        ("CUDA_VISIBLE_DEVICES=1", "GPU1 wiring"),
        ("subprocess.Popen", "parallel subprocess launch"),
        ("Launching two parallel GPU workers", "T4x2 concurrent branch"),
        ("single-GPU fallback", "one-GPU fallback"),
        ("shard_complete", "resume completeness check"),
        ("n == SHARD_EXPECT[shard]", "exact shard resume denominator"),
        ("duplicate prediction id", "duplicate detection"),
        ("merged row count mismatch", "exact merged denominator"),
        ("prediction key mismatch", "exact item/variant key validation"),
        ("provider mismatch in merged rows", "provider validation"),
        ("certification-critical parse failures block packaging", "strict parse gate"),
        ("ovlm.OpenVLMProvider.answer", "scaffold adapter runtime patch"),
        ("pred_{PROVIDER}_{RUN_TAG}_shard{shard}.jsonl", "shard output naming"),
        ("pred_{PROVIDER}_{RUN_TAG}_merged.jsonl", "merged output naming"),
        ("runtime_manifest_{PROVIDER}_{RUN_TAG}.json", "runtime manifest"),
        ("MODEL_REVISION = None", "explicit unresolved model revision lock"),
        ("revision=MODEL_REVISION", "exact model revision download"),
        (".certvic_model_revision", "cached revision marker"),
        ('"model_revision": MODEL_REVISION', "runtime model revision provenance"),
        ('"MODEL_REVISION": MODEL_REVISION', "worker model revision propagation"),
        ("hf_models", "model-cache exclusion surface"),
    ):
        _required(text, needle, errors, label)

    is_v2 = "spurious_v2_T4x2" in path.name
    if is_v2:
        for needle, label in (
            ('RUN_TAG = "spurious_v2"', "frozen V2 run tag"),
            ("_find_exactly_one", "unambiguous archive discovery"),
            ("Unsafe ZIP member", "safe ZIP extraction"),
            ("task_file_sha256", "task source hash"),
            ("CODE_BUNDLE_SHA256", "code bundle source hash"),
            ("CONTROL_BUNDLE_SHA256", "control bundle source hash"),
            ('bundle_manifest.get("image_entries")', "per-image hash manifest"),
            ("Spurious V2 image hash mismatch", "per-image hash validation"),
            ("merged_predictions_sha256", "prediction source hash"),
            ("certvic.v11.spurious_v2.kaggle_output_manifest.v3", "V2 output manifest schema"),
            ('run_prefix = "v9" if RUN_TAG == "spurious_v2" else "remaining"', "V2 run ID binding"),
            ('evidence_run=(RUN_TAG != "spurious_v2")', "non-paper-evidence V2 execution boundary"),
        ):
            _required(text, needle, errors, label)
    else:
        for fmt in ("object_list", "describe_then_yes_no"):
            if fmt not in DIAGNOSTIC_ANSWER_FORMATS:
                errors.append(f"local parser does not support diagnostic format {fmt}")

    return {
        "path": str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path),
        "provider": provider_hits[0] if len(provider_hits) == 1 else None,
        "kind": "spurious_v2" if is_v2 else "remaining_runs",
        "passed": not errors,
        "errors": errors,
    }


def validate(paths: list[Path] | None = None) -> dict:
    selected = [Path(path) for path in (paths if paths is not None else DEFAULT_NOTEBOOKS)]
    entries = [_validate_one(path) for path in selected]
    return {
        "schema": "certvic.v11.t4x2_notebook_static_validation.v1",
        "mode": "CPU_STATIC_ONLY_NOTEBOOKS_NOT_EXECUTED",
        "n_notebooks": len(entries),
        "passed": bool(entries) and all(entry["passed"] for entry in entries),
        "notebooks": entries,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    result = validate(args.paths or None)
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
