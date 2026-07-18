# 047. Design-scope session guidance and a scoped dialogue surface

Status: proposed
Date: 2026-07-18

## Context

First real dogfood use of design mode (ADR 046, ticket 130) exposed a gap:
a design-scoped session was asked "is `graphwerk/rationale/miner.py`
actually unused?", investigated with `grep`, and answered correctly in
prose — no file ever needed to change. The session finished cleanly
(`state: "done"`, checks passed), but the review UI showed nothing at all,
because:

1. Nothing told the spawned session that a design turn's expected output
   is a written artifact, the way ADR 012's `SESSION_GUIDANCE` shapes
   *implementation* turns toward miner-friendly narration. Design turns
   get no equivalent shaping today.
2. Even if the reply had been worth showing, there's nowhere for it to go:
   `SessionRunner._settle()` (`graphwerk/session.py`) parses the CLI's JSON
   output only far enough to extract `session_id` — the assistant's actual
   text is read into memory and discarded. A diff-only graph structurally
   cannot represent a text-only reply, so a legitimate "no changes needed"
   answer is indistinguishable from a stuck or broken session.

Two things compound this beyond a simple "print the text somewhere" fix.
First, design mode's raw material — ADRs and tickets — already forms a
graph the moment it's written with the right links: ticket 126 (ADR 046)
parses `[text](relative/path.md)` links and `Decision: docs/decisions/
NNN-....md` lines into `references` edges. An agent that doesn't know this
convention exists will write undiscoverable prose instead of a linked
node. Second, design work is conversational by nature — proportionally
more Q&A-shaped than implementation work — and ADR 011's "no chat log,
ever, absent a new product decision" was scoped to *code* review
specifically ("the graph replaces the transcript as the review surface"
for generated diffs). This is that new product decision, but only for the
design domain: the user made the call explicitly, in this session, to add
a free-form dialogue surface for design mode while leaving ADR 011's bet
fully intact for implementation mode.

## Decision

Three additive pieces, no change to the implementation-mode flow:

1. **`graphwerk/design_guidance.py`** (new): a `DESIGN_SESSION_GUIDANCE`
   string constant, same shape as `rationale/guidance.py`'s
   `SESSION_GUIDANCE`. Content:
   - States the deliverable expectation: when a design turn produces an
     actual decision or actionable next step, write it down using the
     existing `docs/decisions/NNN-slug.md` / `docs/tickets/NNN-slug.md`
     conventions (check the highest existing number in each `README.md`
     table the same way `north-star` does) — *not* every turn; pure
     discussion that resolves to "no change needed" can just be the
     reply.
   - States the linking discipline ticket 126 already parses for free: an
     ADR should link forward to the tickets it spawns with inline
     `[NNN](../tickets/NNN-slug.md)` links, and every ticket keeps its
     `Decision: docs/decisions/NNN-slug.md` line — so anything written
     shows up as a connected node in the graph, not an orphaned file.
   - Points at `docs/02-product-concept.md` / `docs/04-roadmap.md` /
     `CLAUDE.md` the same way `north-star` does, so a design session
     grounds itself in the same material a human running `north-star`
     would, without literally invoking the skill (see Alternatives).

2. **Scope-conditional wiring in `SessionRunner`** (`graphwerk/
   session.py`): `start()`/`resume()` already build `--append-system-
   prompt` from `self.system_prompt` (ADR 012). When `scope == "design"`,
   append `DESIGN_SESSION_GUIDANCE` to that string for this call only;
   `implementation`/`None` scope is unaffected. `session.py` stays
   ignorant of the guidance's content, same separation ADR 012 already
   established for rationale guidance.

