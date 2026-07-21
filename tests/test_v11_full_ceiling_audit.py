from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "v11_full_ceiling_audit"

REQUIRED = {
    "V11_AUDIT_SESSION_MANIFEST.md",
    "CERTVIC_REPOSITORY_FORENSIC_INVENTORY.md",
    "CERTVIC_CANONICAL_ARTIFACT_INDEX.md",
    "CERTVIC_EVIDENCE_LEDGER.csv",
    "CERTVIC_EVIDENCE_LEDGER.json",
    "CERTVIC_GATE_LEDGER.csv",
    "CERTVIC_BLOCKER_REGISTER.csv",
    "CERTVIC_CLAIM_LEDGER.md",
    "SOFTWARE_VALIDATION_AND_REPAIR_REPORT.md",
    "SCIENTIFIC_VALIDITY_AUDIT.md",
    "STATISTICAL_AUDIT_AND_POWER_PLAN.md",
    "QWEN_12_FAILURE_FORENSIC_AUDIT.md",
    "SPURIOUS_V2_AND_V2_LARGE_READINESS.md",
    "HUMAN_REVIEW_OPERATIONS_AND_BLINDING.md",
    "MAIN500_DESIGN_LOCK_AND_GO_NOGO.md",
    "SECOND_DOMAIN_DECISION.md",
    "MODEL_MATRIX_DECISION.md",
    "PAPER_AND_NOVELTY_AUDIT.md",
    "REVIEWER_RED_TEAM_V11.md",
    "REPRODUCIBILITY_AND_RELEASE_AUDIT.md",
    "VENUE_CEILING_AND_RESEARCH_ROADMAP.md",
    "V11_CHANGE_MANIFEST.csv",
    "V11_COMMAND_AND_EXIT_CODE_LOG.md",
    "V11_FINAL_VALIDATION.md",
    "CERTVIC_V11_MASTER_HANDOFF.md",
}

EVIDENCE_CLASSES = {
    "REAL_OBSERVED_EVIDENCE",
    "DERIVED_FROM_REAL_EVIDENCE",
    "DIAGNOSTIC_ONLY",
    "MACHINE_ASSISTED_PRELIMINARY",
    "HUMAN_REVIEW_PENDING",
    "PLANNED_NOT_EXECUTED",
    "SYNTHETIC_TEST_FIXTURE",
    "DEPRECATED_OR_STALE",
    "UNKNOWN_REQUIRES_AUDIT",
}

EVIDENCE_FIELDS = {
    "artifact_id",
    "artifact_path",
    "experiment_family",
    "model_provider",
    "dataset_domain",
    "run_tag",
    "item_count",
    "evidence_class",
    "raw_or_derived_status",
    "upstream_source",
    "sha256",
    "timestamp",
    "validation_status",
    "paper_claim_eligibility",
    "paper_evidence",
    "diagnostic_only",
    "human_reviewed",
    "known_limitations",
    "canonical_status",
}


def load_ledger() -> list[dict[str, object]]:
    return json.loads((OUT / "CERTVIC_EVIDENCE_LEDGER.json").read_text(encoding="utf-8"))


def test_required_v11_reports_exist_and_are_nonempty() -> None:
    missing = sorted(name for name in REQUIRED if not (OUT / name).is_file())
    assert not missing
    empty = sorted(name for name in REQUIRED if not (OUT / name).read_text(encoding="utf-8").strip())
    assert not empty
    assert (OUT / "SPURIOUS_V2_EXECUTION_CARD.md").is_file()
    assert (OUT / "V11_PAIRED_COMPARISONS.csv").is_file()
    assert (OUT / "SPURIOUS_V2_LOCAL_CANDIDATE_INVENTORY.csv").is_file()


def test_evidence_ledger_schema_vocabulary_and_csv_json_agree() -> None:
    ledger = load_ledger()
    assert len(ledger) >= 20
    assert all(set(row) == EVIDENCE_FIELDS for row in ledger)
    assert {str(row["evidence_class"]) for row in ledger} <= EVIDENCE_CLASSES
    assert len({str(row["artifact_id"]) for row in ledger}) == len(ledger)

    with (OUT / "CERTVIC_EVIDENCE_LEDGER.csv").open(encoding="utf-8", newline="") as handle:
        csv_rows = list(csv.DictReader(handle))
    assert [row["artifact_id"] for row in csv_rows] == [str(row["artifact_id"]) for row in ledger]
    assert set(csv_rows[0]) == EVIDENCE_FIELDS


def test_evidence_class_overrides_preserve_raw_truth() -> None:
    rows = {str(row["artifact_id"]): row for row in load_ledger()}
    for artifact_id in ("main91_task_manifest", "main91_taskitems", "v1_specificity_tasks"):
        assert rows[artifact_id]["evidence_class"] == "MACHINE_ASSISTED_PRELIMINARY"
        assert rows[artifact_id]["human_reviewed"] is False
        assert "override" in str(rows[artifact_id]["canonical_status"])

    for provider in ("qwen2_5_vl_7b", "internvl_8b", "llava_onevision_7b"):
        assert rows[f"main91_presence_{provider}"]["evidence_class"] == "REAL_OBSERVED_EVIDENCE"
        assert rows[f"v1_specificity_{provider}"]["evidence_class"] == "REAL_OBSERVED_EVIDENCE"
    assert rows["spurious_v2_retrospective_tasks"]["evidence_class"] == "DIAGNOSTIC_ONLY"
    assert rows["main500_protocol"]["evidence_class"] == "PLANNED_NOT_EXECUTED"


