"""Static local run dashboard for CertVIC (V3).

Generates a self-contained static HTML dashboard (plus a JSON data file) over
whatever run artifacts exist locally: runs, metrics, quality gates, review
progress, claim eligibility, and provenance/artifacts. Static files only -- no
external services, no JS framework, no pixel copying. Highlights missing gates
and non-evidence flags so nothing reads as evidence that is not.
"""
