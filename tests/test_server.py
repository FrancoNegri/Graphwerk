import pytest
from fastapi.testclient import TestClient

from graphwerk.apply import ApplyEngine
from graphwerk.commit import CommitEngine
from graphwerk.discard import DiscardEngine
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
    commit_engine = CommitEngine(base, engine, service.builder)
    discard_engine = DiscardEngine(base, staged, service.builder)
    return TestClient(create_app(service, engine, stub_runner, commit_engine, discard_engine))


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
    service = GraphService(base, staged, rationale)
    engine = ApplyEngine(base, staged)
    commit_engine = CommitEngine(base, engine, service.builder)
    discard_engine = DiscardEngine(base, staged, service.builder)
    client = TestClient(create_app(service, engine, stub_runner, commit_engine, discard_engine))

    response = client.get("/api/graph", headers={"Accept-Encoding": "gzip"})

    assert response.status_code == 200
    assert response.headers["content-encoding"] == "gzip"
    assert response.json()["nodes"]


def test_commit_endpoint_returns_paths_and_hash(tmp_path, stub_runner):
    import subprocess

    base = tmp_path / "base"
    staged = tmp_path / "staged"
    base.mkdir()
    staged.mkdir()
    (base / "mod.py").write_text("def f():\n    return 1\n")
    (staged / "mod.py").write_text("def f():\n    return 2\n")
    for args in (["init", "-q"], ["config", "user.email", "t@e.st"],
                 ["config", "user.name", "T"], ["add", "-A"],
                 ["commit", "-q", "-m", "initial"]):
        subprocess.run(["git", "-C", str(base), *args], check=True, capture_output=True)
    rationale = RationaleStore(sidecar_path=staged / ".graphwerk" / "rationale.json",
                               transcript_path=None, staged_root=staged, base_root=base)
    service = GraphService(base, staged, rationale)
    engine = ApplyEngine(base, staged)
    commit_engine = CommitEngine(base, engine, service.builder)
    discard_engine = DiscardEngine(base, staged, service.builder)
    client = TestClient(create_app(service, engine, stub_runner, commit_engine, discard_engine))

    response = client.post("/api/commit", json={"message": "Bump f"})

    assert response.status_code == 200
    assert response.json()["paths"] == ["mod.py"]
    assert response.json()["commit"]


def test_commit_endpoint_maps_preflight_failures_to_400(client):
    response = client.post("/api/commit", json={"message": "msg"})

    assert response.status_code == 400
    assert "git repository" in response.json()["detail"]


def test_discard_endpoint_refuses_while_session_running(client, stub_runner):
    stub_runner.snapshot = {"state": "running", "detail": "", "session_id": "s1"}

    response = client.post("/api/discard")

    assert response.status_code == 409


def test_discard_endpoint_reverts_the_staged_changes(tmp_path, stub_runner):
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    base.mkdir()
    staged.mkdir()
    (base / "mod.py").write_text("def f():\n    return 1\n")
    (staged / "mod.py").write_text("def f():\n    return 2\n")
    rationale = RationaleStore(sidecar_path=staged / ".graphwerk" / "rationale.json",
                               transcript_path=None, staged_root=staged, base_root=base)
    service = GraphService(base, staged, rationale)
    engine = ApplyEngine(base, staged)
    commit_engine = CommitEngine(base, engine, service.builder)
    discard_engine = DiscardEngine(base, staged, service.builder)
    client = TestClient(create_app(service, engine, stub_runner, commit_engine, discard_engine))

    response = client.post("/api/discard")

    assert response.status_code == 200
    assert response.json()["paths"] == ["mod.py"]
    assert (staged / "mod.py").read_text() == "def f():\n    return 1\n"
