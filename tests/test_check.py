import time

import pytest

from graphwerk.check import CheckBusyError, CheckRunner


@pytest.fixture
def root(tmp_path):
    check_root = tmp_path / "root"
    check_root.mkdir()
    return check_root


def wait_until_settled(runner, timeout_seconds=5.0):
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        snapshot = runner.status()
        if snapshot["state"] != "running":
            return snapshot
        time.sleep(0.02)
    raise AssertionError("check did not settle in time")


def test_starts_idle(root):
    runner = CheckRunner("true", root)

    assert runner.status() == {"state": "idle", "exit_code": None, "tail": ""}


def test_passing_command_settles_to_passed(root):
    runner = CheckRunner("true", root)

    started = runner.start()

    assert started["state"] in ("running", "passed")
    finished = wait_until_settled(runner)
    assert finished == {"state": "passed", "exit_code": 0, "tail": ""}


def test_failing_command_settles_to_failed_with_exit_code(root):
    runner = CheckRunner("exit 3", root)

    runner.start()
    finished = wait_until_settled(runner)

    assert finished["state"] == "failed"
    assert finished["exit_code"] == 3


def test_command_runs_in_given_root(root):
    marker = root / "marker.txt"
    runner = CheckRunner(f"pwd > {marker.name}", root)

    runner.start()
    wait_until_settled(runner)

    assert marker.read_text().strip() == str(root.resolve())


def test_stdout_and_stderr_are_combined_in_the_tail(root):
    runner = CheckRunner('echo "to stdout"; echo "to stderr" >&2; exit 1', root)

    runner.start()
    finished = wait_until_settled(runner)

    assert "to stdout" in finished["tail"]
    assert "to stderr" in finished["tail"]


def test_tail_bounded_to_last_hundred_lines(root):
    runner = CheckRunner('for i in $(seq 1 150); do echo "line $i"; done', root)

    runner.start()
    finished = wait_until_settled(runner)

    lines = finished["tail"].splitlines()
    assert len(lines) <= 100
    assert "line 150" in finished["tail"]
    assert "line 1\n" not in finished["tail"] and finished["tail"].split("\n")[0] != "line 1"


def test_tail_bounded_by_byte_cap(root):
    runner = CheckRunner('for i in $(seq 1 5000); do echo "a very long line of check output $i"; done', root)

    runner.start()
    finished = wait_until_settled(runner)

    assert len(finished["tail"].encode()) <= 4096


def test_start_while_running_raises_busy(root, tmp_path):
    release = tmp_path / "release"
    runner = CheckRunner(f"while [ ! -e {release} ]; do sleep 0.02; done", root)
    runner.start()
    try:
        with pytest.raises(CheckBusyError):
            runner.start()
        assert runner.status()["state"] == "running"
    finally:
        release.touch()
    assert wait_until_settled(runner)["state"] == "passed"


def test_command_that_cannot_launch_settles_to_error(tmp_path):
    missing_root = tmp_path / "does-not-exist"
    runner = CheckRunner("true", missing_root)

    started = runner.start()

    assert started["state"] == "error"
    assert started["exit_code"] is None
    assert started["tail"] != ""
    assert runner.status()["state"] == "error"
