"""Spawn and track one headless Claude Code session in the staging worktree."""

from __future__ import annotations

import json
import subprocess
import tempfile
import threading
from pathlib import Path


class SessionBusyError(RuntimeError):
    """A session is already running; only one child at a time."""


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
        self._state = "idle"
        self._detail = ""
        self._last_session_id = ""
        # status() runs concurrently from FastAPI's threadpool (every open
        # tab polls /api/session); the lock keeps _settle to one run per child.
        self._lock = threading.Lock()

    def start(self, prompt: str) -> dict:
        with self._lock:
            if self._status_locked()["state"] == "running":
                raise SessionBusyError("a session is already running")
            command = [self.claude_cmd, "-p", prompt,
                       "--output-format", "json",
                       "--permission-mode", self.permission_mode]
            if self.system_prompt:
                command += ["--append-system-prompt", self.system_prompt]
            self._child_output = tempfile.TemporaryFile()
            try:
                self._child = subprocess.Popen(command, cwd=self.staged_root,
                                               stdout=self._child_output,
                                               stderr=subprocess.STDOUT)
            except OSError as exc:
                self._child_output.close()
                self._child_output = None
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
        self._child_output.seek(0)
        output = self._child_output.read().decode(errors="replace")
        self._child_output.close()
        self._child_output = None
        self._child = None
        if exit_code != 0:
            self._state = "failed"
            self._detail = f"{self.claude_cmd} exited with code {exit_code}"
            return
        try:
            self._last_session_id = json.loads(output)["session_id"]
        except (json.JSONDecodeError, KeyError, TypeError):
            self._state = "failed"
            self._detail = f"{self.claude_cmd} succeeded but returned no parseable session result"
            return
        self._state = "done"
        self._detail = ""
