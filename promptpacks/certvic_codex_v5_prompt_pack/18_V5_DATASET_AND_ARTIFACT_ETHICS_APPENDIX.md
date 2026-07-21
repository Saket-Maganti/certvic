# CertVIC V5 Prompt — Dataset and Artifact Ethics Appendix

Read `00_V5_MASTER_CONTEXT.md` first.

Do not initialize git. Do not create commits or tags. Do not use paid services. Do not download datasets or weights. Do not run GPU jobs. Do not run VLM inference. Do not fabricate results. Do not make evidence claims.

Build ethics/reproducibility appendix scaffold.

Create:
- `paper/supp/ethics_reproducibility.tex`
- `docs/ETHICS_AND_ARTIFACTS.md`
- `certvic/paper/ethics_audit.py`

Include:
- zero-cost reproducibility
- public datasets
- no paid annotation
- pointer-only release
- non-rehostable pixels caveat
- human review privacy
- no deployment claims
- model limitations

Tests:
- required ethics topics present
- no privacy leak
- no deployment claims
- artifact caveats included

Docs:
- `docs/V5_ETHICS_APPENDIX_REPORT.md`

At the end:
- list files changed
- list tests run
- list commands added
- state whether this prompt passed
- state next prompt
