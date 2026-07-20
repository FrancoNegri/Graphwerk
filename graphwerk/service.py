"""Assembles staging diff + rationale into graph snapshots for the UI."""

from __future__ import annotations

import hashlib
from collections import deque
from pathlib import Path

from graphwerk.approval import ApprovalStore
from graphwerk.codeview import build_code_view
from graphwerk.highlight import highlight_lines
from graphwerk.indexing.walk import iter_markdown_files, iter_python_files
from graphwerk.layout import assign_layers, is_test_path
from graphwerk.models import GraphEdge, GraphNode, Snapshot, Status, SymbolInfo
from graphwerk.rationale import RationaleStore
from graphwerk.staging import ChangeSetBuilder

CHANGED = {Status.MODIFIED, Status.ADDED, Status.DELETED}


def _domain_for(rel: str) -> str:
    """Direct readout of the differ's own extractor dispatch (ticket 125):
    ".md" goes to MarkdownExtractor, everything else to PythonAstExtractor."""
    return "doc" if rel.endswith(".md") else "code"


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
    def __init__(self, base_root: Path, staged_root: Path, rationale: RationaleStore,
                 approval_store: ApprovalStore):
        self.base_root = base_root
        self.staged_root = staged_root
        self.rationale = rationale
        self.approval_store = approval_store
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
        snap = Snapshot(meta={
            "rationale": self.rationale.status.to_dict(),
            # null (not absent) when no message was mined, so the UI can
            # tell "no message" apart from an old payload (ADR 037)
            "commit_message": self.rationale.commit_message,
        })
        name_to_ids: dict[str, list[str]] = {}  # simple name -> symbol node ids
        symbol_calls: dict[str, set[str]] = {}  # node id -> called simple names

        for rel, change in changes.items():
            if change.status is Status.UNCHANGED and not change.symbols:
                continue  # e.g. empty __init__.py — pure noise in the graph
            why = self.rationale.why_for(rel) if change.status in CHANGED else None
            domain = _domain_for(rel)
            snap.nodes.append(
                GraphNode(
                    id=rel,
                    label=rel,
                    kind="file",
                    path=rel,
                    status=change.status,
                    why=why,
                    why_confident=self.rationale.confident_for(rel) if why is not None else None,
                    why_justifies=self.rationale.justifies_for(rel) if why is not None else None,
                    diff=change.diff or None,
                    source=change.source,
                    code=self._code_view(change.base_source, change.staged_source),
                    is_test=is_test_path(rel),
                    domain=domain,
                    approved=self.approval_store.is_approved(rel),
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
                        why_justifies=self.rationale.justifies_for(rel, qualname)
                        if symbol_why is not None else None,
                        diff=diff or None,
                        source=info.source,
                        code=self._code_view(
                            base_info.source if base_info else None,
                            staged_info.source if staged_info else None,
                        ),
                        is_test=is_test_path(rel),
                        domain=domain,
                    )
                )
                simple = qualname.split(".")[-1]
                name_to_ids.setdefault(simple, []).append(node_id)
                symbol_calls[node_id] = info.calls

        resolver = ModuleFileResolver(changes)
        self._add_call_edges(snap, name_to_ids, symbol_calls, changes, resolver)
        self._add_import_edges(snap, changes, resolver)
        self._add_reference_edges(snap, changes)
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
            for path, rel in (*iter_python_files(root), *iter_markdown_files(root)):
                stat = path.stat()
                digest.update(f"{rel}:{stat.st_mtime_ns}:{stat.st_size};".encode())
        return digest.hexdigest()

    def _add_call_edges(
        self, snap: Snapshot, name_to_ids: dict, symbol_calls: dict, changes: dict, resolver: ModuleFileResolver
    ) -> None:
        """Only wires a caller to targets that (a) shared a parsed tree with
        it (ADR 032) and (b) live in a file the caller can actually reach —
        its own file, or a file resolved from its relevant tree's imports
        (ADR 034). A deleted caller's calls/imports came from base_info, so
        both checks resolve within base; every other caller's came from
        staged_info, so both resolve within staged. Without (a), a relocated
        symbol's old and new copies (same simple name, one deleted, one
        added) would wire together despite never having coexisted in either
        tree. Without (b), any two same-named symbols anywhere in the repo
        would wire together regardless of whether either file can see the
        other (the agendabot phantom-edge case)."""
        status_by_id = {n.id: n.status for n in snap.nodes}
        path_by_id = {n.id: n.path for n in snap.nodes}
        admitting_modules_cache: dict[tuple[str, bool], dict[str, list[str]]] = {}
        reachable_files_cache: dict[tuple[str, bool], frozenset[str]] = {}

        def admitting_modules_by_file(rel: str, caller_deleted: bool) -> dict[str, list[str]]:
            key = (rel, caller_deleted)
            cached = admitting_modules_cache.get(key)
            if cached is not None:
                return cached
            change = changes.get(rel)
            index = (change.base if caller_deleted else change.staged) if change else None
            modules_by_file: dict[str, list[str]] = {}
            if index:
                for module in sorted(index.imports):
                    target = resolver.resolve(module)
                    if target:
                        modules_by_file.setdefault(target, []).append(module)
            admitting_modules_cache[key] = modules_by_file
            return modules_by_file

        def reachable_files(rel: str, caller_deleted: bool) -> frozenset[str]:
            """Files reachable from `rel` by repeatedly following resolved
            imports, staying within the same tree at every hop (ADR 048).
            `visited` also guards against cyclic import graphs."""
            key = (rel, caller_deleted)
            cached = reachable_files_cache.get(key)
            if cached is not None:
                return cached
            visited = {rel}
            frontier = [rel]
            while frontier:
                current = frontier.pop()
                for target in admitting_modules_by_file(current, caller_deleted):
                    if target not in visited:
                        visited.add(target)
                        frontier.append(target)
            result = frozenset(visited)
            reachable_files_cache[key] = result
            return result

        def admitting_entry(rel: str, module: str, caller_deleted: bool, caller_symbol: SymbolInfo | None) -> dict:
            change = changes[rel]
            index = change.base if caller_deleted else change.staged
            # First statement in the module's list — caller-scoped selection
            # among multiple statements is ticket 148; this keeps today's
            # first-wins behavior over the new list shape (ticket 147).
            statements = index.import_statements.get(module)
            statement = statements[0] if statements else None
            return {
                "module": module,
                "status": change.imports[module].value,
                "code": _statement_code_lines(statement, change.imports[module]),
                "in_caller_code": _statement_in_caller_span(statement, caller_symbol),
            }

        def import_chain(caller_rel: str, target_rel: str, caller_deleted: bool) -> list[tuple[str, str, str]] | None:
            """Shortest chain of resolved imports from caller_rel to
            target_rel, as (from_file, module, to_file) hops — the same
            reachability `reachable_files` computes, but keeping the path
            that got there (ADR 048's deferred multi-hop provenance)."""
            parent: dict[str, tuple[str, str]] = {}
            visited = {caller_rel}
            frontier = deque([caller_rel])
            while frontier:
                current = frontier.popleft()
                for next_file, modules in admitting_modules_by_file(current, caller_deleted).items():
                    if next_file in visited:
                        continue
                    visited.add(next_file)
                    parent[next_file] = (current, modules[0])
                    frontier.append(next_file)
            if target_rel not in parent:
                return None
            hops: list[tuple[str, str, str]] = []
            node = target_rel
            while node != caller_rel:
                from_file, module = parent[node]
                hops.append((from_file, module, node))
                node = from_file
            hops.reverse()
            return hops

        def via_imports_entries(
            caller_rel: str, target_rel: str, modules_by_file: dict, caller_deleted: bool, source_id: str
        ) -> list | None:
            if target_rel == caller_rel:
                return None
            change = changes[caller_rel]
            index = change.base if caller_deleted else change.staged
            caller_qualname = source_id.split("::", 1)[1]
            caller_symbol = index.symbols.get(caller_qualname)
            if target_rel in modules_by_file:
                return [
                    admitting_entry(caller_rel, module, caller_deleted, caller_symbol)
                    for module in modules_by_file[target_rel]
                ]
            chain = import_chain(caller_rel, target_rel, caller_deleted)
            if chain is None:
                return None
            return [
                {
                    **admitting_entry(from_file, module, caller_deleted, caller_symbol if from_file == caller_rel else None),
                    "file": to_file,
                }
                for from_file, module, to_file in chain
            ]

        seen: set[tuple[str, str]] = set()
        for source_id, calls in symbol_calls.items():
            caller_deleted = status_by_id.get(source_id) is Status.DELETED
            allowed_target_statuses = (
                {Status.DELETED, Status.MODIFIED, Status.UNCHANGED}
                if caller_deleted
                else {Status.ADDED, Status.MODIFIED, Status.UNCHANGED}
            )
            caller_rel = path_by_id.get(source_id)
            modules_by_file = admitting_modules_by_file(caller_rel, caller_deleted)
            allowed_files = reachable_files(caller_rel, caller_deleted)
            for name in calls:
                for target_id in name_to_ids.get(name, []):
                    if target_id == source_id or (source_id, target_id) in seen:
                        continue
                    if status_by_id.get(target_id) not in allowed_target_statuses:
                        continue
                    target_rel = path_by_id.get(target_id)
                    if target_rel not in allowed_files:
                        continue
                    seen.add((source_id, target_id))
                    via_imports = via_imports_entries(
                        caller_rel, target_rel, modules_by_file, caller_deleted, source_id
                    )
                    snap.edges.append(GraphEdge(source_id, target_id, "calls", via_imports=via_imports))

    def _add_import_edges(self, snap: Snapshot, changes: dict, resolver: ModuleFileResolver) -> None:
        for rel, change in changes.items():
            base_index, staged_index = change.base, change.staged
            all_modules = (base_index.imports if base_index else set()) | (
                staged_index.imports if staged_index else set()
            )
            for module in all_modules:
                target = resolver.resolve(module)
                if target and target != rel:
                    snap.edges.append(GraphEdge(rel, target, "imports", change.imports[module], module))

    def _add_reference_edges(self, snap: Snapshot, changes: dict) -> None:
        """Doc-to-doc links (ADR 046): targets already resolved to
        repo-root-relative paths at extraction time, so this only needs to
        check the target is an actual tracked file — an unresolvable link
        (external URL, path outside the tree) simply isn't a key in
        `changes` and is silently skipped, same posture as import
        resolution."""
        for rel, change in changes.items():
            for target, status in change.references.items():
                if target != rel and target in changes:
                    snap.edges.append(GraphEdge(rel, target, "references", status))

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
        """Lets a `calls` edge say whether it leads into changed code — same
        review signal as node color, moved onto the edge (ADR 016). A call
        into unchanged code stays `unchanged` even when its source is
        `affected` via some *other* call: `affected` only ever describes the
        edge that itself targets changed code, and that edge already gets
        the target's real status below, so no edge is ever "affected" —
        an unrelated call from an affected node carries no information about
        the change itself."""
        status_by_id = {n.id: n.status for n in snap.nodes}
        for edge in snap.edges:
            if edge.kind != "calls":
                continue
            target_status = status_by_id.get(edge.target)
            if target_status in CHANGED:
                edge.status = target_status


_IMPORT_STATUS_TO_OP = {Status.ADDED: "add", Status.DELETED: "del"}


def _statement_in_caller_span(statement: tuple[str, int] | None, caller_symbol: SymbolInfo | None) -> bool:
    """True when the import statement's start line falls inside the caller
    symbol's own line span (nested imports, ticket 065) rather than at the
    top of the file."""
    if statement is None or caller_symbol is None:
        return False
    _, start_line = statement
    return caller_symbol.lineno <= start_line <= caller_symbol.end_lineno


def _statement_code_lines(statement: tuple[str, int] | None, status: Status) -> list | None:
    """Render one import statement in the code-view line shape the panel
    already consumes (ADR 038), so the frontend reuses renderCode as-is."""
    if statement is None:
        return None
    text, start_line = statement
    op = _IMPORT_STATUS_TO_OP.get(status, "ctx")
    spans_per_line = highlight_lines(text)
    return [
        {
            "text": line_text,
            "op": op,
            "line": start_line + offset,
            "spans": [list(span) for span in spans_per_line[offset]],
        }
        for offset, line_text in enumerate(text.splitlines())
    ]
