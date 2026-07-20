# 144. Frontend: approve/unapprove toggle + approved-count commit gate

Status: done
Decision: docs/decisions/050-apply-becomes-approval-scoped-commit.md

## Goal

Replace the sidebar's immediate "Apply file X" action with an
Approve/Unapprove toggle reflecting server-held state, and make the commit
bar show how much is actually approved.

## Acceptance criteria

- Selecting a changed file node shows "Approve file X" when
  `node.approved` is false, "Unapprove file X" when true; clicking posts to
  `/api/apply` or `/api/unapprove` respectively and refreshes the graph.
- The commit bar displays the count of currently-approved files (e.g.
  "Commit 2 approved files") and disables the commit button when the count
  is 0.
- Discard button behavior is unchanged (still acts on the whole change
  set, enabled regardless of approval count).

## Likely files

- `static/app.js` — toggle button logic, commit bar approved-count display.
- `static/index.html` / `static/style.css` — only if the toggle needs new
  markup beyond relabeling the existing button.

## Out of scope

- Grouped/multi-select approval — still file-by-file.
- Any change to discard's behavior.
