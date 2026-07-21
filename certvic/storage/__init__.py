"""Storage and path-policy planning for CertVIC (V3).

Prevents disk blowups, private-path leaks, broken symlinks, duplicate output
roots, and release packaging mistakes before large studies run. Planning only:
no real dataset scanning unless a root is explicitly passed, no downloads, no
paid services, no evidence claims.
"""
