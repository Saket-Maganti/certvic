"""Secret / credential / paid-endpoint scanner (V3 prompt 16).

Scans text files for token-like strings (API keys, AWS keys, GitHub tokens,
bearer tokens, private-key headers), committed ``.env`` files, and paid API
endpoints. Static text inspection only; the allowlist exempts files that define
these patterns by design.
"""

from __future__ import annotations

import re
from pathlib import Path

from certvic.security.path_audit import DEFAULT_ALLOWLIST, is_allowlisted, iter_text_files

# (name, compiled regex). Patterns are intentionally conservative.
SECRET_PATTERNS = [
    ("aws_access_key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("github_token", re.compile(r"ghp_[0-9A-Za-z]{36}")),
    ("openai_key", re.compile(r"sk-[A-Za-z0-9]{20,}")),
    ("slack_token", re.compile(r"xox[baprs]-[0-9A-Za-z-]{10,}")),
    ("bearer_token", re.compile(r"(?i)authorization:\s*bearer\s+[A-Za-z0-9._-]{12,}")),
    ("private_key_header", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("generic_api_key_assign", re.compile(r"(?i)(?:api[_-]?key|secret[_-]?key|access[_-]?token)\s*[:=]\s*['\"][A-Za-z0-9/+=_-]{16,}['\"]")),
]

PAID_ENDPOINT_HOSTS = (
    "api.openai.com", "openai.com/v1", "api.anthropic.com", "api.cohere.ai",
    "api.replicate.com", "api.together.xyz", "generativelanguage.googleapis.com",
)


def scan_secrets(root: str, *, allowlist: tuple[str, ...] = DEFAULT_ALLOWLIST) -> dict:
    rootp = Path(root)
    findings: list[dict] = []
    env_files: list[str] = []
    paid_endpoints: list[dict] = []

    # Committed real .env files (".env.example" / templates are fine).
    for path in sorted(rootp.rglob(".env*")):
        if path.is_file() and path.name in {".env", ".env.local", ".env.prod"}:
            rel = path.relative_to(rootp).as_posix()
            if not is_allowlisted(rel, allowlist):
                env_files.append(rel)

    for path, rel in iter_text_files(rootp):
        if is_allowlisted(rel, allowlist):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            for name, pattern in SECRET_PATTERNS:
                if pattern.search(line):
                    findings.append({"file": rel, "line": line_no, "kind": name})
            low = line.lower()
            for host in PAID_ENDPOINT_HOSTS:
                if host in low:
                    paid_endpoints.append({"file": rel, "line": line_no, "host": host})

    ok = not findings and not env_files and not paid_endpoints
    return {
        "scan": "secrets",
        "n_secret_findings": len(findings),
        "secret_findings": findings,
        "committed_env_files": env_files,
        "paid_endpoints": paid_endpoints,
        "ok": ok,
    }
