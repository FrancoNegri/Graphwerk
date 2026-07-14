# 016. Thread full source text into the snapshot for every node

Status: done
Decision: docs/decisions/004-always-show-source.md

## Goal

Every node in the snapshot — file or symbol, changed or not — carries its
full source text, so the sidebar can show code for nodes that have no diff.

## Acceptance criteria

- `GraphNode` gains a `source: str | None` field, included in `to_dict()`.
- Symbol nodes: `source` is the resolved `SymbolInfo.source` for that
  symbol (staged version if present, else base) — the same `info` already
  resolved in `GraphService.snapshot()` for diffing.
- File nodes: `source` is the file's full staged text, or base text if the
  file was deleted (no staged side). Captured while `FileChange` is built
  in `ChangeSetBuilder` and carried on `FileChange` for `service.py` to
  read — don't re-read the file a second time in `service.py`.
- A file/symbol that no longer exists on either side (shouldn't occur, but)
  yields `source = None` rather than an error.
- Existing `diff`/`why` behavior is unchanged; `source` is additive.

## Likely files

- `graphwerk/models.py` — `GraphNode.source` field + `to_dict()`.
- `graphwerk/staging/differ.py` — `FileChange` captures full text alongside
  the diff it already computes.
- `graphwerk/service.py` — populate `source` for file and symbol nodes.

## Out of scope

Frontend rendering (ticket 017); syntax highlighting; lazy/on-demand
loading.
