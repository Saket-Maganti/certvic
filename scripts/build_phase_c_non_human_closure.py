#!/usr/bin/env python3
"""Generate truthful Phase C inventories, locks, blocker ledgers, and handoffs."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/non_human_closure"


def sha(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def write_json(path: Path, value: Any) -> None:
    write(path, json.dumps(value, indent=2, sort_keys=True))


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def artifact(relative: str, category: str, status: str) -> dict[str, Any]:
    path = ROOT / relative
    return {
        "path": relative,
        "category": category,
        "exists": path.is_file() or path.is_dir(),
        "size_bytes": path.stat().st_size if path.is_file() else "",
        "sha256": sha(path) or "",
        "status": status,
        "paper_evidence": False,
    }


def main() -> None:
    REPORT.mkdir(parents=True, exist_ok=True)
    authority = json.loads((ROOT / "configs/studies/certvic_confirmatory_authority.json").read_text())
    immutable = json.loads((ROOT / "configs/models/certvic_immutable_model_registry.json").read_text())
    historical = ROOT / "dist/certvic_historical_kaggleoutputs.zip"
    wheelhouse = ROOT / "kaggle_uploads/01_wheelhouse/certvic_offline_wheelhouse.zip"
    wheel_validation_path = REPORT / "wheelhouse_clean_linux_validation.json"
    wheel_validation = (
        json.loads(wheel_validation_path.read_text(encoding="utf-8"))
        if wheel_validation_path.is_file() else {}
    )
    phase_c_release = ROOT / "release/certvic_phase_c_pre_human_release.zip"

    inventory = [
        artifact("reports/non_human_closure/phase_c_baseline_validation/validation_results.json", "baseline", "PASS_15_OF_15"),
        artifact("reports/kaggle_execution_pack/CERTVIC_KAGGLE_READY_FOR_PHASE_B_HANDOFF.md", "phase_a", "PRESERVED"),
        artifact("reports/cpu_execution/CERTVIC_CPU_READY_FOR_GPU_HANDOFF.md", "phase_b", "PRESERVED"),
        artifact("kaggle_uploads/00_code/certvic_code_bundle.zip", "repository_bundle", "CREATED_AND_VALIDATED"),
        artifact("kaggle_uploads/00_code/certvic_configs_bundle.zip", "repository_bundle", "CREATED_AND_VALIDATED"),
        artifact("kaggle_uploads/00_code/certvic_execution_tools_bundle.zip", "repository_bundle", "CREATED_AND_VALIDATED"),
        artifact("kaggle_uploads/01_wheelhouse/certvic_offline_wheelhouse.zip", "external_runtime", "PROVISIONED_CLEAN_LINUX_CP310_VALIDATED" if wheel_validation.get("passed") is True else "PROVISIONED_REQUIRES_CLEAN_LINUX_INSTALL" if wheelhouse.is_file() else "EXTERNAL_PROVISIONING_HANDOFF_READY"),
        artifact("kaggle_uploads/02_snapshots/qwen2_5_vl_7b_snapshot.zip", "external_model_bytes", "EXTERNAL_BYTES_REQUIRED"),
        artifact("kaggle_uploads/02_snapshots/internvl2_8b_snapshot.zip", "external_model_bytes", "EXTERNAL_BYTES_REQUIRED"),
        artifact("kaggle_uploads/02_snapshots/llava_onevision_7b_snapshot.zip", "external_model_bytes", "EXTERNAL_BYTES_REQUIRED"),
        artifact("kaggle_uploads/03_smoke/certvic_real_two_item_smoke_bundle.zip", "real_smoke", "BLOCKED_NO_LICENSE_VERIFIED_ZERO_OVERLAP_TASKS"),
        artifact("data/runtime/00A_environment_bundle.zip", "return", "EXTERNAL_KAGGLE_RETURN_ABSENT"),
        artifact("data/runtime/00B_qwen2_5_vl_7b_snapshot_bundle.zip", "return", "EXTERNAL_KAGGLE_RETURN_ABSENT"),
        artifact("data/runtime/00B_internvl_8b_snapshot_bundle.zip", "return", "EXTERNAL_KAGGLE_RETURN_ABSENT"),
        artifact("data/runtime/00B_llava_onevision_7b_snapshot_bundle.zip", "return", "EXTERNAL_KAGGLE_RETURN_ABSENT"),
        artifact("data/runtime/00C2_qwen2_5_vl_7b_real_model_smoke.zip", "return", "EXTERNAL_KAGGLE_RETURN_ABSENT"),
        artifact("data/runtime/00C2_internvl_8b_real_model_smoke.zip", "return", "EXTERNAL_KAGGLE_RETURN_ABSENT"),
        artifact("data/runtime/00C2_llava_onevision_7b_real_model_smoke.zip", "return", "EXTERNAL_KAGGLE_RETURN_ABSENT"),
        artifact("data/studies/specificity_confirmatory_cvpr/candidates.jsonl", "confirmatory", "EXTERNAL_SOURCE_AND_GENERATION_REQUIRED"),
        artifact("data/studies/specificity_confirmatory_cvpr/qa_candidates.jsonl", "confirmatory", "UPSTREAM_CANDIDATES_ABSENT"),
        artifact("reports/v11_full_ceiling_audit/human_review_packet/certvic_v11_blinded_reviewer_bundle.zip", "historical_review", "READY_BLANK_HISTORICAL_FORENSIC_PACKET"),
        artifact("dist/certvic_historical_kaggleoutputs.zip", "two_part_distribution", "SEPARATE_HASH_LOCKED_ARCHIVE"),
        artifact("release/certvic_phase_c_pre_human_release.zip", "release", "DETERMINISTIC_PRE_HUMAN_RELEASE" if phase_c_release.is_file() else "BUILD_PENDING"),
    ]
    write_csv(REPORT / "CERTVIC_PHASE_C_INVENTORY.csv", list(inventory[0]), inventory)

    blockers = [
        {"id": "C-EXT-01", "category": "external_bytes", "artifact": "three immutable model snapshot ZIPs", "status": "BLOCKED", "next_action": "Run provisioning notebook 01 once per locked provider and return each ZIP.", "local_work_remaining": False},
        {"id": "C-EXT-02", "category": "licensed_external_bytes", "artifact": "two real zero-overlap smoke tasks", "status": "BLOCKED", "next_action": "Supply exactly two source/edit/mask task rows with verified licenses at local_inputs/smoke/real_smoke_tasks.jsonl, then run the canonical smoke-input builder command in the handoff.", "local_work_remaining": False},
        {"id": "C-PLAT-01", "category": "external_platform", "artifact": "00A and three 00B returns", "status": "BLOCKED", "next_action": "Follow reports/cpu_execution/CERTVIC_FIRST_GPU_WAVE_HANDOFF.md in CPU Kaggle sessions.", "local_work_remaining": False},
        {"id": "C-PLAT-02", "category": "external_platform_and_upstream", "artifact": "three genuine 00C2 returns", "status": "BLOCKED", "next_action": "After 00A/00B and real smoke input, issue pre-smoke permissions and run 00C2.", "local_work_remaining": False},
        {"id": "C-EXT-03", "category": "licensed_external_bytes", "artifact": "ADE20K validation source/license manifest and insertion assets", "status": "BLOCKED", "next_action": "Mount verified private source bytes and execute confirmatory generation handoff.", "local_work_remaining": False},
        {"id": "C-PLAT-03", "category": "external_platform_and_upstream", "artifact": "prospective candidate generation", "status": "BLOCKED", "next_action": "Run notebook 01 after strict real-smoke GO.", "local_work_remaining": False},
        {"id": "C-HUMAN-01", "category": "genuine_human_judgment", "artifact": "prospective two-rater review and adjudication", "status": "BLOCKED", "next_action": "Begins only after a genuine generated candidate packet exists.", "local_work_remaining": False},
        {"id": "C-GATE-01", "category": "upstream_scientific_gate", "artifact": "Main and second-domain execution", "status": "BLOCKED", "next_action": "Keep execution_allowed=false until genuine confirmatory and domain-specific gates pass.", "local_work_remaining": False},
    ]
    write_csv(REPORT / "CERTVIC_PHASE_C_BLOCKER_LEDGER.csv", list(blockers[0]), blockers)

    write(REPORT / "CERTVIC_PHASE_C_BASELINE.md", """# CertVIC Phase C baseline

