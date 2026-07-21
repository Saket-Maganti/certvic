# Playbook: GPU / Preflight Failure

**Symptoms: a VLM or diffusion preflight reports not-ready / blocking failures.**

## Actions

1. Read `blocking_failures`: missing deps, missing local weights, no GPU, or zero-cost policy not set.
2. Pre-download model/diffusion weights to a local/cached dir (preflight never downloads).
3. Enable the GPU accelerator; verify with `--check-gpu`.
4. Confirm `paid_services_enabled: false` and the optional engine is explicitly enabled in the config.

Do not fabricate results to clear this symptom; if the honest outcome is a null
result or an ineligible claim, report it and adjust the protocol, not the numbers.
