"""Assembles staging diff + rationale into graph snapshots for the UI."""

from __future__ import annotations

import hashlib
from pathlib import Path

from graphwerk.indexing.walk import iter_python_files
from graphwerk.layout import assign_layers
from graphwerk.models import GraphEdge, GraphNode, Snapshot, Status
from graphwerk.rationale import RationaleStore
from graphwerk.staging import ChangeSetBuilder

CHANGED = {Status.MODIFIED, Status.ADDED, Status.DELETED}


class ModuleFileResolver:
    """Maps imported module names to repo files, tolerating src/-style
    package roots by matching dotted-path suffixes ("pkg.store" finds
    "src/pkg/store.py")."""

    def __init__(self, rel_paths):
        self._file_by_exact_path: dict[str, str] = {}
        self._files_by_suffix: dict[str, list[str]] = {}
        for rel in rel_paths:
            dotted = rel[:-3].replace("/", ".")
            if dotted == "__init__":
                continue
            if dotted.endswith(".__init__"):
                dotted = dotted.removesuffix(".__init__")
            self._file_by_exact_path[dotted] = rel
            parts = dotted.split(".")
            for start in range(len(parts)):
                suffix = ".".join(parts[start:])
                self._files_by_suffix.setdefault(suffix, []).append(rel)

    def resolve(self, module: str) -> str | None:
        if module in self._file_by_exact_path:
            return self._file_by_exact_path[module]
        matches = self._files_by_suffix.get(module, [])
        return matches[0] if len(matches) == 1 else None


class GraphService:
    def __init__(self, base_root: Path, staged_root: Path, rationale: RationaleStore):
        self.base_root = base_root
        self.staged_root = staged_root
        self.rationale = rationale
        self.builder = ChangeSetBuilder(base_root, staged_root)

    def snapshot(self) -> Snapshot:
        self.rationale.reload()
        changes = self.builder.build()
        snap = Snapshot()
        name_to_ids: dict[str, list[str]] = {}  # simple name -> symbol node ids
        symbol_calls: dict[str, set[str]] = {}  # node id -> called simple names

        for rel, change in changes.items():
            if change.status is Status.UNCHANGED and not change.symbols:
                continue  # e.g. empty __init__.py — pure noise in the graph
            snap.nodes.append(
                GraphNode(
                    id=rel,
                    label=rel,
                    kind="file",
                    path=rel,
                    status=change.status,
                    why=self.rationale.why_for(rel) if change.status in CHANGED else None,
                    diff=change.diff or None,
                    source=change.source,
                )
            )
            index = change.staged or change.base
            if index is None:
                continue
            for qualname, (status, diff) in change.symbols.items():
                info = index.symbols.get(qualname) or (change.base.symbols.get(qualname) if change.base else None)
                if info is None:
                    continue
                node_id = f"{rel}::{qualname}"
                parent = f"{rel}::{qualname.split('.')[0]}" if "." in qualname else rel
                snap.nodes.append(
                    GraphNode(
                        id=node_id,
                        label=qualname.split(".")[-1],
                        kind=info.kind,
                        path=rel,
                        status=status,
                        parent=parent,
                        why=self.rationale.why_for(rel, qualname) if status in CHANGED else None,
                        diff=diff or None,
                        source=info.source,
                    )
                )
                simple = qualname.split(".")[-1]
                name_to_ids.setdefault(simple, []).append(node_id)
                symbol_calls[node_id] = info.calls

        self._add_call_edges(snap, name_to_ids, symbol_calls)
        self._add_import_edges(snap, changes)
        self._mark_affected(snap)
        assign_layers(snap.nodes, snap.edges)
        return snap

    def state_hash(self) -> str:
        """Cheap fingerprint of both trees; the UI polls this to know when to refetch."""
        digest = hashlib.md5()
        for root in (self.base_root, self.staged_root):
            for path, rel in iter_python_files(root):
                stat = path.stat()
                digest.update(f"{rel}:{stat.st_mtime_ns}:{stat.st_size};".encode())
        return digest.hexdigest()

    def _add_call_edges(self, snap: Snapshot, name_to_ids: dict, symbol_calls: dict) -> None:
        seen: set[tuple[str, str]] = set()
        for source_id, calls in symbol_calls.items():
            for name in calls:
                for target_id in name_to_ids.get(name, []):
                    if target_id == source_id or (source_id, target_id) in seen:
                        continue
                    seen.add((source_id, target_id))
                    snap.edges.append(GraphEdge(source_id, target_id, "calls"))

    def _add_import_edges(self, snap: Snapshot, changes: dict) -> None:
        resolver = ModuleFileResolver(changes)
        for rel, change in changes.items():
            index = change.staged or change.base
            if index is None:
                continue
            for module in index.imports:
                target = resolver.resolve(module)
                if target and target != rel:
                    snap.edges.append(GraphEdge(rel, target, "imports"))

    def _mark_affected(self, snap: Snapshot) -> None:
        """Yellow ring: unchanged symbols that call into changed ones (human blast radius)."""
        status_by_id = {n.id: n.status for n in snap.nodes}
        changed = {nid for nid, st in status_by_id.items() if st in CHANGED}
        affected = {
            e.source
            for e in snap.edges
            if e.kind == "calls" and e.target in changed and status_by_id.get(e.source) is Status.UNCHANGED
        }
        for node in snap.nodes:
            if node.id in affected:
                node.status = Status.AFFECTED
