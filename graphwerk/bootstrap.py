"""Composition root: wires the engine objects behind a running graphwerk app."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from graphwerk.apply import ApplyEngine
from graphwerk.approval import ApprovalStore
from graphwerk.commit import CommitEngine
from graphwerk.cycle import SessionCycle
from graphwerk.discard import DiscardEngine
from graphwerk.rationale import RationaleStore
from graphwerk.rationale.guidance import SESSION_GUIDANCE
from graphwerk.server import create_app
from graphwerk.service import GraphService
from graphwerk.session import SessionRunner


def build_app(repo: Path, base_ref: str, sidecar: Path | None, transcript: Path | None,
              agent_permissions: str,
              check_command: str | None = None, check_retries: int = 1) -> FastAPI:
    rationale = RationaleStore(sidecar_path=sidecar, transcript_path=transcript,
                               staged_root=repo, base_root=repo)
    approval_store = ApprovalStore(repo)
    service = GraphService(repo, base_ref, rationale, approval_store)
    # ADR 058: there is no second directory anymore — base and staged are
    # both `repo`. The mutation engines below become unreachable in
    # practice (ticket 159 deletes them and their endpoints); they're wired
    # here only so `create_app`'s existing signature keeps working until then.
    engine = ApplyEngine(repo, repo)
    runner = SessionRunner(repo, permission_mode=agent_permissions,
                           system_prompt=SESSION_GUIDANCE)
    cycle = SessionCycle(runner, check_command, max_retries=check_retries)
    commit_engine = CommitEngine(repo, engine, service.builder, approval_store)
    discard_engine = DiscardEngine(repo, repo, service.builder)
    return create_app(service, engine, cycle, commit_engine, discard_engine, approval_store)
