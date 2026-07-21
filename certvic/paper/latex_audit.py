"""Static LaTeX paper audit for camera-ready preparation."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from certvic.validation.paper_numbers_guard import verify_paper

REQUIRED_SECTIONS = ("01_intro.tex", "03_method.tex", "04_experiments.tex", "05_results.tex")


def audit_latex(paper_dir: str) -> dict:
    root = Path(paper_dir)
    tex_files = sorted(root.rglob("*.tex")) if root.exists() else []
    text = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in tex_files)
    includes = re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", text)
    missing_figures = [inc for inc in includes if not (root / inc).exists() and not (root / f"{inc}.pdf").exists()]
    missing_sections = [name for name in REQUIRED_SECTIONS if not (root / "sections" / name).exists()]
    guard = verify_paper(repo_root=root.parent if root.name == "paper" else Path("."))
    return {
        "paper_dir": paper_dir,
        "n_tex_files": len(tex_files),
        "missing_figures": missing_figures,
        "missing_sections": missing_sections,
        "paper_numbers_guard": guard,
        "compile_required": False,
        "fake_numbers_found": bool(guard.get("n_violations")),
        "passed": not missing_sections and not guard.get("n_violations"),
    }


def render_latex_audit(result: dict) -> str:
    return "\n".join(
        [
            "# LaTeX Audit",
            "",
            f"Passed: {result['passed']}",
            f"TeX files: {result['n_tex_files']}",
            f"Missing sections: {result['missing_sections']}",
            f"Missing figures: {result['missing_figures']}",
            f"Paper-number violations: {result['paper_numbers_guard'].get('n_violations')}",
            "Compile optional: yes",
            "",
        ]
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Audit paper LaTeX inputs")
    parser.add_argument("--paper-dir", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    result = audit_latex(args.paper_dir)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(render_latex_audit(result), encoding="utf-8")
    print(json.dumps({"out": args.out, "passed": result["passed"]}, sort_keys=True))


if __name__ == "__main__":
    main()

