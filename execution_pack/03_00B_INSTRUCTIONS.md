# 00B: immutable model snapshot smoke

Run `notebooks/kaggle/cvpr/00B_certvic_model_snapshot_smoke.ipynb` once for each provider in isolated
Kaggle T4x2 sessions after 00A passes. Inputs are the accepted 00A bundle, one unified offline model
and processor snapshot, the frozen model registry, and the generated provider config. Budget 20–45
minutes per provider.

Expected files are `00B_<provider>_snapshot.json`, its validation JSON, and its bundle ZIP. Validation
requires exact model/processor commits, every snapshot file hash, expected architecture, offline load,
and teardown. Copy unchanged files to `data/runtime/`; never copy hashes between provider manifests.

After all three pass, build the pre-smoke matrix authorization using the exact command and arguments
printed by the notebook/handoff. Derive one provider child per snapshot. These permissions authorize
only 00C2 and cannot authorize confirmatory or Main inference.

Retry a failed provider in a new session with the same snapshot bytes. If bytes change, regenerate the
snapshot manifest and reissue downstream pre-smoke authorization.

