
# CertVIC Offline Kaggle Environment Guide

Lock: `configs/runtime/kaggle_t4x2_environment.lock.json`  
Current canonical lock SHA-256: `b9b306991f7b0d25bc90306741761d5a93c4e92605f0c9077b2e8f587ff46182`.

The lock is a structured target, not observed Kaggle compatibility. Stage every wheel outside the
offline run, then hash it with `scripts/build_cvpr_wheelhouse_manifest.py`. On Kaggle install only via
`pip --no-index --find-links ... --require-hashes`; any missing, extra, or changed wheel is terminal.
00A validates Python, exact package versions, CUDA topology, code ZIP bytes, package source, and
offline environment variables. Do not use internet fallback or mutate the lock in a running study.
The target remains `STRUCTURED_TARGET_REQUIRES_LEVEL3_KAGGLE_VERIFICATION` until 00A passes on T4 x2.