The complete Phase B baseline runner executed 15 of 15 planned commands with status `PASS` before
Phase C changes. No canonical 00A, 00B, or 00C2 return exists. The repository contained no Linux
wheelhouse ZIP, no target model snapshot bytes, no legally verified two-item real smoke bundle, no
licensed unseen confirmatory source manifest, and no prospective generated candidates. Historical
`kaggleoutputs` bytes were present in the live checkout and are preserved under the explicit two-part
distribution contract.

Blockers were classified as scientific protocol, stale authority, external bytes, external platform,
genuine human judgment, and upstream scientific gates. The first two classes are repaired in Phase C;
the blocker ledger contains only the remaining external/human/gate boundaries. `paper_evidence=false`
and genuine `human_reviewed=true` count remains zero.""")

    freeze = {
        "schema": "certvic.phase_c.feature_freeze.v1",
        "status": "FROZEN",
        "effective_date": "2026-07-21",
        "protocol_authority_sha256": sha(ROOT / "configs/studies/certvic_confirmatory_authority.json"),
        "primary_analysis_sha256": authority["analysis_lock_sha256"],
        "allowed_repairs": ["real execution failure", "scientific-integrity defect", "security or privacy defect", "external-byte binding update without scientific-policy change"],
        "prohibited_without_versioned_amendment": ["new broad infrastructure layer", "new primary endpoint", "post-outcome threshold change", "gate weakening", "unregistered model or dataset substitution"],
        "amendment_policy": "Version, justify, hash-lock, and complete before prospective provider outputs.",
        "paper_evidence": False,
    }
    write_json(ROOT / "configs/execution/CERTVIC_FEATURE_FREEZE.json", freeze)
    write(REPORT / "CERTVIC_FEATURE_FREEZE.md", """# CertVIC feature freeze

