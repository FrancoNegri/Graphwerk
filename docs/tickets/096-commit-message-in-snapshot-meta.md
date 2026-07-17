# 096. Snapshot meta carries the mined commit message

Status: done
Decision: docs/decisions/037-bottom-session-bar-commit-discard.md

## Goal

`/api/graph` payloads expose the transcript-mined commit message as
`meta.commit_message`, so the UI can fill the session bar's text box.

## Acceptance criteria

- `RationaleStore` exposes the parsed commit message (ticket 095) for the
  currently mined transcript; `None` when there is none.
- `GraphService.snapshot()` sets `meta["commit_message"]` from it (the key
  present, value `null`, when none was mined — the UI distinguishes "no
  message" without guessing).
- Service-level test: a snapshot built over a transcript containing the
  guidance-shaped closing line carries the message in `meta`; one without
  it carries `null`.

## Likely files

- `graphwerk/rationale/` (store) — surface the parsed message
- `graphwerk/service.py` — one meta assignment
- `tests/test_service.py` — coverage

## Out of scope

Parsing (ticket 095). UI consumption (ticket 099).
