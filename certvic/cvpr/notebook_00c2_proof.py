"""Execute the generated 00C2 route with synthetic adapters and non-evidence bytes."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from certvic.cvpr.notebook_builder import build_suite
from certvic.cvpr.synthetic_smoke import PROVIDERS, run as run_synthetic_smoke


ROUTE_MARKERS = (
    "verify_matrix_authorization(MATRIX_AUTHORIZATION)",
    "permission = verify_provider_permission(",
    "active_run_contract = build_run_contract(",
    '"-m", "certvic.cvpr.worker"',
    '"-m", "certvic.cvpr.package_run"',
    "KAGGLE_ZERO_EDIT_CANONICAL_RETURN_MISSING",
)


def execute_generated_route(root: str | Path) -> dict[str, Any]:
    """Prove that the generated route and the exercised runtime share one command order.

    The generated notebook is the source of the checked route.  The execution uses the
    same worker, package_run, canonical artifact builder, and strict gate with a mock
    adapter/runtime classification.  The result is always non-evidence.
    """
    out = Path(root)
    if out.exists() and any(out.iterdir()):
        raise ValueError("notebook proof root must be new or empty")
    out.mkdir(parents=True, exist_ok=True)
    notebook_root = out / "generated_notebooks"
    build_suite(notebook_root)
    notebook_path = notebook_root / "00C2_qwen2_5_vl_7b_real_model_two_item_smoke.ipynb"
    notebook_bytes = notebook_path.read_bytes()
    notebook = json.loads(notebook_bytes)
    source = "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook.get("cells", [])
        if cell.get("cell_type") == "code"
    )
    positions = [source.find(marker) for marker in ROUTE_MARKERS]
    if any(position < 0 for position in positions) or positions != sorted(positions):
        raise ValueError("generated 00C2 notebook no longer exposes the authorized route order")
    runtime_root = out / "executed_route"
    result = run_synthetic_smoke(runtime_root)
    proof_archives: dict[str, str] = {}
    for provider in PROVIDERS:
        source_archive = Path(result["archives"][provider])
        target = out / f"00C2_{provider}_synthetic_notebook_proof.zip"
        shutil.copyfile(source_archive, target)
        proof_archives[provider] = str(target)
    report = {
        "schema": "certvic.cvpr.notebook_00c2_synthetic_proof.v1",
        "status": "NOTEBOOK_DERIVED_SYNTHETIC_00C2_PASSED",
        "notebook": str(notebook_path),
        "notebook_sha256": hashlib.sha256(notebook_bytes).hexdigest(),
        "route_markers": list(ROUTE_MARKERS),
        "providers": list(PROVIDERS),
        "proof_archives": proof_archives,
        "strict_gate_status": result["status"],
        "strict_contract_verified": result["strict_contract_verified"],
        "synthetic_fixture": True,
        "paper_evidence": False,
    }
    (out / "notebook_00c2_synthetic_proof.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report
