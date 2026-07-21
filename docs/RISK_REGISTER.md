# Risk Register

| Risk | Mitigation |
| --- | --- |
| Edit artifacts create invalid labels | quality gates and human validity checks |
| No measurable gap | report null result; adjust future edit families without faking claims |
| Licensing ambiguity | recipe-first release modes and source manifests |
| Free compute limits | batch/resume runner and sharding |
| Prompt leakage | leakage guards and manifest checks |
| Overclaims | claim ledger and paper scanner |
| Unsupported ADE20K layout | dry-run layout inspection with actionable blockers |
| ADE20K mask parser uncertainty | support semantic PNG only; mark non-PNG or uncertain layouts `parser_required` |
| Accidental pixel redistribution | pointer-only defaults and recipe-first release mode |
| Binary mask export misuse | disabled by default and documented as local inspection only |
| Unresolved ADE20K label names | use conservative `ade20k_label_<id>` names until a verified label map is supplied |
| Pilot target shortfall | write selection summary warnings and keep generation blocked until reviewed |
| Infeasible planned edits | write `pilot_edit_plan_rejected.jsonl` with explicit rejection reasons |
| Task preview mistaken for runnable eval | mark previews `PREVIEW_ONLY`, edited image `planned_unavailable`, and runnable task `false` |
| Non-evidence artifacts used for claims | claim gate blocks candidate, planned, preview, generated-edit, and edit-ready non-evidence statuses |
| Simple generated edits mistaken for evidence | mark generated rows `GENERATED_EDIT_ONLY` and require quality/human review before inference |
| Simple-mode artifacts are too crude | document simple mode as pipeline validation only; use quality gates and manual review |
| Optional inpainting downloads weights | keep `diffusers_inpaint` disabled by default and require explicit local/cache weights |
| Global destructive edit passes | quality gates check edit-specific allowed regions and control-change limits |
| Failed edits enter eval tasks | materialization includes only generated edits with passing quality gates and clean leakage checks |
| Unverified label map yields ill-posed questions | ship label policy as unverified template; restrict unresolved labels to control-only edits; record policy version/hash |
| Background 'stuff' edited as if a single object | label policy blocks wall/sky/floor/ceiling/road; selection and planner reject blocked labels |
| Incompatible label/family/edit combinations | label policy enforces eligible families and allowed edits in selector and edit planner; rejections summarized by label/family/edit_type |
| Task-family imbalance | per-family target with explicit warning when a family target cannot be met |
| Non-photorealistic / degenerate edits enter eval | edit-quality gates (uniform/all-black-white/sharpness/duplicate detectors); diffusion engine disabled until photorealistic edits are human-validated |
| Non-reproducible edit generation | replay metadata (engine version, seed, source/mask/plan hashes, actual params) on every generated row |
| Accidental overwrite or partial batch | no-overwrite default, resume-by-edit_id, rejected-file append, max_items required unless allow-full-run |

## Edit artifact confound (construct validity) — V3 probe

**Risk:** A VLM may respond to the edit *artifact* (flat blob, seam, sharpness
change) rather than the intended semantic single-factor change, confounding the
consistency gap. The crude `simple` edit engine is trivially detectable
(`edit_detectability` AUC ≈ 1.0 on flat-gray-blob edits).

**Mitigation / monitor:** Run `certvic.validation.edit_detectability` on reviewed
tasks before trusting any gap. AUC ≥ 0.8 flags artifact risk. Prefer
photorealistic diffusion-inpaint edits, add original-only/edited-only ablations,
and route flagged items through extra human review. The probe is descriptive
(`CONSTRUCT_VALIDITY_DIAGNOSTIC_NON_EVIDENCE`) and reported alongside, never
instead of, the certified gap. See `docs/EDIT_DETECTABILITY_PROBE.md`.

## Failure-mode playbooks (V3)

When a real run misbehaves, `certvic.playbooks.diagnose_failure` maps the observed
symptom to an operational playbook in `docs/playbooks/` (edit realism, no gap,
high parse failure, high control flip, low IAA, Kaggle session death, label
policy, claim gate, low original accuracy, too few candidates, GPU preflight):

```bash
python3 -m certvic.playbooks.diagnose_failure --report-dir data/results/tiny_real_pilot --out docs/playbooks/DIAGNOSIS.md
```

Playbooks are checklists, not ways to manufacture results: a null result or an
ineligible claim is reported honestly. See `docs/playbooks/README.md`.