Phase C freezes broad infrastructure expansion. New work is permitted only to repair an observed real
execution failure, scientific-integrity defect, security/privacy defect, or to bind newly returned
external bytes without changing scientific policy. Endpoint, threshold, selection, prompt, parser,
and gate changes require a prospective versioned amendment before provider outputs. The machine lock
is `configs/execution/CERTVIC_FEATURE_FREEZE.json`.""")

    write(REPORT / "CERTVIC_PROTOCOL_AUTHORITY.md", f"""# CertVIC protocol authority

The sole live prospective protocol is `{authority['authoritative_config_path']}`
(`{authority['authoritative_schema_version']}`, SHA-256 `{authority['protocol_sha256']}`). Its primary
analysis lock is `{authority['analysis_lock_path']}` (SHA-256 `{authority['analysis_lock_sha256']}`).
`configs/certvic_v11_protocol.yaml` is retained for immutable historical context and marked
`DEPRECATED_NOT_FOR_EXECUTION`; no doctor or paper promotion may select it. In-place amendments are
locked. A feasibility amendment must precede prospective outputs, increment the version, justify power,
and replace both hashes.""")

    write(REPORT / "CERTVIC_PRIMARY_ENDPOINT_AND_CERTIFICATE.md", """# Primary endpoint and certificate

`semantic_update_success` requires: original correct, edited correct, changed gold, and a model answer
that changes to the edited gold. `irrelevant_flip` requires unchanged gold and a changed normalized
answer. A never-updating model therefore receives zero relevant successes and cannot pass.

The primary fixed-sample certificate passes only when the one-sided exact lower bound for update
success is at least 0.50 and the one-sided exact upper bound for irrelevant flips is at most 0.10.
Familywise alpha 0.05 is Bonferroni-allocated over three models by two gates (1/120 per bound). Missing,
abstaining, and parser-failed relevant rows fail responsiveness; corresponding irrelevant rows count
as flips. The old accuracy-minus-change gap is secondary descriptive output only.""")

    write(REPORT / "CERTVIC_STATISTICAL_PREREGISTRATION.md", """# Statistical preregistration

