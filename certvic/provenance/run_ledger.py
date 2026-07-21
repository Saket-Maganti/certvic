"""Central run ledger for CertVIC provenance (V3 prompt 01).

The ledger is an append-only JSONL file. Each line is one :class:`LedgerEntry`
describing a single stage of work: what command/config produced it, the hashes
of every input and output artifact, the evidence status, and the zero-cost
policy acknowledgement. Hashes let later audits detect missing or mutated
artifacts; the evidence status lets claim gates refuse non-evidence provenance.

This module is import-safe and never downloads data, runs GPU jobs, calls paid
services, or makes evidence claims. Hashing only reads files that already exist
on disk; missing paths are recorded as ``null`` rather than fetched.
"""

from __future__ import annotations

import argparse
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from certvic.hashing import sha256_bytes, sha256_file, stable_json_dumps
from certvic.io import append_jsonl, ensure_parent, read_jsonl

LEDGER_SCHEMA_VERSION = "certvic.provenance.v1"

DEFAULT_LEDGER_PATH = "data/provenance/run_ledger.jsonl"

# Recommended (not enforced) stage names; free-form stages are allowed but
# warned about so the ledger stays greppable across the pipeline.
KNOWN_STAGES = (
    "source_manifest",
    "mask_generation",
    "edit_planning",
    "edit_generation",
    "quality_gates",
    "visual_review",
    "task_build",
    "vlm_inference",
    "scoring",
    "certification",
    "ablation",
    "report",
    "release",
    "paper",
)

# Evidence statuses that are *eligible* to back a certified claim. Everything
# else (mock/simulated/planned/preview) is non-evidence by construction. Kept in
# sync with certvic.validation.claims.NON_EVIDENCE_STATUSES.
EVIDENCE_ELIGIBLE_STATUSES = {"REAL_EVIDENCE", "EVIDENCE_ELIGIBLE", "REAL_PILOT", "REAL_MAIN"}


