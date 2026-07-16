"""Assembles staging diff + rationale into graph snapshots for the UI."""

from __future__ import annotations

import hashlib
from pathlib import Path

from graphwerk.codeview import build_code_view
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
        # (base_text, staged_text) -> code view; unbounded for the process
        # lifetime (ADR 019, out of scope: eviction/memory bounds).
        self._code_view_cache: dict[tuple[str | None, str | None], list | None] = {}

    def _code_view(self, base_text: str | None, staged_text: str | None) -> list | None:
        if base_text is None and staged_text is None:
            return None
        key = (base_text, staged_text)
        if key not in self._code_view_cache:
            self._code_view_cache[key] = build_code_view(base_text, staged_text)
        return self._code_view_cache[key]

    def snapshot(self) -> Snapshot:
        changes = self.builder.build()
        self.rationale.reload(changed_symbols=self._changed_symbols(changes))
        snap = Snapshot(meta={"rationale": self.rationale.status.to_dict()})
        name_to_ids: dict[str, list[str]] = {}  # simple name -> symbol node ids
        symbol_calls: dict[str, set[str]] = {}  # node id -> called simple names

        for rel, change in changes.items():
            if change.status is Status.UNCHANGED and not change.symbols:
                continue  # e.g. empty __init__.py — pure noise in the graph
            why = self.rationale.why_for(rel) if change.status in CHANGED else None
            snap.nodes.append(
                GraphNode(
                    id=rel,
                    label=rel,
                    kind="file",
                    path=rel,
                    status=change.status,
                    why=why,
                    why_confident=self.rationale.confident_for(rel) if why is not None else None,
                    diff=change.diff or None,
                    source=change.source,
                    code=self._code_view(change.base_source, change.staged_source),
                )
            )
            index = change.staged or change.base
            if index is None:
                continue
            for qualname, (status, diff) in change.symbols.items():
                base_info = change.base.symbols.get(qualname) if change.base else None
                staged_info = change.staged.symbols.get(qualname) if change.staged else None
                info = staged_info or base_info
                if info is None:
                    continue
                node_id = f"{rel}::{qualname}"
                parent = f"{rel}::{qualname.split('.')[0]}" if "." in qualname else rel
                symbol_why = self.rationale.why_for(rel, qualname) if status in CHANGED else None
                snap.nodes.append(
                    GraphNode(
                        id=node_id,
                        label=qualname.split(".")[-1],
                        kind=info.kind,
                        path=rel,
                        status=status,
                        parent=parent,
                        why=symbol_why,
                        why_confident=self.rationale.confident_for(rel, qualname)
                        if symbol_why is not None else None,
                        diff=diff or None,
                        source=info.source,
                        code=self._code_view(
                            base_info.source if base_info else None,
                            staged_info.source if staged_info else None,
                        ),
                    )
                )
                simple = qualname.split(".")[-1]
                name_to_ids.setdefault(simple, []).append(node_id)
                symbol_calls[node_id] = info.calls

        self._add_call_edges(snap, name_to_ids, symbol_calls)
        self._add_import_edges(snap, changes)
        self._mark_affected(snap)
        self._mark_edge_status(snap)
        assign_layers(snap.nodes, snap.edges)
        changed_nodes_exist = any(node.status in CHANGED for node in snap.nodes)
        snap.meta["rationale"]["message"] = self.rationale.status_message(changed_nodes_exist)
        return snap

    @staticmethod
    def _changed_symbols(changes: dict) -> dict[str, list[str]]:
        by_file = {
            rel: [qualname for qualname, (status, _) in change.symbols.items() if status in CHANGED]
            for rel, change in changes.items()
        }
        return {rel: qualnames for rel, qualnames in by_file.items() if qualnames}

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

    def _mark_edge_status(self, snap: Snapshot) -> None:
        """Lets a `calls` edge say whether it leads into changed code, or is
        the reason its source shows `affected` — same review signal as node
        color, moved onto the edge (ADR 016)."""
        status_by_id = {n.id: n.status for n in snap.nodes}
        for edge in snap.edges:
            if edge.kind != "calls":
                continue
            target_status = status_by_id.get(edge.target)
            if target_status in CHANGED:
                edge.status = target_status
            elif status_by_id.get(edge.source) is Status.AFFECTED and target_status is Status.UNCHANGED:
                edge.status = Status.AFFECTED
