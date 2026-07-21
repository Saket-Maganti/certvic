# CertVIC V5 Prompt — Paper Figure Placeholder System

Read `00_V5_MASTER_CONTEXT.md` first.

Do not initialize git. Do not create commits or tags. Do not use paid services. Do not download datasets or weights. Do not run GPU jobs. Do not run VLM inference. Do not fabricate results. Do not make evidence claims.

Create exact paper figure slots and expected generators.

Create:
- `paper/figures/README.md`
- `paper/figure_manifest.yaml`
- `certvic/paper/figure_manifest_audit.py`

Figures:
- pipeline overview
- edit examples
- CS trajectory
- main result gap
- control spurious flip
- ablation summary
- failure gallery
- artifact/release diagram

CLI:
`python3 -m certvic.paper.figure_manifest_audit --manifest paper/figure_manifest.yaml --paper-dir paper --out docs/FIGURE_MANIFEST_AUDIT.md`

Tests:
- every figure slot has generator/source/claim status
- paper references known figures
- no missing placeholders

Docs:
- `docs/V5_FIGURE_PLACEHOLDER_REPORT.md`

At the end:
- list files changed
- list tests run
- list commands added
- state whether this prompt passed
- state next prompt
