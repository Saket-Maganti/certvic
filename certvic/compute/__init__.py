"""Free-compute job bundles for CertVIC (V3).

Prepares portable, copy-safe job bundles for free Kaggle/Colab sessions
(diffusion edits, VLM inference, ablations, report-only jobs) **without executing
them**. Bundles carry a README, command list, preflight script, resume
instructions, expected inputs/outputs, the zero-cost policy, and a file manifest.
No credentials, no private pixels, no paid endpoints, no execution. Paths are
anonymized to placeholders by default.
"""