Primary mode is fixed-sample, not sequential. There are 120 relevant and 120 irrelevant primary items,
plus 30+30 same-stratum reserves. At n=120 and alpha=1/120, at least 74 semantic-update successes are
needed for the exact lower bound to exceed 0.50; at most 4 irrelevant flips are compatible with an
exact upper bound at or below 0.10. All six bounds must pass for the all-model claim. Confidence
sequences are operational secondary displays only. Original/edited accuracy, raw answer change,
conditional update rate, transitions, failure taxonomy, family/category breakdowns, risk differences,
exact McNemar tests, and Holm-adjusted comparisons are prespecified reports.""")

    model_lines = ["# Immutable model identity lock", ""]
    for provider, model in immutable["models"].items():
        model_lines += [
            f"- `{provider}`: `{model['repository_id']}@{model['model_commit']}`; processor/tokenizer at the same immutable commit; license `{model['license']}`; architecture `{model['architecture']}`; remote bytes at lock `{model['remote_repository_bytes_at_lock']}`; local snapshot root hash **pending real bytes**.",
        ]
    model_lines += ["", f"Environment lock SHA-256: `{immutable['environment_lock']['sha256']}`. Mutable branch names do not authorize execution."]
    write(REPORT / "CERTVIC_MODEL_IDENTITY_LOCK.md", "\n".join(model_lines))

    categories = ["person", "car", "chair", "table", "dog", "cat", "tree", "building", "bicycle", "bus", "sofa", "television"]
    census = [{"category": category, "eligible_sources_observed": 0, "primary_relevant_quota": 10, "primary_irrelevant_quota": 10, "reserve_total_quota": 5, "status": "EXTERNAL_LICENSED_SOURCE_CENSUS_REQUIRED"} for category in categories]
    write_csv(REPORT / "CERTVIC_CONFIRMATORY_SOURCE_CENSUS.csv", list(census[0]), census)
    write(REPORT / "CERTVIC_CONFIRMATORY_FEASIBILITY.md", """# Confirmatory feasibility

Feasibility is not established because ADE20K validation bytes, an image-level license manifest, and
licensed insertion assets are absent. The frozen intended design is 120 relevant plus 120 irrelevant
primary items and 60 reserves across twelve categories. No quota is forced from zero observed supply.
The external generation notebook must first emit a source census; any shortage requires a versioned
pre-output amendment and new authority hashes.""")
    write_csv(REPORT / "CERTVIC_CONFIRMATORY_ZERO_OVERLAP_AUDIT.csv", ["candidate_id", "v1_overlap", "v2_30_overlap", "status"], [{"candidate_id": "NO_REAL_CANDIDATES", "v1_overlap": "NOT_COMPUTED", "v2_30_overlap": "NOT_COMPUTED", "status": "BLOCKED_EXTERNAL_SOURCE_AND_GENERATION"}])
    write(REPORT / "CERTVIC_CONFIRMATORY_POWER_AND_QUOTA_LOCK.md", """# Confirmatory power and quota lock

The pre-output quota lock is 240 primary (120 relevant, 120 irrelevant) and 60 reserve (30/30), with
twenty primary items per category split ten/ten. The exact decision boundaries at n=120 are 74 update
successes and 4 irrelevant flips under alpha=1/120. This is an operating-rule lock, not a claim that
the absent source pool is feasible. Source shortages trigger a documented prospective amendment.""")

    write(REPORT / "CERTVIC_CONFIRMATORY_GENERATION_VALIDATION.md", """# Confirmatory generation validation

