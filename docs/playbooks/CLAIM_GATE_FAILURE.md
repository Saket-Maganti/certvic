# Playbook: Claim Gate Failure

**Symptoms: the claim gate blocks a certified claim (non-evidence status, mock provider, no CS, etc.).**

## Actions

1. Read the gate errors: split is smoke, evidence_status non-evidence, provider mock, or CS unavailable.
2. Use a real open-local provider on a real (non-smoke) reviewed split; mock/baseline cannot certify.
3. Ensure an anytime-valid CS is available (install `certvic[stats]` or use the native fallback).
4. Do not bypass the gate — fix the underlying eligibility, or report descriptively.

Do not fabricate results to clear this symptom; if the honest outcome is a null
result or an ineligible claim, report it and adjust the protocol, not the numbers.
