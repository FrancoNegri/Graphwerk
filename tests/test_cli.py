import subprocess

import pytest

from graphwerk import cli


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


@pytest.fixture
def git_repo(tmp_path):
    repo = tmp_path / "myrepo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "a.py").write_text("def f():\n    return 1\n")
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.email=t@t.com", "-c", "user.name=t", "commit", "-qm", "init")
    return repo


@pytest.fixture
def serve_harness(monkeypatch):
    """Record calls to _serve instead of actually building an app/server."""
    calls = []

    def recording_serve(repo, base_ref, sidecar, transcript, host, port,
                        agent_permissions, check_command=None, check_retries=1):
        calls.append((repo, base_ref, sidecar, transcript, host, port,
                      agent_permissions, check_command, check_retries))

    monkeypatch.setattr(cli, "_serve", recording_serve)
    return calls


def head_sha(repo):
    result = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                            capture_output=True, text=True, check=True)
    return result.stdout.strip()


def test_serve_defaults_repo_to_cwd_and_base_ref_to_head(git_repo, serve_harness, monkeypatch):
    monkeypatch.chdir(git_repo)

    cli.main(["serve"])

    repo, base_ref = serve_harness[0][0], serve_harness[0][1]
    assert repo == git_repo
    assert base_ref == head_sha(git_repo)


def test_serve_honors_explicit_repo_and_base_ref(git_repo, serve_harness):
    cli.main(["serve", "--repo", str(git_repo), "--base-ref", "some-other-ref"])

    repo, base_ref = serve_harness[0][0], serve_harness[0][1]
    assert repo == git_repo
    assert base_ref == "some-other-ref"


def test_serve_rejects_old_base_and_staged_flags(git_repo):
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["serve", "--base", str(git_repo), "--staged", str(git_repo)])

    assert excinfo.value.code not in (0, None)


def test_serve_sidecar_and_transcript_defaults(git_repo, serve_harness):
    cli.main(["serve", "--repo", str(git_repo)])

    call = serve_harness[0]
    assert call[2] == git_repo / ".graphwerk" / "rationale.json"
    assert call[3] is None


def test_serve_passes_agent_permissions_through(git_repo, serve_harness):
    cli.main(["serve", "--repo", str(git_repo), "--agent-permissions", "plan"])

    assert serve_harness[0][6] == "plan"


def test_serve_defaults_agent_permissions_to_accept_edits(git_repo, serve_harness):
    cli.main(["serve", "--repo", str(git_repo)])

    assert serve_harness[0][6] == "acceptEdits"


def test_serve_defaults_check_gate_off(git_repo, serve_harness):
    cli.main(["serve", "--repo", str(git_repo)])

    assert serve_harness[0][7:] == (None, 1)


def test_serve_passes_check_flags_through(git_repo, serve_harness):
    cli.main(["serve", "--repo", str(git_repo), "--check", "make check", "--check-retries", "2"])

    assert serve_harness[0][7:] == ("make check", 2)


def test_start_defaults_repo_to_cwd_and_base_ref_to_head(git_repo, serve_harness, monkeypatch):
    monkeypatch.chdir(git_repo)

    cli.main(["start"])

    repo, base_ref = serve_harness[0][0], serve_harness[0][1]
    assert repo == git_repo
    assert base_ref == head_sha(git_repo)


def test_start_honors_explicit_repo_and_base_ref(git_repo, serve_harness):
    cli.main(["start", "--repo", str(git_repo), "--base-ref", "some-other-ref"])

    repo, base_ref = serve_harness[0][0], serve_harness[0][1]
    assert repo == git_repo
    assert base_ref == "some-other-ref"


def test_start_no_longer_accepts_staging_or_branch_flags(git_repo):
    with pytest.raises(SystemExit):
        cli.main(["start", "--repo", str(git_repo), "--staging", "/tmp/x"])

    with pytest.raises(SystemExit):
        cli.main(["start", "--repo", str(git_repo), "--branch", "feature-x"])


