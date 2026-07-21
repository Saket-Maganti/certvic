"""Camera-ready paper check wrapper."""

from __future__ import annotations

from certvic.paper.latex_audit import audit_latex


def build_paper_check(paper_dir: str) -> dict:
    result = audit_latex(paper_dir)
    result["camera_ready_checklist"] = [
        "Run paper number guard",
        "Confirm all figures exist",
        "Confirm result lockfile before injecting paper numbers",
        "Compile manually only when local LaTeX is available",
    ]
    return result

