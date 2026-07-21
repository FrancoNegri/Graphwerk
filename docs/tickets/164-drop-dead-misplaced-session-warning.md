# 164. Drop the dead misplaced-session warning and its retired-flag wording

Status: done
Decision: docs/audit/runs/002-2026-07-21.md

## Goal

`RationaleStore` stops carrying a warning path that can never fire under
the single-directory model (audit finding F-009), and stops telling a
reviewer to check `--base`/`--staged` flags that ticket 158 deleted.

## Acceptance criteria

- `RationaleStore._misplaced_session_warning` (or whatever replaces it) no
  longer references `--base`/`--staged` flags or a second "staging
  worktree" directory distinct from the one the session runs in.
- Since `bootstrap.build_app()` always constructs `RationaleStore` with
  `staged_root` and `base_root` set to the same directory (ticket 158),
  the warning path is unreachable in production; either remove it
  outright or replace it with a check that's actually meaningful under
  one directory (reviewer's call during implementation — the acceptance
  bar is "no message describes a scenario that can't happen anymore").
- `tests/rationale/test_miner.py`'s tests around the misplaced-session
  warning (currently constructing `RationaleStore` with deliberately
  distinct `staged_root`/`base_root`) are updated to match — either
  removed if the scenario is gone, or rewritten against whatever replaces
  it.
- `docs/decisions/009-rationale-fails-loudly.md` reconciled with whichever
  side changed (the ADR's misplaced-session wording, if the check is
  removed; nothing, if it's kept in a new form).

## Likely files

- `graphwerk/rationale/miner.py` — the warning method itself.
- `tests/rationale/test_miner.py` — matching test updates.
- `docs/decisions/009-rationale-fails-loudly.md` — doc-side wording, if
  the ADR's own description of the check no longer matches.

## Out of scope

- `graphwerk/session.py`'s docstring ("in the staging worktree") — already
  named in ticket 161's own Likely files, don't duplicate the fix here.
- Any new detection mechanism for "session ran somewhere unexpected" under
  the single-directory model — if ADR 058 genuinely makes the original
  mistake impossible, removing the check is sufficient; don't invent a
  speculative replacement.
