from pathlib import Path
import asyncio
import socket
import time
import base64
import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

from .config import settings
from .services import ask_ollama, ask_ollama_stream, detect_once, get_weather, weather_summary
from .state import LabState


app = FastAPI(title=settings.name, description=settings.expansion)
state = LabState()
WEB = Path(__file__).parent / "web"


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


class MusicCommand(BaseModel):
    action: str
    track: str | None = None
    volume: int | None = None


class MemoryRequest(BaseModel):
    content: str
    category: str = "note"


class BriefingSchedule(BaseModel):
    morning: str = "07:00"
    afternoon: str = "13:00"
    enabled: bool = False


class SettingsUpdate(BaseModel):
    personality: str | None = None
    voice: str | None = None
    confirm_sensitive_actions: bool | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


class SignupRequest(BaseModel):
    username: str
    password: str


class ImageGenerateRequest(BaseModel):
    prompt: str
    negative_prompt: str = "blurry, low quality, distorted, text, watermark"


class ImageSaveRequest(BaseModel):
    image_base64: str
    prompt: str = ""


SESSIONS: dict[str, dict] = {}
IMAGE_DIR = Path(__file__).parent / "generated_images"


def _hash_password(password: str) -> str:
    salt = secrets.token_urlsafe(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200000)
    return f"pbkdf2_sha256$200000${salt}${base64.urlsafe_b64encode(digest).decode()}"


def _password_matches(password: str) -> bool:
    try:
        algorithm, rounds, salt, expected = settings.admin_password_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        derived = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(rounds))
        return hmac.compare_digest(base64.urlsafe_b64encode(derived).decode(), expected)
    except (ValueError, TypeError):
        return False


def require_admin(request: Request) -> None:
    token = request.cookies.get("grace_admin_session")
    if not token or SESSIONS.get(token, {}).get("role") != "admin":
        raise HTTPException(status_code=401, detail="Admin login required.")


def require_user(request: Request) -> dict:
    token = request.cookies.get("grace_admin_session")
    user = SESSIONS.get(token or "")
    if not user:
        raise HTTPException(status_code=401, detail="Login required.")
    return user


class PreferenceUpdate(BaseModel):
    key: str
    value: str


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


@app.post("/api/auth/login")
def login(credentials: LoginRequest) -> JSONResponse:
    user: dict | None = None
    if settings.admin_password_hash and hmac.compare_digest(credentials.username, settings.admin_username) and _password_matches(credentials.password):
        user = {"id": "admin", "username": settings.admin_username, "role": "admin"}
    else:
        account = next((item for item in state.users if item["username"].lower() == credentials.username.lower()), None)
        if account and _password_matches_hash(credentials.password, account["password_hash"]):
            user = {"id": account["id"], "username": account["username"], "role": "user"}
    if not user:
        return JSONResponse({"error": "Invalid admin credentials."}, status_code=401)
    token = secrets.token_urlsafe(32)
    SESSIONS[token] = user
    response = JSONResponse({"authenticated": True, **user})
    response.set_cookie("grace_admin_session", token, httponly=True, samesite="lax", max_age=86400)
    return response


@app.post("/api/auth/logout")
def logout(request: Request) -> JSONResponse:
    token = request.cookies.get("grace_admin_session")
    if token:
        SESSIONS.pop(token, None)
    response = JSONResponse({"authenticated": False})
    response.delete_cookie("grace_admin_session")
    return response


@app.get("/api/auth/me")
def auth_me(request: Request) -> dict:
    token = request.cookies.get("grace_admin_session")
    user = SESSIONS.get(token or "")
    return {"authenticated": bool(user), **(user or {})}


def _password_matches_hash(password: str, encoded: str) -> bool:
    try:
        algorithm, rounds, salt, expected = encoded.split("$", 3)
        derived = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(rounds))
        return algorithm == "pbkdf2_sha256" and hmac.compare_digest(base64.urlsafe_b64encode(derived).decode(), expected)
    except (ValueError, TypeError):
        return False


@app.post("/api/auth/signup")
def signup(credentials: SignupRequest) -> JSONResponse:
    username = credentials.username.strip()
    if len(username) < 3 or len(credentials.password) < 8:
        return JSONResponse({"error": "Use a username of at least 3 characters and a password of at least 8 characters."}, status_code=400)
    if username.lower() == settings.admin_username.lower() or any(item["username"].lower() == username.lower() for item in state.users):
        return JSONResponse({"error": "That username is already in use."}, status_code=409)
    account = {"id": secrets.token_urlsafe(12), "username": username, "password_hash": _hash_password(credentials.password), "created_at": datetime.now(timezone.utc).isoformat()}
    state.add_user(account)
    return JSONResponse({"created": True, "username": username}, status_code=201)


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


