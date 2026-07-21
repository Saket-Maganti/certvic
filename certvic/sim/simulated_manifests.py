"""Synthetic CertVIC manifests for simulation-only pre-run stress tests."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from certvic.io import load_model_jsonl, write_json, write_jsonl
from certvic.metrics.score_predictions import score_predictions
from certvic.metrics.summary import summarize_pair_scores
from certvic.schema import PairScore, PredictionRecord, TaskItem
from certvic.sim import SIMULATION_EVIDENCE_STATUS
from certvic.sim.outcome_models import BUILTIN_SCENARIOS, generate_outcome


TASK_FAMILIES = [
    "support_stability",
    "affordance_reachability",
    "occlusion_safety",
    "control_irrelevant",
]
DOMAINS = ["household", "driving"]
EDIT_TYPES_BY_FAMILY = {
    "support_stability": "displace",
    "affordance_reachability": "remove",
    "occlusion_safety": "occlude",
    "control_irrelevant": "control_irrelevant",
}
REQUIRED_CHANGE_BY_FAMILY = {
    "support_stability": "change",
    "affordance_reachability": "change",
    "occlusion_safety": "no_change",
    "control_irrelevant": "no_change",
}


def build_synthetic_run(out_dir: str | Path, scenario: str, n_items: int, seed: int) -> dict:
    if scenario not in BUILTIN_SCENARIOS:
        raise ValueError(f"Unknown simulation scenario: {scenario}")
    if n_items <= 0:
        raise ValueError("n_items must be positive")

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    run_id = f"sim_{scenario}_seed_{seed}_n_{n_items}"
    tasks = [_task_record(index, scenario, seed, run_id) for index in range(n_items)]
    predictions = _prediction_records(tasks, scenario=scenario, seed=seed, run_id=run_id)

    tasks_path = out / "simulated_tasks.jsonl"
    preds_path = out / "simulated_predictions.jsonl"
    scores_path = out / "simulated_pair_scores.jsonl"
    metadata_path = out / "simulated_run_metadata.json"
    config_path = out / "scenario_config.json"

    write_jsonl(tasks_path, tasks)
    write_jsonl(preds_path, predictions)
    scores = score_predictions(str(tasks_path), str(preds_path))
    for score in scores:
        score.metadata.update(_simulation_metadata(scenario=scenario, seed=seed))
        score.notes = "SIMULATED_ONLY; not real data, not model evidence, not for paper claims."
    write_jsonl(scores_path, scores)
    loaded_scores = load_model_jsonl(scores_path, PairScore)
    summary = summarize_pair_scores(loaded_scores)
    metadata = {
        "run_id": run_id,
        "scenario": scenario,
        "n_items": n_items,
        "seed": seed,
        "created_utc": datetime(2026, 6, 22, tzinfo=timezone.utc).isoformat(),
        "outputs": {
            "tasks": str(tasks_path),
            "predictions": str(preds_path),
            "pair_scores": str(scores_path),
        },
        "summary": summary,
        **_simulation_metadata(scenario=scenario, seed=seed),
    }
    scenario_config = {
        "scenario": scenario,
        "n_items": n_items,
        "seed": seed,
        "task_families": TASK_FAMILIES,
        "domains": DOMAINS,
        "evidence_status": SIMULATION_EVIDENCE_STATUS,
        "simulated": True,
        "zero_cost": True,
        "not_for_paper_claims": True,
    }
    write_json(metadata_path, metadata)
    write_json(config_path, scenario_config)
    return {
        "out_dir": str(out),
        "run_id": run_id,
        "scenario": scenario,
        "n_items": n_items,
        "seed": seed,
        "tasks_path": str(tasks_path),
        "predictions_path": str(preds_path),
        "scores_path": str(scores_path),
        "metadata_path": str(metadata_path),
        "scenario_config_path": str(config_path),
        "summary": summary,
        **_simulation_metadata(scenario=scenario, seed=seed),
    }


def _task_record(index: int, scenario: str, seed: int, run_id: str) -> dict:
    family = TASK_FAMILIES[index % len(TASK_FAMILIES)]
    domain = DOMAINS[(index // len(TASK_FAMILIES)) % len(DOMAINS)]
    edit_type = EDIT_TYPES_BY_FAMILY[family]
    required_change = REQUIRED_CHANGE_BY_FAMILY[family]
    answer_original = "yes"
    answer_edited = "no" if required_change == "change" else "yes"
    item_id = f"sim_{index:06d}"
    source_id = f"sim_source_{index:06d}"
    mask_id = f"sim_mask_{index:06d}"
    return {
        "item_id": item_id,
        "source": {
            "source_id": source_id,
            "source_name": "CertVIC simulation-only source",
            "source_url_or_pointer": f"simulated://source/{source_id}",
            "local_path": None,
            "sha256": None,
            "license_category": "pointer_only",
            "license_text": None,
            "redistribution_allowed": False,
            "notes": "Synthetic simulation-only record; contains no real pixels.",
        },
        "mask": {
            "mask_id": mask_id,
            "source_id": source_id,
            "mask_path": f"simulated://mask/{mask_id}",
            "object_label": "simulated_object",
            "bbox_xyxy": [1, 1, 5, 5],
            "mask_sha256": None,
            "method": "simulation_only",
            "quality_notes": "Synthetic mask placeholder.",
            "label_id": index % 150,
            "annotation_path": None,
            "mask_area_fraction": 0.10,
            "metadata": _simulation_metadata(scenario=scenario, seed=seed),
        },
        "edit": {
            "edit_id": f"sim_edit_{index:06d}",
            "source_id": source_id,
            "mask_id": mask_id,
            "edit_type": edit_type,
            "task_family": family,
            "domain": domain,
            "seed": seed,
            "params": {"simulated": True, "scenario": scenario, "zero_cost": True},
            "expected_effect": "Synthetic simulation-only expected effect.",
            "single_factor": True,
            "edited_image_path": f"simulated://edited/{item_id}",
            "edited_sha256": None,
        },
        "original_image_path": f"simulated://original/{item_id}",
        "edited_image_path": f"simulated://edited/{item_id}",
        "question_original": "Is the relevant condition satisfied? Respond with exactly one token: yes or no.",
        "question_edited": "Is the relevant condition satisfied? Respond with exactly one token: yes or no.",
        "answer_original": answer_original,
        "answer_edited": answer_edited,
        "required_change": required_change,
        "answer_format": "yes_no",
        "task_family": family,
        "domain": domain,
        "split": "simulation",
        "metadata": {
            **_simulation_metadata(scenario=scenario, seed=seed),
            "run_id": run_id,
            "edit_type": edit_type,
            "not_runnable_real_eval": True,
        },
    }


def _prediction_records(tasks: list[dict], scenario: str, seed: int, run_id: str) -> list[dict]:
    predictions = []
    timestamp = datetime(2026, 6, 22, tzinfo=timezone.utc).isoformat()
    for index, task in enumerate(tasks):
        outcome = generate_outcome(_task_outcome_view(task), scenario=scenario, seed=seed, index=index)
        base = {
            "run_id": run_id,
            "item_id": task["item_id"],
            "provider_name": "certvic_simulator",
            "provider_type": "baseline",
            "model_name": f"simulated_{scenario}",
            "model_version": "v2.1",
            "timestamp_utc": timestamp,
            "metadata": {
                **_simulation_metadata(scenario=scenario, seed=seed),
                "provider_evidence_status": SIMULATION_EVIDENCE_STATUS,
                "behavior_note": outcome.behavior_note,
                "not_real_model_output": True,
            },
        }
        predictions.append(
            {
                **base,
                "image_variant": "original",
                "prompt": task["question_original"],
                "raw_output": outcome.raw_original,
                "parsed_answer": outcome.parsed_original,
                "parse_confidence": outcome.parse_confidence,
                "parse_ok": outcome.parse_ok,
                "latency_s": 0.0,
            }
        )
        predictions.append(
            {
                **base,
                "image_variant": "edited",
                "prompt": task["question_edited"],
                "raw_output": outcome.raw_edited,
                "parsed_answer": outcome.parsed_edited,
                "parse_confidence": outcome.parse_confidence,
                "parse_ok": outcome.parse_ok,
                "latency_s": 0.0,
            }
        )
    return predictions


def _task_outcome_view(task: dict) -> dict:
    return {
        "item_id": task["item_id"],
        "answer_original": task["answer_original"],
        "answer_edited": task["answer_edited"],
        "required_change": task["required_change"],
        "task_family": task["task_family"],
        "domain": task["domain"],
        "edit_type": task["edit"]["edit_type"],
    }


def validate_synthetic_artifacts(tasks_path: str, predictions_path: str, scores_path: str) -> dict:
    tasks = load_model_jsonl(tasks_path, TaskItem)
    predictions = load_model_jsonl(predictions_path, PredictionRecord)
    scores = load_model_jsonl(scores_path, PairScore)
    statuses = {
        *(task.metadata.get("evidence_status", "") for task in tasks),
        *(pred.metadata.get("provider_evidence_status", "") for pred in predictions),
        *(score.metadata.get("evidence_status", "") for score in scores),
    }
    return {
        "tasks": len(tasks),
        "predictions": len(predictions),
        "scores": len(scores),
        "all_simulated_only": statuses == {SIMULATION_EVIDENCE_STATUS},
        "evidence_statuses": sorted(statuses),
    }


def _simulation_metadata(scenario: str, seed: int) -> dict:
    return {
        "evidence_status": SIMULATION_EVIDENCE_STATUS,
        "simulated": True,
        "simulation_scenario": scenario,
        "simulation_seed": seed,
        "zero_cost": True,
        "not_for_paper_claims": True,
    }