3. **A design-scoped reply surface**, built from the smallest plumbing
   change that unblocks it:
   - `SessionRunner._settle()` additionally extracts the final result
     event's reply text (the same JSON event `_session_id_from` already
     locates) and exposes it as a `reply` field in the status dict.
     `SessionCycle` needs no change — it already copies the runner's
     status dict wholesale before overwriting only the fields it owns, so
     `reply` passes through both the checked and unchecked (`check_command
     is None`) paths for free.
   - The frontend renders a small scrollable exchange list — prompt +
     reply pairs — but **only when the domain-mode toggle is on
     Design**; it's built and held entirely client-side (append on every
     successful `/api/prompt` response while in design mode, cleared on a
     fresh `start()`, i.e. not `continue_session`), no server-side
     history storage. Implementation mode's prompt box is completely
     unchanged: input-only, no reply rendered, exactly ADR 011 today.

## Alternatives considered

- **Point the spawned session at the actual `north-star` skill file**
  (`Read .claude/skills/north-star/SKILL.md` and follow it) instead of a
  bespoke guidance constant — one single definition of "how graphwerk
  designs things," reused by humans and spawned sessions alike. Rejected
  for this pass: whether a headless `claude -p` session reliably follows a
  skill file it's told to read (vs. the skill being a first-class,
  harness-recognized construct in interactive sessions) is unproven, and
  the full re-ground-in-docs/weigh-alternatives/ADR-numbering ceremony is
  heavier than most design turns warrant. A bespoke constant is smaller,
  testable the way ADR 012's guidance is (round-trip test pinning the
  contract), and ships now; revisit skill-reuse later if bespoke guidance
  proves to drift from what `north-star` actually does.
- **Force every design turn to leave a written artifact, decision or not**
  — guarantees the graph is never empty after a design turn without
  needing a dialogue surface at all, but produces junk ADRs for pure
  fact-checking questions (the dogfood case that triggered this: "is
  `miner.py` unused?" resolved to "no, false alarm" — not a decision).
  Rejected once the dialogue surface was decided: ephemeral back-and-forth
  now has a real home that isn't `docs/decisions/`.
- **Reopen ADR 011 generally** (a chat log for both domains) — the
  implementation-mode bet ("the graph replaces the transcript") is
  unrelated to this problem and still holds; a code-review chat log would
  compete with the diff/rationale review surface for attention. Rejected;
  scoped to design only.
- **Persist the design dialogue server-side** (so it survives a page
  reload / is visible across browser tabs) — the underlying data already
  exists in the Claude Code session transcript JSONL (mined for rationale
  elsewhere), so this would be a second, redundant persistence path.
  Rejected: client-side accumulation for the tab's lifetime is enough for
  "keep talking to this session," and matches "no persistence beyond the
  filesystem" (docs/04).

## Consequences

- No invariant touched: still stdlib + fastapi/uvicorn only, JS stays a
  render-only consumer of payload fields it's given (the `reply` field),
  worktree/differ untouched, implementation-mode flow byte-for-byte
  unchanged.
- `SessionRunner` gains one more field to a dict it already builds
  (`reply`) — no new class, no new concurrency surface.
- Design-mode sessions now have a standing incentive to produce
  graph-legible, cross-linked artifacts instead of prose that disappears
  once the CLI process exits — directly strengthens ADR 046's "knowledge
  base as a graph" bet.
- ADR 011's "no chat log" stance is narrowed, not repealed: it now reads
  as "no chat log for implementation-mode code review," which is what its
  own Context section was actually arguing for.
- The guidance is advisory, same as ADR 012's: an agent can ignore or
  half-follow it. Worst case reverts to exactly today's behavior (a
  visible reply in the new dialogue box, but no written artifact) — never
  worse than the status quo this ADR fixes.

## Out of scope

- Literal `north-star` skill invocation by spawned sessions (see
  Alternatives — revisit if bespoke guidance drifts from the skill).
- A chat log / reply surface for implementation-mode sessions — ADR 011
  stands for that domain.
- Server-side persistence of the design dialogue across page loads or
  browser tabs.
- Streaming/incremental reply rendering — the reply appears once the turn
  settles, same polling model as everything else in the session bar.
- Enforcing or validating that agent-authored docs actually follow the
  linking convention (no lint/check) — advisory only, same posture as ADR
  012's rationale guidance.
- Auto-chaining a design session's resulting ticket into an
  implementation-mode prompt — still deferred, per ADR 046's own Out of
  scope.
