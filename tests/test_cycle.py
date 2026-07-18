import json
import time

import pytest

from graphwerk.cycle import FAILURE_PROMPT_TEMPLATE, SessionCycle
from graphwerk.session import NoSessionToResumeError, SessionBusyError


class StubSessionRunner:
    """In-memory SessionRunner stand-in: settles to a queued outcome after
    being polled twice, so tests can observe an intermediate 'running' state
    without a real subprocess."""

    def __init__(self, staged_root, outcomes):
        self.staged_root = staged_root
        self._outcomes = list(outcomes)
        self._state = "idle"
        self._detail = ""
        self._session_id = ""
        self._poll_count = 0
        self.start_prompts = []
        self.start_scopes = []
        self.resume_prompts = []
        self.resume_scopes = []

    def start(self, prompt, scope=None):
        if self._state == "running":
            raise SessionBusyError("a session is already running")
        self.start_prompts.append(prompt)
        self.start_scopes.append(scope)
        self._begin_run()
        return self._snapshot()

    def resume(self, prompt, scope=None):
        if self._state == "running":
            raise SessionBusyError("a session is already running")
        if not self._session_id:
            raise NoSessionToResumeError("no prior session to resume")
        self.resume_prompts.append(prompt)
        self.resume_scopes.append(scope)
        self._begin_run()
        return self._snapshot()

    def _begin_run(self):
        self._state = "running"
        self._poll_count = 0

    def status(self):
        if self._state == "running":
            self._poll_count += 1
            if self._poll_count >= 2 and self._outcomes:
                outcome = self._outcomes.pop(0)
                self._state = outcome["state"]
                self._detail = outcome.get("detail", "")
                if "session_id" in outcome:
                    self._session_id = outcome["session_id"]
        return self._snapshot()

    def _snapshot(self):
        return {"state": self._state, "detail": self._detail, "session_id": self._session_id}


def drive_to_terminal(cycle, timeout_seconds=5.0):
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        snapshot = cycle.status()
        if snapshot["state"] in ("done", "failed", "check_failed"):
            return snapshot
        time.sleep(0.02)
    raise AssertionError("cycle did not reach a terminal state in time")


class FixedStatusRunner:
    """A SessionRunner stand-in whose status() is a pure read (no settling
    side effects), for asserting passthrough without stub statefulness."""

    def __init__(self, staged_root, snapshot):
        self.staged_root = staged_root
        self._snapshot = snapshot
        self.start_prompts = []
        self.start_scopes = []
        self.resume_prompts = []
        self.resume_scopes = []

    def start(self, prompt, scope=None):
        self.start_prompts.append(prompt)
        self.start_scopes.append(scope)
        return dict(self._snapshot)

    def resume(self, prompt, scope=None):
        self.resume_prompts.append(prompt)
        self.resume_scopes.append(scope)
        return dict(self._snapshot)

    def status(self):
        return dict(self._snapshot)


def test_no_check_command_is_a_transparent_passthrough(tmp_path):
    runner = FixedStatusRunner(tmp_path, {"state": "running", "detail": "", "session_id": ""})
    cycle = SessionCycle(runner, check_command=None)

    started = cycle.start("do the thing")

    assert started == {"state": "running", "detail": "", "session_id": "", "check_configured": False}
    assert "attempt" not in cycle.status()


def test_no_check_command_reports_check_configured_false(tmp_path):
    runner = FixedStatusRunner(tmp_path, {"state": "running", "detail": "", "session_id": ""})
    cycle = SessionCycle(runner, check_command=None)

    cycle.start("do the thing")
    status = cycle.status()

    assert status["check_configured"] is False
    underlying = dict(runner.status())
    underlying["check_configured"] = False
    assert status == underlying


def test_reply_passes_through_both_the_unchecked_and_checked_paths(tmp_path):
    runner = FixedStatusRunner(tmp_path, {"state": "done", "detail": "", "session_id": "sess-1",
                                          "reply": "no changes needed, miner.py is still referenced"})

    unchecked_cycle = SessionCycle(runner, check_command=None)
    unchecked_cycle.start("is miner.py unused?")
    assert unchecked_cycle.status()["reply"] == "no changes needed, miner.py is still referenced"

    checked_cycle = SessionCycle(runner, check_command="true")
    checked_cycle.start("is miner.py unused?")
    finished = drive_to_terminal(checked_cycle)
    assert finished["reply"] == "no changes needed, miner.py is still referenced"


def test_check_command_configured_reports_check_configured_true(tmp_path):
    runner = StubSessionRunner(tmp_path, [{"state": "done", "session_id": "sess-1"}])
    cycle = SessionCycle(runner, check_command="true")

    started = cycle.start("do the thing")
    finished = drive_to_terminal(cycle)

    assert started["check_configured"] is True
    assert finished["check_configured"] is True


