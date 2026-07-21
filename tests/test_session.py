import json
import subprocess
import tempfile
import threading
import time

import pytest

from graphwerk.design_guidance import DESIGN_SESSION_GUIDANCE
from graphwerk.session import NoSessionToResumeError, SessionBusyError, SessionRunner


@pytest.fixture
def repo_root(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    return root


def make_stub(tmp_path, script_body, name="claude-stub"):
    stub = tmp_path / name
    stub.write_text(f"#!/bin/sh\n{script_body}\n")
    stub.chmod(0o755)
    return stub


def wait_until_finished(runner, timeout_seconds=5.0):
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        snapshot = runner.status()
        if snapshot["state"] != "running":
            return snapshot
        time.sleep(0.02)
    raise AssertionError("session did not finish in time")


def test_starts_idle(repo_root):
    runner = SessionRunner(repo_root)

    assert runner.status() == {"state": "idle", "detail": "", "session_id": "", "reply": ""}


def test_successful_run_reports_done_with_session_id(repo_root, tmp_path):
    stub = make_stub(tmp_path, 'echo \'{"session_id": "sess-42"}\'')
    runner = SessionRunner(repo_root, claude_cmd=str(stub))

    started = runner.start("add a docstring")

    # the stub may already have exited by the time start() reports back
    assert started["state"] in ("running", "done")
    finished = wait_until_finished(runner)
    assert finished == {"state": "done", "detail": "", "session_id": "sess-42", "reply": ""}


def test_child_runs_in_repo_root_with_headless_flags(repo_root, tmp_path):
    record = tmp_path / "record.txt"
    stub = make_stub(tmp_path, f'pwd > {record}\necho "$@" >> {record}\n'
                               'echo \'{"session_id": "s"}\'')
    runner = SessionRunner(repo_root, claude_cmd=str(stub),
                           permission_mode="bypassPermissions")

    runner.start("do the thing")
    wait_until_finished(runner)

    recorded_cwd, recorded_args = record.read_text().splitlines()
    assert recorded_cwd == str(repo_root.resolve())
    assert recorded_args == ("-p do the thing --output-format json "
                             "--permission-mode bypassPermissions")


def test_system_prompt_appends_flag_when_set(repo_root, tmp_path):
    record = tmp_path / "record.txt"
    stub = make_stub(tmp_path, f'echo "$@" > {record}\n'
                               'echo \'{"session_id": "s"}\'')
    runner = SessionRunner(repo_root, claude_cmd=str(stub),
                           system_prompt="follow the guidance")

    runner.start("do the thing")
    wait_until_finished(runner)

    assert record.read_text().strip() == (
        "-p do the thing --output-format json --permission-mode acceptEdits "
        "--append-system-prompt follow the guidance")


def test_no_system_prompt_leaves_command_unchanged(repo_root, tmp_path):
    record = tmp_path / "record.txt"
    stub = make_stub(tmp_path, f'echo "$@" > {record}\n'
                               'echo \'{"session_id": "s"}\'')
    runner = SessionRunner(repo_root, claude_cmd=str(stub))

    runner.start("do the thing")
    wait_until_finished(runner)

    assert record.read_text().strip() == (
        "-p do the thing --output-format json --permission-mode acceptEdits")


def test_design_scope_appends_design_guidance_with_no_system_prompt_set(repo_root, tmp_path):
    record = tmp_path / "record.txt"
    stub = make_stub(tmp_path, f'echo "$@" > {record}\n'
                               'echo \'{"session_id": "s"}\'')
    runner = SessionRunner(repo_root, claude_cmd=str(stub))

    runner.start("do the thing", scope="design")
    wait_until_finished(runner)

    assert record.read_text().strip() == (
        "-p do the thing --output-format json --permission-mode acceptEdits "
        f"--append-system-prompt {DESIGN_SESSION_GUIDANCE}")


def test_design_scope_appends_design_guidance_after_the_existing_system_prompt(repo_root, tmp_path):
    record = tmp_path / "record.txt"
    stub = make_stub(tmp_path, f'echo "$@" > {record}\n'
                               'echo \'{"session_id": "s"}\'')
    runner = SessionRunner(repo_root, claude_cmd=str(stub),
                           system_prompt="follow the guidance")

    runner.start("do the thing", scope="design")
    wait_until_finished(runner)

    assert record.read_text().strip() == (
        "-p do the thing --output-format json --permission-mode acceptEdits "
        f"--append-system-prompt follow the guidance\n\n{DESIGN_SESSION_GUIDANCE}")


def test_implementation_scope_builds_the_exact_same_command_as_no_scope(repo_root, tmp_path):
    record = tmp_path / "record.txt"
    stub = make_stub(tmp_path, f'echo "$@" > {record}\n'
                               'echo \'{"session_id": "s"}\'')
    runner = SessionRunner(repo_root, claude_cmd=str(stub),
                           system_prompt="follow the guidance")

    runner.start("do the thing", scope="implementation")
    wait_until_finished(runner)

    assert record.read_text().strip() == (
        "-p do the thing --output-format json --permission-mode acceptEdits "
        "--append-system-prompt follow the guidance")


def test_resume_with_design_scope_appends_design_guidance(repo_root, tmp_path):
    first_stub = make_stub(tmp_path, 'echo \'{"session_id": "sess-1"}\'', name="first-stub")
    runner = SessionRunner(repo_root, claude_cmd=str(first_stub))
    runner.start("initial prompt")
    wait_until_finished(runner)

    record = tmp_path / "record.txt"
    resume_stub = make_stub(tmp_path, f'echo "$@" > {record}\n'
                                      'echo \'{"session_id": "sess-2"}\'', name="resume-stub")
    runner.claude_cmd = str(resume_stub)
    runner.resume("please fix the failures", scope="design")
    wait_until_finished(runner)

    assert record.read_text().strip() == (
        "-p please fix the failures --resume sess-1 --output-format json "
        f"--permission-mode acceptEdits --append-system-prompt {DESIGN_SESSION_GUIDANCE}")


def test_start_while_running_raises_busy(repo_root, tmp_path):
    release = tmp_path / "release"
    stub = make_stub(tmp_path, f'while [ ! -e {release} ]; do sleep 0.02; done\n'
                               'echo \'{"session_id": "s"}\'')
    runner = SessionRunner(repo_root, claude_cmd=str(stub))
    runner.start("first prompt")
    try:
        with pytest.raises(SessionBusyError):
            runner.start("second prompt")
        assert runner.status()["state"] == "running"
    finally:
        release.touch()
    assert wait_until_finished(runner)["state"] == "done"


def test_nonzero_exit_reports_failed_with_exit_detail(repo_root, tmp_path):
    stub = make_stub(tmp_path, "exit 3")
    runner = SessionRunner(repo_root, claude_cmd=str(stub))

    runner.start("break please")
    finished = wait_until_finished(runner)

    assert finished["state"] == "failed"
    assert "3" in finished["detail"]


def test_missing_binary_reports_failed_without_raising(repo_root, tmp_path):
    runner = SessionRunner(repo_root, claude_cmd=str(tmp_path / "no-such-claude"))

    started = runner.start("hello")

    assert started["state"] == "failed"
    assert "no-such-claude" in started["detail"]
    assert runner.status()["state"] == "failed"


def test_unparseable_success_output_reports_failed(repo_root, tmp_path):
    stub = make_stub(tmp_path, "echo not-json")
    runner = SessionRunner(repo_root, claude_cmd=str(stub))

    runner.start("hello")
    finished = wait_until_finished(runner)

    assert finished["state"] == "failed"
    assert finished["detail"] != ""


class SlowExitingChild:
    """Fake child whose poll() is slow enough for unsynchronized threads to overlap in it."""

    def __init__(self, exit_code=0, poll_delay=0.05):
        self.exit_code = exit_code
        self.poll_delay = poll_delay

    def poll(self):
        time.sleep(self.poll_delay)
        return self.exit_code


def make_settling_runner(repo_root, output=b'{"session_id": "sess-race"}'):
    """A runner whose child has already exited but has not been settled yet."""
    runner = SessionRunner(repo_root)
    runner._child = SlowExitingChild()
    runner._child_output = tempfile.TemporaryFile()
    runner._child_output.write(output)
    runner._child_errors = tempfile.TemporaryFile()
    runner._state = "running"
    return runner


def run_in_threads(*targets):
    errors = []

    def wrap(target):
        def guarded():
            try:
                target()
            except Exception as exc:  # noqa: BLE001 - the test asserts on this
                errors.append(exc)
        return guarded

    threads = [threading.Thread(target=wrap(target)) for target in targets]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return errors


def test_concurrent_status_polls_settle_exactly_once(repo_root):
    runner = make_settling_runner(repo_root)
    barrier = threading.Barrier(2)

    def poll_status():
        barrier.wait()
        runner.status()

    errors = run_in_threads(poll_status, poll_status)

    assert errors == []
    assert runner.status() == {"state": "done", "detail": "",
                               "session_id": "sess-race", "reply": ""}


def test_start_racing_a_settling_poll_sees_settled_state(repo_root, tmp_path):
    stub = make_stub(tmp_path, 'echo \'{"session_id": "sess-next"}\'')
    runner = make_settling_runner(repo_root)
    runner.claude_cmd = str(stub)
    barrier = threading.Barrier(2)

    def poll_status():
        barrier.wait()
        runner.status()

    def start_next():
        barrier.wait()
        time.sleep(0.01)  # land inside the other thread's settling poll
        runner.start("next prompt")

    errors = run_in_threads(poll_status, start_next)

    assert errors == []
    assert wait_until_finished(runner) == {"state": "done", "detail": "",
                                           "session_id": "sess-next", "reply": ""}


def test_failed_run_keeps_last_successful_session_id(repo_root, tmp_path):
    ok_stub = make_stub(tmp_path, 'echo \'{"session_id": "sess-1"}\'')
    runner = SessionRunner(repo_root, claude_cmd=str(ok_stub))
    runner.start("first")
    assert wait_until_finished(runner)["session_id"] == "sess-1"

    runner.claude_cmd = str(make_stub(tmp_path, "exit 1", name="failing-stub"))
    runner.start("second")
    finished = wait_until_finished(runner)

    assert finished["state"] == "failed"
    assert finished["session_id"] == "sess-1"


def test_stderr_warning_does_not_corrupt_the_session_result(repo_root, tmp_path):
    stub = make_stub(tmp_path, 'echo "warning: connectors disabled" >&2\n'
                               'echo \'{"session_id": "sess-clean"}\'')
    runner = SessionRunner(repo_root, claude_cmd=str(stub))

    runner.start("hello")
    finished = wait_until_finished(runner)

    assert finished == {"state": "done", "detail": "", "session_id": "sess-clean", "reply": ""}


def test_event_array_output_yields_the_result_events_session_id(repo_root, tmp_path):
    events = ('[{"type": "system", "subtype": "init", "session_id": "sess-events"},'
              ' {"type": "assistant", "session_id": "sess-events"},'
              ' {"type": "result", "subtype": "success", "session_id": "sess-events"}]')
    stub = make_stub(tmp_path, f"echo '{events}'")
    runner = SessionRunner(repo_root, claude_cmd=str(stub))

    runner.start("hello")
    finished = wait_until_finished(runner)

    assert finished == {"state": "done", "detail": "", "session_id": "sess-events", "reply": ""}


def test_result_events_result_field_is_exposed_as_reply(repo_root, tmp_path):
    events = ('[{"type": "assistant", "session_id": "sess-reply"},'
              ' {"type": "result", "subtype": "success", "session_id": "sess-reply",'
              ' "result": "no changes needed, miner.py is still referenced"}]')
    stub = make_stub(tmp_path, f"echo '{events}'")
    runner = SessionRunner(repo_root, claude_cmd=str(stub))

    runner.start("is miner.py unused?")
    finished = wait_until_finished(runner)

    assert finished == {"state": "done", "detail": "", "session_id": "sess-reply",
                        "reply": "no changes needed, miner.py is still referenced"}


def test_no_result_event_yields_empty_string_reply(repo_root, tmp_path):
    stub = make_stub(tmp_path, 'echo \'{"session_id": "sess-no-result"}\'')
    runner = SessionRunner(repo_root, claude_cmd=str(stub))

    runner.start("hello")
    finished = wait_until_finished(runner)

    assert finished["reply"] == ""


def test_failed_run_reports_empty_string_reply_not_the_prior_turns(repo_root, tmp_path):
    ok_stub = make_stub(tmp_path, 'echo \'[{"type": "result", "session_id": "sess-1", '
                                  '"result": "first turn reply"}]\'')
    runner = SessionRunner(repo_root, claude_cmd=str(ok_stub))
    runner.start("first")
    assert wait_until_finished(runner)["reply"] == "first turn reply"

    runner.claude_cmd = str(make_stub(tmp_path, "exit 1", name="failing-stub"))
    runner.start("second")
    finished = wait_until_finished(runner)

    assert finished["state"] == "failed"
    assert finished["reply"] == ""


def test_second_turns_reply_replaces_the_first_no_accumulation(repo_root, tmp_path):
    first_stub = make_stub(tmp_path, 'echo \'[{"type": "result", "session_id": "sess-1", '
                                     '"result": "first reply"}]\'')
    runner = SessionRunner(repo_root, claude_cmd=str(first_stub))
    runner.start("first prompt")
    assert wait_until_finished(runner)["reply"] == "first reply"

    resume_stub = make_stub(tmp_path, 'echo \'[{"type": "result", "session_id": "sess-1", '
                                      '"result": "second reply"}]\'', name="resume-stub")
    runner.claude_cmd = str(resume_stub)
    runner.resume("second prompt")
    finished = wait_until_finished(runner)

    assert finished["reply"] == "second reply"


def test_nonzero_exit_detail_includes_stderr(repo_root, tmp_path):
    stub = make_stub(tmp_path, 'echo "credit balance too low" >&2\nexit 1')
    runner = SessionRunner(repo_root, claude_cmd=str(stub))

    runner.start("hello")
    finished = wait_until_finished(runner)

    assert finished["state"] == "failed"
    assert "credit balance too low" in finished["detail"]


def test_unparseable_output_detail_includes_a_snippet(repo_root, tmp_path):
    stub = make_stub(tmp_path, "echo not-json-at-all")
    runner = SessionRunner(repo_root, claude_cmd=str(stub))

    runner.start("hello")
    finished = wait_until_finished(runner)

    assert finished["state"] == "failed"
    assert "not-json-at-all" in finished["detail"]


def test_resume_raises_when_no_prior_session(repo_root, tmp_path):
    runner = SessionRunner(repo_root, claude_cmd=str(tmp_path / "unused"))

    with pytest.raises(NoSessionToResumeError):
        runner.resume("follow up")


def test_resume_sends_resume_flag_with_last_session_id(repo_root, tmp_path):
    record = tmp_path / "record.txt"
    first_stub = make_stub(tmp_path, 'echo \'{"session_id": "sess-1"}\'', name="first-stub")
    runner = SessionRunner(repo_root, claude_cmd=str(first_stub),
                           permission_mode="bypassPermissions")
    runner.start("initial prompt")
    wait_until_finished(runner)

    resume_stub = make_stub(tmp_path, f'echo "$@" > {record}\n'
                                      'echo \'{"session_id": "sess-2"}\'', name="resume-stub")
    runner.claude_cmd = str(resume_stub)
    runner.resume("please fix the failures")
    finished = wait_until_finished(runner)

    assert record.read_text().strip() == (
        "-p please fix the failures --resume sess-1 --output-format json "
        "--permission-mode bypassPermissions")
    assert finished == {"state": "done", "detail": "", "session_id": "sess-2", "reply": ""}


def test_resume_appends_system_prompt_when_set(repo_root, tmp_path):
    record = tmp_path / "record.txt"
    first_stub = make_stub(tmp_path, 'echo \'{"session_id": "sess-1"}\'', name="first-stub")
    runner = SessionRunner(repo_root, claude_cmd=str(first_stub),
                           system_prompt="follow the guidance")
    runner.start("initial prompt")
    wait_until_finished(runner)

    resume_stub = make_stub(tmp_path, f'echo "$@" > {record}\n'
                                      'echo \'{"session_id": "sess-2"}\'', name="resume-stub")
    runner.claude_cmd = str(resume_stub)
    runner.resume("please fix the failures")
    wait_until_finished(runner)

    assert record.read_text().strip() == (
        "-p please fix the failures --resume sess-1 --output-format json "
        "--permission-mode acceptEdits --append-system-prompt follow the guidance")


def test_resume_while_running_raises_busy(repo_root, tmp_path):
    first_stub = make_stub(tmp_path, 'echo \'{"session_id": "sess-1"}\'', name="first-stub")
    runner = SessionRunner(repo_root, claude_cmd=str(first_stub))
    runner.start("initial prompt")
    wait_until_finished(runner)

    release = tmp_path / "release"
    slow_stub = make_stub(tmp_path, f'while [ ! -e {release} ]; do sleep 0.02; done\n'
                                    'echo \'{"session_id": "sess-2"}\'', name="slow-stub")
    runner.claude_cmd = str(slow_stub)
    runner.start("kick off a long one")
    try:
        with pytest.raises(SessionBusyError):
            runner.resume("try to resume mid-run")
        assert runner.status()["state"] == "running"
    finally:
        release.touch()
    assert wait_until_finished(runner)["state"] == "done"


def test_resume_failure_keeps_the_prior_session_id(repo_root, tmp_path):
    first_stub = make_stub(tmp_path, 'echo \'{"session_id": "sess-1"}\'', name="first-stub")
    runner = SessionRunner(repo_root, claude_cmd=str(first_stub))
    runner.start("initial prompt")
    wait_until_finished(runner)

    failing_stub = make_stub(tmp_path, "exit 2", name="failing-resume-stub")
    runner.claude_cmd = str(failing_stub)
    runner.resume("please fix the failures")
    finished = wait_until_finished(runner)

    assert finished["state"] == "failed"
    assert finished["session_id"] == "sess-1"


def settings_path(repo_root):
    return repo_root / ".claude" / "settings.local.json"


def test_start_with_no_scope_writes_no_hook_config(repo_root, tmp_path):
    stub = make_stub(tmp_path, 'echo \'{"session_id": "s"}\'')
    runner = SessionRunner(repo_root, claude_cmd=str(stub))

    runner.start("do the thing")
    wait_until_finished(runner)

    assert not settings_path(repo_root).exists()


def test_start_with_design_scope_writes_a_pretooluse_hook_config(repo_root, tmp_path):
    stub = make_stub(tmp_path, 'echo \'{"session_id": "s"}\'')
    runner = SessionRunner(repo_root, claude_cmd=str(stub))

    runner.start("do the thing", scope="design")
    wait_until_finished(runner)

    settings = json.loads(settings_path(repo_root).read_text())
    entry = settings["hooks"]["PreToolUse"][0]
    assert entry["matcher"] == "Edit|Write"
    command = entry["hooks"][0]["command"]
    assert "graphwerk.hooks.scope_guard" in command
    assert "GRAPHWERK_SCOPE=design" in command


def test_resume_with_implementation_scope_writes_a_hook_config(repo_root, tmp_path):
    first_stub = make_stub(tmp_path, 'echo \'{"session_id": "sess-1"}\'', name="first-stub")
    runner = SessionRunner(repo_root, claude_cmd=str(first_stub))
    runner.start("initial prompt")
    wait_until_finished(runner)

    resume_stub = make_stub(tmp_path, 'echo \'{"session_id": "sess-2"}\'', name="resume-stub")
    runner.claude_cmd = str(resume_stub)
    runner.resume("please fix the failures", scope="implementation")
    wait_until_finished(runner)

    command = json.loads(settings_path(repo_root).read_text())["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
    assert "GRAPHWERK_SCOPE=implementation" in command


def test_design_scope_hook_denies_py_writes_and_allows_md_writes_without_corrupting_session_result(
    repo_root, tmp_path
):
    stub = make_stub(tmp_path, 'echo \'{"session_id": "sess-scoped"}\'')
    runner = SessionRunner(repo_root, claude_cmd=str(stub))

    runner.start("update the docs", scope="design")
    finished = wait_until_finished(runner)

    command = json.loads(settings_path(repo_root).read_text())["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
    py_result = subprocess.run(
        command, shell=True, capture_output=True, text=True,
        input=json.dumps({"tool_name": "Write", "tool_input": {"file_path": "graphwerk/service.py"}}),
    )
    md_result = subprocess.run(
        command, shell=True, capture_output=True, text=True,
        input=json.dumps({"tool_name": "Write", "tool_input": {"file_path": "docs/x.md"}}),
    )

    assert json.loads(py_result.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert json.loads(md_result.stdout)["hookSpecificOutput"]["permissionDecision"] == "allow"
    assert finished == {"state": "done", "detail": "", "session_id": "sess-scoped", "reply": ""}


def test_rerunning_with_a_new_scope_replaces_the_old_hook_entry_rather_than_duplicating(repo_root, tmp_path):
    stub = make_stub(tmp_path, 'echo \'{"session_id": "s"}\'')
    runner = SessionRunner(repo_root, claude_cmd=str(stub))

    runner.start("first", scope="design")
    wait_until_finished(runner)
    runner.start("second", scope="implementation")
    wait_until_finished(runner)

    pre_tool_use = json.loads(settings_path(repo_root).read_text())["hooks"]["PreToolUse"]
    assert len(pre_tool_use) == 1
    assert "GRAPHWERK_SCOPE=implementation" in pre_tool_use[0]["hooks"][0]["command"]


def test_scope_hook_config_preserves_unrelated_existing_settings(repo_root, tmp_path):
    settings_path(repo_root).parent.mkdir(parents=True)
    settings_path(repo_root).write_text(json.dumps({"otherSetting": "keep-me"}))
    stub = make_stub(tmp_path, 'echo \'{"session_id": "s"}\'')
    runner = SessionRunner(repo_root, claude_cmd=str(stub))

    runner.start("do the thing", scope="design")
    wait_until_finished(runner)

    assert json.loads(settings_path(repo_root).read_text())["otherSetting"] == "keep-me"
