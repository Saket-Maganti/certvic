# CertVIC V6 Prompt — Formal Proof TODO and CS Bridge

Read `00_V6_MASTER_CONTEXT.md` first.

You are correcting project direction, not building generic infrastructure.

Hard constraints:
- Do not initialize git.
- Do not commit or tag.
- Do not use paid APIs.
- Do not use paid cloud.
- Do not download data or weights.
- Do not run GPU jobs.
- Do not run VLM inference.
- Do not fabricate results.
- Do not fabricate citations.
- Do not insert fake paper numbers.
- Do not make evidence claims from mock/smoke/simulated/planned/unreviewed/simple-edit-only artifacts.
- Keep tests local and CPU-only.
- Heavy dependencies must be optional/import-safe.

Bridge the implemented native anytime CS with supplement proof text.

Create/update:
- `paper/supp/proofs.tex`
- `docs/CS_PROOF_BRIDGE.md`
- `certvic/paper/proof_bridge_audit.py`

Required:
- define bounded variable
- define estimand
- state optional stopping condition
- connect implementation assumptions to theorem assumptions
- cite implementation file names, not fake papers
- mark theorem as proof-required until citations are added

CLI:
`python3 -m certvic.paper.proof_bridge_audit --paper-dir paper --out docs/V6_PROOF_BRIDGE_AUDIT.md`

Tests:
- proof appendix names CS/optional stopping
- no unsupported theorem overclaim
- implementation bridge references native CS module

At the end report:
- files changed
- tests added/updated
- commands added
- docs added
- verification commands run
- whether this prompt passed
- next prompt
