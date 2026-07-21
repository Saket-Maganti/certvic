"""Failure-mode diagnosis and operational playbooks for CertVIC (V3).

When a real run misbehaves, `certvic.playbooks.diagnose_failure` maps observed
symptoms (low quality pass, high detectability, high parse failure, high control
flip, no certified gap, low original accuracy, low human agreement, too few
candidates, GPU preflight failure) to the matching playbook in
`docs/playbooks/`. Read-only diagnosis: no inference, no downloads, no claims.
"""
