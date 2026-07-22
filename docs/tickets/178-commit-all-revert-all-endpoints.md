# 178. `POST /api/commit-all` and `POST /api/revert-all`

Status: done
Decision: docs/decisions/061-whole-tree-commit-all-revert-all.md

## Goal

Depends on tickets 176 and 177. Wire the git helpers and `changed_paths()`
into the running server, gated to the live pair per ADR 061/060.

## Acceptance criteria

- `POST /api/commit-all?base=<ref>&staged=<ref>` in `graphwerk/server.py`
  resolves the pair via the registry with the same param handling
  `/api/graph` already uses. If the resolved `staged` isn't the
  working-directory token, respond 400 (nothing to commit for a
  historical pair). Otherwise call `landing.commit_all(registry.repo_root,
  service.changed_paths(), message)`, where `message` is the optional
  JSON body field `{"message": ...}` if present, else the pair's mined
  commit message (`service.rationale.commit_message`), else 400 ("no
  commit message available — none mined and none provided"). Respond with
  the same shape `/api/graph` returns for that pair post-commit, so the
  frontend can render directly from the response instead of always
  issuing a second fetch.
- `POST /api/revert-all` mirrors the same param handling and live-pair
  gate, calling `landing.revert_all(registry.repo_root,
  service.changed_paths())`, and responds the same way.
- A test posts to `/api/commit-all` against a temp-repo-backed app with
  the live pair and a real diff, asserts a new commit exists with the
  expected message, and asserts the response is well-formed.
- A test posts to `/api/revert-all` the same way and asserts a stash entry
  exists and the working tree is restored.
- A test posts to each route against a historical (non-live) pair and
  asserts a 400.

## Likely files

- `graphwerk/server.py` — the two routes.
- `tests/test_server.py` — the tests above.

## Out of scope

- Frontend buttons — ticket 179.
- Any message-editing UI beyond accepting the plain string field.
