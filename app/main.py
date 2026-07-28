from pathlib import Path
import socket

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from .config import settings
from .services import ask_ollama, detect_once, get_weather, weather_summary
from .state import LabState


app = FastAPI(title=settings.name, description=settings.expansion)
state = LabState()
WEB = Path(__file__).parent / "web"


class ChatRequest(BaseModel):
    message: str


@app.get("/", response_class=FileResponse)
def dashboard() -> FileResponse:
    return FileResponse(WEB / "index.html")


@app.get("/manifest.webmanifest")
def manifest() -> FileResponse:
    return FileResponse(WEB / "manifest.webmanifest", media_type="application/manifest+json")


@app.get("/sw.js")
def service_worker() -> FileResponse:
    return FileResponse(WEB / "sw.js", media_type="application/javascript")


@app.get("/workflow.md")
def workflow_doc() -> FileResponse:
    return FileResponse(WEB / "workflow.md", media_type="text/markdown")


@app.get("/johns_todo.md")
def johns_todo_doc() -> FileResponse:
    return FileResponse(WEB / "johns_todo.md", media_type="text/markdown")


@app.get("/backup_inventory.md")
def backup_inventory_doc() -> FileResponse:
    return FileResponse(WEB.parent.parent / "D_DRIVE_BACKUP_INVENTORY.md", media_type="text/markdown")


@app.get("/icon.svg")
def icon() -> FileResponse:
    return FileResponse(WEB / "icon.svg", media_type="image/svg+xml")


@app.get("/api/status")
def status() -> dict:
    return {"name": settings.name, "expansion": settings.expansion, **state.snapshot()}


@app.get("/api/weather")
async def weather(force_refresh: bool = False) -> dict:
    return await get_weather(force_refresh=force_refresh)


@app.get("/api/network")
def network(request: Request) -> dict:
    hostname = socket.gethostname()
    try:
        addresses = sorted({address[4][0] for address in socket.getaddrinfo(hostname, None)})
    except socket.gaierror:
        addresses = []
    return {
        "hostname": hostname,
        "addresses": addresses,
        "server_host": request.url.hostname,
        "server_port": request.url.port or settings.port,
        "client_host": request.client.host if request.client else None,
        "local_only": True,
    }


@app.post("/api/detect")
def detect() -> dict:
    return {"message": detect_once(state), **state.snapshot()}


@app.post("/api/chat")
async def chat(request: ChatRequest) -> dict:
    message = request.message.strip()
    if not message:
        return JSONResponse({"error": "message is required"}, status_code=400)
    if message in {"/watch-room", "watch the room"}:
        state.watch_mode = True
        state.add_event("watch mode enabled")
        answer = "Watch mode enabled. I will track changes in the scene."
    elif message in {"/stop-watch", "stop watching"}:
        state.watch_mode = False
        state.add_event("watch mode disabled")
        answer = "Watch mode disabled."
    elif message in {"/status", "/what-do-you-see", "what do you see?"}:
        scene = state.snapshot()
        labels = [item["label"] for item in scene["current_objects"]]
        answer = f"I see {', '.join(labels) if labels else 'no detected objects'}; watch mode is {scene['watch_mode']}."
    elif message in {"/weather", "what is the weather?", "what's the weather?"}:
        answer = weather_summary(await get_weather())
    elif message == "/help":
        answer = "Try /status, /weather, /what-do-you-see, /watch-room, /stop-watch, or ask a question."
    else:
        answer = await ask_ollama(message, state.snapshot())
    return {"answer": answer, **state.snapshot()}

