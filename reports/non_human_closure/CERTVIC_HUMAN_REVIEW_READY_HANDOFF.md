# Human-review handoff

Status: `NOT_READY_FOR_GENUINE_PROSPECTIVE_HUMAN_REVIEW`. The historical blank forensic packet is ready
for two independent raters and covers 91 relevant and 94 V1 irrelevant pairs, but it cannot substitute
for prospective review. The prospective packet does not exist because real candidate generation has
not run. After that external return, run automated QA and packet construction, then use two independent
outcome-blind raters plus outcome-blind adjudication. Do not populate judgment fields by automation.

After genuine prospective review files exist, run:

```bash
python3 scripts/run_all_cpu_workflows.py --resume-after-human-review
```