Status: `CONFIRMATORY_GENERATION_EXTERNAL_EXECUTION_HANDOFF_COMPLETE`. No real candidate archive has
returned; generated files, geometry, corruption, duplicates, leakage, and pairing therefore remain
unobserved. The validated notebook and exact handoff are ready, and no model outcome may be used for
candidate filtering.""")
    write_csv(REPORT / "CERTVIC_CONFIRMATORY_AUTOMATED_QA.csv", ["candidate_id", "qa_status", "reason"], [{"candidate_id": "NO_REAL_CANDIDATES", "qa_status": "NOT_RUN", "reason": "external generation return absent"}])
    write_csv(REPORT / "CERTVIC_CONFIRMATORY_SALIENCE_MATCHING.csv", ["family", "items", "status"], [{"family": "relevant_vs_irrelevant", "items": 0, "status": "NOT_COMPUTED_EXTERNAL_GENERATION_PENDING"}])
    write(REPORT / "CERTVIC_CONFIRMATORY_MACHINE_DETECTABILITY.md", """# Confirmatory machine detectability

No candidate-wide machine detectability result exists because no real candidate pixels exist. The
locked diagnostic is machine-only, runs before provider outcomes, and cannot replace human validity.
The selected-set gate remains blocked until genuine review and exact selection.""")

    historical_packet = ROOT / "reports/v11_full_ceiling_audit/human_review_packet/certvic_v11_blinded_reviewer_bundle.zip"
    review_hashes = {
        "schema": "certvic.phase_c.review_packet_hashes.v1",
        "historical_forensic_packet": {"path": historical_packet.relative_to(ROOT).as_posix(), "sha256": sha(historical_packet), "pairs": {"intervention": 91, "v1_irrelevant_control": 94}, "status": "READY_BLANK_TEMPLATES"},
        "prospective_confirmatory_packet": {"path": None, "sha256": None, "pairs": 0, "status": "BLOCKED_EXTERNAL_GENERATION"},
        "genuine_human_reviewed_true_count": 0,
        "paper_evidence": False,
    }
    write_json(REPORT / "CERTVIC_REVIEW_PACKET_HASHES.json", review_hashes)
    review_rows = [
        {"track": "historical_intervention91", "pairs": 91, "raters_required": 2, "packet": historical_packet.relative_to(ROOT).as_posix(), "status": "READY_BLANK_HISTORICAL_FORENSIC_ONLY"},
        {"track": "historical_control94", "pairs": 94, "raters_required": 2, "packet": historical_packet.relative_to(ROOT).as_posix(), "status": "READY_BLANK_HISTORICAL_FORENSIC_ONLY"},
        {"track": "prospective_confirmatory", "pairs": 0, "raters_required": 2, "packet": "", "status": "BLOCKED_EXTERNAL_GENERATION_NO_PACKET"},
    ]
    write_csv(REPORT / "CERTVIC_REVIEW_PACKET_INVENTORY.csv", list(review_rows[0]), review_rows)
    write(ROOT / "data/annotations/human_review/README.md", """# Human-review boundary

No judgment is stored here. The existing blank historical forensic packet is at
`reports/v11_full_ceiling_audit/human_review_packet/` and separately covers 91 intervention and 94 V1
control pairs. A prospective packet must not be created until genuine generated candidates pass
automated QA; it must remain separate from historical review.""")
    write(REPORT / "CERTVIC_HUMAN_REVIEW_READY_HANDOFF.md", """# Human-review handoff

Status: `NOT_READY_FOR_GENUINE_PROSPECTIVE_HUMAN_REVIEW`. The historical blank forensic packet is ready
for two independent raters and covers 91 relevant and 94 V1 irrelevant pairs, but it cannot substitute
for prospective review. The prospective packet does not exist because real candidate generation has
not run. After that external return, run automated QA and packet construction, then use two independent
outcome-blind raters plus outcome-blind adjudication. Do not populate judgment fields by automation.

After genuine prospective review files exist, run:

```bash
python3 scripts/run_all_cpu_workflows.py --resume-after-human-review
```""")

    write(REPORT / "CERTVIC_WHEELHOUSE_EXTERNAL_EXECUTION_HANDOFF.md", """# Wheelhouse validation handoff

