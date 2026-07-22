import json
import subprocess

import pytest
from fastapi.testclient import TestClient

import time
from pathlib import Path

from graphwerk.comparisons import ComparisonRegistry, WORKING_TREE_TOKEN
from graphwerk.cycle import SessionCycle
from graphwerk.server import create_app
from graphwerk.session import NoSessionToResumeError, SessionBusyError


class StubRunner:
    def __init__(self, repo_root=None):
        self.snapshot = {"state": "idle", "detail": "", "session_id": ""}
        self.prompts = []
        self.start_scopes = []
        self.resume_prompts = []
        self.resume_scopes = []
        self.busy = False
        self.has_session = False
        self.repo_root = repo_root

    def start(self, prompt, scope=None):
        if self.busy:
            raise SessionBusyError("a session is already running")
        self.prompts.append(prompt)
        self.start_scopes.append(scope)
        self.snapshot = {"state": "running", "detail": "", "session_id": ""}
        return dict(self.snapshot)

    def resume(self, prompt, scope=None):
        if self.busy:
            raise SessionBusyError("a session is already running")
        if not self.has_session:
            raise NoSessionToResumeError("no prior session to resume")
        self.resume_prompts.append(prompt)
        self.resume_scopes.append(scope)
        self.snapshot = {"state": "running", "detail": "", "session_id": ""}
        return dict(self.snapshot)

    def continue_session(self, prompt, scope=None):
        return self.resume(prompt, scope=scope)

    def status(self):
        return dict(self.snapshot)


@pytest.fixture
def stub_runner():
    return StubRunner()


@pytest.fixture
def client(tmp_path, stub_runner):
    staged = tmp_path / "staged"
    staged.mkdir()
    registry = ComparisonRegistry(staged, "HEAD", sidecar_path=staged / ".graphwerk" / "rationale.json")
    return TestClient(create_app(registry, stub_runner))


def test_prompt_starts_a_run_and_returns_its_status(client, stub_runner):
    response = client.post("/api/prompt", json={"prompt": "add a docstring"})

    assert response.status_code == 200
    assert response.json()["state"] == "running"
    assert stub_runner.prompts == ["add a docstring"]


def test_prompt_missing_or_blank_is_400(client, stub_runner):
    assert client.post("/api/prompt", json={}).status_code == 400
    assert client.post("/api/prompt", json={"prompt": "   "}).status_code == 400
    assert stub_runner.prompts == []


def test_prompt_while_running_is_409(client, stub_runner):
    stub_runner.busy = True

    response = client.post("/api/prompt", json={"prompt": "another"})

    assert response.status_code == 409


def test_prompt_with_continue_session_dispatches_to_resume(client, stub_runner):
    stub_runner.has_session = True

    response = client.post("/api/prompt",
                           json={"prompt": "keep talking", "continue_session": True})

    assert response.status_code == 200
    assert response.json()["state"] == "running"
    assert stub_runner.resume_prompts == ["keep talking"]
    assert stub_runner.prompts == []


def test_prompt_forwards_scope_to_start(client, stub_runner):
    response = client.post("/api/prompt", json={"prompt": "add a docstring", "scope": "implementation"})

    assert response.status_code == 200
    assert stub_runner.start_scopes == ["implementation"]


def test_prompt_forwards_scope_to_continue_session(client, stub_runner):
    stub_runner.has_session = True

    response = client.post("/api/prompt", json={
        "prompt": "keep talking", "continue_session": True, "scope": "design"})

    assert response.status_code == 200
    assert stub_runner.resume_scopes == ["design"]


def test_prompt_without_scope_forwards_none(client, stub_runner):
    client.post("/api/prompt", json={"prompt": "add a docstring"})

    assert stub_runner.start_scopes == [None]


def test_prompt_continue_session_without_a_prior_session_is_409(client, stub_runner):
    response = client.post("/api/prompt",
                           json={"prompt": "keep talking", "continue_session": True})

    assert response.status_code == 409
    assert stub_runner.resume_prompts == []


def test_failed_spawn_surfaces_runner_message(client, stub_runner):
    def failing_start(prompt, scope=None):
        stub_runner.snapshot = {"state": "failed",
                                "detail": "could not launch claude: not found",
                                "session_id": ""}
        return dict(stub_runner.snapshot)
    stub_runner.start = failing_start

    response = client.post("/api/prompt", json={"prompt": "hello"})

    assert response.status_code == 503
    assert "could not launch claude" in response.json()["detail"]