def test_passing_check_settles_cycle_to_done(tmp_path):
    runner = StubSessionRunner(tmp_path, [{"state": "done", "session_id": "sess-1"}])
    cycle = SessionCycle(runner, check_command="true")

    cycle.start("do the thing")
    finished = drive_to_terminal(cycle)

    assert finished["state"] == "done"
    assert finished["attempt"] == 0
    assert finished["check_exit_code"] == 0
    assert finished["session_id"] == "sess-1"
    assert finished["check_summary"] is None
    assert isinstance(finished["check_duration_s"], float)


def test_failing_check_resumes_with_a_failure_prompt_naming_command_exit_code_and_tail(tmp_path):
    # marker file makes the check fail once, then pass — standing in for the
    # agent's resumed session actually fixing the failures.
    marker = tmp_path / "fixed-after-resume"
    check_command = (
        f'if [ -f {marker} ]; then exit 0; '
        f'else touch {marker}; echo "boom detail" >&2; exit 7; fi'
    )
    runner = StubSessionRunner(tmp_path, [
        {"state": "done", "session_id": "sess-1"},
        {"state": "done", "session_id": "sess-2"},
    ])
    cycle = SessionCycle(runner, check_command=check_command, max_retries=1)

    cycle.start("do the thing")
    finished = drive_to_terminal(cycle)

    assert finished["state"] == "done"
    assert finished["attempt"] == 1
    assert len(runner.resume_prompts) == 1
    prompt = runner.resume_prompts[0]
    assert check_command in prompt
    assert "7" in prompt
    assert "boom detail" in prompt
    # no summary file written this run: prompt is unchanged from today's
    # template, byte for byte — no regression for operators who don't opt in.
    assert prompt == FAILURE_PROMPT_TEMPLATE.format(
        command=check_command, exit_code=7, tail=prompt.split("Output tail:\n", 1)[1].rsplit(
            "\n\nFix the failures shown above.", 1)[0])


def test_resume_prompt_names_failing_tests_when_summary_has_a_failures_list(tmp_path):
    marker = tmp_path / "fixed-after-resume"
    first_run_summary = json.dumps({
        "passed": 1, "failed": 2, "total": 3,
        "failures": ["tests/test_a.py::test_x", "tests/test_b.py::test_y"],
    })
    check_command = (
        f"if [ -f {marker} ]; then exit 0; "
        f"else touch {marker}; echo '{first_run_summary}' > .graphwerk-check.json; exit 7; fi"
    )
    runner = StubSessionRunner(tmp_path, [
        {"state": "done", "session_id": "sess-1"},
        {"state": "done", "session_id": "sess-2"},
    ])
    cycle = SessionCycle(runner, check_command=check_command, max_retries=1)

    cycle.start("do the thing")
    finished = drive_to_terminal(cycle)

    assert finished["state"] == "done"
    assert len(runner.resume_prompts) == 1
    prompt = runner.resume_prompts[0]
    assert "tests/test_a.py::test_x" in prompt
    assert "tests/test_b.py::test_y" in prompt
    assert "may not show all" in prompt


def test_resume_prompt_unchanged_when_summary_has_no_failures_list(tmp_path):
    marker = tmp_path / "fixed-after-resume"
    first_run_summary = json.dumps({"passed": 1, "failed": 2, "total": 3})
    check_command = (
        f"if [ -f {marker} ]; then exit 0; "
        f"else touch {marker}; echo '{first_run_summary}' > .graphwerk-check.json; exit 7; fi"
    )
    runner = StubSessionRunner(tmp_path, [
        {"state": "done", "session_id": "sess-1"},
        {"state": "done", "session_id": "sess-2"},
    ])
    cycle = SessionCycle(runner, check_command=check_command, max_retries=1)

    cycle.start("do the thing")
    finished = drive_to_terminal(cycle)

    assert finished["state"] == "done"
    prompt = runner.resume_prompts[0]
    assert "may not show all" not in prompt
    assert prompt == FAILURE_PROMPT_TEMPLATE.format(
        command=check_command, exit_code=7, tail=prompt.split("Output tail:\n", 1)[1].rsplit(
            "\n\nFix the failures shown above.", 1)[0])


def test_check_failed_after_retries_exhausted(tmp_path):
    runner = StubSessionRunner(tmp_path, [
        {"state": "done", "session_id": "sess-1"},
        {"state": "done", "session_id": "sess-2"},
    ])
    cycle = SessionCycle(runner, check_command="exit 1", max_retries=1)

    cycle.start("do the thing")
    finished = drive_to_terminal(cycle)

    assert finished["state"] == "check_failed"
    assert finished["attempt"] == 1
    assert finished["check_exit_code"] == 1
    assert len(runner.resume_prompts) == 1
    assert finished["check_summary"] is None
    assert isinstance(finished["check_duration_s"], float)


