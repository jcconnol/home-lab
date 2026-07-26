from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from .config import settings
from .services import ask_ollama, detect_once
from .state import LabState


app = FastAPI(title=settings.name, description=settings.expansion)
state = LabState()
WEB = Path(__file__).parent / "web"


class ChatRequest(BaseModel):
    message: str


@app.get("/", response_class=FileResponse)
def dashboard() -> FileResponse:
    return FileResponse(WEB / "index.html")


@app.get("/api/status")
def status() -> dict:
    return {"name": settings.name, "expansion": settings.expansion, **state.snapshot()}


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
    elif message == "/help":
        answer = "Try /status, /what-do-you-see, /watch-room, /stop-watch, or ask a question."
    else:
        answer = await ask_ollama(message, state.snapshot())
    return {"answer": answer, **state.snapshot()}

