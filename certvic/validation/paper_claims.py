"""Paper overclaim scanner."""

from __future__ import annotations

import re
from pathlib import Path

from certvic.validation.claims import FORBIDDEN_CLAIM_PHRASES


def scan_paper(path: str) -> dict:
    paper = Path(path)
    if not paper.exists():
        return {"passed": False, "errors": [f"paper path missing: {path}"], "warnings": []}
    text = paper.read_text(encoding="utf-8").lower()
    errors: list[str] = []
    warnings: list[str] = []
    for phrase in FORBIDDEN_CLAIM_PHRASES:
        if phrase in text:
            errors.append(f"forbidden phrase in paper: {phrase}")
    if "limitations" not in text:
        errors.append("paper missing limitations section")
    if "zero-cost" not in text and "zero cost" not in text:
        warnings.append("paper should mention zero-cost reproducibility")
    fake_result = re.search(r"(accuracy|consistency|gap)[^\n]{0,30}\b0\.\d{2,}\b", text)
    if fake_result and "[result required]" in text:
        errors.append("numeric-looking result appears near result placeholders")
    return {"passed": not errors, "errors": errors, "warnings": warnings}
