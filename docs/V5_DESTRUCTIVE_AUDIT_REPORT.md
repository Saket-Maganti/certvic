# V5 Destructive Audit Report

**Date:** 2026-06-22
**Auditor stance:** destructive internal auditor, harsh CVPR reviewer, ML systems engineer, statistician, adversarial QA lead.
**Goal:** break the project before reviewers do. No feelings protected.

**Constraints honored:** no git init, no commits/tags, no paid APIs/cloud, no downloads, no GPU jobs, no VLM inference, no fabricated results, no fake paper numbers, no evidence claims, no gate weakening. Every fix strengthens a gate; none removes a check. All tests remain CPU/local.

---

## A. Overall audit status

**CONDITIONAL PASS. Empirical runs MAY begin — starting with the ADE20K dry-run.**

The infrastructure is genuinely strong and, in places, over-built. I attacked the claim-safety machinery hard. It is layered and fails closed: every fake/ineligible path I constructed (mock provider, synthetic/smoke split, simulated-only, generated-edit-only, unreviewed tasks, missing CS, bootstrap-only, tiny-n, missing provenance) was blocked end-to-end. But I found **4 real bugs** inside individual safety gates — each one a place where a single gate leaked and was only saved by defense-in-depth or by never being exercised yet. All four are now fixed with regression tests. The conditional is: run the empirical pipeline **staged and gated**, not via one wholesale `bash commands.sh`, and treat edit-detectability, IAA, and effect-existence as live empirical risks.

The "CVPR-ready except results" framing is **too generous**: the paper is also missing every citation, a bibliography, and any formal theorem/proof. It is "CVPR-ready in scaffold and tooling; not yet in scholarship or evidence."

---

## B. Bugs found (all fixed)

| ID | Severity | Area | File | One-line |
|----|----------|------|------|----------|
| BUG-1 | Medium | Claim gates / stats | `certvic/metrics/certification_policy.py` | Policy gate leaked the required status into a module-global allowlist across calls |
| BUG-2 | Medium-High | Paper-number guard | `certvic/validation/paper_numbers_guard.py` | Fake numbers hidden on any line containing `--`/`TBD`/`N/A`; `.42`-style missed |
| BUG-3 | Medium | Edit validity | `certvic/validity/certificate_schema.py` | Item certificate never blocked detectable / unassessed edits |
| BUG-4 | Medium-High | Release/privacy | `certvic/security/release_privacy_audit.py` | Pre-release audit text-scanned everything **except** the release dir |

### BUG-1 — Certification policy leaks the required evidence status globally
`evaluate_certification_policy()` did `_REVIEWED_OR_STRONGER.add(required)` on a **module-level** set. One call with a custom/permissive `evidence_status_required` permanently widened the allowlist, so a later **default-policy** call accepted a non-evidence status.

Reproduced: after a call with `evidence_status_required="GENERATED_EDIT_ONLY"`, a default-policy call with `evidence_statuses=["GENERATED_EDIT_ONLY"]` returned `policy_passed=True`.

Why it mattered: the policy gate is the *allow-list* half of certification. The integrated pipeline ANDs it with the `claims.py` *deny-list*, which still blocked `GENERATED_EDIT_ONLY`, so no end-to-end certified claim was emitted — but the policy gate itself was defeated, the leak is order-dependent (test pollution), and any consumer reading `policy_passed` standalone would be misled.

**Fix:** build the accepted set locally (`accepted = _REVIEWED_OR_STRONGER | {required}`); never mutate the global. Strictly stronger.

### BUG-2 — Paper-number guard bypass (em-dash / placeholder line-skip; leading-dot decimals)
`extract_paper_numbers()` skipped any results-prose line containing a `PLACEHOLDER_TOKEN`. But `"--"` matches ordinary em-dashes (`---`), en-dashes, and numeric ranges (`10--20`) — all common LaTeX. A fabricated number sharing such a line was never scanned. Separately, the number regex required a leading digit, so `.42` was invisible.

