import pytest
from fastapi.testclient import TestClient

import time

from graphwerk.cycle import SessionCycle
from graphwerk.rationale import RationaleStore
from graphwerk.server import create_app
from graphwerk.service import GraphService
from graphwerk.session import NoSessionToResumeError, SessionBusyError


class StubRunner:
    def __init__(self, staged_root=None):
        self.snapshot = {"state": "idle", "detail": "", "session_id": ""}
        self.prompts = []
        self.start_scopes = []
        self.resume_prompts = []
        self.resume_scopes = []
        self.busy = False
        self.has_session = False
        self.staged_root = staged_root

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
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    base.mkdir()
    staged.mkdir()
    rationale = RationaleStore(sidecar_path=staged / ".graphwerk" / "rationale.json",
                               transcript_path=None, staged_root=staged, base_root=base)
    service = GraphService(staged, "HEAD", rationale)
    return TestClient(create_app(service, stub_runner))


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
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    base.mkdir()
    staged.mkdir()
    stub_runner = StubRunner(staged_root=staged)
    cycle = SessionCycle(stub_runner, check_command, max_retries=max_retries)
    rationale = RationaleStore(sidecar_path=staged / ".graphwerk" / "rationale.json",
                               transcript_path=None, staged_root=staged, base_root=base)
    service = GraphService(staged, "HEAD", rationale)
    client = TestClient(create_app(service, cycle))
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
    rationale = RationaleStore(sidecar_path=staged / ".graphwerk" / "rationale.json",
                               transcript_path=None, staged_root=staged, base_root=base)
    service = GraphService(staged, "HEAD", rationale)
    client = TestClient(create_app(service, stub_runner))

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
