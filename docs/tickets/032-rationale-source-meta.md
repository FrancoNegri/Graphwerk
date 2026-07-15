# 032. Snapshot meta reports rationale sources

Status: ready
Decision: docs/decisions/009-rationale-fails-loudly.md

## Goal

The `/api/graph` payload says which rationale sources were actually loaded
— sidecar path, transcript path, entries mined — instead of degrading to
"no why anywhere" silently.

## Acceptance criteria

- After `reload()`, `RationaleStore` exposes a status object: sidecar path
  used or `None`, transcript path used (explicit or discovered) or `None`,
  and the count of mined/loaded rationale entries.
- `Snapshot` gains a `meta` field; `GraphService.snapshot()` fills
  `meta["rationale"]` from the store's status. Serialization includes it
  in the `/api/graph` response.
- Demo instance: meta shows the sidecar path and a nonzero entry count.
- A store pointed at a staged root with no project dir under
  `~/.claude/projects/` reports transcript `None` and zero transcript
  entries (pytest, using a tmp claude dir).
- Existing payload fields and the `/api/hash` contract are unchanged.

## Likely files

- `graphwerk/rationale/miner.py` — expose source status after reload
- `graphwerk/models.py` — `Snapshot.meta`
- `graphwerk/service.py` — copy status into the snapshot
- `tests/` — coverage for store status and snapshot meta

## Out of scope

- The misplaced-session warning (ticket 033) — `warning` can ship here as
  an always-`None` placeholder key or be added in 033, implementer's call.
- Any UI rendering (ticket 034).
