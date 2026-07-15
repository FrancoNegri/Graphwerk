"""FastAPI server: JSON API for the graph UI plus the static frontend."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from graphwerk.apply import ApplyEngine
from graphwerk.service import GraphService
from graphwerk.session import SessionBusyError, SessionRunner

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


class ApplyRequest(BaseModel):
    path: str


class PromptRequest(BaseModel):
    prompt: str = ""


class RejectRequest(BaseModel):
    id: str
    label: str = ""
    status: str = ""
    diff: str = ""
    comment: str


def create_app(service: GraphService, engine: ApplyEngine,
               runner: SessionRunner) -> FastAPI:
    app = FastAPI(title="graphwerk")

    @app.get("/")
    def home():
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/api/graph")
    def graph():
        return {
            "base": str(service.base_root),
            "staged": str(service.staged_root),
            "hash": service.state_hash(),
            **service.snapshot().to_dict(),
        }

    @app.get("/api/hash")
    def state_hash():
        return {"hash": service.state_hash()}

    @app.post("/api/apply")
    def apply(req: ApplyRequest):
        try:
            return {"result": engine.apply_file(req.path)}
        except (ValueError, FileNotFoundError) as exc:
            raise HTTPException(status_code=400, detail=str(exc))

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
            started = runner.start(req.prompt)
        except SessionBusyError as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        if started["state"] == "failed":
            raise HTTPException(status_code=503, detail=started["detail"])
        return started

    @app.get("/api/session")
    def session():
        return runner.status()

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app