NETWORK_SCAN_PORTS = (22, 53, 80, 443, 445, 3389, 8000, 8080, 11434)


async def _probe_host(host: str, semaphore: asyncio.Semaphore) -> dict | None:
    async with semaphore:
        started = time.perf_counter()
        ping_task = asyncio.create_task(_ping_host(host))
        ports_task = asyncio.create_task(_probe_ports(host))
        reachable_by_ping, open_ports = await asyncio.gather(ping_task, ports_task)
        if not reachable_by_ping and not open_ports:
            return None
        method = "ping+tcp" if reachable_by_ping and open_ports else "ping" if reachable_by_ping else "tcp"
        try:
            hostname = await asyncio.to_thread(socket.gethostbyaddr, host)
            name = hostname[0]
        except (socket.herror, socket.gaierror, OSError):
            name = None
        return {
            "address": host,
            "hostname": name,
            "open_ports": open_ports,
            "reachable_by_ping": reachable_by_ping,
            "method": method,
            "latency_ms": round((time.perf_counter() - started) * 1000),
        }


async def _ping_host(host: str) -> bool:
    try:
        process = await asyncio.create_subprocess_exec(
            "ping.exe", "-n", "1", "-w", "250", host,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(process.wait(), timeout=1)
        return process.returncode == 0
    except (OSError, asyncio.TimeoutError):
        return False


async def _probe_ports(host: str) -> list[int]:
    open_ports: list[int] = []
    for port in NETWORK_SCAN_PORTS:
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=0.25
            )
            writer.close()
            await writer.wait_closed()
            open_ports.append(port)
        except (ConnectionError, OSError, asyncio.TimeoutError):
            continue
    return open_ports


async def _arp_table() -> dict[str, str]:
    try:
        process = await asyncio.create_subprocess_exec(
            "arp.exe", "-a", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL
        )
        output, _ = await asyncio.wait_for(process.communicate(), timeout=5)
    except (OSError, asyncio.TimeoutError):
        return {}
    table: dict[str, str] = {}
    for line in output.decode(errors="ignore").splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0].startswith("10.0.0.") and parts[0].count(".") == 3:
            table[parts[0]] = parts[1]
    return table


@app.get("/api/network/scan")
async def network_scan() -> dict:
    """Discover responsive hosts on the user's fixed 10.0.0.x private subnet."""
    semaphore = asyncio.Semaphore(32)
    hosts = [f"10.0.0.{number}" for number in range(1, 226)]
    results = await asyncio.gather(*(_probe_host(host, semaphore) for host in hosts))
    arp = await _arp_table()
    discovered = {result["address"]: result for result in results if result}
    for address, mac_address in arp.items():
        discovered.setdefault(address, {
            "address": address,
            "hostname": None,
            "open_ports": [],
            "reachable_by_ping": False,
            "method": "arp",
            "latency_ms": None,
        })
    machines = sorted(discovered.values(), key=lambda item: tuple(int(part) for part in item["address"].split(".")))
    for machine in machines:
        machine["mac_address"] = arp.get(machine["address"])
    payload = {
        "subnet": "10.0.0.0/24",
        "scanned_hosts": 225,
        "ports": list(NETWORK_SCAN_PORTS),
        "machines": machines,
    }
    state.record_network({"timestamp": datetime.now(timezone.utc).isoformat(), "machine_count": len(machines), "subnet": payload["subnet"]})
    return payload


@app.get("/api/network/telemetry")
def network_telemetry() -> dict:
    return {"history": list(state.network_telemetry)}


@app.get("/api/music")
def music() -> dict:
    return {"available": False, "provider": "local-command-adapter", "message": "Playback commands are ready; configure a speaker provider to produce audio.", **state.music}


async def _generate_image(prompt: str, negative_prompt: str) -> dict:
    from .image_generation import generate_image as run_image_generation

    content = await asyncio.to_thread(run_image_generation, prompt, negative_prompt)
    return {"image_base64": base64.b64encode(content).decode("ascii"), "mime_type": "image/png", "prompt": prompt}


@app.get("/api/images/saved")
def saved_images(request: Request) -> dict:
    require_user(request)
    return {"images": list(reversed(state.saved_images))}


