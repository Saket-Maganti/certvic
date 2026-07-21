"""Provenance and traceability for CertVIC (V3).

A central run ledger (:mod:`certvic.provenance.run_ledger`) records every
data/edit/VLM/scoring/report/paper artifact with the command, configs,
input/output hashes, evidence status, and zero-cost policy that produced it.
The artifact graph (:mod:`certvic.provenance.artifact_graph`) and claim tracer
(:mod:`certvic.provenance.trace_claim`) then let any future paper number be
traced back to the run that produced it -- or flagged as missing,
hash-mismatched, or evidence-ineligible.

Nothing here downloads data, runs GPU jobs, calls paid services, or makes
evidence claims; it only records and audits provenance metadata.
"""