def test_check_command_that_cannot_launch_is_terminal_with_no_resume(tmp_path):
    missing_root = tmp_path / "does-not-exist"
    runner = StubSessionRunner(missing_root, [{"state": "done", "session_id": "sess-1"}])
    cycle = SessionCycle(runner, check_command="true", max_retries=3)

    cycle.start("do the thing")
    finished = drive_to_terminal(cycle)

    assert finished["state"] == "check_failed"
    assert finished["check_exit_code"] is None
    assert finished["check_tail"] != ""
    assert runner.resume_prompts == []


def test_session_failure_ends_cycle_without_checking(tmp_path):
    runner = StubSessionRunner(tmp_path, [{"state": "failed", "detail": "agent crashed"}])
    cycle = SessionCycle(runner, check_command="true")

    cycle.start("do the thing")
    finished = drive_to_terminal(cycle)

    assert finished["state"] == "failed"
    assert finished["detail"] == "agent crashed"
    assert finished["attempt"] == 0
    assert finished["check_exit_code"] is None
    assert finished["check_summary"] is None
    assert finished["check_duration_s"] is None


def test_start_raises_busy_while_session_running(tmp_path):
    runner = StubSessionRunner(tmp_path, [])  # never settles: stays "running"
    cycle = SessionCycle(runner, check_command="true")

    cycle.start("first")
    assert cycle.status()["state"] == "running"

    with pytest.raises(SessionBusyError):
        cycle.start("second")


def test_start_raises_busy_while_check_running(tmp_path):
    runner = StubSessionRunner(tmp_path, [{"state": "done", "session_id": "sess-1"}])
    cycle = SessionCycle(runner, check_command="sleep 0.3")

    cycle.start("first")
    # first status() poll settles the stub runner to done and kicks off the check
    cycle.status()
    cycle.status()
    assert cycle.status()["state"] == "checking"

    with pytest.raises(SessionBusyError):
        cycle.start("second")


def test_continue_session_with_no_check_command_calls_resume_directly(tmp_path):
    runner = FixedStatusRunner(tmp_path, {"state": "running", "detail": "", "session_id": "sess-1"})
    cycle = SessionCycle(runner, check_command=None)

    continued = cycle.continue_session("keep talking")

    assert continued == {"state": "running", "detail": "", "session_id": "sess-1",
                          "check_configured": False}
    assert runner.resume_prompts == ["keep talking"]


def test_continue_session_raises_busy_while_session_running(tmp_path):
    runner = StubSessionRunner(tmp_path, [])  # never settles: stays "running"
    cycle = SessionCycle(runner, check_command="true")

    cycle.start("first")
    assert cycle.status()["state"] == "running"

    with pytest.raises(SessionBusyError):
        cycle.continue_session("keep talking")


def test_continue_session_raises_no_session_to_resume_without_a_prior_session(tmp_path):
    runner = StubSessionRunner(tmp_path, [])
    cycle = SessionCycle(runner, check_command="true")

    with pytest.raises(NoSessionToResumeError):
        cycle.continue_session("keep talking")


def test_continue_session_resets_bookkeeping_and_lands_running_like_start(tmp_path):
    runner = StubSessionRunner(tmp_path, [
        {"state": "done", "session_id": "sess-1"},
        {"state": "done", "session_id": "sess-2"},
    ])
    cycle = SessionCycle(runner, check_command="true")
    cycle.start("first")
    drive_to_terminal(cycle)

    continued = cycle.continue_session("second turn")

    assert continued["state"] == "running"
    assert continued["attempt"] == 0
    finished = drive_to_terminal(cycle)
    assert finished["state"] == "done"
    assert finished["session_id"] == "sess-2"
    assert runner.resume_prompts == ["second turn"]


def test_start_forwards_scope_to_the_runner(tmp_path):
    runner = FixedStatusRunner(tmp_path, {"state": "running", "detail": "", "session_id": ""})
    cycle = SessionCycle(runner, check_command=None)

    cycle.start("do the thing", scope="design")

    assert runner.start_scopes == ["design"]


def test_continue_session_forwards_scope_to_the_runner(tmp_path):
    runner = FixedStatusRunner(tmp_path, {"state": "running", "detail": "", "session_id": "sess-1"})
    cycle = SessionCycle(runner, check_command=None)

    cycle.continue_session("keep talking", scope="implementation")

    assert runner.resume_scopes == ["implementation"]


def test_start_succeeds_again_after_a_terminal_state(tmp_path):
    runner = StubSessionRunner(tmp_path, [
        {"state": "done", "session_id": "sess-1"},
        {"state": "done", "session_id": "sess-2"},
    ])
    cycle = SessionCycle(runner, check_command="true")

    cycle.start("first")
    drive_to_terminal(cycle)

    cycle.start("second")
    finished = drive_to_terminal(cycle)

    assert finished["state"] == "done"
    assert finished["session_id"] == "sess-2"
    assert finished["attempt"] == 0
