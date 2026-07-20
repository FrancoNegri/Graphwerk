"""FastAPI server: JSON API for the graph UI plus the static frontend."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.middleware.gzip import GZipMiddleware

from graphwerk.apply import ApplyEngine
from graphwerk.approval import ApprovalStore
from graphwerk.commit import CommitEngine, CommitError
from graphwerk.cycle import TERMINAL_STATES, SessionCycle
from graphwerk.discard import DiscardEngine
from graphwerk.service import GraphService
from graphwerk.session import NoSessionToResumeError, SessionBusyError

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


class ApplyRequest(BaseModel):
    path: str


class PromptRequest(BaseModel):
    prompt: str = ""
    continue_session: bool = False
    scope: str | None = None


class CommitRequest(BaseModel):
    message: str = ""


class RejectRequest(BaseModel):
    id: str
    label: str = ""
    status: str = ""
    diff: str = ""
    comment: str


def create_app(service: GraphService, engine: ApplyEngine,
               runner: SessionCycle, commit_engine: CommitEngine,
               discard_engine: DiscardEngine, approval_store: ApprovalStore) -> FastAPI:
    app = FastAPI(title="graphwerk")
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    @app.get("/")
    def home():
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/api/graph")
    def graph():
        # to_dict() already yields plain str/int/float/bool/None/list/dict —
        # returning JSONResponse directly skips FastAPI's jsonable_encoder
        # pass, which otherwise dominates response time on large graphs.
        return JSONResponse({
            "base": str(service.base_root),
            "staged": str(service.staged_root),
            "hash": service.state_hash(),
            **service.snapshot().to_dict(),
        })

    @app.get("/api/hash")
    def state_hash():
        return {"hash": service.state_hash()}

    @app.post("/api/apply")
    def apply(req: ApplyRequest):
        approval_store.approve(req.path)
        return {"path": req.path, "approved": True}

    @app.post("/api/unapprove")
    def unapprove(req: ApplyRequest):
        approval_store.unapprove(req.path)
        return {"path": req.path, "approved": False}

    @app.post("/api/commit")
    def commit(req: CommitRequest):
        try:
            return commit_engine.commit_all(req.message)
        except CommitError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.post("/api/discard")
    def discard():
        # never yank files out from under a live agent session or its check
        # gate (ADR 037, ADR 040)
        if runner.status()["state"] not in TERMINAL_STATES:
            raise HTTPException(status_code=409, detail="a session is running — wait for it to finish")
        return {"paths": discard_engine.discard_all()}

    @app.post("/api/reject")
    def reject(req: RejectRequest):
        if not req.comment.strip():
            raise HTTPException(status_code=400, detail="comment is required")
        prompt = engine.reject(req.id, req.label or req.id, req.status, req.comment, req.diff)
        return {"prompt": prompt}

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

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app
