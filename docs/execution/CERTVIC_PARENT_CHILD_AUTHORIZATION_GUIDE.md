# CertVIC Parent-Child Authorization Guide

The immutable matrix authorization binds the study, provider set, code, environment, task bundle,
final tasks, task universe, edited images, review, detectability gate, model registry, output schema,
exact prompt template, and expiry. Each provider child binds that parent plus its model revision,
snapshot and root hashes, parser/model contract, run tag, one-run nonce, and run-contract hash.

Model notebooks attach `MATRIX_AUTHORIZATION` and the provider-specific `PROVIDER_PERMISSION`.
Before hardware inspection, CUDA access, adapter import, model loading, or model-output creation they:

1. verify the parent signature, ID, fields, provider membership, and expiry;
2. verify the child signature, ID, parent linkage, provider, run tag, and expiry;
3. derive hashes from active notebook paths and scalars;
4. derive `prompt_template_hash` from the exact active prompt string;
5. derive the frozen run contract and compare its hash with the child;
6. claim the child permission.

A child from a different parent, one changed prompt character, or any active-path drift fails before
the model path is touched. Scientific children additionally require the exact non-synthetic smoke
identity authorized by the gate.

