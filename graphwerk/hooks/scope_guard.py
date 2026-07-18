"""Deterministic design/implementation write boundary (ADR 046).

The decision logic (`is_allowed`) is pure and independently testable; `main`
is the thin Claude Code PreToolUse hook wrapper that invokes it (ticket 132
wires the hook config itself into a spawned session's worktree).
"""

from __future__ import annotations

import json
import os
import sys

SCOPE_ENV_VAR = "GRAPHWERK_SCOPE"


def is_allowed(scope: str | None, path: str) -> bool:
    if scope == "design":
        return path.endswith(".md")
    if scope == "implementation":
        return not path.endswith(".md")
    return True


def main() -> None:
    payload = json.loads(sys.stdin.read())
    path = payload.get("tool_input", {}).get("file_path", "")
    scope = os.environ.get(SCOPE_ENV_VAR)
    allowed = is_allowed(scope, path)
    hook_output = {"hookEventName": "PreToolUse",
                   "permissionDecision": "allow" if allowed else "deny"}
    if not allowed:
        hook_output["permissionDecisionReason"] = (
            f'scope "{scope}" does not permit editing {path}')
    print(json.dumps({"hookSpecificOutput": hook_output}))


if __name__ == "__main__":
    main()
