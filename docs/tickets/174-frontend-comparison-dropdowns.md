# 174. Frontend: base / compare-to dropdowns

Status: done
Decision: docs/decisions/060-comparison-picker-any-ref-vs-any-ref.md

## Goal

Depends on tickets 172 and 173. Let the developer pick both sides of the
comparison from the UI instead of only ever seeing the server's
default-configured pair.

## Acceptance criteria

- On load, `static/app.js` fetches `/api/refs` and populates two
  `<select>` elements in the header (base / compare-to), each listing the
  branches/tags/commits plus the working-directory option; both default to
  selecting whatever `/api/graph`'s current default-pair response reports
  (`data.base` / `data.staged`) so the initial view is unchanged.
- Changing either dropdown refetches `/api/graph` (and subsequent
  `/api/hash` polls, until ticket 175 changes that) with the new `base`/
  `staged` query params, and re-renders the graph.
- The existing "reviewing `<staged>` against `<base>`" line (ticket 165)
  updates to reflect the newly selected pair.
- Manually verified against the running demo server (`.venv/bin/python -m
  graphwerk demo`) in a browser: both dropdowns list real refs, switching
  either one updates the graph and the paths line.

## Likely files

- `static/app.js` — dropdown population, change handlers, refetch logic.
- `static/index.html` (or wherever the header markup lives) — the two
  `<select>` elements.

## Out of scope

- Hiding the prompt box / stopping `/api/hash` polling for historical
  pairs — that's ticket 175.
- Any styling beyond making the dropdowns usable (this is a JS-logic
  ticket per CLAUDE.md's "thin JS" rule — the user eyeballs the UI rather
  than this ticket needing a JS test harness).
