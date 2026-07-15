# 033. Misplaced-session hint when the transcript sits with the base tree

Status: done
Decision: docs/decisions/009-rationale-fails-loudly.md

## Goal

The exact dogfood failure — agent session run in the main repo instead of
the staging worktree — produces an explicit warning in `meta.rationale`
instead of a silent empty pipeline.

## Acceptance criteria

- When no transcript exists for the staged root, discovery probes the
  *base* root's encoded project dir. If the latest transcript there
  contains edit events whose paths resolve inside the base root, the
  rationale status carries a warning naming the base tree and telling the
  user to run the agent in the staging worktree (or check for swapped
  `--base`/`--staged`).
- That base-tree transcript contributes **zero** rationale entries — it
  only powers the warning (pytest asserts both halves).
- When the staged root has its own transcript, the base root is never
  probed and no warning is set.
- When neither root has a transcript, transcript is `None` with no
  warning beyond the ordinary "no source" state (the UI wording for that
  is ticket 034's job, driven by the `None`/zero fields from ticket 032).
- `GraphService` needs the base root available to the store for the probe
  — thread it through construction, not a global.

## Likely files

- `graphwerk/rationale/discovery.py` — probe helper for a second root
- `graphwerk/rationale/miner.py` — warning in the status object
- `graphwerk/cli.py` or `graphwerk/service.py` — pass base root to the store
- `tests/` — tmp claude dir + two tmp trees reproducing the agendabot case

## Out of scope

- Adopting the base-tree transcript as a rationale source (ADR 009 says
  never).
- Any other swap heuristics (timestamps, git state).
- UI rendering (ticket 034).
