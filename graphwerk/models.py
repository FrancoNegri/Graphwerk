"""Core domain model shared by all layers."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Status(str, Enum):
    UNCHANGED = "unchanged"
    MODIFIED = "modified"
    ADDED = "added"
    DELETED = "deleted"
    AFFECTED = "affected"  # unchanged itself, but calls into changed code


@dataclass
class SymbolInfo:
    """A named unit of code inside one file (class, function, or method)."""

    qualname: str  # e.g. "PaymentGateway.charge"
    kind: str  # "class" | "function" | "method"
    lineno: int
    end_lineno: int
    source: str
    calls: set[str] = field(default_factory=set)  # simple names this symbol calls


@dataclass
class FileIndex:
    """Everything the indexer extracted from a single file."""

    rel_path: str
    symbols: dict[str, SymbolInfo] = field(default_factory=dict)  # qualname -> info
    imports: set[str] = field(default_factory=set)  # imported module names
    parse_error: str | None = None


@dataclass
class GraphNode:
    id: str  # "<rel_path>" for files, "<rel_path>::<qualname>" for symbols
    label: str
    kind: str  # "file" | "class" | "function" | "method"
    path: str
    status: Status = Status.UNCHANGED
    parent: str | None = None  # file node id for symbols, class node id for methods
    why: str | None = None
    why_confident: bool | None = None  # False: proximity fallback, not a real mention
    why_justifies: bool | None = None  # False: describes the code rather than arguing for the change
    diff: str | None = None
    layer: int | None = None  # layout band; files and top-level functions only
    order: int | None = None  # left-to-right position within the layer; same contract as layer
    group: str | None = None  # top-level directory of path; files only, None for symbols
    source: str | None = None  # full text of the node, changed or not
    code: list | None = None  # merged diff/highlight line view (see codeview.py)
    is_test: bool = False  # path matches the pytest discovery convention

    def to_dict(self) -> dict:
        payload = {
            "id": self.id,
            "label": self.label,
            "kind": self.kind,
            "path": self.path,
            "status": self.status.value,
            "parent": self.parent,
            "why": self.why,
            "why_confident": self.why_confident,
            "why_justifies": self.why_justifies,
            "diff": self.diff,
            "layer": self.layer,
            "order": self.order,
            "group": self.group,
            "code": self.code,
        }
        if self.is_test:
            payload["is_test"] = True
        return payload


@dataclass
class GraphEdge:
    source: str
    target: str
    kind: str  # "calls" | "imports"
    status: Status = Status.UNCHANGED
    module: str | None = None  # imports-kind only: the module name responsible for the edge
    # calls-kind, cross-file only: [{"module", "status"}] for each import
    # of the caller's file that admits the target's file
    via_imports: list | None = None

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "target": self.target,
            "kind": self.kind,
            "status": self.status.value,
            "module": self.module,
            "via_imports": self.via_imports,
        }


@dataclass
class Snapshot:
    """One consistent view of base tree + staged tree, ready for the UI."""

    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)
    meta: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "meta": self.meta,
        }
