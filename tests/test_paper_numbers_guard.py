"""Tests for the V2.6 paper auto-injection / number-provenance guard."""

from __future__ import annotations

import json
from pathlib import Path

from certvic.validation.paper_numbers_guard import (
    extract_paper_numbers,
    verify_paper,
    verify_paper_numbers,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

GOOD_WITH_MANIFEST = r"""\section{Results}
% main_results_table.tex has the gap (0.42) -- this is a comment, ignored.
Until an eligible run exists, every result is [RESULT REQUIRED].
We report at alpha = 0.05.
\input{tables/main_results_table.tex}
"""

FABRICATED = r"""\section{Results}
The certified consistency gap is 0.42 (95\% CS lower bound 0.31).
"""

FORBIDDEN = r"""\section{Results}
Our results show that all vlms fail catastrophically.
"""


def _write(tmp_path, text):
    p = tmp_path / "05_results.tex"
    p.write_text(text, encoding="utf-8")
    return p


def test_current_repo_results_section_passes():
    # The real placeholder-only results section must always pass the guard.
    result = verify_paper(repo_root=REPO_ROOT)
    assert result["passed"] is True
    assert result["n_violations"] == 0


def test_comments_and_constants_are_ignored(tmp_path):
    extracted = extract_paper_numbers(GOOD_WITH_MANIFEST)
    # The 0.42 lives inside a comment and must not be treated as untraced.
    assert extracted["untraced_numbers"] == []
    assert "tables/main_results_table.tex" in extracted["inputs"]


def test_fabricated_numbers_are_flagged(tmp_path):
    p = _write(tmp_path, FABRICATED)
    result = verify_paper_numbers(p)
    assert result["passed"] is False
    assert any("untraced number" in v for v in result["violations"])


def test_forbidden_phrase_flagged(tmp_path):
    p = _write(tmp_path, FORBIDDEN)
    result = verify_paper_numbers(p)
    assert result["passed"] is False
    assert any("forbidden claim phrase" in v for v in result["violations"])


def test_input_requires_manifest(tmp_path):
    p = _write(tmp_path, GOOD_WITH_MANIFEST)
    result = verify_paper_numbers(p)  # no manifest
    assert result["passed"] is False
    assert any("provenance manifest" in v for v in result["violations"])


def test_eligible_manifest_passes(tmp_path):
    p = _write(tmp_path, GOOD_WITH_MANIFEST)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "name": "main_gap",
                        "value": "0.42",
                        "run_id": "tiny_eval_qwen_v1",
                        "evidence_status": "OPEN_LOCAL_VLM_RESULT",
                        "provider_type": "open_local",
                        "artifact": "tables/main_results_table.tex",
                        "sha256": "deadbeef",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    result = verify_paper_numbers(p, manifest_path=manifest)
    assert result["passed"] is True, result["violations"]


def test_ineligible_manifest_blocks(tmp_path):
    p = _write(tmp_path, GOOD_WITH_MANIFEST)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "name": "main_gap",
                        "value": "0.42",
                        "run_id": "sim_run",
                        "evidence_status": "SIMULATED_ONLY",
                        "provider_type": "baseline",
                        "artifact": "tables/main_results_table.tex",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    result = verify_paper_numbers(p, manifest_path=manifest)
    assert result["passed"] is False
    assert any("ineligible" in v for v in result["violations"])
