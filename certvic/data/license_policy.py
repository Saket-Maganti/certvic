"""License and release-mode policy."""

from __future__ import annotations

from certvic.schema import LicenseCategory, SourceImageRecord


def can_rehost_pixels(license_category: str, redistribution_allowed: bool) -> bool:
    if not redistribution_allowed:
        return False
    return license_category in {
        LicenseCategory.CC0.value,
        LicenseCategory.PUBLIC_DOMAIN.value,
        LicenseCategory.CC_BY.value,
    }


def release_mode_for_source(record: SourceImageRecord) -> str:
    category = str(record.license_category)
    if category in {LicenseCategory.CC0.value, LicenseCategory.PUBLIC_DOMAIN.value}:
        return "pixel_release_ok" if record.redistribution_allowed else "recipe_only"
    if category == LicenseCategory.CC_BY.value:
        if record.redistribution_allowed and record.license_text:
            return "pixel_release_ok"
        return "recipe_only"
    if category in {LicenseCategory.RESEARCH_ONLY.value, LicenseCategory.POINTER_ONLY.value}:
        return "recipe_only"
    return "blocked_until_verified"


def validate_license_for_split(record: SourceImageRecord, split: str) -> list[str]:
    warnings: list[str] = []
    category = str(record.license_category)
    mode = release_mode_for_source(record)
    if category == LicenseCategory.UNKNOWN.value:
        msg = "unknown license"
        if split == "smoke":
            warnings.append(f"warning: {msg} allowed only for smoke")
        else:
            warnings.append(f"blocked: {msg} for split={split}")
    if mode == "blocked_until_verified" and split != "smoke":
        warnings.append("blocked: release mode requires verification")
    if category == LicenseCategory.CC_BY.value and record.redistribution_allowed and not record.license_text:
        warnings.append("warning: cc_by source needs attribution text before pixel release")
    return warnings
