# CertVIC V5 Prompt — Theory and Proof Appendix Scaffold

Read `00_V5_MASTER_CONTEXT.md` first.

Do not initialize git. Do not create commits or tags. Do not use paid services. Do not download datasets or weights. Do not run GPU jobs. Do not run VLM inference. Do not fabricate results. Do not make evidence claims.

Build a result-free theory/proof appendix scaffold.

Create:
- `paper/sections/03b_theory.tex`
- `paper/supp/proofs.tex`
- `docs/THEORY_NOTES.md`
- `certvic/paper/theory_audit.py`

Include:
- formal definition of intervention pair
- consistency indicator
- intervention-consistency gap
- bounded transform for CS
- optional-stopping claim
- bootstrap-descriptive-only caveat
- assumptions and limitations

CLI:
`python3 -m certvic.paper.theory_audit --paper-dir paper --out docs/THEORY_AUDIT.md`

Tests:
- required definitions present
- forbidden overclaims absent
- bootstrap not called certification
- theorem statements have caveat labels
- no fake empirical numbers

Docs:
- `docs/V5_THEORY_APPENDIX_REPORT.md`

At the end:
- list files changed
- list tests run
- list commands added
- state whether this prompt passed
- state next prompt
