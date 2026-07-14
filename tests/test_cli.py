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

    def recording_serve(base, staged, sidecar, transcript, host, port):
        calls.append(("serve", base, staged, sidecar, transcript, host, port))

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
    _, base, staged, sidecar, transcript, host, port = next(
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
