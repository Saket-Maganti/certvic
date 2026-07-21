"""Claim-gated paper result injection and traceability (V3).

Builds a hash-stamped manifest of generated result artifacts, injects only
*eligible* (non-mock / non-simulated, hash-verified) tables/figures into the
paper (dry-run by default, ``--allow-write`` to write), and traces every
injected number back to its artifact. It refuses fabricated or non-evidence
numbers and preserves ``[RESULT REQUIRED]`` placeholders when ineligible.
"""
