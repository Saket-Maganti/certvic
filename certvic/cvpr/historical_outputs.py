"""Safe restoration of the separately distributed historical Kaggle outputs."""

from __future__ import annotations

import hashlib
import json
import shutil
import stat
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any


class HistoricalRestoreError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def restore(
    archive: str | Path,
    *,
    manifest: str | Path,
    project_root: str | Path = ".",
    dry_run: bool = False,
) -> dict[str, Any]:
    source = Path(archive).resolve()
    base = Path(project_root).resolve()
    contract = json.loads(Path(manifest).read_text(encoding="utf-8"))
    historical = contract.get("historical_outputs", {})
    expected_hash = historical.get("archive_sha256")
    if not isinstance(expected_hash, str) or len(expected_hash) != 64:
        raise HistoricalRestoreError("distribution manifest has no locked historical archive hash")
    observed_hash = sha256_file(source)
    if observed_hash != expected_hash:
        raise HistoricalRestoreError("historical archive SHA-256 mismatch")
    canonical = str(historical.get("canonical_restore_root", "kaggleoutputs"))
    if canonical != "kaggleoutputs":
        raise HistoricalRestoreError("canonical historical-output root must be kaggleoutputs")
    destination = (base / canonical).resolve()
    if destination.parent != base:
        raise HistoricalRestoreError("restore destination escapes project root")

    planned: list[tuple[zipfile.ZipInfo, Path]] = []
    identical = 0
    with zipfile.ZipFile(source) as handle:
        infos = handle.infolist()
        names = [info.filename for info in infos]
        if len(names) != len(set(names)):
            raise HistoricalRestoreError("historical archive contains duplicate member names")
        for info in infos:
            pure = PurePosixPath(info.filename.replace("\\", "/"))
            if pure.is_absolute() or ".." in pure.parts or not pure.parts:
                raise HistoricalRestoreError(f"unsafe archive member: {info.filename}")
            if pure.parts[0] != canonical:
                raise HistoricalRestoreError(f"member is outside {canonical}: {info.filename}")
            if stat.S_ISLNK((info.external_attr >> 16) & 0xFFFF):
                raise HistoricalRestoreError(f"symlink member prohibited: {info.filename}")
            target = (base / Path(*pure.parts)).resolve()
            if destination != target and destination not in target.parents:
                raise HistoricalRestoreError(f"member escapes canonical root: {info.filename}")
            if info.is_dir():
                continue
            if target.exists():
                if not target.is_file():
                    raise HistoricalRestoreError(f"restore conflict is not a file: {target}")
                digest = hashlib.sha256()
                with handle.open(info) as member:
                    for block in iter(lambda: member.read(1024 * 1024), b""):
                        digest.update(block)
                if digest.hexdigest() != sha256_file(target):
                    raise HistoricalRestoreError(f"conflicting file would be overwritten: {target}")
                identical += 1
                continue
            planned.append((info, target))
        if not dry_run:
            for info, target in planned:
                target.parent.mkdir(parents=True, exist_ok=True)
                try:
                    with handle.open(info) as member, target.open("xb") as output:
                        shutil.copyfileobj(member, output, length=1024 * 1024)
                except FileExistsError as exc:
                    raise HistoricalRestoreError(f"concurrent restore conflict: {target}") from exc
    return {
        "schema": "certvic.historical_outputs_restore.v1",
        "status": "DRY_RUN_PASS" if dry_run else "RESTORE_COMPLETE",
        "archive_sha256": observed_hash,
        "canonical_restore_root": canonical,
        "files_created": len(planned) if not dry_run else 0,
        "files_planned": len(planned),
        "identical_files_preserved": identical,
        "conflicting_files_overwritten": 0,
        "paper_evidence": False,
    }
