"""Regression tests for bugs found in the V5 destructive audit.

Each test pins a specific claim-safety / leak-prevention hole that was found and
fixed during the destructive audit (see docs/V5_DESTRUCTIVE_AUDIT_REPORT.md and
docs/V5_AUDIT_FIXES_REPORT.md). These tests must fail on the pre-fix code and
pass after the fix. They run CPU-only, make no evidence claims, and download
nothing.
"""

from __future__ import annotations

import json

from certvic.metrics.certification_policy import DEFAULT_POLICY, evaluate_certification_policy
from certvic.security.release_privacy_audit import audit as release_privacy_audit
from certvic.validation.paper_numbers_guard import extract_paper_numbers, verify_paper_numbers
from certvic.validity.certificate_schema import BLOCKING_FIELDS
from certvic.validity.item_certificate import build_certificates


# --- Bug 1: certification policy must not leak the required status globally ---

def _policy_summary() -> dict:
    return {"n": 200, "by_task_family": {}, "parse_failure_rate": 0.0, "control_edit": {"spurious_flip_rate": 0.0}}


def test_certification_policy_does_not_leak_required_status_across_calls():
    summary = _policy_summary()
    cert_ok = {"confidence_sequence": {"available": True}, "lower_bound": 0.2}

    # Call once with a permissive custom policy that names a NON-evidence status as
    # the required one. Pre-fix this permanently widened the module-global allowlist.
    evil = {**DEFAULT_POLICY, "evidence_status_required": "GENERATED_EDIT_ONLY"}
    evaluate_certification_policy(
        summary, cert_ok, evil,
        {"evidence_statuses": ["GENERATED_EDIT_ONLY"], "provider_types": ["qwen_vl"]},
    )

    # A later DEFAULT-policy call with the same non-evidence status MUST still block.
    decision = evaluate_certification_policy(
        summary, cert_ok, dict(DEFAULT_POLICY),
        {"evidence_statuses": ["GENERATED_EDIT_ONLY"], "provider_types": ["qwen_vl"]},
    )
    assert decision["policy_passed"] is False
    assert any("evidence_status meets required" in e for e in decision["errors"])


def test_certification_policy_custom_required_still_accepts_that_status():
    # Sanity: the custom required status is accepted *within* the call that sets it.
    summary = _policy_summary()
    cert_ok = {"confidence_sequence": {"available": True}, "lower_bound": 0.2}
    policy = {**DEFAULT_POLICY, "evidence_status_required": "OPEN_LOCAL_VLM_RESULT"}
    decision = evaluate_certification_policy(
        summary, cert_ok, policy,
        {"evidence_statuses": ["OPEN_LOCAL_VLM_RESULT"], "provider_types": ["open_local"]},
    )
    assert decision["policy_passed"] is True


# --- Bug 2: paper number guard must not be bypassed by em-dashes / placeholders ---

def test_paper_guard_flags_number_on_emdash_line():
    tex = r"Our method achieves a gap of 0.42 --- a substantial margin over baselines."
    untraced = {n["value"] for n in extract_paper_numbers(tex)["untraced_numbers"]}
    assert "0.42" in untraced


def test_paper_guard_flags_number_sharing_line_with_placeholder():
    # A fabricated number must not ride along on a line that also has a placeholder.
    tex = "Final accuracy 0.913 TBD pending the full run."
    untraced = {n["value"] for n in extract_paper_numbers(tex)["untraced_numbers"]}
    assert "0.913" in untraced


def test_paper_guard_flags_leading_dot_decimal():
    tex = "We report a certified gap of .42 on the reviewed split."
    untraced = {n["value"] for n in extract_paper_numbers(tex)["untraced_numbers"]}
    assert ".42" in untraced


def test_paper_guard_verify_blocks_emdash_fabrication(tmp_path):
    p = tmp_path / "05_results.tex"
    p.write_text(r"The consistency gap is 0.42 --- well above threshold.", encoding="utf-8")
    result = verify_paper_numbers(p)
    assert result["passed"] is False
    assert any("untraced number" in v for v in result["violations"])


# --- Bug 3: detectable / unassessed edits must not be evidence-eligible ---

def _build_item(tmp_path, *, detectability: str | None) -> dict:
    tasks = tmp_path / "tasks.jsonl"
    edits = tmp_path / "edits.jsonl"
    review = tmp_path / "review.json"
    meta = {"leakage_status": "pass"}
    if detectability is not None:
        meta["detectability_status"] = detectability
    tasks.write_text(
        json.dumps({
            "item_id": "i1", "source_id": "s1", "edit_id": "e1",
            "task_family": "support_stability", "domain": "household", "metadata": meta,
        }, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    edits.write_text(json.dumps({"edit_id": "e1", "quality_gate_status": "pass"}, sort_keys=True) + "\n", encoding="utf-8")
    review.write_text(json.dumps({"items": [{
        "item_id": "i1", "visual_review_status": "pass", "human_answerability_status": "pass",
        "single_factor_status": "pass", "photorealism_status": "pass",
    }]}), encoding="utf-8")
    return build_certificates(str(tasks), str(edits), str(review), str(tmp_path / "certs.jsonl"), str(tmp_path / "report"))


def test_detectability_is_a_blocking_field():
    assert "detectability_status" in BLOCKING_FIELDS


def test_item_certificate_blocks_highly_detectable_edit(tmp_path):
    summary = _build_item(tmp_path, detectability="fail")
    assert summary["n_candidate_eligible"] == 0
    assert any("detectability_status" in r for r in summary["blocking_reasons"])


def test_item_certificate_unassessed_detectability_not_eligible(tmp_path):
    # Detectability never assessed (unknown) -> must not be evidence-eligible.
    summary = _build_item(tmp_path, detectability=None)
    assert summary["n_candidate_eligible"] == 0
    assert "incomplete_review_state" in summary["warnings"]


def test_item_certificate_eligible_only_when_detectability_passes(tmp_path):
    summary = _build_item(tmp_path, detectability="pass")
    assert summary["n_candidate_eligible"] == 1


# --- Bug 4: release privacy audit must text-scan the release dir, not just pixels ---

def test_release_audit_scans_release_dir_text_files(tmp_path):
    rel = tmp_path / "release" / "capsule"
    rel.mkdir(parents=True)
    (rel / "run_config.yaml").write_text(
        'dataset_root: /Users/example/private/ade20k\napi_key: "sk-AAAAAAAAAAAAAAAAAAAAAAAA"\n',
        encoding="utf-8",
    )
    result = release_privacy_audit(str(tmp_path), release_dir=str(rel))
    assert result["passed"] is False
    assert result["release_private_paths"]["n_findings"] >= 1
    assert result["release_secrets"]["n_secret_findings"] >= 1


def test_release_audit_clean_release_dir_passes(tmp_path):
    rel = tmp_path / "release" / "capsule"
    rel.mkdir(parents=True)
    (rel / "README.md").write_text("Recipe-first release. No pixels, no private paths.\n", encoding="utf-8")
    result = release_privacy_audit(str(tmp_path), release_dir=str(rel))
    assert result["passed"] is True
    assert result["release_private_paths"]["ok"] is True
    assert result["release_secrets"]["ok"] is True
