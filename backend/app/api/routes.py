import json
import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field
from typing import Literal
from ..core.config import settings
from ..core.db import read_setting, write_setting
from ..services.ignore_list import get_ignored, update_ignored
from ..services.storage import activity_for, capture_details, cleanup, image_for, list_captures
from ..services.search import hybrid_search
from ..services.ai_chat import available_models, retrieve, stream_answer
from .. import state

router = APIRouter()


class SettingsUpdate(BaseModel):
    capture_interval_seconds: int | None = Field(default=None, ge=1, le=3600)
    ignored_processes: list[str] | None = None
    capture_enabled: bool | None = None


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    model: str | None = None
    date_from: str | None = None
    date_to: str | None = None


@router.get("/timeline")
def timeline(limit: int = 20, offset: int = 0, app: str | None = None, date_from: str | None = None, date_to: str | None = None):
    return list_captures(limit, offset, app, date_from, date_to)


@router.get("/timeline/activity")
def timeline_activity(date_from: str, date_to: str, utc_offset_minutes: int = 0):
    if not -840 <= utc_offset_minutes <= 840:
        raise HTTPException(400, "Invalid UTC offset")
    return {"hours": activity_for(date_from, date_to, utc_offset_minutes)}


@router.get("/screenshots/{capture_id}")
def screenshot(capture_id: int):
    data = image_for(capture_id)
    if data is None:
        raise HTTPException(404, "Screenshot not found")
    return Response(data, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@router.get("/screenshots/{capture_id}/details")
def screenshot_details(capture_id: int):
    details = capture_details(capture_id)
    if details is None:
        raise HTTPException(404, "Screenshot not found")
    return details


@router.get("/search")
def search_endpoint(q: str = "", app: str | None = None, date_from: str | None = None, date_to: str | None = None, limit: int = 50, mode: Literal["hybrid", "semantic", "text"] = "hybrid"):
    return hybrid_search(q, limit, app, date_from, date_to, vector_only=mode == "semantic", lexical_only=mode == "text")


@router.get("/chat/models")
async def chat_models():
    try:
        return {"models": await available_models()}
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(503, "Ollama is unavailable on this computer") from exc


@router.post("/chat")
async def chat(body: ChatRequest):
    try:
        models = await available_models()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(503, "Ollama is unavailable on this computer") from exc
    if not models:
        raise HTTPException(503, "No Ollama models are installed")
    model = body.model or (settings.ollama_model if settings.ollama_model in models else models[0])
    if model not in models:
        raise HTTPException(400, "Selected Ollama model is not installed")
    sources = retrieve(body.query, body.date_from, body.date_to)
    references = [{key: source[key] for key in ("id", "captured_at", "process_name", "window_title")}
                  for source in sources]

    async def events():
        yield f"event: sources\ndata: {json.dumps({'source_screenshots': references})}\n\n"
        try:
            async for token in stream_answer(body.query, model, sources):
                yield f"event: token\ndata: {json.dumps(token)}\n\n"
            yield "event: done\ndata: {}\n\n"
        except (httpx.HTTPError, ValueError, json.JSONDecodeError) as exc:
            yield f"event: error\ndata: {json.dumps(str(exc))}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


def current_settings():
    return {
        "capture_interval_seconds": settings.capture_interval_seconds,
        "capture_enabled": state.worker.running,
        "ignored_processes": get_ignored(),
    }


@router.get("/settings")
def read_settings():
    return current_settings()


@router.post("/settings")
def write_settings(body: SettingsUpdate):
    if body.capture_interval_seconds is not None:
        settings.capture_interval_seconds = body.capture_interval_seconds
        write_setting("capture_interval_seconds", str(body.capture_interval_seconds))
    if body.ignored_processes is not None:
        update_ignored(body.ignored_processes)
    if body.capture_enabled is True:
        state.start_worker()
    elif body.capture_enabled is False:
        state.stop_worker()
    return current_settings()


@router.delete("/cleanup")
def cleanup_old(days: int = 30):
    if not 1 <= days <= 3650:
        raise HTTPException(400, "days must be between 1 and 3650")
    return {"deleted": cleanup(days)}


@router.get("/status")
def status():
    return {"online": True, "capture_enabled": state.worker.running, "local_only": True, "data_dir": str(settings.data_dir)}
