# 008. Distinct state for unparseable staged files

Status: ready
Decision: docs/decisions/001-phase-2-real-session.md (dogfood finding, ticket 007)

## Goal

A staged Python file that fails to parse must not be presented as "every
symbol deleted". During a live session the agent routinely saves files
mid-edit, so transient syntax errors are the normal case, not the edge case.

Observed in the ticket 007 Flask run: appending `def broken(:` to a staged
file kept the server up (good) but flipped the file's entire symbol set to
`deleted` — a reviewer would read that as the agent having gutted the file.

## Acceptance criteria

- Indexing a file with a syntax error yields a `FileIndex` that records the
  parse failure instead of silently returning zero symbols.
- The differ maps "staged side unparseable" to a distinct node state (e.g.
  `error`) on the file node, and leaves the base-side symbols visible rather
  than marking them `deleted`.
- The UI renders the error state visibly distinct from `deleted`
  (styling only; no new controls).
- A staged file that is genuinely deleted still reports `deleted` — the two
  cases must not blur.

## Likely files

- `graphwerk/indexing/python_ast.py` — capture the parse failure
- `graphwerk/models.py` — carry it on `FileIndex` / node status
- `graphwerk/staging/differ.py` — map to the error state
- `static/app.js`, `static/style.css` — render it

## Out of scope

Recovering partial symbols from a broken file; surfacing the syntax error
text in the UI beyond the state itself.
