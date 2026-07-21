from __future__ import annotations
import csv
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SHEET = ROOT / "data/annotations/main500_human_review/main500_review_sheet.csv"
OUT = ROOT / "data/results/main_500/human_review/main500_human_review_apply_report.json"
rows = list(csv.DictReader(SHEET.open())) if SHEET.exists() else []
required = ["human_valid_item", "human_answerable", "human_reviewer_id", "human_review_timestamp"]
blank = [r.get("item_id", "") for r in rows if any(not r.get(c, "").strip() for c in required)]
status = "BLOCKED_NO_REVIEW_ROWS" if not rows else ("BLOCKED_BLANK_HUMAN_REVIEW" if blank else "DONE_READY_FOR_MANUAL_CERTIFICATION_REVIEW")
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({"status": status, "n_rows": len(rows), "blank_rows": blank, "paper_evidence": False}, indent=2)+"\n")
print(status)
sys.exit(2 if status.startswith("BLOCKED") else 0)
