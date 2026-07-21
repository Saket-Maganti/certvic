# Edit Family Risk Matrix

Risk dimensions:
- detectability
- photorealism
- answerability
- single-factor validity
- ADE20K label ambiguity
- expected VLM sensitivity
- free-GPU feasibility

Missing data is unknown, not pass. High detectability or low review pass rate
holds that edit family at pilot scale until repaired.

Command:
`python3 -m certvic.edit.family_risk --edit-manifest <generated_edits.jsonl> --detectability <detectability.json> --review <review_summary.json> --out docs/EDIT_FAMILY_RISK_MATRIX.md`