def test_session_returns_runner_status_snapshot(client, stub_runner):
    stub_runner.snapshot = {"state": "done", "detail": "", "session_id": "sess-9"}

    response = client.get("/api/session")

    assert response.status_code == 200
    assert response.json() == {"state": "done", "detail": "", "session_id": "sess-9"}


def make_cycle_client(tmp_path, check_command, max_retries=1):
    staged = tmp_path / "staged"
    staged.mkdir()
    stub_runner = StubRunner(repo_root=staged)
    cycle = SessionCycle(stub_runner, check_command, max_retries=max_retries)
    registry = ComparisonRegistry(staged, "HEAD", sidecar_path=staged / ".graphwerk" / "rationale.json")
    client = TestClient(create_app(registry, cycle))
    return client, stub_runner


def drive_session_to_terminal(client, timeout_seconds=5.0):
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        snapshot = client.get("/api/session").json()
        if snapshot["state"] in ("done", "failed", "check_failed"):
            return snapshot
        time.sleep(0.02)
    raise AssertionError("session did not reach a terminal state in time")


def test_gate_off_session_payload_is_backward_compatible(tmp_path):
    client, stub_runner = make_cycle_client(tmp_path, check_command=None)

    response = client.post("/api/prompt", json={"prompt": "add a docstring"})
    stub_runner.snapshot = {"state": "done", "detail": "", "session_id": "sess-1"}

    assert response.status_code == 200
    assert client.get("/api/session").json() == {
        "state": "done", "detail": "", "session_id": "sess-1", "check_configured": False}


def test_gate_on_passing_check_reports_done(tmp_path):
    client, stub_runner = make_cycle_client(tmp_path, check_command="true")

    client.post("/api/prompt", json={"prompt": "add a docstring"})
    stub_runner.snapshot = {"state": "done", "detail": "", "session_id": "sess-1"}
    finished = drive_session_to_terminal(client)

    assert finished["state"] == "done"
    assert finished["attempt"] == 0
    assert finished["check_exit_code"] == 0


def test_gate_on_failing_check_surfaces_check_failed_and_tail(tmp_path):
    client, stub_runner = make_cycle_client(
        tmp_path, check_command='echo "assertion failed" >&2; exit 1', max_retries=0)

    client.post("/api/prompt", json={"prompt": "add a docstring"})
    stub_runner.snapshot = {"state": "done", "detail": "", "session_id": "sess-1"}
    finished = drive_session_to_terminal(client)

    assert finished["state"] == "check_failed"
    assert finished["check_exit_code"] == 1
    assert "assertion failed" in finished["check_tail"]


def test_prompt_409s_for_the_whole_cycle_not_just_the_agent_subprocess(tmp_path):
    client, stub_runner = make_cycle_client(tmp_path, check_command="sleep 0.3")

    client.post("/api/prompt", json={"prompt": "add a docstring"})
    stub_runner.snapshot = {"state": "done", "detail": "", "session_id": "sess-1"}
    deadline = time.monotonic() + 5.0
    while client.get("/api/session").json()["state"] != "checking":
        assert time.monotonic() < deadline, "check never started"

    response = client.post("/api/prompt", json={"prompt": "another"})

    assert response.status_code == 409


def test_existing_endpoints_still_respond(client):
    assert client.get("/api/hash").status_code == 200
    assert client.get("/api/graph").status_code == 200


def test_graph_endpoint_skips_jsonable_encoder(client, monkeypatch):
    """`/api/graph`'s payload is already JSON-primitive (models.py's to_dict()
    methods guarantee it); routing it through FastAPI's generic
    jsonable_encoder is pure overhead that dominates response time on large
    graphs (profiled: ~1.2s of a ~1.8s response). Returning a JSONResponse
    directly skips that pass — this pins the behavior so it can't regress."""
    import fastapi.routing

    def _fail(*args, **kwargs):
        raise AssertionError("jsonable_encoder should not run for /api/graph")

    monkeypatch.setattr(fastapi.routing, "jsonable_encoder", _fail)

    response = client.get("/api/graph")

    assert response.status_code == 200
    assert response.json()["nodes"] == []