@app.post("/api/images/generate")
async def generate_image(request: ImageGenerateRequest, http_request: Request) -> dict:
    require_user(http_request)
    if not request.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt is required.")
    try:
        return await _generate_image(request.prompt.strip(), request.negative_prompt.strip())
    except (FileNotFoundError, ImportError, OSError, RuntimeError, ValueError, TimeoutError) as error:
        raise HTTPException(status_code=502, detail=f"Image generation unavailable: {error}") from error


@app.post("/api/images/save")
def save_image(request: ImageSaveRequest, http_request: Request) -> dict:
    require_user(http_request)
    try:
        raw = base64.b64decode(request.image_base64, validate=True)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid image data.")
    if len(raw) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image is too large.")
    IMAGE_DIR.mkdir(exist_ok=True)
    image_id = uuid.uuid4().hex
    filename = f"{image_id}.png"
    (IMAGE_DIR / filename).write_bytes(raw)
    item = {"id": image_id, "filename": filename, "prompt": request.prompt, "created_at": datetime.now(timezone.utc).isoformat()}
    return {"image": state.add_saved_image(item)}


@app.get("/api/images/saved/{filename}")
def saved_image_file(filename: str, request: Request) -> FileResponse:
    require_user(request)
    if Path(filename).name != filename or not filename.endswith(".png"):
        raise HTTPException(status_code=404, detail="Image not found.")
    path = IMAGE_DIR / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Image not found.")
    return FileResponse(path, media_type="image/png")


@app.delete("/api/images/saved/{image_id}")
def delete_saved_image(image_id: str, request: Request) -> dict:
    require_user(request)
    item = next((entry for entry in state.saved_images if entry["id"] == image_id), None)
    if not item or not state.remove_saved_image(image_id):
        raise HTTPException(status_code=404, detail="Image not found.")
    path = IMAGE_DIR / item["filename"]
    if path.is_file():
        path.unlink()
    return {"deleted": True}


@app.post("/api/music/command")
def music_command(command: MusicCommand) -> dict:
    action = command.action.lower().strip()
    if action not in {"play", "pause", "stop", "next", "previous", "volume", "shuffle", "select"}:
        return JSONResponse({"error": "Unsupported music action."}, status_code=400)
    changes: dict[str, object] = {}
    queue = state.music.get("queue", [])
    if action == "select" and command.track in queue:
        changes = {"status": "playing", "track": command.track, "index": queue.index(command.track)}
    elif action == "play": changes = {"status": "playing", "track": command.track or state.music.get("track") or (queue[0] if queue else "Local playback queue")}
    elif action in {"pause", "stop"}: changes = {"status": "paused" if action == "pause" else "stopped"}
    elif action in {"next", "previous"} and queue:
        step = 1 if action == "next" else -1
        index = (int(state.music.get("index", 0)) + step) % len(queue)
        changes = {"status": "playing", "track": queue[index], "index": index}
    elif action == "shuffle": changes = {"shuffle": bool(command.track == "on")}
    elif command.volume is not None: changes = {"volume": max(0, min(100, command.volume))}
    return {"available": False, "message": "Command recorded locally. Add a speaker adapter when ready.", **state.update_music(**changes)}


@app.get("/api/memory")
def memories() -> dict:
    return {"memories": list(state.memories), "preferences": dict(state.preferences)}


@app.post("/api/memory")
def add_memory(memory: MemoryRequest) -> dict:
    if not memory.content.strip():
        return JSONResponse({"error": "content is required"}, status_code=400)
    return state.add_memory(memory.content.strip(), memory.category.strip() or "note")


@app.delete("/api/memory/{memory_id}")
def delete_memory(memory_id: str) -> dict:
    return {"deleted": state.remove_memory(memory_id)}


@app.put("/api/memory/preferences")
def update_preference(preference: PreferenceUpdate) -> dict:
    if not preference.key.strip():
        return JSONResponse({"error": "key is required"}, status_code=400)
    state.preferences[preference.key.strip()] = preference.value.strip(); state._save()
    return {"preferences": dict(state.preferences)}


@app.get("/api/memory/export")
def export_memory() -> JSONResponse:
    return JSONResponse({"memories": state.memories, "preferences": state.preferences})


@app.get("/api/briefings")
def briefings() -> dict:
    return {"schedule": dict(state.briefing_schedule), "history": list(state.briefings)}


@app.put("/api/briefings/schedule")
def update_briefing_schedule(schedule: BriefingSchedule) -> dict:
    state.briefing_schedule = schedule.model_dump()
    state._save()
    return state.briefing_schedule


