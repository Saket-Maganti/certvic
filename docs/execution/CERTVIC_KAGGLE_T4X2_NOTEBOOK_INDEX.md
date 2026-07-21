
# CertVIC CVPR Kaggle Notebook Index

The exact suite has 16 notebooks: 00A, 00B, 00C1, 00C2; confirmatory 01-04; Main 10-13; and COCO
20-23. The manifest at `notebooks/kaggle/cvpr/notebook_manifest.json` is authoritative for bytes.
00C1 is mock-only; 00C2 is real-model-only. Generation applies one global bound and launches both T4
workers concurrently. Evaluation uses one process per visible T4 with a declared single-GPU fallback.
