"""End-to-end tiny real-pilot orchestrator (no VLM inference).

Chains: pilot readiness -> manifests -> label policy report -> selection ->
edit planning -> task preview -> pilot plan report -> tiny edit generation ->
quality report -> task materialization -> visual review sheet export.

Requires a user-supplied local ADE20K root. Downloads nothing, runs no GPU jobs,
runs no VLM inference, and makes no evidence claims. `--dry-run` inspects only.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from certvic.config import load_config
from certvic.data.ade20k_adapter import build_ade20k_manifests
from certvic.data.apply_visual_review import apply_visual_review  # noqa: F401 (kept for parity / future use)
from certvic.data.label_policy_report import build_label_policy_report
from certvic.data.materialize_tasks import materialize_tasks
from certvic.data.pilot_readiness import build_pilot_readiness_report
from certvic.data.preview_tasks import build_task_preview
from certvic.data.select_pilot_items import select_pilot_items
from certvic.edit.engines import batch_generate
from certvic.edit.plan_edits import build_edit_plan
from certvic.edit.quality_report import build_quality_report
from certvic.io import write_json
from certvic.reporting.pilot_plan_report import build_pilot_plan_report
from certvic.validation.export_visual_review import export_visual_review

# Stages up to and including this index run during --dry-run.
DRY_RUN_LAST_STAGE = "label_policy_report"


def _p(out: Path, *parts: str) -> str:
    path = out.joinpath(*parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    return str(path)


def run_tiny_pilot(config_path: str, ade20k_root: str, out_dir: str, max_items: int = 20, seed: int = 0, dry_run: bool = False, force: bool = False) -> dict:
    config = load_config(config_path)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    label_policy = config.get("label_policy")
    sel_cfg = config.get("pilot_selection", {}) or {}

    status_path = out / "stage_status.json"
    status: dict = json.loads(status_path.read_text(encoding="utf-8")) if status_path.exists() and not force else {"stages": {}}
    command_log: list[str] = []

    paths = {
        "sources": _p(out, "ade20k_sources.jsonl"),
        "masks": _p(out, "ade20k_masks.jsonl"),
        "label_policy_report": _p(out, "label_policy_report"),
        "selection": _p(out, "pilot_selection.jsonl"),
        "selection_summary": _p(out, "pilot_selection_summary.json"),
        "edit_plan": _p(out, "pilot_edit_plan.jsonl"),
        "edit_plan_summary": _p(out, "pilot_edit_plan_summary.json"),
        "edit_plan_rejected": _p(out, "pilot_edit_plan_rejected.jsonl"),
        "task_preview": _p(out, "pilot_task_preview.jsonl"),
        "task_preview_summary": _p(out, "pilot_task_preview_summary.json"),
        "plan_report": _p(out, "pilot_plan_report"),
        "edits_dir": _p(out, "edits"),
        "generated_edits": _p(out, "pilot_generated_edits.jsonl"),
        "generated_rejected": _p(out, "pilot_generated_rejected.jsonl"),
        "generation_summary": _p(out, "pilot_generation_summary.json"),
        "quality_report": _p(out, "tiny_edit_quality_report"),
        "eval_tasks": _p(out, "pilot_eval_tasks_tiny.jsonl"),
        "eval_tasks_summary": _p(out, "pilot_eval_tasks_tiny_summary.json"),
        "review_sheet": _p(out, "visual_review_sheet.csv"),
    }

    def stage(name: str, fn, command: str):
        command_log.append(command)
        if status["stages"].get(name, {}).get("status") == "completed" and not force:
            return status["stages"][name]
        start = time.time()
        try:
            result = fn()
            entry = {"status": "completed", "seconds": round(time.time() - start, 3), "result_keys": sorted(result.keys()) if isinstance(result, dict) else None}
        except Exception as exc:  # record and stop the chain cleanly
            entry = {"status": "failed", "error": f"{type(exc).__name__}: {exc}"}
        status["stages"][name] = entry
        return entry

    stages_run: list[str] = []

    # 1. readiness
    stages_run.append("pilot_readiness")
    stage("pilot_readiness", lambda: build_pilot_readiness_report(config_path, ade20k_root, _p(out, "readiness"), dry_run=True),
          f"python3 -m certvic.data.pilot_readiness --config {config_path} --ade20k-root {ade20k_root} --dry-run --out-dir {out}/readiness")

    # 2. manifests
    stages_run.append("manifests")
    stage("manifests", lambda: build_ade20k_manifests(ade20k_root, paths["sources"], paths["masks"], max_items=max(50, max_items * 5)),
          f"python3 -m certvic.data.ade20k_adapter --ade20k-root {ade20k_root} --out-sources {paths['sources']} --out-masks {paths['masks']}")

    # 3. label policy report
    stages_run.append("label_policy_report")
    stage("label_policy_report", lambda: build_label_policy_report(paths["masks"], label_policy, paths["label_policy_report"]),
          f"python3 -m certvic.data.label_policy_report --masks {paths['masks']} --policy {label_policy} --out-dir {paths['label_policy_report']}")

    next_commands = _remaining_commands(paths, config_path, label_policy, max_items, seed)

    if not dry_run:
        # 4. selection
        stages_run.append("selection")
        stage("selection", lambda: select_pilot_items(
            paths["sources"], paths["masks"], paths["selection"], target=max_items, seed=seed,
            summary_out=paths["selection_summary"], label_policy_path=label_policy,
            allowed_task_families=config.get("allowed_task_families"),
            min_mask_area_fraction=sel_cfg.get("min_mask_area_fraction"),
            max_mask_area_fraction=sel_cfg.get("max_mask_area_fraction"),
            require_target=False,
        ), "python3 -m certvic.data.select_pilot_items ...")

        # 5. edit planning
        stages_run.append("edit_planning")
        stage("edit_planning", lambda: build_edit_plan(
            paths["selection"], paths["edit_plan"], paths["edit_plan_summary"], seed=seed,
            rejected_out=paths["edit_plan_rejected"], label_policy_path=label_policy,
        ), "python3 -m certvic.edit.plan_edits ...")

        # 6. task preview
        stages_run.append("task_preview")
        stage("task_preview", lambda: build_task_preview(paths["edit_plan"], paths["task_preview"], paths["task_preview_summary"]),
              "python3 -m certvic.data.preview_tasks ...")

        # 7. pilot plan report
        stages_run.append("pilot_plan_report")
        stage("pilot_plan_report", lambda: build_pilot_plan_report(
            paths["selection"], paths["edit_plan"], paths["task_preview"], paths["plan_report"],
        ), "python3 -m certvic.reporting.pilot_plan_report ...")

        # 8. tiny edit generation
        stages_run.append("edit_generation")
        stage("edit_generation", lambda: batch_generate(
            paths["edit_plan"], paths["edits_dir"], paths["generated_edits"], paths["generated_rejected"],
            paths["generation_summary"], max_items=max_items, seed=seed, resume=True,
        ), "python3 -m certvic.edit.engines ...")

        # 9. quality report
        stages_run.append("quality_report")
        stage("quality_report", lambda: build_quality_report(paths["generated_edits"], paths["generated_rejected"], paths["quality_report"]),
              "python3 -m certvic.edit.quality_report ...")

        # 10. materialization
        stages_run.append("materialization")
        stage("materialization", lambda: materialize_tasks(paths["task_preview"], paths["generated_edits"], paths["eval_tasks"], paths["eval_tasks_summary"]),
              "python3 -m certvic.data.materialize_tasks ...")

        # 11. visual review sheet
        stages_run.append("visual_review_sheet")
        stage("visual_review_sheet", lambda: {"rows": export_visual_review(paths["eval_tasks"], paths["generated_edits"], paths["review_sheet"], max_items=max_items, seed=seed)},
              "python3 -m certvic.validation.export_visual_review ...")

    write_json(str(status_path), status)
    (out / "command_log.txt").write_text("\n".join(command_log) + "\n", encoding="utf-8")
    zero_cost_audit = {
        "dry_run": dry_run,
        "downloads_attempted": False,
        "gpu_required": False,
        "vlm_inference_run": False,
        "paid_services": False,
        "evidence_status": "PIPELINE_NON_EVIDENCE",
    }
    write_json(_p(out, "zero_cost_audit.json"), zero_cost_audit)

    completed = [name for name, entry in status["stages"].items() if entry.get("status") == "completed"]
    failed = [name for name, entry in status["stages"].items() if entry.get("status") == "failed"]
    summary = {
        "config": config_path,
        "ade20k_root": ade20k_root,
        "out_dir": out_dir,
        "dry_run": dry_run,
        "max_items": max_items,
        "stages_attempted": stages_run,
        "stages_completed": completed,
        "stages_failed": failed,
        "next_commands": next_commands if dry_run else [],
        "zero_cost_audit": zero_cost_audit,
        "evidence_status": "PIPELINE_NON_EVIDENCE",
    }
    write_json(_p(out, "tiny_pilot_summary.json"), summary)
    return summary


def _remaining_commands(paths, config_path, label_policy, max_items, seed) -> list[str]:
    return [
        f"python3 -m certvic.data.select_pilot_items --sources {paths['sources']} --masks {paths['masks']} --out {paths['selection']} --target {max_items} --label-policy {label_policy} --allow-partial",
        f"python3 -m certvic.edit.plan_edits --selection {paths['selection']} --out {paths['edit_plan']} --summary-out {paths['edit_plan_summary']} --label-policy {label_policy}",
        f"python3 -m certvic.data.preview_tasks --edit-plan {paths['edit_plan']} --out {paths['task_preview']} --summary-out {paths['task_preview_summary']}",
        f"python3 -m certvic.edit.engines --edit-plan {paths['edit_plan']} --out-dir {paths['edits_dir']} --out-manifest {paths['generated_edits']} --rejected-out {paths['generated_rejected']} --summary-out {paths['generation_summary']} --max-items {max_items}",
        f"python3 -m certvic.data.materialize_tasks --task-preview {paths['task_preview']} --generated-edits {paths['generated_edits']} --out {paths['eval_tasks']} --summary-out {paths['eval_tasks_summary']}",
        f"python3 -m certvic.validation.export_visual_review --tasks {paths['eval_tasks']} --generated-edits {paths['generated_edits']} --out {paths['review_sheet']} --max-items {max_items} --seed {seed}",
    ]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="CertVIC tiny real-pilot orchestrator (no VLM inference)")
    parser.add_argument("--config", required=True)
    parser.add_argument("--ade20k-root", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--max-items", type=int, default=20)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    summary = run_tiny_pilot(args.config, args.ade20k_root, args.out_dir, max_items=args.max_items, seed=args.seed, dry_run=args.dry_run, force=args.force)
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
