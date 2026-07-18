"""SessionCycle: session -> check -> bounded auto-resume state machine."""

from __future__ import annotations

import threading

from graphwerk.check import CheckRunner
from graphwerk.session import SessionBusyError

TERMINAL_STATES = ("idle", "done", "failed", "check_failed")

FAILURE_PROMPT_TEMPLATE = (
    "The check command `{command}` failed with exit code {exit_code}.\n\n"
    "Output tail:\n{tail}\n\n"
    "Fix the failures shown above."
)

FAILURE_PROMPT_WITH_FAILURES_TEMPLATE = (
    "The check command `{command}` failed with exit code {exit_code}.\n\n"
    "Known failing tests:\n{failures_list}\n\n"
    "The output tail below may not show all of them.\n\n"
    "Output tail:\n{tail}\n\n"
    "Fix the failures shown above."
)


class SessionCycle:
    """Wraps a SessionRunner with a deterministic post-session check gate."""

    def __init__(self, runner, check_command: str | None, max_retries: int = 1) -> None:
        self.runner = runner
        self.check_command = check_command
        self.max_retries = max_retries
        self._check: CheckRunner | None = None
        self._state = "idle"
        self._attempt = 0
        self._check_exit_code = None
        self._check_tail = ""
        self._check_summary = None
        self._check_duration_s = None
        # status() runs concurrently from FastAPI's threadpool; guards the
        # same way SessionRunner/CheckRunner do (ticket 086).
        self._lock = threading.Lock()

    def start(self, prompt: str) -> dict:
        if self.check_command is None:
            payload = dict(self.runner.start(prompt))
            payload["check_configured"] = False
            return payload
        return self._begin_locked(self.runner.start, prompt)

    def continue_session(self, prompt: str) -> dict:
        if self.check_command is None:
            payload = dict(self.runner.resume(prompt))
            payload["check_configured"] = False
            return payload
        return self._begin_locked(self.runner.resume, prompt)

    def _begin_locked(self, operation, prompt: str) -> dict:
        with self._lock:
            current = self._status_locked()
            if current["state"] not in TERMINAL_STATES:
                raise SessionBusyError("a session is already running")
            operation(prompt)
            self._check = None
            self._state = "running"
            self._attempt = 0
            self._check_exit_code = None
            self._check_tail = ""
            self._check_summary = None
            self._check_duration_s = None
            return self._status_locked()

    def status(self) -> dict:
        if self.check_command is None:
            payload = dict(self.runner.status())
            payload["check_configured"] = False
            return payload
        with self._lock:
            return self._status_locked()

    def _status_locked(self) -> dict:
        # a single poll of the runner, reused both to drive the state
        # transition and to fill the payload — polling twice would let the
        # runner settle out from under the second read.
        runner_status = self.runner.status()
        self._advance_locked(runner_status)
        payload = dict(runner_status)
        payload["state"] = self._state
        payload["check_configured"] = True
        payload["attempt"] = self._attempt
        payload["check_exit_code"] = self._check_exit_code
        payload["check_tail"] = self._check_tail
        payload["check_summary"] = self._check_summary
        payload["check_duration_s"] = self._check_duration_s
        return payload

    def _advance_locked(self, runner_status: dict) -> None:
        if self._state in ("running", "resuming"):
            self._advance_session_locked(runner_status)
        elif self._state == "checking":
            self._advance_check_locked()

    def _advance_session_locked(self, runner_status: dict) -> None:
        if runner_status["state"] == "running":
            return
        if runner_status["state"] == "failed":
            self._state = "failed"
            return
        if runner_status["state"] == "done":
            self._check = CheckRunner(self.check_command, self.runner.staged_root)
            self._check.start()
            self._state = "checking"

    def _advance_check_locked(self) -> None:
        check_status = self._check.status()
        if check_status["state"] == "running":
            return
        self._check_exit_code = check_status["exit_code"]
        self._check_tail = check_status["tail"]
        self._check_summary = check_status.get("check_summary")
        self._check_duration_s = check_status.get("duration_s")
        if check_status["state"] == "passed":
            self._state = "done"
        elif check_status["state"] == "error":
            self._state = "check_failed"
        elif self._attempt < self.max_retries:
            self._attempt += 1
            self.runner.resume(self._build_resume_prompt(check_status))
            self._state = "resuming"
        else:
            self._state = "check_failed"

    def _build_resume_prompt(self, check_status: dict) -> str:
        failures = (self._check_summary or {}).get("failures") or []
        if not failures:
            return FAILURE_PROMPT_TEMPLATE.format(
                command=self.check_command,
                exit_code=check_status["exit_code"],
                tail=check_status["tail"])
        return FAILURE_PROMPT_WITH_FAILURES_TEMPLATE.format(
            command=self.check_command,
            exit_code=check_status["exit_code"],
            tail=check_status["tail"],
            failures_list="\n".join(f"- {name}" for name in failures))
