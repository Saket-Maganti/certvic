"""Fail-closed Phase C continuation entry points and synthetic end-to-end proofs."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _synthetic(out: Path, *, continuation: str) -> dict[str, Any]:
    from certvic.cvpr.synthetic_closure import run

    # Synthetic fixture rows carry their generated image paths through several
    # builders. Resolve once so a caller-supplied relative output directory is
    # never accidentally prefixed a second time by a downstream source root.
    out = out.resolve()
    result = run(out)
    return {
        "schema": "certvic.phase_c.continuation_proof.v1",
        "status": "SYNTHETIC_CONTINUATION_COMPLETE",
        "continuation": continuation,
        "synthetic_fixture": True,
        "paper_evidence": False,
        "human_reviewed": False,
        "closure_status": result["status"],
        "routes": sorted(result["routes"]),
        "artifact": str(out / "synthetic_closure_status.json"),
    }


def resume_after_human_review(
    root: str | Path = ".",
    *,
    config_path: str | Path = "configs/execution/certvic_confirmatory_post_review_pipeline.json",
    synthetic_fixture: bool = False,
    synthetic_out: str | Path | None = None,
) -> dict[str, Any]:
    base = Path(root).resolve()
    if synthetic_fixture:
        if synthetic_out is None:
            raise ValueError("synthetic continuation requires an explicit new output directory")
        return _synthetic(Path(synthetic_out), continuation="AFTER_HUMAN_REVIEW")
    from certvic.cvpr.post_review_pipeline import run

    return run(base, config_path)


def resume_after_confirmatory_returns(
    root: str | Path = ".",
    *,
    input_dir: str | Path | None = None,
    synthetic_fixture: bool = False,
    synthetic_out: str | Path | None = None,
) -> dict[str, Any]:
    base = Path(root).resolve()
    if synthetic_fixture:
        if synthetic_out is None:
            raise ValueError("synthetic continuation requires an explicit new output directory")
        return _synthetic(Path(synthetic_out), continuation="AFTER_CONFIRMATORY_RETURNS")
    from certvic.cvpr.after_runs import process

    returned = Path(input_dir) if input_dir else (
        base / "local_inputs/provider_returns/specificity_confirmatory_cvpr"
    )
    return process(returned, "specificity_confirmatory_cvpr", project_root=base)
