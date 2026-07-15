# 024. Code view builder: merged lines + highlight spans

Status: done
Decision: docs/decisions/007-sidebar-code-view.md

Depends on: tickets 022, 023.

## Goal

One function produces the complete, serializable code view for a node:
merged diff lines with the right highlight spans attached to each side.

## Acceptance criteria

- `graphwerk/codeview.py` gains e.g.
  `build_code_view(base_text, staged_text) -> list[dict]`, each entry
  `{"text": ..., "op": ..., "spans": [[start, end, cls], ...]}` — a shape
  `GraphNode.to_dict` can embed directly.
- `ctx`/`add` lines carry spans from highlighting the staged text; `del`
  lines from the base text, looked up via each merged line's origin line
  number — so multi-line constructs highlight correctly on both sides.
- An unchanged node (staged text only, or identical texts) yields an
  all-`ctx` fully highlighted view.
- Unhighlightable text (ticket 022 fallback) yields the merged view with
  empty span lists — the diff overlay must not depend on highlighting
  succeeding.
- Unit tests cover: spans landing on the correct side of a modification
  (a string changed between base and staged shows the old spans on the
  `del` line and new spans on the `add` line), unchanged-node view,
  syntax-error text with intact ops.

## Likely files

- `graphwerk/codeview.py` — builder added
- `tests/test_codeview.py` — extended

## Out of scope

Wiring into differ/service/models (tickets 025-026); payload size work.
