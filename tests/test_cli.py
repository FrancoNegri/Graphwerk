import subprocess
from pathlib import Path

import pytest

from graphwerk import cli


@pytest.fixture
def git_repo(tmp_path):
    repo = tmp_path / "myrepo"
    repo.mkdir()
    subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
    return repo


@pytest.fixture
def start_harness(monkeypatch):
    """Record ShadowWorkspace.ensure and _serve calls instead of running them."""
    calls = []

    class RecordingWorkspace:
        @classmethod
        def ensure(cls, repo_root, staging_root, branch="graphwerk-staging"):
            calls.append(("ensure", repo_root, staging_root, branch))

    def recording_serve(base, staged, sidecar, transcript, host, port,
                        agent_permissions, check_command=None, check_retries=1):
        calls.append(("serve", base, staged, sidecar, transcript, host, port,
                      agent_permissions, check_command, check_retries))

    monkeypatch.setattr(cli, "ShadowWorkspace", RecordingWorkspace)
    monkeypatch.setattr(cli, "_serve", recording_serve)
    return calls


def ensure_call(calls):
    return next(call for call in calls if call[0] == "ensure")


def test_start_defaults_staging_to_sibling_and_branch(git_repo, start_harness):
    cli.main(["start", "--repo", str(git_repo)])

    _, repo_root, staging_root, branch = ensure_call(start_harness)
    assert repo_root == git_repo
    assert staging_root == git_repo.parent / "myrepo-graphwerk-staging"
    assert branch == "graphwerk-staging"


def test_start_defaults_repo_to_cwd(git_repo, start_harness, monkeypatch):
    monkeypatch.chdir(git_repo)

    cli.main(["start"])

    _, repo_root, staging_root, _ = ensure_call(start_harness)
    assert repo_root == git_repo
    assert staging_root == git_repo.parent / "myrepo-graphwerk-staging"


def test_start_prints_claude_invocation_before_serving(git_repo, start_harness, capsys):
    cli.main(["start", "--repo", str(git_repo)])

    staging = git_repo.parent / "myrepo-graphwerk-staging"
    assert f"cd {staging} && claude" in capsys.readouterr().out
    assert [call[0] for call in start_harness] == ["ensure", "serve"]


def test_start_serves_repo_against_worktree_with_transcript_autodiscovery(git_repo, start_harness):
    cli.main(["start", "--repo", str(git_repo), "--host", "0.0.0.0", "--port", "9000"])

    staging = git_repo.parent / "myrepo-graphwerk-staging"
    _, base, staged, sidecar, transcript, host, port, _, _, _ = next(
        call for call in start_harness if call[0] == "serve")
    assert base == git_repo
    assert staged == staging
    assert sidecar == staging / ".graphwerk" / "rationale.json"
    assert transcript is None
    assert (host, port) == ("0.0.0.0", 9000)


def test_start_honors_explicit_staging_and_branch(git_repo, start_harness, tmp_path):
    staging = tmp_path / "elsewhere"

    cli.main(["start", "--repo", str(git_repo),
              "--staging", str(staging), "--branch", "feature-x"])

    _, repo_root, staging_root, branch = ensure_call(start_harness)
    assert repo_root == git_repo
    assert staging_root == staging
    assert branch == "feature-x"


def test_start_rejects_non_git_repo(tmp_path, start_harness):
    not_a_repo = tmp_path / "plain-dir"
    not_a_repo.mkdir()

    with pytest.raises(SystemExit) as excinfo:
        cli.main(["start", "--repo", str(not_a_repo)])

    assert excinfo.value.code not in (0, None)
    assert "not a git repository" in str(excinfo.value)
    assert start_harness == []


def serve_call(calls):
    return next(call for call in calls if call[0] == "serve")


def test_start_defaults_agent_permissions_to_accept_edits(git_repo, start_harness):
    cli.main(["start", "--repo", str(git_repo)])

    assert serve_call(start_harness)[7] == "acceptEdits"


def test_start_passes_agent_permissions_through(git_repo, start_harness):
    cli.main(["start", "--repo", str(git_repo),
              "--agent-permissions", "bypassPermissions"])

    assert serve_call(start_harness)[7] == "bypassPermissions"


def test_serve_passes_agent_permissions_through(start_harness, tmp_path):
    cli.main(["serve", "--base", str(tmp_path / "base"),
              "--staged", str(tmp_path / "staged"),
              "--agent-permissions", "plan"])

    assert serve_call(start_harness)[7] == "plan"


def test_serve_defaults_agent_permissions_to_accept_edits(start_harness, tmp_path):
    cli.main(["serve", "--base", str(tmp_path / "base"),
              "--staged", str(tmp_path / "staged")])

    assert serve_call(start_harness)[7] == "acceptEdits"


def test_start_defaults_check_gate_off(git_repo, start_harness):
    cli.main(["start", "--repo", str(git_repo)])

    assert serve_call(start_harness)[8:] == (None, 1)


def test_start_passes_check_flags_through(git_repo, start_harness):
    cli.main(["start", "--repo", str(git_repo),
              "--check", "pytest -x", "--check-retries", "3"])

    assert serve_call(start_harness)[8:] == ("pytest -x", 3)


def test_serve_defaults_check_gate_off(start_harness, tmp_path):
    cli.main(["serve", "--base", str(tmp_path / "base"),
              "--staged", str(tmp_path / "staged")])

    assert serve_call(start_harness)[8:] == (None, 1)


def test_serve_passes_check_flags_through(start_harness, tmp_path):
    cli.main(["serve", "--base", str(tmp_path / "base"),
              "--staged", str(tmp_path / "staged"),
              "--check", "make check", "--check-retries", "2"])

    assert serve_call(start_harness)[8:] == ("make check", 2)


@pytest.fixture
def real_serve_harness(monkeypatch):
    """Call the real `_serve`, but stub out uvicorn so it never actually
    starts a server."""
    class RecordingUvicorn:
        @staticmethod
        def run(app, host, port, log_level):
            pass

    monkeypatch.setattr(cli, "uvicorn", RecordingUvicorn)


def test_serve_builds_and_runs_an_app(real_serve_harness, tmp_path):
    cli._serve(tmp_path / "base", tmp_path / "staged", None, None,
               "127.0.0.1", 8135, "acceptEdits")
