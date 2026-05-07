from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

import uvicorn
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

try:
    from app.backend import Backend, SupervisorClient, get_backend, get_supervisor_client
    from app.models import (
        ActivationResult,
        InvestigationResult,
        PolicyConfig,
        PolicyPatch,
        SignalIncident,
        SignalListItem,
    )
except ModuleNotFoundError:  # pragma: no cover - supports direct `python app.py`
    from backend import Backend, SupervisorClient, get_backend, get_supervisor_client
    from models import (
        ActivationResult,
        InvestigationResult,
        PolicyConfig,
        PolicyPatch,
        SignalIncident,
        SignalListItem,
    )

api = APIRouter(prefix="/api")


def backend_dependency(request: Request) -> Backend:
    return request.app.state.backend


def supervisor_dependency(request: Request) -> SupervisorClient:
    return request.app.state.supervisor


BackendDep = Annotated[Backend, Depends(backend_dependency)]
SupervisorDep = Annotated[SupervisorClient, Depends(supervisor_dependency)]


@api.get("/health", operation_id="getHealth")
async def get_health() -> dict[str, str]:
    return {"status": "ok", "service": "nba-decisioning-engine"}


@api.get("/signals", response_model=list[SignalListItem], operation_id="listSignals")
async def list_signals(backend: BackendDep) -> list[SignalListItem]:
    return backend.list_signals()


@api.get("/signals/{signal_id}", response_model=SignalIncident, operation_id="getSignal")
async def get_signal(signal_id: str, backend: BackendDep) -> SignalIncident:
    try:
        return backend.get_signal(signal_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Signal not found") from exc


@api.get("/policy", response_model=PolicyConfig, operation_id="getPolicy")
async def get_policy(backend: BackendDep) -> PolicyConfig:
    return backend.get_policy()


@api.patch("/policy", response_model=PolicyConfig, operation_id="updatePolicy")
async def update_policy(patch: PolicyPatch, backend: BackendDep) -> PolicyConfig:
    return backend.update_policy(patch)


@api.post(
    "/signals/{signal_id}/investigate",
    response_model=InvestigationResult,
    operation_id="investigateSignal",
)
async def investigate_signal(
    signal_id: str,
    backend: BackendDep,
    supervisor: SupervisorDep,
) -> InvestigationResult:
    try:
        signal = backend.get_signal(signal_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Signal not found") from exc
    return supervisor.investigate(signal)


@api.post(
    "/signals/{signal_id}/activate",
    response_model=ActivationResult,
    operation_id="simulateActivation",
)
async def simulate_activation(signal_id: str, backend: BackendDep) -> ActivationResult:
    try:
        return backend.simulate_activation(signal_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Signal not found") from exc


def create_app() -> FastAPI:
    app = FastAPI(
        title="CME Next Best Actions Engine",
        version="0.1.0",
        description="Agent-driven Next Best Actions decisioning API for the CME media demo.",
    )
    app.state.backend = get_backend()
    app.state.supervisor = get_supervisor_client()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api)
    _mount_frontend(app)
    return app


def _mount_frontend(app: FastAPI) -> None:
    dist_dir = Path(__file__).resolve().parent / "ui" / "dist"
    index_file = dist_dir / "index.html"
    if not index_file.exists():
        return

    assets_dir = dist_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str) -> FileResponse:
        requested = dist_dir / full_path
        if requested.is_file():
            return FileResponse(requested)
        return FileResponse(index_file)


app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