def test_graph_endpoint_compresses_large_responses(tmp_path, stub_runner):
    """The graph JSON is served over LAN to a browser (CLAUDE.md); highlighted
    code makes the payload large but highly compressible (~90% smaller
    gzipped, profiled). Without compression, LAN transfer time dominates the
    already-fast warm-cache response."""
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    base.mkdir()
    staged.mkdir()
    source = "def f():\n    pass\n" * 200  # comfortably past the gzip floor
    (base / "a.py").write_text(source)
    (staged / "a.py").write_text(source)
    registry = ComparisonRegistry(staged, "HEAD", sidecar_path=staged / ".graphwerk" / "rationale.json")
    client = TestClient(create_app(registry, stub_runner))

    response = client.get("/api/graph", headers={"Accept-Encoding": "gzip"})

    assert response.status_code == 200
    assert response.headers["content-encoding"] == "gzip"
    assert response.json()["nodes"]


@pytest.mark.parametrize("method,path", [
    ("post", "/api/apply"),
    ("post", "/api/unapprove"),
    ("post", "/api/commit"),
    ("post", "/api/discard"),
    ("post", "/api/reject"),
])
def test_mutation_endpoints_are_gone(client, method, path):
    response = getattr(client, method)(path, json={})

    assert response.status_code == 404


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True)
    return result.stdout


def _commit(repo: Path, message: str) -> str:
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.email=test@graphwerk.local", "-c", "user.name=test",
         "commit", "-q", "-m", message, "--allow-empty")
    return _git(repo, "rev-parse", "HEAD").strip()


def make_git_backed_client(tmp_path, stub_runner):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _commit(repo, "first")
    _commit(repo, "second")
    _git(repo, "tag", "v1.0")
    _git(repo, "branch", "feature-x")
    registry = ComparisonRegistry(repo, "HEAD", sidecar_path=repo / ".graphwerk" / "rationale.json")
    return TestClient(create_app(registry, stub_runner))


def make_two_commit_repo_client(tmp_path, stub_runner):
    """A repo with two commits touching the same symbol, plus a further
    uncommitted change on top, so the working tree, the second commit, and
    the first commit are all distinguishable (mirrors test_comparisons.py's
    fixture, but exercised through the live HTTP surface)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    (repo / "a.py").write_text("def foo():\n    return 1\n")
    first = _commit(repo, "first")
    (repo / "a.py").write_text("def foo():\n    return 2\n")
    second = _commit(repo, "second")
    (repo / "a.py").write_text("def foo():\n    return 3\n")  # uncommitted
    registry = ComparisonRegistry(repo, first, sidecar_path=repo / ".graphwerk" / "rationale.json")
    client = TestClient(create_app(registry, stub_runner))
    return client, first, second


def test_refs_endpoint_lists_branches_tags_commits_and_working_directory(tmp_path, stub_runner):
    client = make_git_backed_client(tmp_path, stub_runner)

    response = client.get("/api/refs")

    assert response.status_code == 200
    entries = response.json()
    kinds = {entry["kind"] for entry in entries}
    assert kinds == {"working_tree", "branch", "tag", "commit"}
    working_tree_entries = [entry for entry in entries if entry["kind"] == "working_tree"]
    assert working_tree_entries == [
        {"ref": WORKING_TREE_TOKEN, "label": "working directory, uncommitted", "kind": "working_tree"}
    ]
    branch_names = {entry["ref"] for entry in entries if entry["kind"] == "branch"}
    assert branch_names == {"main", "feature-x"}
    tag_names = {entry["ref"] for entry in entries if entry["kind"] == "tag"}
    assert tag_names == {"v1.0"}


def test_refs_endpoint_is_just_the_working_directory_for_a_non_git_repo(client):
    response = client.get("/api/refs")

    assert response.status_code == 200
    assert response.json() == [
        {"ref": WORKING_TREE_TOKEN, "label": "working directory, uncommitted", "kind": "working_tree"}
    ]


def test_graph_endpoint_with_no_params_matches_the_default_pair_explicitly_requested(tmp_path, stub_runner):
    """Ticket 173: omitting both params must fall back to the registry's
    CLI-configured default pair (today's base_ref vs. the working
    directory) byte-for-byte — pinned here by comparing against the same
    pair requested explicitly."""
    client, first, _second = make_two_commit_repo_client(tmp_path, stub_runner)

    default_response = client.get("/api/graph")
    explicit_default_response = client.get("/api/graph", params={"base": first, "staged": WORKING_TREE_TOKEN})

    assert default_response.status_code == 200
    assert default_response.json() == explicit_default_response.json()
    foo = next(n for n in default_response.json()["nodes"] if n["id"] == "a.py::foo")
    assert "return 3" in foo["diff"]  # the uncommitted working-tree version
    assert default_response.json()["base"] == first
    assert default_response.json()["staged"] == str(tmp_path / "repo")


def test_graph_endpoint_resolves_an_explicit_historical_pair(tmp_path, stub_runner):
    """Ticket 173: an explicit (base, staged) pair resolves through the
    registry and reflects that pair's diff, not the default one."""
    client, first, second = make_two_commit_repo_client(tmp_path, stub_runner)

    response = client.get("/api/graph", params={"base": first, "staged": second})

    assert response.status_code == 200
    payload = response.json()
    assert payload["base"] == first
    assert payload["staged"] == second
    foo = next(n for n in payload["nodes"] if n["id"] == "a.py::foo")
    assert "return 2" in foo["diff"]


