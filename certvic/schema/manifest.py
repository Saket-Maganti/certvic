"""Run manifest schema."""

from __future__ import annotations

from pydantic import Field

from certvic.schema.base import CertVICModel


class RunManifest(CertVICModel):
    run_id: str
    provider: str
    config_hash: str | None = None
    task_manifest_hash: str | None = None
    timestamp_utc: str
    command_args: dict = Field(default_factory=dict)
    zero_cost_policy_ack: bool = True
    paid_services_used: bool = False
    metadata: dict = Field(default_factory=dict)
