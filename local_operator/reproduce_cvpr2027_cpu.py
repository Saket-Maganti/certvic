"""Reproduce deterministic C11 CPU artifacts from a clean archive of committed HEAD."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from local_operator.cvpr2027_common import REPORT_ROOT, canonical_json_bytes, write_json  # noqa: E402


COMPARE_FILES = [
    "statistics/power_summary.json",
    "statistics/statistics_design_validation.json",
    "statistics/CS_VALIDATION_VERDICT.json",
    "statistics/power_grid.csv",
    "statistics/familywise_error_simulation.csv",
    "statistics/cs_coverage_simulation.csv",
    "analysis/pilot_baseline_metrics.csv",
    "analysis/pilot_component_ablations.csv",
    "analysis/pilot_pairwise_comparisons.csv",
    "analysis/heterogeneity_summary.csv",
    "audits/IMAGE_QUALITY_AUDIT.json",
    "audits/relevant_irrelevant_balance.csv",
    "statistics/DETECTABILITY_VERDICT.json",
    "statistics/detectability_cv.csv",
    "audits/DUPLICATE_LEAKAGE_AUDIT.json",
    "evidence/model_certificates.json",
    "evidence/CLAIM_STATUS.json",
    "SCIENTIFIC_RED_TEAM.json",
]


def _semantic_value(path: Path) -> Any:
    if path.suffix == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    if path.suffix == ".csv":
        with path.open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))
    return path.read_bytes()


def _semantic_hash(path: Path) -> str:
    value = _semantic_value(path)
    payload = value if isinstance(value, bytes) else canonical_json_bytes(value)
    return hashlib.sha256(payload).hexdigest()


def _safe_extract(archive: tarfile.TarFile, destination: Path) -> None:
    base = destination.resolve()
    for member in archive.getmembers():
        target = (destination / member.name).resolve()
        if not target.is_relative_to(base):
            raise RuntimeError(f"unsafe git archive member: {member.name}")
    archive.extractall(destination)  # noqa: S202 - members validated above


def run(*, mode: str = "quick", output_root: Path = REPORT_ROOT) -> dict[str, Any]:
    started = time.perf_counter()
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPOSITORY_ROOT, check=True,
        capture_output=True, text=True,
    ).stdout.strip()
    output_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="certvic-c11-clean-") as temporary:
        temporary_root = Path(temporary)
        archive_path = temporary_root / "repository.tar"
        with archive_path.open("wb") as handle:
            subprocess.run(
                ["git", "archive", "--format=tar", "HEAD"],
                cwd=REPOSITORY_ROOT, check=True, stdout=handle,
            )
        clean_root = temporary_root / "checkout"
        clean_root.mkdir()
        with tarfile.open(archive_path, "r") as archive:
            _safe_extract(archive, clean_root)
        command = [
            sys.executable,
            "local_operator/run_cvpr2027_max_ceiling_cpu.py",
            "--mode", mode,
            "--force",
        ]
        completed = subprocess.run(
            command, cwd=clean_root, capture_output=True, text=True, timeout=21_600,
        )
        clean_output = clean_root / "reports/cvpr2027_max_ceiling"
        comparisons = []
        for relative in COMPARE_FILES:
            reference = output_root / relative
            reproduced = clean_output / relative
            if not reference.is_file() or not reproduced.is_file():
                comparisons.append({
                    "path": relative, "status": "MISSING",
                    "reference_present": reference.is_file(),
                    "reproduced_present": reproduced.is_file(),
                })
                continue
            reference_hash = _semantic_hash(reference)
            reproduced_hash = _semantic_hash(reproduced)
            comparisons.append({
                "path": relative,
                "status": "MATCH" if reference_hash == reproduced_hash else "MISMATCH",
                "reference_semantic_sha256": reference_hash,
                "reproduced_semantic_sha256": reproduced_hash,
            })
        mismatches = [row for row in comparisons if row["status"] != "MATCH"]
        result = {
            "schema": "certvic.cvpr2027.clean_reproduction.v1",
            "status": (
                "CLEAN_REPRODUCTION_COMPLETE"
                if completed.returncode == 0 and not mismatches
                else "CLEAN_REPRODUCTION_FAILED"
            ),
            "archived_commit": commit,
            "mode": mode,
            "command": command,
            "subprocess_returncode": completed.returncode,
            "subprocess_stdout_tail": completed.stdout[-2000:],
            "subprocess_stderr_tail": completed.stderr[-4000:],
            "comparisons": comparisons,
            "mismatch_count": len(mismatches),
            "runtime_seconds": time.perf_counter() - started,
            "paper_evidence": False,
        }
    write_json(output_root / "reproducibility/CLEAN_REPRODUCTION.json", result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["quick", "full"], default="quick")
    parser.add_argument("--output-root", type=Path, default=REPORT_ROOT)
    args = parser.parse_args(argv)
    result = run(mode=args.mode, output_root=args.output_root)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "CLEAN_REPRODUCTION_COMPLETE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
