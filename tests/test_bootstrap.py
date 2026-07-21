import subprocess

from fastapi import FastAPI
from fastapi.testclient import TestClient

from graphwerk.bootstrap import build_app


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def test_build_app_wires_a_real_app_against_one_repo_directory(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()

    app = build_app(repo, "HEAD", None, None, "acceptEdits")

    assert isinstance(app, FastAPI)


def test_build_app_wires_session_guidance_into_the_runner(monkeypatch, tmp_path):
    from graphwerk.rationale.guidance import SESSION_GUIDANCE

    runners = []

    class RecordingSessionRunner:
        def __init__(self, staged_root, permission_mode="acceptEdits", system_prompt=""):
            self.staged_root = staged_root
            self.permission_mode = permission_mode
            self.system_prompt = system_prompt
            runners.append(self)

    import graphwerk.bootstrap as bootstrap
    monkeypatch.setattr(bootstrap, "SessionRunner", RecordingSessionRunner)

    repo = tmp_path / "repo"
    repo.mkdir()

    build_app(repo, "HEAD", None, None, "acceptEdits")

    assert runners[0].system_prompt == SESSION_GUIDANCE
    assert runners[0].staged_root == repo


def test_build_app_diffs_uncommitted_local_changes_against_the_base_ref(tmp_path):
    """ADR 058 / ticket 158: a developer's own working directory may have
    uncommitted changes when a review session starts — those changes are
    simply part of the initial diff against base_ref, not an error."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "a.py").write_text("def f():\n    return 1\n")
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.email=t@t.com", "-c", "user.name=t", "commit", "-qm", "init")
    (repo / "a.py").write_text("def f():\n    return 2\n")  # uncommitted

    app = build_app(repo, "HEAD", None, None, "acceptEdits")
    response = TestClient(app).get("/api/graph")

    assert response.status_code == 200
    node = next(n for n in response.json()["nodes"] if n["id"] == "a.py")
    assert node["status"] == "modified"
