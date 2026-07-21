from __future__ import annotations
import csv
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
R1 = ROOT / "data/annotations/main500_human_review/rater1_sheet.csv"
R2 = ROOT / "data/annotations/main500_human_review/rater2_sheet.csv"
OUT = ROOT / "data/results/main_500/human_review/main500_iaa_report.json"
r1 = list(csv.DictReader(R1.open())) if R1.exists() else []
r2 = list(csv.DictReader(R2.open())) if R2.exists() else []
status = "BLOCKED_NO_RATER_LABELS" if not r1 or not r2 else "READY_TO_COMPUTE_AFTER_LABELS"
report = {"status": status, "percent_agreement": None, "cohens_kappa": None, "disagreements": [], "excluded_items": [], "final_approved_item_count": 0, "paper_evidence": False}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(report, indent=2)+"\n")
print(status)
sys.exit(2 if status.startswith("BLOCKED") else 0)
