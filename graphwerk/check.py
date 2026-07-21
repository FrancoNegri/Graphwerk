"""Run the configured check command in the repo directory, non-blocking, poll-settled."""

from __future__ import annotations

import json
import subprocess
import tempfile
import threading
import time
from pathlib import Path

MAX_TAIL_LINES = 100
MAX_TAIL_BYTES = 4096
SUMMARY_FILENAME = ".graphwerk-check.json"


class CheckBusyError(RuntimeError):
    """A check is already running; only one child at a time."""


class CheckRunner:
    """Owns at most one check subprocess and its outcome."""

    def __init__(self, command: str, root: Path) -> None:
        self.command = command
        self.root = Path(root)
        self._child: subprocess.Popen | None = None
        self._output = None
        self._state = "idle"
        self._exit_code = None
        self._tail = ""
        self._check_summary = None
        self._duration_s = None
        self._start_monotonic = None
        # status() runs concurrently from FastAPI's threadpool; the lock
        # keeps _settle to one run per child (mirrors SessionRunner, ticket 086).
        self._lock = threading.Lock()

    def start(self) -> dict:
        with self._lock:
            if self._status_locked()["state"] == "running":
                raise CheckBusyError("a check is already running")
            # a leftover summary from a prior run must never be misread as
            # this run's result.
            (self.root / SUMMARY_FILENAME).unlink(missing_ok=True)
            self._output = tempfile.TemporaryFile()
            self._start_monotonic = time.monotonic()
            try:
                self._child = subprocess.Popen(self.command, shell=True, cwd=self.root,
                                               stdout=self._output, stderr=subprocess.STDOUT)
            except OSError as exc:
                self._output.close()
                self._output = None
                self._state = "error"
                self._exit_code = None
                self._tail = str(exc)
                self._check_summary = None
                self._duration_s = time.monotonic() - self._start_monotonic
                return self._status_locked()
            self._state = "running"
            self._exit_code = None
            self._tail = ""
            self._check_summary = None
            self._duration_s = None
            return self._status_locked()

    def status(self) -> dict:
        with self._lock:
            return self._status_locked()

    def _status_locked(self) -> dict:
        if self._child is not None:
            exit_code = self._child.poll()
            if exit_code is not None:
                self._settle(exit_code)
        result = {"state": self._state, "exit_code": self._exit_code, "tail": self._tail}
        if self._state in ("passed", "failed", "error"):
            result["check_summary"] = self._check_summary
            result["duration_s"] = self._duration_s
        return result

    def _settle(self, exit_code: int) -> None:
        output = _read_back(self._output)
        self._output.close()
        self._output = None
        self._child = None
        self._exit_code = exit_code
        self._tail = _bounded_tail(output)
        self._state = "passed" if exit_code == 0 else "failed"
        self._duration_s = time.monotonic() - self._start_monotonic
        self._check_summary = _read_check_summary(self.root)


def _read_check_summary(root: Path) -> dict | None:
    try:
        text = (root / SUMMARY_FILENAME).read_text()
    except OSError:
        return None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _read_back(handle) -> str:
    handle.seek(0)
    return handle.read().decode(errors="replace")


def _bounded_tail(text: str, max_lines: int = MAX_TAIL_LINES,
                  max_bytes: int = MAX_TAIL_BYTES) -> str:
    tail = "\n".join(text.splitlines()[-max_lines:])
    encoded = tail.encode()
    if len(encoded) > max_bytes:
        tail = encoded[-max_bytes:].decode(errors="replace")
    return tail