@app.post("/api/briefings/{period}")
async def create_briefing(period: str) -> dict:
    if period not in {"morning", "afternoon"}:
        return JSONResponse({"error": "period must be morning or afternoon"}, status_code=400)
    weather_data = await get_weather()
    scene = state.snapshot()
    text = f"{period.title()} briefing: {len(scene['current_objects'])} scene object(s), {scene['memory_count']} saved memory item(s). "
    text += weather_summary(weather_data) if weather_data.get("available") else "Weather is currently unavailable."
    item = {"period": period, "text": text, "created_at": datetime.now(timezone.utc).isoformat()}
    state.add_briefing(item)
    return item


@app.get("/api/settings")
def grace_settings(request: Request) -> dict:
    require_admin(request)
    return dict(state.grace_settings)


@app.put("/api/settings")
def update_grace_settings(update: SettingsUpdate, request: Request) -> dict:
    require_admin(request)
    changes = {key: value for key, value in update.model_dump().items() if value is not None}
    state.grace_settings.update(changes); state._save()
    return dict(state.grace_settings)


@app.post("/api/detect")
def detect() -> dict:
    return {"message": detect_once(state), **state.snapshot()}


@app.post("/api/chat")
async def chat(request: ChatRequest, http_request: Request) -> dict:
    user = require_user(http_request)
    message = request.message.strip()
    if not message:
        return JSONResponse({"error": "message is required"}, status_code=400)
    conversation_id = request.conversation_id or secrets.token_urlsafe(12)
    state.add_conversation_message(user["id"], user["username"], conversation_id, "user", message)
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
        answer = "Try /status, /weather, /what-do-you-see, /watch-room, /stop-watch, or say 'remember that ...' to save a note."
    elif message.lower().startswith(("remember that ", "save a note: ", "save note: ")):
        prefix = next(prefix for prefix in ("remember that ", "save a note: ", "save note: ") if message.lower().startswith(prefix))
        content = message[len(prefix):].strip()
        if not content:
            answer = "Tell me what you want remembered, and I will save it."
        else:
            saved = state.add_memory(content, "chat note")
            answer = f"Saved that note: {saved['content']}"
    elif any(term in message.lower() for term in ("what note", "saved note", "remembered")):
        memories = state.memories
        answer = "I have no saved notes." if not memories else "Saved notes:\n" + "\n".join(f"- {item['content']}" for item in memories)
    else:
        scene = state.snapshot()
        scene["memories"] = list(state.memories)
        answer = await ask_ollama(message, scene)
    state.add_conversation_message(user["id"], user["username"], conversation_id, "assistant", answer)
    return {"answer": answer, "conversation_id": conversation_id, **state.snapshot()}


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest, http_request: Request) -> StreamingResponse:
    user = require_user(http_request)
    message = request.message.strip()
    if not message:
        return StreamingResponse(iter(("Message is required.",)), media_type="text/plain")
    conversation_id = request.conversation_id or secrets.token_urlsafe(12)
    state.add_conversation_message(user["id"], user["username"], conversation_id, "user", message)
    lower = message.lower()
    if lower.startswith(("remember that ", "save a note: ", "save note: ")):
        prefix = next(prefix for prefix in ("remember that ", "save a note: ", "save note: ") if lower.startswith(prefix))
        content = message[len(prefix):].strip()
        answer = "Tell me what you want remembered, and I will save it." if not content else f"Saved that note: {state.add_memory(content, 'chat note')['content']}"
        state.add_conversation_message(user["id"], user["username"], conversation_id, "assistant", answer)
        return StreamingResponse(iter((answer,)), media_type="text/plain", headers={"X-Conversation-Id": conversation_id})
    scene = state.snapshot()
    scene["memories"] = list(state.memories)
    async def generate():
        parts: list[str] = []
        async for part in ask_ollama_stream(message, scene):
            parts.append(part)
            yield part
        state.add_conversation_message(user["id"], user["username"], conversation_id, "assistant", "".join(parts))
    return StreamingResponse(generate(), media_type="text/plain; charset=utf-8", headers={"X-Conversation-Id": conversation_id})


@app.get("/api/conversations")
def conversations(request: Request) -> dict:
    user = require_user(request)
    if user["role"] == "admin":
        return {"conversations": list(state.conversations)}
    return {"conversations": [item for item in state.conversations if item["user_id"] == user["id"]]}

