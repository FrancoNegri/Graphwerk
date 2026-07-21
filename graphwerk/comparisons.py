"""Builds and caches a `GraphService` per `(base, staged)` ref pair (ADR
060), so the server can serve any requested comparison without restarting.
Only the pair where `staged` resolves to the working directory is "live":
that's the one pair a running Claude session can actually be narrating, so
it's the only one that gets real rationale mining (ticket 171) — every
other pair gets a no-op rationale rather than a misattributed one.
"""

from __future__ import annotations

from pathlib import Path

from graphwerk.rationale import NullRationaleStore, RationaleStore
from graphwerk.service import WORKING_TREE_TOKEN, GraphService

__all__ = ["ComparisonRegistry", "WORKING_TREE_TOKEN"]


class ComparisonRegistry:
    def __init__(self, repo_root: Path, base_ref: str, staged_ref: str = WORKING_TREE_TOKEN,
                 sidecar_path: Path | None = None, transcript_path: Path | None = None):
        self.repo_root = repo_root
        self.default_base = base_ref
        self.default_staged = staged_ref
        self.sidecar_path = sidecar_path
        self.transcript_path = transcript_path
        # (base, staged) -> GraphService; unbounded for the process lifetime
        # (ADR 019's existing posture — see GraphService's own caches).
        self._services: dict[tuple[str, str], GraphService] = {}

    def get(self, base: str | None = None, staged: str | None = None) -> GraphService:
        base = base if base is not None else self.default_base
        staged = staged if staged is not None else self.default_staged
        key = (base, staged)
        service = self._services.get(key)
        if service is None:
            service = GraphService(self.repo_root, base, self._rationale_for(staged), staged_ref=staged)
            self._services[key] = service
        return service

    def _rationale_for(self, staged: str) -> RationaleStore | NullRationaleStore:
        if staged != WORKING_TREE_TOKEN:
            return NullRationaleStore()
        return RationaleStore(
            sidecar_path=self.sidecar_path, transcript_path=self.transcript_path, staged_root=self.repo_root
        )
