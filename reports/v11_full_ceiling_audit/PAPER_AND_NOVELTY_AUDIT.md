# Paper and Novelty Audit

**Status:** evidence-bounded V11 audit; `paper_evidence=false`

The V11 paper is an evidence-safe pilot draft, not a submission-ready manuscript.

## Defensible contribution

The strongest current framing is a protocol contribution: separate responsiveness under intended
interventions from specificity under matched irrelevant edits, retain raw paired traces, and attach
explicit uncertainty and claim gates. The pilot observation is that these quantities separate and
that specificity is model-dependent on the available V1 control.

## Prohibited overreach

- Do not claim causal visual understanding, universal robustness, architecture-level explanation,
  independent V2 confirmation, completed human validation, broad domain generalization, or certification.
- Do not call a numerical CS crossing the full scientific gate.
- Do not describe current V2 or Main-500 outputs; none exist.
- Do not make priority claims until primary literature and bibliographic anchors are verified.

## Section-level gap audit

| Section | Current quality / evidence conflict | Required repair | Completed locally? |
|---|---|---|---|
| Title/abstract | evidence-safe short draft; contribution hierarchy still provisional | lead with responsiveness--specificity protocol and pilot scope | partial |
| Introduction | problem distinction present; novelty comparison unsupported | add source-backed gap and one primary contribution | no, citations blocked |
| Related work | no verified bibliography | compare counterfactual editing, VLM consistency, robustness, and confidence sequences using primary sources | no |
| Method | estimands and CS present; “certified” can be misread | map every symbol to code and state conditional guarantee/non-guarantees | yes in V11 spec; paper partial |
| Experimental design | real pilot described; review/revision provenance incomplete | add frozen independent-set, blinding, missing-data, and model-setting contracts | protocol complete, evidence pending |
| Results | exact pilot/V1 table present; no V2/Main-500 result | keep pilot result hierarchy and explicit missing-result placeholders | yes |
| Failure analysis | Qwen observation framed scientifically; mechanism unknown | insert blinded human outcomes and salience sensitivity when real | pending evidence |
| Limitations/ethics | main blockers stated; dataset/license ethics incomplete | add redistribution, annotation, environmental/compute, and scope discussion | partial |
| Figures | no overloaded engineering figure; conceptual visual absent | add one responsiveness-vs-specificity protocol figure from verified design | no |
| Tables | main pilot table answers a scientific question | add paired uncertainty and validity table after real review | partial |
| Appendix/reproducibility | audit artifacts exist outside manuscript | link schemas, hashes, parser tests, model revisions, and review codebook | partial |
| Bibliography/anonymity | anonymity passes; bibliography absent | create and verify `.bib`, citations, and source priority before submission | anonymity yes; bibliography no |

## Paper readiness

`paper/main_v11.pdf` compiles to a short evidence-bound draft and was rendered page-by-page for
layout review. Remaining paper blockers are empirical scope, human validity, independent specificity,
reproducibility metadata, citations, and a complete anonymous release. All current ledger entries
remain `paper_evidence=false`.

Repository-root LICENSE/COPYING present: false; paper
bibliography file present: false. The existing
`docs/CITATION_TODO.md` is a reminder, not a bibliography or source verification.