Reproduced: `Our method achieves a gap of 0.42 --- a substantial margin` → `0.42` **not** flagged; `.42` not flagged.

This directly defeats the guard's stated purpose (catch hand-entered/fabricated result numbers). For a fabrication guard the only acceptable failure mode is **fail-closed**.

**Fix:** neutralize placeholder tokens *in place* (they carry no digits) instead of skipping the whole line, so a real number sharing the line is still scanned; extend the number regex to match leading-dot decimals. Verified the real placeholder-only `paper/sections/05_results.tex` still passes (0 violations).

### BUG-3 — Item validity certificate never gated on edit detectability
`detectability_status` was a certificate field but was **not** in `BLOCKING_FIELDS`, and the "incomplete_review_state" warning only inspected `BLOCKING_FIELDS`. So a highly-detectable (crude) edit — or, worse, an item whose detectability was **never assessed** (`unknown`) — could be marked `evidence_eligible_candidate=True`. This is exactly the construct-validity hole audit area 5 warns about: "crude/detectable edits cannot become evidence."

**Fix:** add `detectability_status` to `BLOCKING_FIELDS`. A failing value now produces a blocking reason; an `unknown` value now triggers `incomplete_review_state` → not evidence-eligible (conservative: unassessed = ineligible).

**Residual (documented as RISK-3 wiring gap):** the detectability *probe* (`edit_detectability.py`) emits `artifact_risk`/`auc`/flagged items but does **not** write a per-item `detectability_status` back into task metadata, and `evidence_eligible_candidate` is consumed nowhere downstream yet. The gate is now correct; wiring the probe → metadata → eval-eligibility is real-run integration, not infra to build now.

### BUG-4 — Release privacy audit skips the release directory's text files
`scan_private_paths`/`scan_secrets` use `iter_text_files`, which skips `GENERATED_PREFIXES` — and that list **includes `"release"`**. The combined audit ran only a *pixel* scan on `--release-dir`. So a home-directory absolute path, a private dataset root, or an API-key-like token inside a release **config/script/README** was never inspected by the gate that is explicitly "critical before any artifact release."

Reproduced: a release capsule text file with a private dataset root + OpenAI key → `audit(...) passed=True`.

**Fix:** when `release_dir` is supplied, additionally run `scan_private_paths`/`scan_secrets` rooted **at** the release dir (so its contents are not skipped) and fold those findings into the pass decision and report.

---

## C. Unfixed risks

| ID | Severity | Why not fixed | Blocks real runs? |
|----|----------|---------------|-------------------|
| RISK-1 | Low | `cvpr_ready` check `no_evidence_claims_from_planned_artifacts` is hardcoded `True` (vacuous). It is not a claim-safety hole (it never admits evidence); an honest version needs a real claim ledger to check against, which won't exist until after the first run. Wire it to `trace_claims()` post-run. | No |
| RISK-2 | Low-Med | `theory_audit` / `result_free_completeness_audit` are **presence/keyword** checks, not depth checks (`theory_audit` passes if the words "theorem" and "caveat" both appear). They overstate the "5/5 passed" assurance. Cannot be auto-graded honestly without fabricating content. | No |
| RISK-3 | Medium | `tiny_pilot` `commands.sh` chains dry-run → execute → GPU edit generation → VLM inference in one script. Per-command guards make it fail-safe (`run_eval --evidence-run` hard-blocks non-open-local + unreviewed tasks; `--dry-run` writes nothing; `set -euo pipefail` + `<ADE20K_ROOT>` placeholder aborts blind runs). Residual is process/doc only. Stop-doc updated to a staged, gated next-command. | No (mitigated) |
| RISK-4 | Low | `freeze_results` marker scan skips files ≥1MB, so a large simulated artifact could evade the `claim_eligible` heuristic. It is a backstop; real eligibility is enforced by certification policy + provenance trace + paper-number guard. | No |

