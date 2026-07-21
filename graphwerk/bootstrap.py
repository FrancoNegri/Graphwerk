"""Composition root: wires the engine objects behind a running graphwerk app."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from graphwerk.comparisons import ComparisonRegistry
from graphwerk.cycle import SessionCycle
from graphwerk.rationale.guidance import SESSION_GUIDANCE
from graphwerk.server import create_app
from graphwerk.session import SessionRunner


def build_app(repo: Path, base_ref: str, sidecar: Path | None, transcript: Path | None,
              agent_permissions: str,
              check_command: str | None = None, check_retries: int = 1) -> FastAPI:
    registry = ComparisonRegistry(repo, base_ref, sidecar_path=sidecar, transcript_path=transcript)
    runner = SessionRunner(repo, permission_mode=agent_permissions,
                           system_prompt=SESSION_GUIDANCE)
    cycle = SessionCycle(runner, check_command, max_retries=check_retries)
    return create_app(registry, cycle)