def test_hash_endpoint_accepts_base_and_staged_params(tmp_path, stub_runner):
    client, first, second = make_two_commit_repo_client(tmp_path, stub_runner)

    default_response = client.get("/api/hash")
    explicit_response = client.get("/api/hash", params={"base": first, "staged": second})

    assert default_response.status_code == 200
    assert explicit_response.status_code == 200
    assert "hash" in default_response.json()
    assert "hash" in explicit_response.json()


def test_commit_all_commits_the_live_pairs_changed_paths_with_the_given_message(tmp_path, stub_runner):
    client, first, _second = make_two_commit_repo_client(tmp_path, stub_runner)
    repo = tmp_path / "repo"

    response = client.post("/api/commit-all", json={"message": "wire up the fix"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["base"] == first
    assert payload["staged"] == str(repo)
    assert "hash" in payload and "nodes" in payload and "edges" in payload
    assert _git(repo, "log", "-1", "--format=%s").strip() == "wire up the fix"
    assert _git(repo, "status", "--porcelain").strip() == ""  # working tree clean post-commit


def test_commit_all_falls_back_to_the_mined_commit_message_when_none_is_given(tmp_path, stub_runner):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    (repo / "a.py").write_text("def foo():\n    return 1\n")
    first = _commit(repo, "first")
    (repo / "a.py").write_text("def foo():\n    return 2\n")  # uncommitted
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text(json.dumps({
        "type": "assistant",
        "message": {"content": [{"type": "text", "text": "Commit-message: mined message"}]},
    }) + "\n")
    registry = ComparisonRegistry(repo, first, sidecar_path=repo / ".graphwerk" / "rationale.json",
                                   transcript_path=transcript)
    client = TestClient(create_app(registry, stub_runner))

    response = client.post("/api/commit-all", json={})

    assert response.status_code == 200
    assert _git(repo, "log", "-1", "--format=%s").strip() == "mined message"


def test_commit_all_400s_when_no_message_is_available(tmp_path, stub_runner):
    client, _first, _second = make_two_commit_repo_client(tmp_path, stub_runner)

    response = client.post("/api/commit-all", json={})

    assert response.status_code == 400
    assert "no commit message available" in response.json()["detail"]


def test_revert_all_stashes_the_live_pairs_changed_paths_and_restores_the_tree(tmp_path, stub_runner):
    client, _first, _second = make_two_commit_repo_client(tmp_path, stub_runner)
    repo = tmp_path / "repo"

    response = client.post("/api/revert-all")

    assert response.status_code == 200
    payload = response.json()
    assert "hash" in payload and "nodes" in payload and "edges" in payload
    assert _git(repo, "stash", "list").strip() != ""
    assert (repo / "a.py").read_text() == "def foo():\n    return 2\n"  # HEAD's content, restored


@pytest.mark.parametrize("path", ["/api/commit-all", "/api/revert-all"])
def test_commit_all_and_revert_all_400_for_a_historical_non_live_pair(tmp_path, stub_runner, path):
    client, first, second = make_two_commit_repo_client(tmp_path, stub_runner)

    response = client.post(path, params={"base": first, "staged": second}, json={"message": "x"})

    assert response.status_code == 400
