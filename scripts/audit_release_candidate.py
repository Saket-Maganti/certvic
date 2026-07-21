"""Build + audit a release-candidate manifest for the main_200 pilot (V7 prompt 11).

Classifies repo artifacts into release-safe / needs-relativization / cannot-release, attaches
sha256 for the canonical scored artifacts (from the result ledger), runs the project's privacy
/ path / secrets audit, and records data dependencies, model-weight policy, license blockers,
and expected runtimes. Releases nothing; only assesses readiness.

Hard rules honored: never package ADE20K pixels or model weights; never leak absolute local
home-directory paths; never include credentials/Kaggle tokens; never release unreviewed/raw
private files.
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from certvic.hashing import sha256_file  # noqa: E402
from certvic.io import read_json, write_json  # noqa: E402
from certvic.security.release_privacy_audit import audit as privacy_audit  # noqa: E402

OUT = REPO / "data/results/release_candidate_manifest.json"
LEDGER = REPO / "registry/results/main200_pilot_result_ledger.json"

# Canonical scored artifacts that are safe to release (derived numbers, no pixels, no paths).
RELEASE_SAFE_GLOBS = [
    "data/results/main_real_200/pilot_report*/pilot_result.json",
    "data/results/main_real_200/pilot_report*/pilot_result.md",
    "data/results/main_real_200/pilot_report*/presence_certification.json",
    "data/results/main_real_200/pilot_report*/presence_scores_summary.json",
    "data/results/main_real_200/pilot_report*/presence_by_edit_type.json",
    "data/results/main_real_200/pilot_report*/absent_object_control.json",
    "data/results/main_real_200/multimodel_pilot_summary.*",
    "data/results/main_real_200/tables/*",
    "data/results/main_real_200/score_summary_v2.json",
    "registry/results/main200_pilot_result_ledger.*",
    "registry/datasets/*.json",
]
# Path-bearing artifacts: safe ONLY after stripping absolute local home-directory paths.
NEEDS_RELATIVIZATION_GLOBS = [
    "data/results/main_real_200/pilot_eval_tasks_reviewed_v2.jsonl",
    "data/results/main_real_200/pilot_eval_taskitems_v2.jsonl",
    "data/results/main_real_200/residual_cue_review/*.csv",
    "data/results/main_real_200/review_iaa/*.csv",
    "data/results/main_real_200/mechanism_probes/*/tasks.jsonl",
    "data/results/main_real_200/prompt_ablations/*/tasks.jsonl",
]
# Never release.
CANNOT_RELEASE_GLOBS = [
    "data/edits/**/*.jpg", "ade20k_root/**", "ade20kdataset/**",
    "data/results/main_real_200/ade20k_sources.jsonl",
    "data/results/main_real_200/ade20k_masks.jsonl",
    "data/results/main_real_200/*rejected*.jsonl",
]


def _expand(globs: list[str]) -> list[str]:
    out: set[str] = set()
    for g in globs:
        for p in glob.glob(str(REPO / g), recursive=True):
            rp = Path(p)
            if rp.is_file():
                out.add(rp.relative_to(REPO).as_posix())
    return sorted(out)


def _ledger_hashes() -> dict[str, str]:
    if not LEDGER.exists():
        return {}
    led = read_json(LEDGER)
    h: dict[str, str] = {}
    for row in led.get("rows", []):
        for art in row.get("artifacts", {}).get("scoring", []) or []:
            if art.get("path") and art.get("sha256"):
                h[art["path"]] = art["sha256"]
    return h


def build() -> dict:
    safe = _expand(RELEASE_SAFE_GLOBS)
    needs_rel = _expand(NEEDS_RELATIVIZATION_GLOBS)
    cannot = _expand(CANNOT_RELEASE_GLOBS)

    ledger_h = _ledger_hashes()
    safe_entries = []
    for rel in safe:
        safe_entries.append({"path": rel,
                             "sha256": ledger_h.get(rel) or sha256_file(REPO / rel)})

    priv = privacy_audit(str(REPO))

    blockers = []
    if needs_rel:
        blockers.append({"blocker": "absolute_paths", "severity": "high",
                         "detail": f"{len(needs_rel)} task/sheet files embed absolute local "
                                   "home-directory paths; relativize before release.",
                         "files_sample": needs_rel[:5]})
    blockers.append({"blocker": "ade20k_pixels", "severity": "license",
                     "detail": "ADE20K image pixels must not be redistributed; release recipes "
                               "+ hashes, not pixels. Requires explicit license clearance + user request.",
                     "n_pixel_files": len([c for c in cannot if c.endswith('.jpg')])})

    release_ready = bool(priv["passed"]) and not any(b["severity"] == "high" for b in blockers)
    manifest = {
        "schema": "certvic.release_candidate.v1",
        "evidence_status": "RELEASE_READINESS_NON_EVIDENCE", "paper_evidence": False,
        "release_ready": release_ready,
        "release_ready_note": "release-safe set is clean; high-severity blockers must be cleared "
                              "(path relativization) before packaging." if not release_ready
                              else "privacy audit clean and no high-severity blockers.",
        "data_dependencies": {
            "required_to_reproduce_scoring": [
                "data/results/main_real_200/raw_predictions*/ (model predictions, sha256-locked)",
                "data/results/main_real_200/pilot_eval_taskitems_v2.jsonl",
                "data/edits/absent_object_control/pilot_eval_tasks_reviewed.jsonl",
            ],
            "required_to_reproduce_from_scratch": [
                "ADE20K (user obtains under its own license; pixels not redistributed)",
                "open VLM weights (downloaded by the user; never packaged)",
            ],
        },
        "model_weight_policy": "Model weights are NEVER packaged. Reproduction downloads open "
                               "weights (Qwen2.5-VL-7B, InternVL2-8B, LLaVA-OneVision-7B) from "
                               "their public hubs on free Kaggle.",
        "release_safe": {"n": len(safe_entries), "entries": safe_entries},
        "needs_path_relativization": {"n": len(needs_rel), "files": needs_rel},
        "cannot_release": {
            "n": len(cannot),
            "categories": {
                "ade20k_pixels": [c for c in cannot if c.endswith(".jpg") or "ade20k" in c.lower()][:10],
                "raw_or_rejected_private": [c for c in cannot if "rejected" in c],
            },
            "n_pixel_files": len([c for c in cannot if c.endswith(".jpg")]),
        },
        "privacy_audit": {
            "passed": priv["passed"], "n_total_findings": priv["n_total_findings"],
            "secrets_ok": priv["secrets"]["ok"],
            "command": "python3 -m certvic.security.release_privacy_audit --root .",
        },
        "license_provenance_blockers": [
            "ADE20K image pixels (redistribution not permitted; ship recipes + hashes)",
        ],
        "expected_runtimes": {
            "local_scoring_pilot_report_from_raw": "~seconds-to-1min per model on CPU (no model load)",
            "kaggle_vlm_eval_per_model": "~minutes (observed VLM latency ~1.5s/inference x ~300)",
            "kaggle_diffusion_edits": "see scale plan assumptions (~25s/edit on free T4)",
        },
        "blockers": blockers,
    }
    write_json(OUT, manifest)
    return manifest


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-fail", action="store_true",
                        help="do not exit non-zero when not release_ready")
    args = parser.parse_args(argv)
    m = build()
    print(json.dumps({"release_ready": m["release_ready"],
                      "privacy_passed": m["privacy_audit"]["passed"],
                      "n_release_safe": m["release_safe"]["n"],
                      "n_cannot_release": m["cannot_release"]["n"],
                      "n_blockers": len(m["blockers"])}, sort_keys=True))
    if not m["privacy_audit"]["passed"] and not args.no_fail:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
