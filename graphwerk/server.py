"""FastAPI server: JSON API for the graph UI plus the static frontend."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.middleware.gzip import GZipMiddleware

from graphwerk.cycle import SessionCycle
from graphwerk.service import GraphService
from graphwerk.session import NoSessionToResumeError, SessionBusyError

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


class PromptRequest(BaseModel):
    prompt: str = ""
    continue_session: bool = False
    scope: str | None = None


def create_app(service: GraphService, runner: SessionCycle) -> FastAPI:
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
            # base is a git ref (often a commit sha), not a directory (ADR 058)
            "base": service.base_ref,
            "staged": str(service.repo_root),
            "hash": service.state_hash(),
            **service.snapshot().to_dict(),
        })

    @app.get("/api/hash")
    def state_hash():
        return {"hash": service.state_hash()}

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
