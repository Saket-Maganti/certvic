# CertVIC Codex V3 Prompt 00 — Master Context

You are working on CertVIC / Certified Visual Consistency for a CVPR 2027 main submission.

The project has already completed V1–V2.7 infrastructure: smoke/audit systems, ADE20K readiness, mask manifests, edit planning, tiny edit generation, quality gates, visual review, label policy, open-local VLM readiness, ablations, certification/power planning, reporting, failure taxonomy, recipe-first release, paper scaffold, tiny/main pilot runbooks, V2 full audit, simulation/validity lab, diffusion preflight, adversarial prompt audit, reviewer harness, paper number guard, native anytime-valid CS fallback, and pre-run master audit.

Latest reported state: about 246 tests passing; baseline/full/pre-run audits pass; no paid services; no downloads; no GPU jobs; no VLM inference; no real empirical evidence yet.

## V3 purpose

The user wants to use remaining model credits to build **run-later infrastructure** before real ADE20K/GPU/VLM runs. V3 should improve future real runs by making them more resumable, auditable, scalable, reviewer-proof, paper-ready, and less likely to waste free compute.

V3 must not become generic overengineering. Every build must reduce risk for: real ADE20K runs, free-GPU diffusion edits, free open-VLM inference, human review, 1k–2k scaling, artifact release, and paper traceability.

## Scientific north star

CertVIC is not “just another benchmark.” The intended paper is a certified evaluation protocol: controlled real-image interventions + edit-derived expected answer changes + anytime-valid certification of intervention-consistency gaps + recipe-first zero-cost reproducibility + empirical finding across open VLMs.

The key metric is `Delta = E[a_i - C_i]`, where `a_i` is original-image correctness and `C_i` is intervention-consistency. Certification must use anytime-valid CS, never bootstrap alone.

## Global constraints

- Work in `/Users/saketmaganti/Projects/certVIC`.
- Do not initialize git, commit, or tag.
- Do not use paid APIs, paid cloud, paid datasets, paid annotation, paid credits, or paid tracking.
- Do not download large datasets or model weights.
- Do not run GPU jobs or VLM inference in tests.
- Do not fabricate results or insert fake paper numbers.
- Keep heavy dependencies optional and import-safe.
- Normal tests must run locally without GPU.
- Simulated/pre-run artifacts must be marked non-evidence and blocked from claims.
- Preserve backward compatibility and run `python3 -m pytest -q`.

## V3 stop rule

After V3 final audit passes, stop building infrastructure unless a real run exposes a concrete missing gate. Move to real ADE20K/diffusion/VLM runs.
