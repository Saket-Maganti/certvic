"""Security / privacy / path audit for CertVIC (V3).

Prevents accidental release of private paths, keys/tokens, ``.env`` files, paid
endpoints, local dataset roots, or non-rehostable pixels. Static text inspection
only -- no network, no heavy imports, no evidence claims. A small allowlist
exempts files that legitimately contain example markers (the audit's own pattern
definitions, the path-policy constants, and docs that show examples).
"""
