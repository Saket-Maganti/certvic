# Model Revision Lock Guide

Resolve each model and processor to a 40-character immutable commit, download the exact snapshot
outside the evidence tree, hash its files, record package/CUDA/GPU details, and fill the registry.
Re-run the execution-mode registry validator and rebuild the code ZIP. A branch, tag, cache name, or
`main` is not an immutable revision. If a snapshot disappears, create a new protocol/run version;
never relabel old outputs.
