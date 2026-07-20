"""Composition root: wires the engine objects behind a running graphwerk app."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from graphwerk.apply import ApplyEngine
from graphwerk.commit import CommitEngine
from graphwerk.cycle import SessionCycle
from graphwerk.discard import DiscardEngine
from graphwerk.rationale import RationaleStore
from graphwerk.rationale.guidance import SESSION_GUIDANCE
from graphwerk.server import create_app
from graphwerk.service import GraphService
from graphwerk.session import SessionRunner


def build_app(base: Path, staged: Path, sidecar: Path | None, transcript: Path | None,
              agent_permissions: str,
              check_command: str | None = None, check_retries: int = 1) -> FastAPI:
    rationale = RationaleStore(sidecar_path=sidecar, transcript_path=transcript,
                               staged_root=staged, base_root=base)
    service = GraphService(base, staged, rationale)
    engine = ApplyEngine(base, staged)
    runner = SessionRunner(staged, permission_mode=agent_permissions,
                           system_prompt=SESSION_GUIDANCE)
    cycle = SessionCycle(runner, check_command, max_retries=check_retries)
    commit_engine = CommitEngine(base, engine, service.builder)
    discard_engine = DiscardEngine(base, staged, service.builder)
    return create_app(service, engine, cycle, commit_engine, discard_engine)
