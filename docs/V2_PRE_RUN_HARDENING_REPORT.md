# V2.x Pre-Run Hardening Report (V2.1+ through V2.7)

Pre-run builds completed before any real ADE20K root, GPU, download, or VLM
inference. Everything here runs on local CPU, makes no evidence claims, and marks
all simulated artifacts `SIMULATED_ONLY`.

## Headline correctness fix

The paper's central method (anytime-valid certification) previously routed only
through the optional `confseq` dependency. With `confseq` absent — the common
case on free CPU/Kaggle/Colab — certification silently degraded to "CS
unavailable", i.e. **the core contribution did not run on its target
environment**. Fixed by adding a native, dependency-free anytime-valid CS and an
`auto` backend that prefers `confseq` and falls back to the native CS. See
`docs/STATISTICAL_VALIDITY.md`.

## Builds

| Stage | Module | What it adds |
| --- | --- | --- |
| V2.1+ | `certvic/metrics/anytime_cs.py` | Native Hoeffding-mixture anytime-valid CS (zero deps). |
| V2.1+ | `certvic/sim/anytime_validity.py` | Monte-Carlo lab proving Type-I control + coverage under optional stopping vs a peeked fixed-n CI. |
| V2.2 | `certvic/edit/diffusion_preflight.py` | Edit-generation readiness preflight (diffusion deps, local weights, VRAM, runtime, zero-cost; never downloads). |
| V2.3 | `certvic/eval/adversarial_audit.py` | Prompt/task adversarial audit: label consistency, leakage, non-visual gameability, answer-prior imbalance, design balance, diversity, MCQ prior. |
| V2.5 | `certvic/v2/reviewer_attack_harness.py` | Binds every known reviewer attack to a live executable defense check. |
| V2.6 | `certvic/validation/paper_numbers_guard.py` | Paper auto-injection guard: result prose may contain only placeholders, comments, `\input` of provenance-tracked generated tables, and declared method constants. |
| V2.7 | `certvic/v2/pre_run_master_audit.py` | Single gate aggregating full audit + reviewer harness + paper guard + validity lab (+ optional adversarial audit). |
| analysis | `docs/PRE_REGISTRATION.md` | Pre-committed primary endpoint, stopping rule, multiplicity + clustering policy. |

## Verification

* Full suite: `python3 -m pytest -q` → 246 passed (was 216; +30 tests).
* `python3 -m certvic.sim.anytime_validity --out-dir <d> --n 400 --n-trials 3000`
  → CS false-certification under peeking ~0.001 (alpha=0.05); peeked fixed-n ~0.67.
* `python3 -m certvic.v2.reviewer_attack_harness` → 10/10 blocking defenses ready.
* `python3 -m certvic.v2.pre_run_master_audit` → CLEARED, 5/5 components.

## Not done by design

No real ADE20K inspection, no diffusion edits, no human review, no VLM inference,
no certified evidence. The empirical science is still intentionally empty; this
work certifies *readiness*, not findings.