The Linux x86-64/CPython 3.10 wheel set is locally provisioned. Canonical output:
`kaggle_uploads/01_wheelhouse/certvic_offline_wheelhouse.zip`. Its clean Docker validation installs all
five provider/generation/analysis locks with `--no-index --find-links` and imports every runtime module;
the exact result is `reports/non_human_closure/wheelhouse_clean_linux_validation.json`. 00A must repeat
that check in a fresh Kaggle CPU session, accelerator off and Internet off, because 00A also binds the
Kaggle environment identity. The provisioning notebook remains a recovery route only.""")
    write(REPORT / "CERTVIC_SNAPSHOT_EXTERNAL_EXECUTION_HANDOFF.md", """# Snapshot provisioning handoff

Open `notebooks/kaggle/provisioning/01_build_certvic_model_snapshot_parameterized.ipynb` with Internet
on and accelerator off. Execute it three times with `PROVIDER` exactly `qwen2_5_vl_7b`, `internvl_8b`,
and `llava_onevision_7b`. Download, without renaming, `qwen2_5_vl_7b_snapshot.zip`,
`internvl2_8b_snapshot.zip`, and `llava_onevision_7b_snapshot.zip` to
`kaggle_uploads/02_snapshots/`. Validate each with `python3 -m certvic.cvpr.kaggle_bundle verify <ZIP>`;
then run `python3 scripts/run_all_cpu_workflows.py --resume`. The exact immutable revisions are Qwen
`cc594898137f460bfe9f0759e9844b3ce807cfb5`, InternVL
`6fb9ad6924f69424e57fab2ab061d707688f0296`, and LLaVA
`0d50680527681998e456c7b78950205bedd8a068`; model, processor, and tokenizer must remain on the
provider's same listed commit (including InternVL remote code).""")
    common_uploads = [
        ("kaggle_uploads/00_code/certvic_code_bundle.zip", "certvic/certvic-code", "/kaggle/input/certvic-code"),
        ("kaggle_uploads/00_code/certvic_configs_bundle.zip", "certvic/certvic-configs", "/kaggle/input/certvic-configs"),
        ("kaggle_uploads/00_code/certvic_execution_tools_bundle.zip", "certvic/certvic-execution-tools", "/kaggle/input/certvic-execution-tools"),
        ("kaggle_uploads/01_wheelhouse/certvic_offline_wheelhouse.zip", "certvic/certvic-offline-wheelhouse", "/kaggle/input/certvic-offline-wheelhouse"),
    ]
    upload_rows = "\n".join(
        f"| `{path}` | {ROOT.joinpath(path).stat().st_size if ROOT.joinpath(path).is_file() else 'ABSENT'} | "
        f"`{sha(ROOT / path) or 'ABSENT'}` | `{slug}` | `{mount}` |"
        for path, slug, mount in common_uploads
    )
    snapshot_rows = "\n".join(
        f"| `{provider}` | `kaggle_uploads/02_snapshots/{details['output']}` | "
        f"`{sha(ROOT / 'kaggle_uploads/02_snapshots' / details['output']) or 'ABSENT'}` | "
        f"`{details['dataset']}` |"
        for provider, details in {
            "qwen2_5_vl_7b": {"output": "qwen2_5_vl_7b_snapshot.zip", "dataset": "certvic/qwen2-5-vl-7b-snapshot"},
            "internvl_8b": {"output": "internvl2_8b_snapshot.zip", "dataset": "certvic/internvl2-8b-snapshot"},
            "llava_onevision_7b": {"output": "llava_onevision_7b_snapshot.zip", "dataset": "certvic/llava-onevision-7b-snapshot"},
        }.items()
    )
    write(ROOT / "reports/cpu_execution/CERTVIC_FIRST_GPU_WAVE_HANDOFF.md", f"""# CertVIC first Kaggle integrity wave handoff

00A and 00B are CPU integrity stages; neither loads a model nor performs inference. 00C2 is the first
genuine GPU model-load/inference stage and is not authorized by this handoff. Publish every ZIP as a
private Kaggle dataset, preserve its filename and SHA-256, use a fresh session, and disable Internet.

| Common upload | Bytes | SHA-256 | Dataset | Mount |
| --- | ---: | --- | --- | --- |
{upload_rows}

| Provider | Snapshot ZIP | SHA-256 | Dataset |
| --- | --- | --- | --- |
{snapshot_rows}

## Exact runs

| Run | Notebook / parameters | Accelerator | Return ZIP | Unchanged local destination |
| --- | --- | --- | --- | --- |
| 00A | `00A_certvic_code_and_environment_smoke.ipynb`; `STAGE=code_smoke`; `PROVIDER=all`; `EXPECTED_GPUS=0`; `USE_REAL_MODEL=false` | off | `00A_environment_bundle.zip` | `data/runtime/00A_environment_bundle.zip` |
| 00B Qwen | `00B_certvic_model_snapshot_smoke.ipynb`; `PROVIDER=qwen2_5_vl_7b`; exact locked commit | off | `00B_qwen2_5_vl_7b_snapshot_bundle.zip` | `data/runtime/00B_qwen2_5_vl_7b_snapshot_bundle.zip` |
| 00B InternVL | same notebook; `PROVIDER=internvl_8b`; exact locked commit | off | `00B_internvl_8b_snapshot_bundle.zip` | `data/runtime/00B_internvl_8b_snapshot_bundle.zip` |
| 00B LLaVA | same notebook; `PROVIDER=llava_onevision_7b`; exact locked commit | off | `00B_llava_onevision_7b_snapshot_bundle.zip` | `data/runtime/00B_llava_onevision_7b_snapshot_bundle.zip` |

Run 00A first. After its unchanged return validates locally, run the three isolated 00B sessions in
parallel or sequence. Attach exactly one provider snapshot to each 00B session. Do not set a mutable
revision, do not enable model loading, and do not rename a return. After each download run:

```bash
python3 scripts/run_all_cpu_workflows.py --resume
```

The resume verifies ZIP security, schemas, byte identities, the immutable model/processor contract,
and `paper_evidence=false`; it refuses partial matrices. Follow
`reports/non_human_closure/CERTVIC_REAL_SMOKE_EXTERNAL_EXECUTION_HANDOFF.md` only after the complete
00A/00B matrix and the licensed two-item smoke bundle exist.""")
    write(REPORT / "CERTVIC_REAL_SMOKE_EXTERNAL_EXECUTION_HANDOFF.md", """# Real-model smoke external handoff

The real two-item input cannot be built until two licensed, portable, zero-overlap task pairs exist.
Create the exact JSONL manifest with source/original/edited image paths, any required masks/assets,
expected original/edited answers, license IDs, provenance, and explicit V1/V2-30 zero-overlap proofs;
then run:

```bash
python3 -m certvic.cvpr.smoke_input_builder --task-manifest local_inputs/smoke/real_smoke_tasks.jsonl --output kaggle_uploads/03_smoke/certvic_real_two_item_smoke_bundle.zip
python3 -m certvic.cvpr.kaggle_bundle verify kaggle_uploads/03_smoke/certvic_real_two_item_smoke_bundle.zip
python3 scripts/run_all_cpu_workflows.py --resume
```

After valid 00A and all three 00B returns, the resume builds the byte-bound pre-smoke permission. Run
`00C2_certvic_real_model_two_item_smoke.ipynb` three times with providers `qwen2_5_vl_7b`,
`internvl_8b`, and `llava_onevision_7b`, T4 x2 (single-T4 fallback permitted), Internet off. Download
the unchanged returns to `data/runtime/00C2_<provider>_real_model_smoke.zip`, then run the same resume
command. No genuine smoke result is claimed before all three ZIPs pass strict local import.""")
    write(REPORT / "CERTVIC_CONFIRMATORY_GENERATION_EXTERNAL_EXECUTION_HANDOFF.md", """# Confirmatory generation external handoff

Prerequisites: strict all-provider 00C2 GO, verified private ADE20K validation source/license manifest,
licensed edit assets, the frozen authority/analysis locks, exclusion inventory, and the offline
wheelhouse. Create `local_inputs/confirmatory_generation_input_roles.json` with `control_files` keys
exactly `source_manifest`, `exclusion_inventory`, `generation_config`, `licenses`, `engine_policy`,
`seed_plan`, `shard_plan`, and `resume_ledger`, each pointing to its real frozen file. Then run:

```bash
python3 -m certvic.cvpr.confirmatory_input_builder --config local_inputs/confirmatory_generation_input_roles.json --output kaggle_uploads/05_confirmatory/certvic_confirmatory_generation_input.zip
python3 -m certvic.cvpr.kaggle_bundle verify kaggle_uploads/05_confirmatory/certvic_confirmatory_generation_input.zip
```

Publish it privately as `certvic/certvic-confirmatory-generation-input`, attach at
`/kaggle/input/certvic-confirmatory-generation-input`, and run
`notebooks/kaggle/cvpr/01_specificity_confirmatory_generation_T4x2.ipynb` with T4x2, Internet off.
Download `confirmatory_generation_return.zip` unchanged to
`local_inputs/generation_returns/specificity_confirmatory_cvpr/`, then run
`python3 scripts/run_all_cpu_workflows.py --resume`.""")

    write(REPORT / "CERTVIC_NON_HUMAN_CLOSURE_VALIDATION.md", """# Non-human closure validation

Validation is regenerated after the final test/guard/release pass. Scientific authority, metric,
certificate, deprecation, archive, and provisioning-notebook tests are present. Until the final pass,
this document makes no success claim about external runs, real smoke, generated candidates, or human
review.""")
    wheel_record = f"{wheelhouse.stat().st_size} bytes / `{sha(wheelhouse)}`" if wheelhouse.is_file() else "absent; external notebook ready"
    write(REPORT / "CERTVIC_NON_HUMAN_EXECUTION_FINAL_HANDOFF.md", f"""# CertVIC non-human execution final handoff

Statuses:

- `SCIENTIFIC_PROTOCOL_CORRECTED_AND_FROZEN`
- `ALL_LOCALLY_AVAILABLE_PROVISIONING_COMPLETE`
- `REAL_SMOKE_EXTERNAL_EXECUTION_HANDOFF_COMPLETE`
- `CONFIRMATORY_GENERATION_EXTERNAL_EXECUTION_HANDOFF_COMPLETE`
- `PAPER_EVIDENCE_FALSE`
- `GENUINE_HUMAN_REVIEWED_TRUE_COUNT_0`

Wheelhouse: {wheel_record}. Immutable model identities are locked. All three local snapshot roots
contain resumable partial downloads, but no complete validated snapshot ZIP exists. Real 00A/00B/00C2
returns and prospective candidate generation remain external. The
prospective human-review packet therefore does not exist and `CONFIRMATORY_PRE_HUMAN_PIPELINE_COMPLETE`
is not claimed.

Exact next action: run 00A using `reports/cpu_execution/CERTVIC_FIRST_GPU_WAVE_HANDOFF.md`; provision
the three immutable snapshots using `reports/non_human_closure/CERTVIC_SNAPSHOT_EXTERNAL_EXECUTION_HANDOFF.md`
before 00B. Local continuation is always
`python3 scripts/run_all_cpu_workflows.py --resume`.""")

    distribution = {
        "schema": "certvic.project_distribution.v1",
        "status": "TWO_PART_DISTRIBUTION_HASH_LOCKED",
        "main_project": {"archive_path": phase_c_release.relative_to(ROOT).as_posix(), "archive_sha256": sha(phase_c_release), "size": phase_c_release.stat().st_size if phase_c_release.is_file() else None, "historical_outputs_embedded": False},
        "historical_outputs": {"archive_path": historical.relative_to(ROOT).as_posix(), "archive_sha256": sha(historical), "size": historical.stat().st_size, "member_count": 47, "canonical_restore_root": "kaggleoutputs", "overwrite_policy": "IDENTICAL_ONLY_OTHERWISE_REFUSE"},
        "restore_script": "scripts/restore_historical_outputs.py",
        "paper_evidence": False,
    }
    write_json(ROOT / "PROJECT_DISTRIBUTION_MANIFEST.json", distribution)


if __name__ == "__main__":
    main()
