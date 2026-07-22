# graphwerk — project instructions

Graph-based staging/review layer for AI-generated code changes. Read
`docs/02-product-concept.md` (the idea) and `docs/04-roadmap.md` (current
phase) before starting feature work. v1 is done; **Phase 2 (real Claude
session end-to-end) is next.**

## Stack rules

- **Python everywhere; JS only in `static/`** (the browser Cytoscape UI).
  This is an explicit user decision — don't add Node-side logic.
- `package.json` still lists express/ws/ts-morph/diff from an abandoned Node
  scaffold. They are unused but user-added — don't remove without asking.
  npm IS used to vendor frontend libs into `static/vendor/` (never CDN).
- Backend deps stay minimal: fastapi + uvicorn only, stdlib otherwise.

## Workflow

Big decisions and small implementation steps are deliberately separated:

- **`north-star` skill** — run before any nontrivial feature or
  architectural change. Re-grounds the decision in docs/02-04 and the
  invariants below, then writes an ADR to `docs/decisions/` and splits it
  into scoped ticket files under `docs/tickets/`. Produces plans, not code.
- **`ticket` skill** — implements exactly one ticket via strict TDD, small
  single-responsibility classes, minimum coupling between the layers below,
  and a passing test for everything touched.
- **`audit` skill** — periodic full-repo consistency sweep. Re-reads
  docs/02-04, CLAUDE.md, and its own ledger at `docs/audit/README.md`,
  checks the code for doc/code drift, bugs, and missing test coverage, and
  files a ticket for anything actionable. Documents only, like `north-star`.
- **`audit-tests` skill** — works through the missing-test backlog `audit`
  queues, one TDD pass per finding. If a new test reveals a real bug
  instead of just a gap, it tickets that too rather than fixing it inline.

Don't skip straight to multi-file code changes for anything that would
count as an architectural decision — run `north-star` first.

## Running

```bash
.venv/bin/python -m graphwerk demo                 # scripted demo + serve :8135
.venv/bin/python -m graphwerk demo --no-serve      # reset demo trees (works while serving)
.venv/bin/python -m graphwerk serve --repo X [--base-ref REF] [--transcript JSONL]
```

- The user browses from another LAN device — start servers with
  `--host 0.0.0.0` when they want to interact (default is loopback-only on
  purpose: /api/apply writes files).
- Verify changes by curling the API (`/api/graph`, `/api/hash`, POST
  `/api/apply`, `/api/reject`), not just imports. Reset the demo afterward.

## Architecture invariants

- The agent must keep a real filesystem to work in — never intercept/
  absorb its writes (docs/03, "the trap"). As of ADR 058, that filesystem
  is the developer's own working directory, not an isolated git worktree:
  graphwerk no longer stages or mutates files, only diffs the working
  directory against a recorded base git ref. Landing/undoing a change is
  the developer's own plain git operation, not a graphwerk endpoint —
  except the whole-tree `commit-all`/`revert-all` convenience (ADR 061),
  which is exactly that same `git add`/`commit`/`stash` with no
  symbol-level staging in between. Node-level apply stays retired.
- The differ compares symbols by qualified name across two parsed trees —
  no hunk-to-symbol mapping. Keep new features consistent with that model.
- `FileIndex`/`SymbolInfo` is the language-neutral contract; new languages
  are new extractors, not new models.
