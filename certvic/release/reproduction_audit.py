"""Reproduction-script audit (V3 prompt 15).

Statically audits the dockerless reproduction scripts for safety and zero-cost
discipline: a `set -euo pipefail` guard, no destructive `rm -rf`, no paid markers,
no Docker requirement, and documented user-provided paths. Text inspection only;
runs nothing.
"""

from __future__ import annotations

import argparse
import re
from datetime import date
from pathlib import Path

# Paid / credential markers that must not appear in a zero-cost reproduction
# script. Deliberately specific: the bare word "paid" is excluded because the
# scripts' own "no paid services" disclaimers legitimately contain it.
PAID_MARKERS = ("openai", "api_key", "apikey", "secret_key", "bearer ", "sk-", "stripe", "aws s3 cp s3://", "gcloud billing", "x-api-key")
# Destructive patterns to forbid.
DESTRUCTIVE_RE = re.compile(r"rm\s+-rf|rm\s+-fr|mkfs|dd\s+if=")
# Heuristic for a user-provided path placeholder that should be documented.
USER_PATH_RE = re.compile(r"<[A-Z_]+>|\$\{?[A-Z_]+ROOT|ADE20K_ROOT")


def audit_script(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    low = text.lower()
    lines = text.splitlines()

    has_shebang = bool(lines) and lines[0].startswith("#!")
    has_strict = "set -euo pipefail" in text
    destructive = sorted(set(DESTRUCTIVE_RE.findall(text)))
    paid = sorted({m for m in PAID_MARKERS if m in low})
    mentions_docker = "docker" in low
    # Requires a user-provided root only when it passes a raw root path (the
    # --ade20k-root flag), not merely when it names a config file that contains
    # "ade20k". Config files carry the root as data, not a CLI requirement.
    references_dataset_root = "--ade20k-root" in low or "dataset_root" in low
    documents_user_path = bool(USER_PATH_RE.search(text))

    findings: list[str] = []
    if not has_shebang:
        findings.append("missing shebang")
    if not has_strict:
        findings.append("missing 'set -euo pipefail'")
    if destructive:
        findings.append(f"destructive command(s): {destructive}")
    if paid:
        findings.append(f"paid marker(s): {paid}")
    if mentions_docker:
        findings.append("references Docker (should be dockerless)")
    if references_dataset_root and not documents_user_path:
        findings.append("uses a dataset root but does not document the required user-provided path")

    return {
        "script": path.name,
        "path": str(path),
        "has_shebang": has_shebang,
        "has_strict_mode": has_strict,
        "destructive": destructive,
        "paid_markers": paid,
        "mentions_docker": mentions_docker,
        "documents_user_path": documents_user_path,
        "ok": not findings,
        "findings": findings,
    }


def audit_scripts(scripts_dir: str) -> dict:
    sdir = Path(scripts_dir)
    scripts = sorted(sdir.glob("reproduce_*.sh")) if sdir.exists() else []
    audits = [audit_script(s) for s in scripts]
    n_ok = sum(1 for a in audits if a["ok"])
    return {
        "audit": "reproduction_scripts",
        "scripts_dir": str(sdir),
        "n_scripts": len(audits),
        "n_ok": n_ok,
        "passed": bool(audits) and n_ok == len(audits),
        "scripts": audits,
        "no_paid_markers": all(not a["paid_markers"] for a in audits),
        "no_destructive": all(not a["destructive"] for a in audits),
        "dockerless": all(not a["mentions_docker"] for a in audits),
        "evidence_claims_made": False,
    }


def render_report(result: dict) -> str:
    status = "PASS" if result["passed"] else "FAIL"
    lines = [
        "# Reproduction Scripts Audit",
        "",
        f"Generated: {date.today().isoformat()}",
        "",
        f"Scripts dir: `{result['scripts_dir']}`",
        f"Status: **{status}** ({result['n_ok']}/{result['n_scripts']} scripts clean)",
        "",
        f"Dockerless: {result['dockerless']}  |  no paid markers: {result['no_paid_markers']}  |  no destructive commands: {result['no_destructive']}",
        "",
        "| Script | strict mode | docs user path | findings |",
        "| --- | --- | --- | --- |",
    ]
    for a in result["scripts"]:
        lines.append(f"| `{a['script']}` | {a['has_strict_mode']} | {a['documents_user_path']} | {', '.join(a['findings']) or 'ok'} |")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="CertVIC reproduction-script audit")
    parser.add_argument("--scripts", default="scripts")
    parser.add_argument("--out", required=True)
    parser.add_argument("--no-fail", action="store_true")
    args = parser.parse_args(argv)
    result = audit_scripts(args.scripts)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(render_report(result), encoding="utf-8")
    import json

    print(json.dumps({"passed": result["passed"], "n_ok": result["n_ok"], "n_scripts": result["n_scripts"], "out": args.out}, sort_keys=True))
    if not result["passed"] and not args.no_fail:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
