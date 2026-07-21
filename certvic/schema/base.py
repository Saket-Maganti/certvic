"""Shared schema primitives."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict

SCHEMA_VERSION = "certvic.v1"


class CertVICModel(BaseModel):
    model_config = ConfigDict(use_enum_values=True, validate_assignment=True, extra="forbid")


class TaskFamily(str, Enum):
    SUPPORT_STABILITY = "support_stability"
    OCCLUSION_SAFETY = "occlusion_safety"
    AFFORDANCE_REACHABILITY = "affordance_reachability"
    CONTROL_IRRELEVANT = "control_irrelevant"


class Domain(str, Enum):
    HOUSEHOLD = "household"
    DRIVING = "driving"
    SYNTHETIC_SANITY = "synthetic_sanity"


class EditType(str, Enum):
    REMOVE = "remove"
    OCCLUDE = "occlude"
    DISPLACE = "displace"
    CONTROL_IRRELEVANT = "control_irrelevant"
    CONTROL_COLOR = "control_color"
    CONTROL_TEXTURE = "control_texture"
    NONE = "none"


class RequiredChange(str, Enum):
    CHANGE = "change"
    NO_CHANGE = "no_change"


class AnswerFormat(str, Enum):
    YES_NO = "yes_no"
    MULTIPLE_CHOICE = "multiple_choice"
    SHORT_ACTION = "short_action"


class LicenseCategory(str, Enum):
    CC0 = "cc0"
    PUBLIC_DOMAIN = "public_domain"
    CC_BY = "cc_by"
    RESEARCH_ONLY = "research_only"
    POINTER_ONLY = "pointer_only"
    UNKNOWN = "unknown"


class ProviderType(str, Enum):
    MOCK = "mock"
    OPEN_LOCAL = "open_local"
    FREE_TIER_REFERENCE = "free_tier_reference"
    BASELINE = "baseline"


class ImageVariant(str, Enum):
    ORIGINAL = "original"
    EDITED = "edited"