class LedgerEntry(BaseModel):
    """A single provenance record. Stable, JSON-serializable, ``extra`` forbidden."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    stage: str
    timestamp_utc: str
    command: str = ""
    config_hash: str | None = None
    input_hashes: dict[str, str | None] = Field(default_factory=dict)
    output_hashes: dict[str, str | None] = Field(default_factory=dict)
    evidence_status: str = "UNKNOWN"
    zero_cost: bool = True
    paid_services_used: bool = False
    environment: dict = Field(default_factory=dict)
    user_notes: str = ""
    schema_version: str = LEDGER_SCHEMA_VERSION


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def environment_summary() -> dict:
    """Light, import-safe environment summary (no heavy imports)."""
    import importlib.util

    def have(mod: str) -> bool:
        try:
            return importlib.util.find_spec(mod) is not None
        except Exception:
            return False

    return {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "executable": sys.executable.rsplit("/", 1)[-1],
        "numpy_available": have("numpy"),
        "pandas_available": have("pandas"),
        "torch_available": have("torch"),
        "diffusers_available": have("diffusers"),
        "confseq_available": have("confseq"),
    }


def hash_path(path: str | Path) -> str | None:
    """Stable hash of a file or directory; ``None`` when the path is missing.

    Directories are hashed as the stable hash of their relative-path -> file-hash
    map so renaming a directory's contents changes the digest deterministically.
    Remote / planned / simulated pointers (``http``, ``planned://``, ...) are not
    fetched; they hash to ``None``.
    """
    text = str(path)
    if text.startswith(("http://", "https://", "planned://", "simulated://", "s3://", "gs://")):
        return None
    p = Path(path)
    if p.is_file():
        return sha256_file(p)
    if p.is_dir():
        members: dict[str, str] = {}
        for child in sorted(p.rglob("*")):
            if child.is_file():
                members[str(child.relative_to(p))] = sha256_file(child)
        return sha256_bytes(stable_json_dumps(members).encode("utf-8"))
    return None


def _hash_paths(paths: list[str] | None) -> dict[str, str | None]:
    return {str(p): hash_path(p) for p in (paths or [])}


def init_ledger(path: str | Path = DEFAULT_LEDGER_PATH, *, exist_ok: bool = True) -> Path:
    """Create an empty ledger file. Refuses to clobber an existing one unless asked."""
    p = Path(path)
    if p.exists() and not exist_ok:
        raise FileExistsError(f"ledger already exists: {p}")
    ensure_parent(p)
    if not p.exists():
        p.write_text("", encoding="utf-8")
    return p


def add_entry(
    *,
    ledger_path: str | Path = DEFAULT_LEDGER_PATH,
    run_id: str,
    stage: str,
    command: str = "",
    config: str | Path | None = None,
    inputs: list[str] | None = None,
    outputs: list[str] | None = None,
    evidence_status: str = "UNKNOWN",
    paid_services_used: bool = False,
    user_notes: str = "",
    timestamp_utc: str | None = None,
) -> LedgerEntry:
    """Append a fully hashed provenance entry to the ledger and return it."""
    entry = LedgerEntry(
        run_id=run_id,
        stage=stage,
        timestamp_utc=timestamp_utc or _now_utc(),
        command=command,
        config_hash=hash_path(config) if config else None,
        input_hashes=_hash_paths(inputs),
        output_hashes=_hash_paths(outputs),
        evidence_status=str(evidence_status).upper(),
        zero_cost=not paid_services_used,
        paid_services_used=bool(paid_services_used),
        environment=environment_summary(),
        user_notes=user_notes,
    )
    ensure_parent(ledger_path)
    append_jsonl(ledger_path, entry.model_dump(mode="json"))
    return entry


def load_ledger(path: str | Path = DEFAULT_LEDGER_PATH) -> list[LedgerEntry]:
    """Load and validate every entry; raises on malformed rows."""
    return [LedgerEntry.model_validate(row) for row in read_jsonl(path)]


def is_evidence_status(status: str | None) -> bool:
    return str(status or "").upper() in EVIDENCE_ELIGIBLE_STATUSES


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="CertVIC run ledger (provenance)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="create an empty ledger")
    p_init.add_argument("--out", default=DEFAULT_LEDGER_PATH)
    p_init.add_argument("--force", action="store_true", help="overwrite an existing ledger")

    p_add = sub.add_parser("add", help="append a provenance entry")
    p_add.add_argument("--ledger", default=DEFAULT_LEDGER_PATH)
    p_add.add_argument("--stage", required=True)
    p_add.add_argument("--run-id", required=True)
    p_add.add_argument("--inputs", nargs="*", default=[])
    p_add.add_argument("--outputs", nargs="*", default=[])
    p_add.add_argument("--config")
    p_add.add_argument("--command", default="")
    p_add.add_argument("--evidence-status", default="UNKNOWN")
    p_add.add_argument("--paid-services-used", action="store_true")
    p_add.add_argument("--notes", default="")

    args = parser.parse_args(argv)

    if args.cmd == "init":
        if args.force and Path(args.out).exists():
            Path(args.out).unlink()
        path = init_ledger(args.out, exist_ok=True)
        print(stable_json_dumps({"action": "init", "ledger": str(path)}))
        return

    if args.cmd == "add":
        if args.stage not in KNOWN_STAGES:
            print(stable_json_dumps({"warning": f"non-standard stage '{args.stage}'", "known_stages": list(KNOWN_STAGES)}))
        entry = add_entry(
            ledger_path=args.ledger,
            run_id=args.run_id,
            stage=args.stage,
            command=args.command,
            config=args.config,
            inputs=args.inputs,
            outputs=args.outputs,
            evidence_status=args.evidence_status,
            paid_services_used=args.paid_services_used,
            user_notes=args.notes,
        )
        missing_in = sorted(k for k, v in entry.input_hashes.items() if v is None)
        missing_out = sorted(k for k, v in entry.output_hashes.items() if v is None)
        print(stable_json_dumps({
            "action": "add",
            "ledger": args.ledger,
            "run_id": entry.run_id,
            "stage": entry.stage,
            "evidence_status": entry.evidence_status,
            "missing_inputs": missing_in,
            "missing_outputs": missing_out,
        }))


if __name__ == "__main__":
    main()