def test_paper_evidence_and_human_review_remain_false() -> None:
    ledger = load_ledger()
    assert all(row["paper_evidence"] is False for row in ledger)
    assert all(row["paper_claim_eligibility"] is False for row in ledger)
    assert all(row["human_reviewed"] is False for row in ledger)

    for path in OUT.rglob("*.json"):
        text = path.read_text(encoding="utf-8")
        assert '"paper_evidence": true' not in text.lower(), path
    for path in OUT.rglob("*.csv"):
        with path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        if rows and "paper_evidence" in rows[0]:
            assert all(row["paper_evidence"].lower() == "false" for row in rows), path


def test_v2_and_main500_claim_boundaries() -> None:
    v2 = (OUT / "SPURIOUS_V2_AND_V2_LARGE_READINESS.md").read_text(encoding="utf-8")
    main500 = (OUT / "MAIN500_DESIGN_LOCK_AND_GO_NOGO.md").read_text(encoding="utf-8")
    handoff = (OUT / "CERTVIC_V11_MASTER_HANDOFF.md").read_text(encoding="utf-8")
    assert "30/30" in v2 or "30 items" in v2
    assert "retrospective" in v2.lower()
    assert "0/3" in v2
    assert "NO-GO" in main500
    assert "execution_allowed_now=false" in main500
    assert "Main-500: **NO-GO**" in handoff
    assert "paper_evidence=false" in handoff


def test_gate_and_blocker_ledgers_cover_required_decisions() -> None:
    with (OUT / "CERTVIC_GATE_LEDGER.csv").open(encoding="utf-8", newline="") as handle:
        gates = {row["gate_name"]: row for row in csv.DictReader(handle)}
    assert gates["v1_qwen_specificity"]["status"] == "FAIL"
    assert gates["current_v2_independence"]["status"] == "FAIL_DIAGNOSTIC_ONLY"
    assert gates["human_validity"]["status"] == "BLOCKED"
    assert gates["main500_go"]["status"] == "BLOCKED"
    assert set(gates) >= {
        "raw_pair_parse_completeness",
        "evidence_class_eligibility",
        "historical_provider_revision_provenance",
        "current_v2_objective_geometry",
        "current_v2_detectability_diagnostic",
        "prospective_v2_three_model_joint",
        "v2_output_and_import_completeness",
        "v2_model_revision_lock",
        "v2_notebook_static_contract",
        "v2_private_package_integrity",
        "paper_bibliography_and_novelty_sources",
        "public_release_license",
    }

    with (OUT / "CERTVIC_BLOCKER_REGISTER.csv").open(encoding="utf-8", newline="") as handle:
        blockers = list(csv.DictReader(handle))
    assert {row["category"] for row in blockers} >= {
        "human validation",
        "scientific validity",
        "missing real evidence",
        "statistics",
        "reproducibility",
        "release defect",
    }


def test_change_manifest_covers_every_required_report() -> None:
    with (OUT / "V11_CHANGE_MANIFEST.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    paths = {row["artifact_path"] for row in rows}
    assert {
        f"reports/v11_full_ceiling_audit/{name}"
        for name in REQUIRED
    } <= paths
    assert all(row["paper_evidence"] == "False" for row in rows)


def test_v11_text_outputs_have_no_private_absolute_paths() -> None:
    for suffix in ("*.md", "*.csv", "*.json"):
        for path in OUT.rglob(suffix):
            text = path.read_text(encoding="utf-8")
            assert "/Users/" not in text, path
    top_level = "\n".join(path.read_text(encoding="utf-8") for path in OUT.glob("*.md"))
    assert "<PROJECT_ROOT>" in top_level


def test_pairwise_comparison_contract() -> None:
    with (OUT / "V11_PAIRED_COMPARISONS.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 3
    assert {row["n"] for row in rows} == {"94"}
    assert {row["analysis_status"] for row in rows} == {"retrospective_exploratory"}
    assert {row["paper_evidence"] for row in rows} == {"False"}


def test_candidate_inventory_and_execution_card_are_operational() -> None:
    with (OUT / "SPURIOUS_V2_LOCAL_CANDIDATE_INVENTORY.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 94
    assert sum(row["decision"] == "retained_retrospective_diagnostic" for row in rows) == 30
    assert all(row["prospective_confirmatory_eligible"] == "False" for row in rows)
    card = (OUT / "SPURIOUS_V2_EXECUTION_CARD.md").read_text(encoding="utf-8")
    for token in (
        "certvic_kaggle_main200_bundle.zip",
        "certvic_spurious_v2_control.zip",
        "GPU T4 x2",
        "exactly 60 merged rows",
        "MODEL_REVISION",
        "import_v9_spurious_v2_outputs.py",
        "DIAGNOSTIC_ONLY",
    ):
        assert token in card
