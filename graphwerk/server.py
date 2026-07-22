"""FastAPI server: JSON API for the graph UI plus the static frontend."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.middleware.gzip import GZipMiddleware

from graphwerk import landing
from graphwerk.comparisons import WORKING_TREE_TOKEN, ComparisonRegistry
from graphwerk.cycle import SessionCycle
from graphwerk.refs import list_refs
from graphwerk.service import GraphService
from graphwerk.session import NoSessionToResumeError, SessionBusyError

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


class PromptRequest(BaseModel):
    prompt: str = ""
    continue_session: bool = False
    scope: str | None = None


class CommitAllRequest(BaseModel):
    message: str | None = None


def _graph_payload(service: GraphService) -> dict:
    """Same shape `/api/graph` returns for `service`'s pair — shared so
    commit-all/revert-all (ticket 178) can respond with it directly and
    the frontend never needs a second fetch after either action."""
    return {
        # base is a git ref (often a commit sha), not a directory (ADR 058)
        "base": service.base_ref,
        "staged": str(service.repo_root) if service.staged_ref == WORKING_TREE_TOKEN else service.staged_ref,
        "hash": service.state_hash(),
        **service.snapshot().to_dict(),
    }


def _live_service(registry: ComparisonRegistry, base: str | None, staged: str | None, action: str) -> GraphService:
    """Resolves the requested pair and gates whole-tree write actions to the
    one pair with an actual working tree behind it (ADR 060/061) — every
    other pair 400s rather than silently doing nothing."""
    service = registry.get(base, staged)
    if service.staged_ref != WORKING_TREE_TOKEN:
        raise HTTPException(status_code=400, detail=f"{action} requires the live (working-directory) pair")
    return service


def create_app(registry: ComparisonRegistry, runner: SessionCycle) -> FastAPI:
    app = FastAPI(title="graphwerk")
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    @app.get("/")
    def home():
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/api/graph")
    def graph(base: str | None = None, staged: str | None = None):
        # Omitting either/both param falls back to the registry's
        # CLI-configured default pair, so a param-less request is
        # byte-for-byte the same response as before this pair became
        # selectable (ADR 060 / ticket 173).
        service = registry.get(base, staged)
        # to_dict() already yields plain str/int/float/bool/None/list/dict —
        # returning JSONResponse directly skips FastAPI's jsonable_encoder
        # pass, which otherwise dominates response time on large graphs.
        return JSONResponse(_graph_payload(service))

    @app.get("/api/hash")
    def state_hash(base: str | None = None, staged: str | None = None):
        service = registry.get(base, staged)
        return {"hash": service.state_hash()}

    @app.get("/api/refs")
    def refs():
        # The working-directory pseudo-ref first — it's the default side of
        # today's one live comparison, so it belongs at the top of the list
        # the frontend's dropdowns are sourced from (ADR 060).
        working_tree_entry = {
            "ref": WORKING_TREE_TOKEN, "label": "working directory, uncommitted", "kind": "working_tree"
        }
        return [working_tree_entry, *list_refs(registry.repo_root)]

    @app.post("/api/prompt")
    def prompt(req: PromptRequest):
        if not req.prompt.strip():
            raise HTTPException(status_code=400, detail="prompt is required")
        try:
            if req.continue_session:
                started = runner.continue_session(req.prompt, scope=req.scope)
            else:
                started = runner.start(req.prompt, scope=req.scope)
        except SessionBusyError as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        except NoSessionToResumeError as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        if started["state"] == "failed":
            raise HTTPException(status_code=503, detail=started["detail"])
        return started

    @app.get("/api/session")
    def session():
        return runner.status()

    @app.post("/api/commit-all")
    def commit_all(base: str | None = None, staged: str | None = None, body: CommitAllRequest = CommitAllRequest()):
        service = _live_service(registry, base, staged, "commit-all")
        message = body.message or service.rationale.commit_message
        if not message:
            raise HTTPException(
                status_code=400, detail="no commit message available — none mined and none provided"
            )
        landing.commit_all(registry.repo_root, service.changed_paths(), message)
        return JSONResponse(_graph_payload(service))

    @app.post("/api/revert-all")
    def revert_all(base: str | None = None, staged: str | None = None):
        service = _live_service(registry, base, staged, "revert-all")
        landing.revert_all(registry.repo_root, service.changed_paths())
        return JSONResponse(_graph_payload(service))

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app
