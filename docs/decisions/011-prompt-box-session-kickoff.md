# 011. Prompt box: graphwerk kicks off the agent session (headless CLI subprocess)

Status: proposed
Date: 2026-07-15

## Context

Today the review flow splits across two surfaces: the browser shows the
graph, but starting the agent means a terminal, a `cd` into the staging
worktree, and a manual `claude` invocation — and that manual step is
exactly where the first real dogfood run failed (session run in the main
repo; ADR 009). The product concept (docs/02) left "where does the
developer type prompts" as an open question; the roadmap answers it under
Phase 3 ("prompt box in the UI so the whole flow happens in one place").
This decision pulls that one bullet forward — an explicit user call (July
2026) — while the rest of Phase 3 (reject → re-prompt, activity
indicator) stays where it is. The user's product constraint: **no chat
log in the UI** — the box is input-only; the agent's output surfaces
exclusively as graph changes and mined per-node rationale, which is the
product's whole bet.

## Decision

The graph app becomes a minimal orchestrator: it can spawn one headless
Claude Code session in the staging worktree.

1. **`SessionRunner`** (new, `graphwerk/session.py`): owns at most one
   child process. Starts `claude -p "<prompt>" --output-format json
   --permission-mode <mode>` with the staged root as working directory;
   tracks status (`idle` / `running` / `done` / `failed` + exit detail);
   parses the session id from the JSON result and keeps the latest one —
   groundwork for Phase 3's `--resume` reject flow. The claude executable
   and permission mode are constructor parameters (tests inject a stub
   script; no test ever runs the real binary).
2. **API**: `POST /api/prompt` starts a run (`409` if one is already
   running, `503`-style failure if the claude binary is missing);
   `GET /api/session` reports status + last session id. Existing
   endpoints untouched.
3. **UI**: a small prompt box; while a run is active the box is disabled
   and a busy indicator shows; failures render the server-provided error
   line. No transcript, no streaming output — the graph itself (existing
   `/api/hash` polling) is the progress display, per the user constraint.
4. **Permission mode**: spawned sessions default to `acceptEdits` — the
   agent can edit freely inside the worktree but can't run arbitrary
   commands. A `--agent-permissions` flag on `serve`/`start` passes a
   different mode through (e.g. `bypassPermissions` when the user wants
   the full edit-build-test loop and accepts the risk). Conservative
   default because `/api/prompt` on a LAN-exposed server is remote code
   execution on the host (see consequences).

Because the app chooses the session's working directory, transcript
discovery (ADR 009's pipeline) always finds the session — the prompt box
structurally eliminates the misplaced-session failure it warns about.

## Alternatives considered

- **Claude Agent SDK** — the architecture notes' "clean option" for
  session control, but it's a new backend dependency (invariant: fastapi +
  uvicorn only) and headless CLI covers this slice; revisit when Phase 3
  needs richer steering. Rejected for now.
- **Status quo (terminal-only) + loud docs** — keeps the flow split and
  keeps the misplaced-session failure reachable; ADR 009 warns about it,
  this removes it. Rejected.
- **Embedded terminal / chat pane in the UI (xterm.js or similar)** — a
  new vendored JS dependency, Node-adjacent complexity, and precisely the
  UI the user said no to; the product bet is that the graph replaces the
  transcript as the review surface. Rejected.

## Consequences

- The whole loop — prompt → watch the graph fill in → review → apply —
  happens in one browser tab; the terminal becomes optional for the
  common path.
- The server gains process-management state (one child, its status, last
  session id) — the first genuinely stateful thing in the app beyond
  filesystem reads; kept in one class so `serve`'s stateless character
  survives everywhere else.
- `POST /api/prompt` executes an agent on the host. With `--host 0.0.0.0`
  (the user's standing setup) anyone on the LAN can prompt it. Mitigated
  by the `acceptEdits` default and the existing "LAN-by-flag is a trusted
  network" stance (docs/04 defers auth deliberately); called out so the
  tradeoff is on record.
- Headless mode cannot answer permission prompts: under `acceptEdits` the
  agent cannot run tests/builds, so its self-verification loop is weaker
  unless the user opts into `bypassPermissions`. Documented tradeoff,
  user-controlled.
- Touches no invariant: the agent keeps a real filesystem (now
  guaranteed), differ/models untouched, stdlib `subprocess` only, JS
  stays a thin consumer.

## Out of scope

- Reject → `claude -p --resume <session>` re-prompting (Phase 3 proper;
  the stored session id is deliberate groundwork).
- Streaming agent output, chat history, or any transcript rendering in
  the UI (user constraint — never, absent a new product decision).
- Agent activity nuance (working / waiting-on-permission) from transcript
  tailing — Phase 3 roadmap line; this ADR's status is process-level only.
- Multi-session orchestration (roadmap Phase 5).
- Auth on the new endpoints (docs/04 "deliberately not now").
