"""Free-compute budget model (V3 prompt 10).

Holds the free-tier envelopes (weekly Kaggle GPU hours, session caps) and the
per-stage rate assumptions, plus helpers to turn a workload (GPU-hours,
human-hours) into wall-clock under quota and per-session batch sizes. Conservative
defaults; no paid services.
"""

from __future__ import annotations

# Free-tier compute envelopes (approximate, conservative).
WEEKLY_KAGGLE_GPU_HOURS = 30.0      # Kaggle free GPU quota per week (~30 h)
KAGGLE_SESSION_HOURS = 11.5         # usable single-session wall-clock before reset
COLAB_SESSION_HOURS = 8.0           # conservative free Colab session before disconnect

# Conservative per-item rate assumptions.
DEFAULTS = {
    "overgeneration_factor": 2.5,   # edit candidates generated per kept item
    "edit_seconds_per_item": 8.0,   # diffusion inpaint per candidate on a free GPU
    "vlm_seconds_per_item": 3.0,    # one VLM forward+decode per image
    "variants_per_item": 2,         # original + edited
    "num_models": 3,                # open VLMs evaluated
    "ablation_multiplier": 1.5,     # extra prompt/caption/original-only conditions
    "cpu_seconds_per_item": 0.5,    # masks/scoring/reporting CPU work
    "human_seconds_per_item": 30.0, # careful single-factor review per item
    "human_hours_per_day": 3.0,     # sustainable manual review per day
    "weekly_free_gpu_hours": WEEKLY_KAGGLE_GPU_HOURS,
    "session_hours": KAGGLE_SESSION_HOURS,
}


def merge_params(overrides: dict | None = None) -> dict:
    params = dict(DEFAULTS)
    if overrides:
        params.update({k: v for k, v in overrides.items() if v is not None})
    return params


def wall_clock_weeks(gpu_hours: float, weekly_free_gpu_hours: float) -> float:
    if weekly_free_gpu_hours <= 0:
        return float("inf")
    return gpu_hours / weekly_free_gpu_hours


def session_batch_size(seconds_per_item: float, session_hours: float) -> int:
    """How many items fit in one free GPU session at a given per-item rate."""
    if seconds_per_item <= 0:
        return 0
    return int((session_hours * 3600.0) / seconds_per_item)
