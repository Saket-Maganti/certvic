# Fallback Dataset Options

ADE20K remains primary. Fallback adapters are pointer-only plans and do not download data.

| Dataset | Role/status | Pointer-only | Risks |
| --- | --- | --- | --- |
| ADE20K | primary | True | non-redistributable pixels by default |
| Open Images | adapter_stub | True | image licenses vary by source; redistribution must be checked per image; ADE20K remains primary unless access blocks |
| Wikimedia Commons | adapter_stub | True | licenses vary by file; attribution and share-alike requirements may affect releases; CC0/public-domain rows are preferred for paper figures |