None of the unfixed items block beginning empirical runs. They are audit-hygiene and process items; RISK-1/RISK-2 should be tightened **after** the first real run produces artifacts to check against.

---

## D. Paper weaknesses (brutal, no fabrication)

The paper is a **complete, honest scaffold** — and that is the ceiling of what it currently is. Three CVPR-critical dimensions are essentially empty:

**Related-work weaknesses (most severe):**
- **Zero `\cite` commands and no `.bib` file in the entire paper.** A CVPR submission with no citations is an automatic desk reject.
- `paper/related_work_matrix.yaml` is a deliberately non-fabricating scaffold: every category has `representative_works: []` and `status: needs_citations`. This is the *correct* discipline (no invented references) but means a human must still do the literature work.
- `02_related.tex` describes *categories* of prior work and how CertVIC differs, but engages **no specific paper**. It reads as a positioning sketch, not a related-work section.

**Theory/proof weaknesses:**
- `03b_theory.tex` defines the estimand `Δ = E[a]−E[C]`, the bounded transform `d=(a−C+1)/2`, and appropriate caveats — but states **no formal theorem and gives no proof**.
- The actual coverage guarantee (Ville's inequality applied to a Hoeffding mixture supermartingale) exists only as a **docstring** in `certvic/metrics/anytime_cs.py`. For a paper whose self-described "core methodological contribution" is anytime-valid certification, `supp/proofs.tex` must formalize this. Right now the theory is prose, not mathematics.
- `theory_audit` passing is weak evidence of rigor — it checks for the presence of phrases, not the existence of a proof.

**Figure/table weaknesses:**
- `figure_manifest.yaml` / `table_manifest.yaml` exist and are structurally audited; all cells are correctly result-gated placeholders.
- The **qualitative edit figures are absent** because no real photorealistic edits exist yet. For a vision venue this is the make-or-break exhibit: reviewers will judge edit realism *by eye*. There is currently nothing to show.

**Result-free weaknesses:**
- Results sections are placeholders (expected and correct).
- `result_free_completeness_audit` verifies section/file presence, not argument quality, so "complete" means "all sections exist," not "all sections are persuasive."

**Bottom line:** "CVPR-ready except results" should read **"CVPR-ready in structure and tooling; still missing all citations, a formal theory section, qualitative figures, and all empirical results."**

---

## E. Verification

Exact commands run:
```bash
python3 -m pytest -q
python3 -m certvic.v5.cvpr_ready_except_results_audit --out docs/V5_CVPR_READY_EXCEPT_RESULTS_AUDIT.md --json-out data/results/v5_cvpr_ready_except_results_audit.json
python3 -m certvic.v5.all_commands_smoke --out data/results/v5_all_commands_smoke.json
python3 -m certvic.validation.claim_language_guard --root paper docs --out docs/CLAIM_LANGUAGE_GUARD_REPORT.md
python3 -m certvic.validation.paper_numbers_guard            # real results section
python3 -m certvic.security.release_privacy_audit --root . --out docs/SECURITY_PRIVACY_AUDIT.md
python3 -m pytest tests/test_v5_destructive_audit_regressions.py -q
```

Results:
- **pytest: 459 passed (baseline) → 471 passed (after fixes + 12 new regression tests).** No regressions.
- cvpr_ready_except_results_audit: **passed (5/5)**.
- all_commands_smoke: **passed**, 4 unsafe commands skipped.
- claim_language_guard: **0 findings**.
- paper_numbers_guard on the real `05_results.tex`: **0 violations** (fix did not break the legitimate placeholder section).
- release_privacy_audit on the real repo: **0 findings** (fix did not introduce false positives).

---

## F. Final go / no-go

| Step | Verdict |
|------|---------|
| Keep building general infrastructure | **No** — it is ready and over-built. Remaining gaps are empirical, not structural. |
| Begin ADE20K dry-run | **Yes — do this next.** CPU-only, no GPU/VLM, validates the dataset-manifest path. |
| Begin tiny diffusion pilot | **Yes, after** the dry-run passes and its outputs are inspected. Keep it tiny; inspect quality + detectability before scaling. |
| Begin VLM runs | **Not yet.** Only after edits pass quality gates, detectability is acceptable, and items are human-reviewed (reviewed status + item certificates). |
| Wait for more audit/fixes | **No.** The 4 bugs are fixed; the rest are documented risks only real runs can resolve. |

**Exact command to run next** (do **not** `bash commands/tiny_pilot/commands.sh` wholesale):
```bash
python3 -m certvic.commands.generate_real_run_commands \
  --stage tiny_pilot --out-dir commands/tiny_pilot \
  --ade20k-root <YOUR_LOCAL_ADE20K_ROOT>
# Then run ONLY these, inspecting output between each:
#   [v3_gate]            CPU audit
#   [study_plan]         plan only
#   [tiny_pilot_dry_run] --dry-run; confirm it passes
# STOP before [tiny_pilot_execute]. Do not proceed to GPU/VLM until the dry-run is clean.
```

---

## G. Ratings and CVPR forecast

### Current state (after V1–V5 infra, before real runs)

| Dimension | Score | One-line justification | What would improve it | What could still kill it |
|---|---|---|---|---|
| Engineering maturity | **8/10** | 48 modules, 471 CPU tests, layered audits/CLIs | Tighten shallow audits (RISK-1/2) | Integration bugs surfacing on first end-to-end run |
| Reproducibility | **7/10** | Recipe-first, hashing, lockfiles, provenance, dockerless | Exercise the pipeline end-to-end once | Pipeline never actually reproduces a real result |
| Statistical rigor | **8/10** | Documented native anytime-valid CS + validity lab + conservative on n=1/empty/tiny-n | Formal theorem/proof in the paper | Cluster dependence invalidating CS coverage |
| Claim safety | **9/10** | Multiple fail-closed gates; every fake path blocked end-to-end | Wire `evidence_eligible_candidate` downstream | A future un-gated consumer of a single leaky gate |
| Run readiness | **7/10** | Bundles, dry-run/resume/max-items/provider-validation/sharding | Enforced gate between dry-run and execute | Free-GPU limits making the pilot impractical |
| Paper-readiness except results | **5/10** | All sections/manifests present and honest | Add citations, bib, formal theory | Reviewers seeing an empty related-work/theory |
| Construct-validity tooling | **8/10** | Detectability, realism rubric, answerability, IAA, calibration, certificates, controls | Join probe output into item certificates | Tooling unused / not wired into eligibility |
| **Actual construct-validity evidence** | **1/10** | None exists | Run real edits + human review | Edits trivially detectable → confounded |
| **Empirical evidence** | **1/10** | Zero eligible non-smoke VLM evidence | Execute the pilot | The effect not existing on open VLMs |
| CVPR-main submission readiness | **2/10** | No results, no citations | Results + citations + theory | Submitting before any of these exist |
| Realistic acceptance probability today | **~2–3%** | Placeholder results + zero citations = desk reject | — | — |

### Future state (perfect execution of all planned runs)

Assumes: ADE20K manifests built; photorealistic edits on free GPU; detectability not trivially high; human review passes with acceptable IAA; answerability + item certificates pass; ≥1k (target 2k) reviewed items; ≥3 (target 4) open VLMs; text-only / prompt-sensitivity / parser-sensitivity / control-edit / ablation studies pass; parse failures and control flips controlled; an eligible anytime-valid certified lower bound; clean cluster diagnostics; release/privacy/provenance pass; figures/tables from eligible artifacts only; no fake numbers.

| Dimension | Score | One-line justification | What would improve it | What could still kill it |
|---|---|---|---|---|
| Engineering maturity | **9/10** | Already strong; hardened by real runs | — | — |
| Reproducibility | **9/10** | Recipe-first + lockfiles + provenance on real artifacts | Independent reproduction | Non-rehostable data friction |
| Statistical rigor | **9/10** | Realized certified lower bound under optional stopping | Formal proof in supp | Cluster dependence |
| Construct validity | **8/10** | Single-factor + detectability + IAA all measured | Higher IAA, lower detectability AUC | Edits detectable → confound survives |
| Empirical strength | **7/10** | 1–2k items × 3–4 open VLMs is solid but modest | More models / scale; a frontier comparison | "So what?" if the gap is unremarkable |
| Paper clarity | **8/10** | Clean structure; needs citations/theory filled | Polished related work + proofs | Thin scholarship |
| Novelty / significance | **8/10** | Certified intervention-consistency gap on real, validated, single-factor edits is a fresh framing | A surprising, confound-ruled-out finding | Framed as "yet another robustness benchmark" |
| Artifact strength | **9/10** | Recipe-first, reproducible, provenance-traced, zero-cost | — | — |
| Reviewer defensibility | **8/10** | Anti-overclaim discipline directly defends rigor attacks | Frontier-model coverage | Open-VLM-only scope attack |
| CVPR-main submission readiness | **8/10** | A clean, honest, complete submission | — | — |
| Realistic acceptance probability | **~35–50%** | Borderline → weak accept | A striking finding + frontier comparison | Modest scale, open-VLM-only, unremarkable effect |

### Verdicts

**A. If submitted today:** **DESK REJECT.** Placeholder results, zero citations, no related-work engagement, no formal theory. There is nothing for a reviewer to evaluate empirically and the paper would not survive the editorial check.

**B. If future perfect-execution succeeds:** **BORDERLINE → WEAK ACCEPT.** A methodologically clean, honest, reproducible study with a genuinely fresh framing (certified intervention-consistency gap on real, human-validated, single-factor edits with the artifact confound *measured*). What keeps it from a confident accept: modest scale (1–2k items), open-VLM-only (no frontier models), and significance that hinges on the actual finding being interesting. Rigor-valuing reviewers push to accept; scale/impact-valuing reviewers push back.

**C. Highest realistic ceiling:** a rigorous, reproducible **measurement-and-certification protocol** paper — the kind that becomes a cited methodology/benchmark. It reaches **highlight** level only if the empirical result is striking *and* the edit-artifact confound is convincingly ruled out. The memorable result would be: *"Even on photorealistic, human-validated, single-factor edits where a cheap detectability probe shows the edit is not trivially separable, open VLMs fail to update their answers at a certified rate of X% (anytime-valid lower bound), under optional stopping."* The certification + ruled-out confound is what would make it stick.

**D. Remaining irreducible risks** (resolvable only by real empirical outcomes):
1. **Edit realism / detectability** — real diffusion edits may be trivially detectable (high AUC) → the gap is confounded by edit artifacts → the central construct is invalid. The probe can *detect* this; it cannot fix it.
2. **Human IAA** — raters may disagree on single-factor validity / answerability → items cannot be certified at scale.
3. **Effect existence** — the gap may be small or absent on open VLMs → no eligible certified lower bound above threshold → no headline.
4. **Cluster dependence** — items sharing source scenes may violate independence → CS coverage threatened; diagnostics may reveal a fatal structure.
5. **Output quality** — parse-failure / control-spurious-flip rates on real model outputs may exceed policy thresholds → ineligible.
6. **Free-GPU feasibility** — edits + 3–4 VLMs over 1–2k items within free-tier limits may force the scale down.

**E. Final go/no-go recommendation:** **Stop building infrastructure. Begin the ADE20K dry-run now** (CPU-only, safe). Then a tiny diffusion pilot once the dry-run is inspected and clean; VLM runs only after edits pass quality + detectability and items are human-reviewed. Do not run the pilot bundle wholesale — run it command-by-command with the dry-run gate. The decisive question for this project is no longer engineering; it is **whether real photorealistic edits survive the detectability probe and whether humans agree they are single-factor and answerable.** Everything else is ready.
