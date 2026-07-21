# CertVIC Thesis

CertVIC is a method-first evaluation pipeline for controlled visual
interventions. It asks whether a model changes or preserves a decision when a
single visual factor is changed under a documented edit recipe.

The central artifact is not a large static benchmark. It is a reproducible,
recipe-first system for source records, masks, edit specs, task manifests,
predictions, metrics, claim gates, and release checks.

Smoke fixtures are `MOCK_ONLY` implementation tests. Real evidence requires
licensed real-image sources, edit quality gates, human validity checks, and
open-model runs.
