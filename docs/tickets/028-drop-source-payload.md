# 028. Drop the redundant source field from the node payload

Status: ready
Decision: docs/decisions/007-sidebar-code-view.md

Depends on: ticket 027 (the UI must no longer read `source`).

## Goal

`code` now carries every node's full text, so shipping `source` too
roughly doubles the text weight of `/api/graph` for no reader. Remove it
from the wire format only.

## Acceptance criteria

- `GraphNode.to_dict()` no longer emits `source`; internal uses
  (`FileChange`, `SymbolInfo`, code-view building) are untouched.
- `grep -rn "node.source\|\.source" static/app.js` shows no remaining
  reader of the payload field.
- Existing tests updated; a service test asserts the key is absent from a
  serialized node while `code` is present.

## Likely files

- `graphwerk/models.py` — `to_dict`
- `tests/test_service.py` (or equivalent) — updated

## Out of scope

Removing `GraphNode.source` the dataclass field if anything internal still
reads it; touching `diff` (the reject payload uses it).
