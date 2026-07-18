"""Spawn and track one headless Claude Code session in the staging worktree."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

SCOPE_HOOK_MARKER = "graphwerk.hooks.scope_guard"
CLAUDE_SETTINGS_REL_PATH = Path(".claude") / "settings.local.json"


class SessionBusyError(RuntimeError):
    """A session is already running; only one child at a time."""


class NoSessionToResumeError(RuntimeError):
    """resume() called with no prior session id stored."""


class SessionRunner:
    """Owns at most one `claude -p` child process and its outcome."""

    def __init__(self, staged_root: Path, claude_cmd: str = "claude",
                 permission_mode: str = "acceptEdits",
                 system_prompt: str = "") -> None:
        self.staged_root = Path(staged_root)
        self.claude_cmd = claude_cmd
        self.permission_mode = permission_mode
        self.system_prompt = system_prompt
        self._child: subprocess.Popen | None = None
        self._child_output = None
        self._child_errors = None
        self._state = "idle"
        self._detail = ""
        self._last_session_id = ""
        # status() runs concurrently from FastAPI's threadpool (every open
        # tab polls /api/session); the lock keeps _settle to one run per child.
        self._lock = threading.Lock()

    def start(self, prompt: str, scope: str | None = None) -> dict:
        with self._lock:
            if self._status_locked()["state"] == "running":
                raise SessionBusyError("a session is already running")
            if scope is not None:
                _configure_scope_hook(self.staged_root, scope)
            command = [self.claude_cmd, "-p", prompt,
                       "--output-format", "json",
                       "--permission-mode", self.permission_mode]
            if self.system_prompt:
                command += ["--append-system-prompt", self.system_prompt]
            return self._spawn(command)

    def resume(self, prompt: str, scope: str | None = None) -> dict:
        with self._lock:
            if self._status_locked()["state"] == "running":
                raise SessionBusyError("a session is already running")
            if not self._last_session_id:
                raise NoSessionToResumeError("no prior session to resume")
            if scope is not None:
                _configure_scope_hook(self.staged_root, scope)
            command = [self.claude_cmd, "-p", prompt,
                       "--resume", self._last_session_id,
                       "--output-format", "json",
                       "--permission-mode", self.permission_mode]
            if self.system_prompt:
                command += ["--append-system-prompt", self.system_prompt]
            return self._spawn(command)

    def _spawn(self, command: list[str]) -> dict:
        # stderr kept apart from stdout: a stray CLI warning must not
        # corrupt the JSON result, and it's the useful detail on failure
        self._child_output = tempfile.TemporaryFile()
        self._child_errors = tempfile.TemporaryFile()
        try:
            self._child = subprocess.Popen(command, cwd=self.staged_root,
                                           stdout=self._child_output,
                                           stderr=self._child_errors)
        except OSError as exc:
            self._close_child_files()
            self._state = "failed"
            self._detail = f"could not launch {self.claude_cmd}: {exc}"
            return self._status_locked()
        self._state = "running"
        self._detail = ""
        return self._status_locked()

    def status(self) -> dict:
        with self._lock:
            return self._status_locked()

    def _status_locked(self) -> dict:
        if self._child is not None:
            exit_code = self._child.poll()
            if exit_code is not None:
                self._settle(exit_code)
        return {"state": self._state, "detail": self._detail,
                "session_id": self._last_session_id}

    def _settle(self, exit_code: int) -> None:
        output = _read_back(self._child_output)
        errors = _read_back(self._child_errors)
        self._close_child_files()
        self._child = None
        if exit_code != 0:
            self._state = "failed"
            self._detail = f"{self.claude_cmd} exited with code {exit_code}"
            if errors.strip():
                self._detail += f": {_snippet(errors)}"
            return
        session_id = _session_id_from(output)
        if session_id is None:
            self._state = "failed"
            self._detail = (f"{self.claude_cmd} succeeded but returned no parseable "
                            f"session result: {_snippet(output)}")
            return
        self._last_session_id = session_id
        self._state = "done"
        self._detail = ""

    def _close_child_files(self) -> None:
        for handle in (self._child_output, self._child_errors):
            if handle is not None:
                handle.close()
        self._child_output = None
        self._child_errors = None


def _configure_scope_hook(staged_root: Path, scope: str) -> None:
    """Writes/replaces this session's PreToolUse hook entry in the staged
    worktree's local settings (ADR 046) so "design can't touch code,
    implementation can't touch docs" is enforced by Claude Code itself, not
    just requested via prompt text. Other hooks/settings already in the
    file are left untouched; a prior graphwerk scope entry is replaced
    rather than duplicated (a session can be re-scoped run over run)."""
    path = staged_root / CLAUDE_SETTINGS_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    settings = _read_json(path)
    hooks = settings.setdefault("hooks", {})
    pre_tool_use = [entry for entry in hooks.get("PreToolUse", [])
                    if not _is_scope_hook_entry(entry)]
    pre_tool_use.append(_scope_hook_entry(scope))
    hooks["PreToolUse"] = pre_tool_use
    path.write_text(json.dumps(settings, indent=2))


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def _is_scope_hook_entry(entry: dict) -> bool:
    return any(SCOPE_HOOK_MARKER in hook.get("command", "") for hook in entry.get("hooks", []))


def _scope_hook_entry(scope: str) -> dict:
    command = f"GRAPHWERK_SCOPE={scope} {sys.executable} -m {SCOPE_HOOK_MARKER}"
    return {"matcher": "Edit|Write", "hooks": [{"type": "command", "command": command}]}


def _read_back(handle) -> str:
    if handle is None:
        return ""
    handle.seek(0)
    return handle.read().decode(errors="replace")


def _snippet(text: str, limit: int = 300) -> str:
    text = text.strip()
    return text[:limit] + ("…" if len(text) > limit else "")


def _session_id_from(output: str) -> str | None:
    """claude ≤2.0's --output-format json printed one result object; 2.1+
    prints the whole event list, whose closing "result" event owns the
    session id. Accept both, falling back to any event that carries one."""
    try:
        parsed = json.loads(output)
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, dict):
        parsed = [parsed]
    if not isinstance(parsed, list):
        return None
    events = [entry for entry in parsed
              if isinstance(entry, dict) and isinstance(entry.get("session_id"), str)]
    for event in reversed(events):
        if event.get("type") == "result":
            return event["session_id"]
    return events[-1]["session_id"] if events else None
