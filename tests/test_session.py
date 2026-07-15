import time

import pytest

from graphwerk.session import SessionBusyError, SessionRunner


@pytest.fixture
def staged_root(tmp_path):
    root = tmp_path / "staged"
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


def test_starts_idle(staged_root):
    runner = SessionRunner(staged_root)

    assert runner.status() == {"state": "idle", "detail": "", "session_id": ""}


def test_successful_run_reports_done_with_session_id(staged_root, tmp_path):
    stub = make_stub(tmp_path, 'echo \'{"session_id": "sess-42"}\'')
    runner = SessionRunner(staged_root, claude_cmd=str(stub))

    started = runner.start("add a docstring")

    assert started["state"] == "running"
    finished = wait_until_finished(runner)
    assert finished == {"state": "done", "detail": "", "session_id": "sess-42"}


def test_child_runs_in_staged_root_with_headless_flags(staged_root, tmp_path):
    record = tmp_path / "record.txt"
    stub = make_stub(tmp_path, f'pwd > {record}\necho "$@" >> {record}\n'
                               'echo \'{"session_id": "s"}\'')
    runner = SessionRunner(staged_root, claude_cmd=str(stub),
                           permission_mode="bypassPermissions")

    runner.start("do the thing")
    wait_until_finished(runner)

    recorded_cwd, recorded_args = record.read_text().splitlines()
    assert recorded_cwd == str(staged_root.resolve())
    assert recorded_args == ("-p do the thing --output-format json "
                             "--permission-mode bypassPermissions")


def test_start_while_running_raises_busy(staged_root, tmp_path):
    release = tmp_path / "release"
    stub = make_stub(tmp_path, f'while [ ! -e {release} ]; do sleep 0.02; done\n'
                               'echo \'{"session_id": "s"}\'')
    runner = SessionRunner(staged_root, claude_cmd=str(stub))
    runner.start("first prompt")
    try:
        with pytest.raises(SessionBusyError):
            runner.start("second prompt")
        assert runner.status()["state"] == "running"
    finally:
        release.touch()
    assert wait_until_finished(runner)["state"] == "done"


def test_nonzero_exit_reports_failed_with_exit_detail(staged_root, tmp_path):
    stub = make_stub(tmp_path, "exit 3")
    runner = SessionRunner(staged_root, claude_cmd=str(stub))

    runner.start("break please")
    finished = wait_until_finished(runner)

    assert finished["state"] == "failed"
    assert "3" in finished["detail"]


def test_missing_binary_reports_failed_without_raising(staged_root, tmp_path):
    runner = SessionRunner(staged_root, claude_cmd=str(tmp_path / "no-such-claude"))

    started = runner.start("hello")

    assert started["state"] == "failed"
    assert "no-such-claude" in started["detail"]
    assert runner.status()["state"] == "failed"


def test_unparseable_success_output_reports_failed(staged_root, tmp_path):
    stub = make_stub(tmp_path, "echo not-json")
    runner = SessionRunner(staged_root, claude_cmd=str(stub))

    runner.start("hello")
    finished = wait_until_finished(runner)

    assert finished["state"] == "failed"
    assert finished["detail"] != ""


def test_failed_run_keeps_last_successful_session_id(staged_root, tmp_path):
    ok_stub = make_stub(tmp_path, 'echo \'{"session_id": "sess-1"}\'')
    runner = SessionRunner(staged_root, claude_cmd=str(ok_stub))
    runner.start("first")
    assert wait_until_finished(runner)["session_id"] == "sess-1"

    runner.claude_cmd = str(make_stub(tmp_path, "exit 1", name="failing-stub"))
    runner.start("second")
    finished = wait_until_finished(runner)

    assert finished["state"] == "failed"
    assert finished["session_id"] == "sess-1"
