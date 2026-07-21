"""Combined release privacy audit (V3 prompt 16).

Runs the private-path scan, the secrets/paid-endpoint scan, and (for a release
directory) an accidental-pixel scan, then writes a markdown report. Static text
inspection only; no network, no heavy imports, no evidence claims. Critical
before any artifact release.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from certvic.security.path_audit import DEFAULT_ALLOWLIST, scan_private_paths
from certvic.security.secrets_audit import scan_secrets

PIXEL_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp", ".gif"}


def scan_release_pixels(release_dir: str) -> dict:
    rdir = Path(release_dir)
    pixels = [str(p.relative_to(rdir)) for p in sorted(rdir.rglob("*")) if p.is_file() and p.suffix.lower() in PIXEL_EXTS] if rdir.exists() else []
    return {"scan": "release_pixels", "release_dir": str(rdir), "n_pixels": len(pixels), "pixels": pixels, "ok": not pixels}


_SKIPPED_PATHS = {"scan": "private_paths", "n_findings": 0, "findings": [], "ok": True, "skipped": True}
_SKIPPED_SECRETS = {
    "scan": "secrets", "n_secret_findings": 0, "secret_findings": [],
    "committed_env_files": [], "paid_endpoints": [], "ok": True, "skipped": True,
}


def audit(root: str, *, allowlist: tuple[str, ...] = DEFAULT_ALLOWLIST, release_dir: str | None = None) -> dict:
    paths = scan_private_paths(root, allowlist=allowlist)
    secrets = scan_secrets(root, allowlist=allowlist)
    if release_dir:
        pixels = scan_release_pixels(release_dir)
        # The repo-root scans skip the generated "release/" tree, so a private path
        # or a secret living in a release *text* file (config/script/README) would
        # otherwise never be inspected -- only its pixels were. Re-scan the release
        # dir rooted at itself so its contents are not skipped. This is the gate
        # that runs immediately before publishing an artifact.
        release_paths = scan_private_paths(release_dir, allowlist=allowlist)
        release_secrets = scan_secrets(release_dir, allowlist=allowlist)
    else:
        pixels = {"scan": "release_pixels", "release_dir": None, "n_pixels": 0, "pixels": [], "ok": True, "skipped": True}
        release_paths = dict(_SKIPPED_PATHS)
        release_secrets = dict(_SKIPPED_SECRETS)

    passed = paths["ok"] and secrets["ok"] and pixels["ok"] and release_paths["ok"] and release_secrets["ok"]
    n_total_findings = (
        paths["n_findings"]
        + secrets["n_secret_findings"] + len(secrets["committed_env_files"]) + len(secrets["paid_endpoints"])
        + pixels["n_pixels"]
        + release_paths["n_findings"]
        + release_secrets["n_secret_findings"] + len(release_secrets["committed_env_files"]) + len(release_secrets["paid_endpoints"])
    )
    return {
        "audit": "release_privacy",
        "root": root,
        "passed": passed,
        "private_paths": paths,
        "secrets": secrets,
        "release_pixels": pixels,
        "release_private_paths": release_paths,
        "release_secrets": release_secrets,
        "n_total_findings": n_total_findings,
        "evidence_claims_made": False,
    }


def render_report(result: dict) -> str:
    status = "PASS" if result["passed"] else "FAIL"
    p = result["private_paths"]
    s = result["secrets"]
    px = result["release_pixels"]
    rp = result.get("release_private_paths", _SKIPPED_PATHS)
    rs = result.get("release_secrets", _SKIPPED_SECRETS)
    lines = [
        "# Security / Privacy / Path Audit",
        "",
        f"Generated: {date.today().isoformat()}",
        "",
        f"Root: `{result['root']}`",
        f"Status: **{status}** ({result['n_total_findings']} finding(s))",
        "",
        "Static text inspection only; no network, no evidence claims.",
        "",
        "## Summary",
        "",
        "| Check | Findings | OK |",
        "| --- | --- | --- |",
        f"| Private absolute paths / dataset roots | {p['n_findings']} | {p['ok']} |",
        f"| Secrets / credentials | {s['n_secret_findings']} | {not s['secret_findings']} |",
        f"| Committed .env files | {len(s['committed_env_files'])} | {not s['committed_env_files']} |",
        f"| Paid endpoints | {len(s['paid_endpoints'])} | {not s['paid_endpoints']} |",
        f"| Release pixels | {px['n_pixels']} | {px['ok']} |",
        f"| Release-dir private paths (text) | {rp['n_findings']} | {rp['ok']} |",
        f"| Release-dir secrets (text) | {rs['n_secret_findings']} | {not rs['secret_findings']} |",
        "",
    ]
    if rp.get("findings"):
        lines += ["## Release-dir private paths", "", "| File | Line | Kind | Match |", "| --- | --- | --- | --- |"]
        lines += [f"| `{f['file']}` | {f['line']} | {f['kind']} | `{f['match']}` |" for f in rp["findings"][:200]]
        lines.append("")
    if rs.get("secret_findings"):
        lines += ["## Release-dir secrets", "", "| File | Line | Kind |", "| --- | --- | --- |"]
        lines += [f"| `{f['file']}` | {f['line']} | {f['kind']} |" for f in rs["secret_findings"][:200]]
        lines.append("")
    if p["findings"]:
        lines += ["## Private paths", "", "| File | Line | Kind | Match |", "| --- | --- | --- | --- |"]
        lines += [f"| `{f['file']}` | {f['line']} | {f['kind']} | `{f['match']}` |" for f in p["findings"][:200]]
        lines.append("")
    if s["secret_findings"]:
        lines += ["## Secrets", "", "| File | Line | Kind |", "| --- | --- | --- |"]
        lines += [f"| `{f['file']}` | {f['line']} | {f['kind']} |" for f in s["secret_findings"][:200]]
        lines.append("")
    if s["paid_endpoints"]:
        lines += ["## Paid endpoints", "", *[f"- `{e['file']}`:{e['line']} → {e['host']}" for e in s["paid_endpoints"][:200]], ""]
    if px["pixels"]:
        lines += ["## Release pixels (must be recipe-first, not rehosted)", "", *[f"- `{x}`" for x in px["pixels"][:200]], ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="CertVIC release security / privacy / path audit")
    parser.add_argument("--root", default=".")
    parser.add_argument("--release-dir", help="optional: a release dir to scan for accidental pixels")
    parser.add_argument("--allowlist", nargs="*", help="extra path substrings to allowlist")
    parser.add_argument("--out", default="docs/SECURITY_PRIVACY_AUDIT.md")
    parser.add_argument("--json-out")
    parser.add_argument("--no-fail", action="store_true")
    args = parser.parse_args(argv)
    allowlist = DEFAULT_ALLOWLIST + tuple(args.allowlist or ())
    result = audit(args.root, allowlist=allowlist, release_dir=args.release_dir)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(render_report(result), encoding="utf-8")
    if args.json_out:
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"passed": result["passed"], "n_total_findings": result["n_total_findings"], "out": args.out}, sort_keys=True))
    if not result["passed"] and not args.no_fail:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
