from contextlib import asynccontextmanager
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.routes import router as api_router
from .core.config import settings
from .core.db import initialize, read_setting
from .state import start_worker as start_capture_worker, stop_worker as stop_capture_worker
from .services.tray import RecallTray


@asynccontextmanager
async def lifespan(_: FastAPI):
    print("[+] App startup: Initializing Capture Worker...", flush=True)
    initialize()
    settings.capture_interval_seconds = int(read_setting("capture_interval_seconds", str(settings.capture_interval_seconds)))
    if read_setting("capture_enabled", "true") == "true":
        start_capture_worker()
    tray = RecallTray(asyncio.get_running_loop())
    try:
        tray.start()
        yield
    finally:
        tray.stop()
        stop_capture_worker(persist=False)


app = FastAPI(
    title="Local Recall API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def root():
    return {"status": "ok", "app": "Local Recall"}
