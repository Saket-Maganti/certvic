# V6 Command Index

Core V6 audits:
- `python3 -m certvic.paper.identity_audit --paper-dir paper --out docs/V6_PAPER_IDENTITY_AUDIT.md`
- `python3 -m certvic.paper.open_only_audit --paper-dir paper --out docs/V6_OPEN_ONLY_AUDIT.md`
- `python3 -m certvic.paper.proof_bridge_audit --paper-dir paper --out docs/V6_PROOF_BRIDGE_AUDIT.md`
- `python3 -m certvic.validation.directional_language_guard --root paper docs/V6_FULL_PACK_REPORT.md --out docs/V6_DIRECTIONAL_LANGUAGE_GUARD_REPORT.md`
- `python3 -m certvic.v6.final_directional_audit --out docs/V6_FINAL_DIRECTIONAL_AUDIT.md --json-out data/results/v6_final_directional_audit.json`

Validity-gated analysis:
- `python3 -m certvic.validity.filter_scores --scores <pair_scores.jsonl> --certificates <item_certificates.jsonl> --out <valid_scores.jsonl> --rejected-out <rejected_scores.jsonl>`
- `python3 -m certvic.reporting.validity_shift_report --scores <pair_scores.jsonl> --certificates <item_certificates.jsonl> --out-dir data/results/validity_shift`
- `python3 -m certvic.reporting.naive_vs_validity_gated --naive <all_scores.jsonl> --valid <valid_scores.jsonl> --certificates <item_certificates.jsonl> --out-dir data/results/naive_vs_validity_gated`

Tiny-pilot gate:
- `python3 -m certvic.pipeline.tiny_pilot_go_no_go --detectability data/results/tiny_real_pilot/edit_detectability --quality data/results/tiny_real_pilot/quality_report.json --out docs/TINY_PILOT_GO_NO_GO.md --json-out data/results/tiny_pilot_go_no_go.json`
- `python3 -m certvic.dashboard.tiny_pilot_decision --pilot-dir data/results/tiny_real_pilot --out docs/TINY_PILOT_DECISION.md --json-out data/results/tiny_pilot_decision.json`

After V6, run. Do not build V7.
