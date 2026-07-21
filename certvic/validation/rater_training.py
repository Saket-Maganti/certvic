"""Generate human rater training and calibration templates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def write_rater_training(out_dir: str) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "rater_guide.md").write_text(
        "# CertVIC Rater Guide\n\n"
        "Judge single-factor validity, edit realism, answerability, and ambiguity. "
        "Do not use model outputs. No paid annotation is required.\n",
        encoding="utf-8",
    )
    (out / "calibration_quiz_template.csv").write_text(
        "item_id,question,expected_single_factor_valid,expected_answerable,notes\n",
        encoding="utf-8",
    )
    (out / "gold_label_rubric_template.csv").write_text(
        "item_id,gold_single_factor_valid,gold_answerable,gold_notes\n",
        encoding="utf-8",
    )
    return {"out_dir": str(out), "guide_generated": True, "paid_annotation": False}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Write rater training materials")
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args(argv)
    print(json.dumps(write_rater_training(args.out_dir), sort_keys=True))


if __name__ == "__main__":
    main()
