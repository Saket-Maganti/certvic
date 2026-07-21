"""CertVIC V2 pipeline orchestrators.

These chain existing stages end to end. They never run VLM inference for the edit
pipeline, never download data, and never make evidence claims.
"""