def test_start_does_not_create_a_worktree(git_repo, serve_harness):
    cli.main(["start", "--repo", str(git_repo)])

    result = subprocess.run(["git", "-C", str(git_repo), "worktree", "list"],
                            capture_output=True, text=True, check=True)
    assert len(result.stdout.strip().splitlines()) == 1  # only the repo itself


def test_start_prints_claude_invocation_for_the_repo_itself(git_repo, serve_harness, capsys):
    cli.main(["start", "--repo", str(git_repo)])

    out = capsys.readouterr().out
    assert f"cd {git_repo} && claude" in out


def test_start_serves_the_repo_directory_itself(git_repo, serve_harness):
    cli.main(["start", "--repo", str(git_repo), "--host", "0.0.0.0", "--port", "9000"])

    repo, base_ref, sidecar, transcript, host, port = serve_harness[0][:6]
    assert repo == git_repo
    assert base_ref == head_sha(git_repo)
    assert sidecar == git_repo / ".graphwerk" / "rationale.json"
    assert transcript is None
    assert (host, port) == ("0.0.0.0", 9000)


def test_start_rejects_non_git_repo(tmp_path, serve_harness):
    not_a_repo = tmp_path / "plain-dir"
    not_a_repo.mkdir()

    with pytest.raises(SystemExit) as excinfo:
        cli.main(["start", "--repo", str(not_a_repo)])

    assert excinfo.value.code not in (0, None)
    assert "not a git repository" in str(excinfo.value)
    assert serve_harness == []


def test_start_defaults_agent_permissions_to_accept_edits(git_repo, serve_harness):
    cli.main(["start", "--repo", str(git_repo)])

    assert serve_harness[0][6] == "acceptEdits"


def test_start_passes_agent_permissions_through(git_repo, serve_harness):
    cli.main(["start", "--repo", str(git_repo), "--agent-permissions", "bypassPermissions"])

    assert serve_harness[0][6] == "bypassPermissions"


def test_start_defaults_check_gate_off(git_repo, serve_harness):
    cli.main(["start", "--repo", str(git_repo)])

    assert serve_harness[0][7:] == (None, 1)


def test_start_passes_check_flags_through(git_repo, serve_harness):
    cli.main(["start", "--repo", str(git_repo), "--check", "pytest -x", "--check-retries", "3"])

    assert serve_harness[0][7:] == ("pytest -x", 3)


def test_serve_and_start_do_not_error_on_uncommitted_local_changes(git_repo, serve_harness):
    (git_repo / "a.py").write_text("def f():\n    return 2\n")  # uncommitted change

    cli.main(["serve", "--repo", str(git_repo)])
    cli.main(["start", "--repo", str(git_repo)])

    assert len(serve_harness) == 2


def test_shadow_workspace_module_is_gone():
    import graphwerk.staging as staging

    assert not hasattr(staging, "ShadowWorkspace")


def test_demo_serves_the_workspace_directory_itself(tmp_path, serve_harness):
    demo_dir = tmp_path / "demo_workspace"

    cli.main(["demo", "--dir", str(demo_dir)])

    repo, base_ref = serve_harness[0][0], serve_harness[0][1]
    assert repo == demo_dir
    assert base_ref == head_sha(demo_dir)
    assert not (tmp_path / "staged").exists()
    assert not (demo_dir / "staged").exists()


def test_demo_no_serve_does_not_call_serve(tmp_path, serve_harness):
    cli.main(["demo", "--dir", str(tmp_path / "demo_workspace"), "--no-serve"])

    assert serve_harness == []
    with pytest.raises(ModuleNotFoundError):
        import graphwerk.staging.workspace  # noqa: F401


@pytest.fixture
def real_serve_harness(monkeypatch):
    """Call the real `_serve`, but stub out uvicorn so it never actually
    starts a server."""
    class RecordingUvicorn:
        @staticmethod
        def run(app, host, port, log_level):
            pass

    monkeypatch.setattr(cli, "uvicorn", RecordingUvicorn)


def test_serve_builds_and_runs_an_app(real_serve_harness, git_repo):
    cli._serve(git_repo, "HEAD", None, None, "127.0.0.1", 8135, "acceptEdits")
