import pytest
from fastapi.testclient import TestClient

from graphwerk.apply import ApplyEngine
from graphwerk.rationale import RationaleStore
from graphwerk.server import create_app
from graphwerk.service import GraphService
from graphwerk.session import SessionBusyError


class StubRunner:
    def __init__(self):
        self.snapshot = {"state": "idle", "detail": "", "session_id": ""}
        self.prompts = []
        self.busy = False

    def start(self, prompt):
        if self.busy:
            raise SessionBusyError("a session is already running")
        self.prompts.append(prompt)
        self.snapshot = {"state": "running", "detail": "", "session_id": ""}
        return dict(self.snapshot)

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
    service = GraphService(base, staged, rationale)
    engine = ApplyEngine(base, staged)
    return TestClient(create_app(service, engine, stub_runner))


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


def test_failed_spawn_surfaces_runner_message(client, stub_runner):
    def failing_start(prompt):
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


def test_existing_endpoints_still_respond(client):
    assert client.get("/api/hash").status_code == 200
    assert client.get("/api/graph").status_code == 200
