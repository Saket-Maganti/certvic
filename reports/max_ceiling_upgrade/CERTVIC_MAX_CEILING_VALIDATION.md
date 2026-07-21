# CertVIC maximum-ceiling validation

## Verdict

All implemented local upgrade, runtime, notebook, guard, paper, recovery, and release paths pass. The
overall requested mission remains `PARTIALLY_READY_WITH_BLOCKERS` because the required repaired
full-project replacement archive was absent and therefore could not be installed transactionally.

## Exact results

| Gate | Result |
| --- | --- |
| Repaired active baseline before change | PASS — 845 tests |
| Final full default suite | PASS — 857 passed, 1 optional duplicate notebook test skipped |
| Actual synthetic notebook suite | PASS — 8/8 routes executed via nbclient |
| Compileall | PASS |
| Ruff | PASS |
| Configured type checker | N/A — none configured |
| Canonical CVPR notebooks | PASS — 16/16 valid and output-free |
| T4x2 static notebooks | PASS — 6/6 |
| Chaos matrix | PASS — 21/21; canonical corruption false |
| Artifact registry | PASS — exact hashes and lineage references valid |
| Reproducibility capsule | Correctly incomplete — seven real external roles absent |
| Data/license registry | PASS; ADE20K and COCO remain externally unverified/fail-closed |
| Review dry-run/operations tests | PASS; no reviewer identity or label fabricated |
| Statistical tiny fixtures | PASS against hand-counted denominators and McNemar case |
| Paper evidence compiler | Correctly blocked: canonical real analysis and genuine review absent |
| Claim guard | PASS — 0 findings |
| Repository privacy/secret/path audit | PASS — 0 findings |
| Paper compile twice | PASS — 3 pages; PDF SHA-256 `71e743b47b565eb7a0d641f33ae394b1743a81d1e68120dd2670bfcb037b83c1` |
| Deterministic release rebuild | PASS — byte-identical |
| Clean release extraction | PASS — compileall plus doctor/next-action/run-graph/chaos CLI probes |
| Clean release privacy audit | PASS — 0 findings |

The default suite skips the duplicate notebook-execution test because nbclient is an optional Kaggle
dependency, not installed in the base project interpreter. The required proof was run separately with
the declared optional dependencies and all eight routes passed. A later attempt to duplicate that
kernel proof inside the final full suite was declined by the app quota; no missing proof is inferred
from that decline.

## Frozen-boundary verification

- `paper_evidence=false` remains active for specificity confirmatory, Main, and second-domain configs.
- `execution_allowed=false` remains active for all three study configs.
- Genuine `human_reviewed=true` count in the canonical V11 JSON evidence tree is zero.
- Main and COCO are not authorized.
- V2-30 remains retrospective sensitivity evidence.
- No real GPU evidence, COCO evidence, human label, model commit, or provider return was created.
- Pre-smoke and scientific permission paths remain distinct.
- Repository notebooks retain empty outputs after synthetic proof because execution used temporary
  notebooks and separate proof reports.

## Replacement validation

`certVIC_9_SMOKE_AUTHORIZATION_FIXED_FULL.zip` and any unambiguous matching full archive were absent.
`CERTVIC_SMOKE_AUTHORIZATION_PATCH_ONLY.zip` was rejected based on its identity and 39-member partial
inventory. No live-tree clearing, staging promotion, stale-file deletion, or archive relocation was
performed. See `reports/repository_replacement/`.

