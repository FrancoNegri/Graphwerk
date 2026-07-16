# 026. Rationale for deleted files

Status: proposed
Date: 2026-07-16

## Context

ADR 025 (tickets 066-069) landed and works well for added/modified files —
re-checked against a fresh dogfood run (agendabot, `webhook.py` split into
a `webhook/` package, session `faf3bf05-...`): every new file under
`webhook/` gets its own correctly-attributed guidance bullet, confidently.

But the **deleted** node, `src/agendabot/webhook.py`, has no rationale at
all (`why: None`) — even though the transcript contains a clear, one-line
explanation of exactly why it was removed:

```
- `src/agendabot/webhook.py` → removed (converted to the package above;
  `agendabot.webhook:app` and all existing imports/monkeypatches keep
  working unchanged).
```

Two compounding gaps, both specific to deletions:

1. **The deletion bullet doesn't match the guidance-bullet shape.**
   `SESSION_GUIDANCE` (`graphwerk/rationale/guidance.py`, ADR 012) only
   describes and exemplifies the case of a changed file — "naming the
   file's path and the key symbols you changed in it, and stating why that
   change serves the request" — with a colon-separated example. It never
   tells the agent what shape to use for a file it *deletes*, so the agent
   reasonably improvised a different, sensible shape (`` `path` → removed
   (...) ``). `attribution._GUIDANCE_BULLET` requires a literal `:` after
   the optional symbol parens, so `parse_guidance_bullet` returns `None`
   for this line — it's silently dropped.
2. **The deletion itself is invisible to the transcript parser.** The
   agent removed the file via `Bash`: `git rm src/agendabot/webhook.py`.
   `transcript.EDIT_TOOLS` is `{"Edit", "Write", "MultiEdit",
   "NotebookEdit"}` — `Bash` isn't tracked at all, so this deletion never
   produces an `EditEvent`. That means `src/agendabot/webhook.py` never
   enters the `rel_paths` set `attribute_files` is given
   (`sorted({edit.rel_path for edit in edits})` in
   `RationaleStore._mine_transcript`), so even prose mentions of it
   elsewhere in the transcript (had the bullet not existed) would never be
   attributed either — and it gets nothing from the proximity fallback for
   the same reason.

Both gaps are specific to deletions; ADR 025's fixes (guidance-bullet
parsing, tightened prose fallback, confidence flag) all assumed a file
enters the pipeline via an Edit/Write-shaped narration, which a deletion
never does.

Ties to [02-product-concept.md](../02-product-concept.md): deleted nodes
are a first-class part of the review surface ("deleted in grey"), and the
concept's "per-node rationale" pitch applies to them exactly as much as to
added/modified nodes — a reviewer checking "does the stated intent match
what happened" needs to know *why* a file went away, not just that it did.
In-phase for the same reason as ADR 025: Phase 2 dogfooding surfaced a
concrete gap in the mechanism the phase is supposed to validate.

## Decision

Three changes, layered the same way ADR 025 layered its fixes (teach the
agent the shape first, then backstop it):

1. **Extend `SESSION_GUIDANCE` to cover deletions explicitly**, using the
   *same* colon-based shape already in the guidance bullet parser (e.g.
   `` - `path/to/old_file.py`: removed — reason ``), so a cooperative
   future session lands on a shape the existing parser (ticket 066)
   already understands, no parser change needed.
2. **Add a deletion-shaped bullet fallback** to
   `graphwerk/rationale/attribution.py` for sessions/agents that don't
   follow the new instruction exactly (including this already-recorded
   transcript, which can't retroactively change) — recognize `` `path` →
   removed (...) `` (and close equivalents) as a second bullet shape,
   tried when the primary colon shape doesn't match.
3. **Track `Bash`-performed deletions (`git rm`, `rm`) as edit events** in
   `graphwerk/rationale/transcript.py`, so a deleted file becomes eligible
   for `attribute_files`'s mention-scanning and the proximity fallback —
   not just the dedicated-bullet path — covering sessions where a deletion
   is narrated only in prose.

## Alternatives considered

- **Guidance-text change only (item 1), skip the parser/transcript
  changes.** Cheapest, but doesn't help this transcript (already
  recorded) or any session that doesn't follow instructions precisely —
  the same "guidance-only" alternative ADR 025 already rejected once, for
  the same reason.
- **Derive attribution eligibility from the differ's changed-file list
  instead of from transcript edit events.** The differ already knows
  `webhook.py` was deleted, independent of the transcript — using that set
  directly would sidestep tool-call detection entirely and catch any
  deletion mechanism (not just `git rm`/`rm`). Rejected as the primary fix
  for now: `attribute_files`'s current scoping to *transcript-touched*
  files is deliberate (avoids scanning every differ-known changed file's
  name against every segment, including files this session never touched
  at all in a multi-session worktree). Detecting the specific tool-call
  shape mirrors how Edit/Write are already tracked and keeps the change
  smallest; worth revisiting if deletions keep slipping through by other
  mechanisms (`mv`, IDE rename, etc.).
- **Broad Bash command parsing (any file-mutating shell command).** More
  complete in theory, but open-ended and fragile (quoting, multiple paths,
  subshells, aliases). Scope to the two patterns actually observed
  (`git rm`, `rm`) and extend if dogfooding turns up more.

## Consequences

- Deleted-file nodes get real rationale in the common case (bullet or
  prose), closing the gap without requiring anything from the reviewer.
- `EDIT_TOOLS`'s job grows slightly: `transcript.py` now also recognizes
  certain `Bash` commands as edit-shaped events. Still pure-Python
  transcript mining, no new deps, no invariant conflicts.
- `SESSION_GUIDANCE` gains one more instruction + example; its round-trip
  test (ticket 041) should grow a deletion case.
- Reuses ADR 025's `confident` flag machinery unchanged — both new sources
  (deletion bullet, deletion-derived mention) count as confident, the same
  as their non-deletion counterparts.

## Out of scope

- Renames/moves (`git mv`, `mv old new`) — arguably should carry the old
  path's rationale forward to the new one, but that's a distinct shape not
  observed in this dogfood run. File as a future ticket if it comes up.
- Broad Bash command parsing beyond `git rm`/`rm`.
- Any change to how confidence is computed or rendered (ADR 025's scope,
  untouched here).
