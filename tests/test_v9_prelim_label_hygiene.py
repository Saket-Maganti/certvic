from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORENSICS = ROOT / "data/results/main_real_200/v8_1_qwen_spurious_forensics"
V9 = ROOT / "data/results/main_real_200/v9_mega_upgrade"

_H = "HU" + "MAN_"
UNSAFE_PREFIXES = tuple(
    _H + suffix
    for suffix in (
        "PRELIMINARY_EVAL",
        "PATCH",
        "VALID",
        "OBJECT",
        "PROMPT",
        "PARSE",
        "IMAGE",
        "LOW",
    )
)


def _text_paths():
    for base in [FORENSICS, ROOT / "scripts", ROOT / "tests"]:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file() and path.suffix in {".md", ".json", ".csv", ".html", ".py", ".txt"} and "__pycache__" not in path.parts:
                yield path


def test_no_unsafe_human_prelim_labels_remain():
    hits = []
    for path in _text_paths():
        text = path.read_text(errors="ignore")
        for unsafe in UNSAFE_PREFIXES:
            if unsafe in text:
                hits.append((str(path.relative_to(ROOT)), unsafe))
    assert hits == []


def test_machine_triage_uses_codex_prelim_namespace_and_disclaimer():
    labels = json.loads((FORENSICS / "qwen_spurious_failed_12_prelim_labels.json").read_text())
    assert labels["label_authority"] == "CODEX_PRELIMINARY_EVAL"
    assert labels["human_validation_claimed"] is False
    assert labels["is_real_human_validation"] is False
    for row in labels["labels"]:
        assert row["preliminary_eval_authority"] == "CODEX_PRELIMINARY_EVAL"
        assert row["preliminary_label"].startswith("CODEX_PRELIM_")
        assert row["triage_code"].startswith("CODEX_PRELIM_")


def test_qwen_gate_and_paper_evidence_unchanged():
    go = json.loads((FORENSICS / "v8_1_go_no_go.json").read_text())
    spurious = json.loads((ROOT / "data/results/main_real_200/v8_upgrade/spurious_specificity_control_report.json").read_text())
    qwen = spurious["providers"]["qwen2_5_vl_7b"]
    assert qwen["flipped"] == 12
    assert qwen["n_items"] == 94
    assert qwen["gate_pass"] is False
    assert go["paper_evidence"] is False
    assert go["main500_should_start_now"] is False


def test_migration_report_records_no_human_validation_created():
    migration = json.loads((V9 / "prelim_label_hygiene_migration.json").read_text())
    assert migration["paper_evidence"] is False
    assert migration["real_human_validation_present"] is False
    assert migration["qwen_gate_unchanged"]["gate_pass"] is False
    assert migration["total_replacements"] > 0
