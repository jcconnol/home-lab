from pathlib import Path
import asyncio
import socket
import time
import base64
import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

from .config import settings
from .services import (
    ask_ollama,
    ask_ollama_stream,
    detect_once,
    get_smart_switch,
    get_weather,
    toggle_smart_switch,
    weather_summary,
)
from .state import LabState


app = FastAPI(title=settings.name, description=settings.expansion)
state = LabState()
WEB = Path(__file__).parent / "web"
CERT_DIR = Path(__file__).parent.parent / ".certs"


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None
    job_id: str | None = None


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
    humor: str | None = None
    formality: str | None = None
    response_length: str | None = None
    proactive_comments: str | None = None
    confirm_sensitive_actions: bool | None = None


class LoginRequest(BaseModel):
    username: str
    password: str
    remember_me: bool = False


class SignupRequest(BaseModel):
    username: str
    password: str


class ImageGenerateRequest(BaseModel):
    prompt: str
    negative_prompt: str = "blurry, low quality, distorted, text, watermark"


class ImageSaveRequest(BaseModel):
    image_base64: str
    prompt: str = ""


IMAGE_DIR = Path(__file__).parent / "generated_images"
SESSION_COOKIE = "grace_session"
SESSION_DAYS = 30
SESSION_MAX_DAYS = 90
chat_jobs: dict[str, dict] = {}
chat_tasks: set[asyncio.Task] = set()


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


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _current_user(request: Request, *, touch: bool = True) -> dict | None:
    token = request.cookies.get(SESSION_COOKIE) or request.cookies.get("grace_admin_session")
    if not token:
        return None
    now = datetime.now(timezone.utc)
    token_hash = _token_hash(token)
    session = next((item for item in state.sessions if hmac.compare_digest(item.get("token_hash", ""), token_hash)), None)
    if not session:
        return None
    try:
        expires_at = datetime.fromisoformat(session["expires_at"])
        absolute_expires_at = datetime.fromisoformat(session["absolute_expires_at"])
    except (KeyError, ValueError, TypeError):
        state.sessions.remove(session); state._save(); return None
    if now >= expires_at or now >= absolute_expires_at:
        state.sessions.remove(session); state._save(); return None
    if touch:
        session["last_used_at"] = now.isoformat()
        if session.get("persistent"):
            session["expires_at"] = min(now + timedelta(days=SESSION_DAYS), absolute_expires_at).isoformat()
        state._save()
    return {key: session[key] for key in ("id", "username", "role")}


def require_admin(request: Request) -> dict:
    user = _current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Admin login required.")
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Administrator access required.")
    return user


def require_user(request: Request) -> dict:
    user = _current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required.")
    return user


class PreferenceUpdate(BaseModel):
    key: str
    value: str


@app.get("/", response_class=FileResponse)
def dashboard() -> FileResponse:
    return FileResponse(WEB / "index.html", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})


@app.get("/certificate", response_class=HTMLResponse)
def certificate_setup(request: Request) -> HTMLResponse:
    host = request.url.hostname or "10.0.0.5"
    secure_url = f"https://{host}:8443"
    certificate_ready = (CERT_DIR / "grace-ca.crt").is_file()
    download = '<a class="primary" href="/certificate/download" download>Download G.R.A.C.E. certificate</a>' if certificate_ready else '<p class="notice">The certificate has not been generated yet. Run <code>.\\start-https.ps1</code> on the server, then refresh this page.</p>'
    return HTMLResponse(f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="theme-color" content="#060a12"><title>G.R.A.C.E. Certificate Setup</title>
<style>:root{{color-scheme:dark;--bg:#060a12;--card:#0d1827;--ink:#eef7ff;--muted:#93a7bb;--cyan:#55e8ff;--line:rgba(85,232,255,.25)}}*{{box-sizing:border-box}}body{{margin:0;min-height:100dvh;padding:24px 16px;overflow-x:hidden;background:radial-gradient(circle at 90% 0,rgba(155,140,255,.16),transparent 28rem),var(--bg);color:var(--ink);font:16px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}}main{{width:100%;max-width:560px;min-width:0;margin:auto}}.brand{{display:flex;align-items:center;gap:12px;margin:12px 0 28px;font-weight:800;letter-spacing:.14em}}.core{{width:42px;height:42px;flex:0 0 42px;border:2px solid var(--cyan);border-radius:50%;box-shadow:0 0 20px rgba(85,232,255,.4)}}.card{{min-width:0;padding:20px;border:1px solid var(--line);border-radius:20px;background:linear-gradient(145deg,rgba(17,31,49,.95),rgba(8,14,24,.97));margin:14px 0}}h1{{font-size:1.7rem;line-height:1.15}}h2{{font-size:1.05rem;margin-top:0}}p,li,small,a{{overflow-wrap:anywhere}}p,li{{color:var(--muted)}}ol{{padding-left:1.4rem}}li{{margin:.65rem 0}}.primary{{display:block;width:100%;padding:14px;border-radius:14px;background:linear-gradient(135deg,#1ca5bf,#4768cf);color:white;text-align:center;text-decoration:none;font-weight:750;margin:18px 0}}code{{overflow-wrap:anywhere;color:var(--cyan)}}.notice{{padding:12px;border-radius:12px;background:rgba(255,109,115,.1)}}small{{color:var(--muted)}}</style></head>
<body><main><div class="brand"><span class="core"></span>G.R.A.C.E.</div><h1>Secure phone setup</h1><p>Install this private certificate authority so your phone can trust G.R.A.C.E. over your local Wi-Fi. This enables browser microphone access.</p><div class="card"><h2>1. Download the public certificate</h2>{download}<small>Only the public certificate is downloaded. The private signing key stays on the G.R.A.C.E. server.</small></div><div class="card"><h2>2. Install and trust it</h2><p><strong>iPhone / iPad</strong></p><ol><li>Open the downloaded certificate and allow the profile download.</li><li>Open Settings → General → VPN &amp; Device Management and install the G.R.A.C.E. profile.</li><li>Open Settings → General → About → Certificate Trust Settings and enable full trust for G.R.A.C.E. Local CA.</li></ol><p><strong>Android</strong></p><ol><li>Open Settings and search for <em>Install a certificate</em>.</li><li>Choose CA certificate, select the downloaded file, and confirm the security warning.</li><li>If your browser still refuses it, close and reopen the browser.</li></ol></div><div class="card"><h2>3. Open the secure app</h2><p><a class="primary" href="{secure_url}">{secure_url}</a></p><small>Remain on the same private Wi-Fi network. Never install this certificate on a device you do not control.</small></div></main></body></html>""")


@app.get("/certificate/download")
def certificate_download() -> FileResponse:
    certificate = CERT_DIR / "grace-ca.crt"
    if not certificate.is_file():
        raise HTTPException(status_code=404, detail="Certificate has not been generated. Run start-https.ps1 first.")
    return FileResponse(certificate, media_type="application/x-x509-ca-cert", filename="grace-local-ca.crt")


@app.get("/manifest.webmanifest")
def manifest() -> FileResponse:
    return FileResponse(WEB / "manifest.webmanifest", media_type="application/manifest+json", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})


@app.get("/sw.js")
def service_worker() -> FileResponse:
    return FileResponse(WEB / "sw.js", media_type="application/javascript", headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Service-Worker-Allowed": "/"})


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


@app.get("/icon-{size}.png")
def install_icon(size: int) -> FileResponse:
    if size not in {192, 512}:
        raise HTTPException(status_code=404, detail="Icon size not found.")
    return FileResponse(WEB / f"icon-{size}.png", media_type="image/png")


@app.get("/api/status")
def status(request: Request) -> dict:
    require_user(request)
    return {"name": settings.name, "expansion": settings.expansion, **state.snapshot()}


@app.post("/api/auth/login")
def login(credentials: LoginRequest, request: Request) -> JSONResponse:
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
    now = datetime.now(timezone.utc)
    duration = timedelta(days=SESSION_DAYS if credentials.remember_me else 1)
    state.sessions.append({**user, "session_id": secrets.token_urlsafe(12), "token_hash": _token_hash(token), "created_at": now.isoformat(), "last_used_at": now.isoformat(), "expires_at": (now + duration).isoformat(), "absolute_expires_at": (now + timedelta(days=SESSION_MAX_DAYS)).isoformat(), "persistent": credentials.remember_me})
    state._save()
    response = JSONResponse({"authenticated": True, **user})
    cookie_options = {"httponly": True, "samesite": "lax", "secure": request.url.scheme == "https", "path": "/"}
    if credentials.remember_me:
        cookie_options["max_age"] = SESSION_DAYS * 86400
    response.set_cookie(SESSION_COOKIE, token, **cookie_options)
    return response


@app.post("/api/auth/logout")
def logout(request: Request) -> JSONResponse:
    token = request.cookies.get(SESSION_COOKIE) or request.cookies.get("grace_admin_session")
    if token:
        token_hash = _token_hash(token)
        state.sessions = [item for item in state.sessions if not hmac.compare_digest(item.get("token_hash", ""), token_hash)]
        state._save()
    response = JSONResponse({"authenticated": False})
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie("grace_admin_session", path="/")
    return response


@app.get("/api/auth/me")
def auth_me(request: Request) -> dict:
    user = _current_user(request)
    return {"authenticated": bool(user), **(user or {})}


@app.get("/api/auth/sessions")
def sessions(request: Request) -> dict:
    user = require_user(request)
    current_hash = _token_hash(request.cookies.get(SESSION_COOKIE, ""))
    items = [{key: item.get(key) for key in ("session_id", "created_at", "last_used_at", "expires_at", "persistent")} | {"current": hmac.compare_digest(item.get("token_hash", ""), current_hash)} for item in state.sessions if item.get("id") == user["id"]]
    return {"sessions": items}


@app.delete("/api/auth/sessions/{session_id}")
def revoke_session(session_id: str, request: Request) -> dict:
    user = require_user(request)
    before = len(state.sessions)
    state.sessions = [item for item in state.sessions if not (item.get("id") == user["id"] and hmac.compare_digest(item.get("session_id", ""), session_id))]
    state._save()
    return {"deleted": len(state.sessions) != before}


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
async def weather(request: Request, force_refresh: bool = False) -> dict:
    require_user(request)
    return await get_weather(force_refresh=force_refresh)


@app.get("/api/devices/smart-switch")
async def smart_switch(request: Request) -> dict:
    require_user(request)
    return await get_smart_switch()


@app.post("/api/devices/smart-switch/toggle")
async def smart_switch_toggle(request: Request) -> dict:
    require_user(request)
    return await toggle_smart_switch()


@app.get("/api/network")
def network(request: Request) -> dict:
    require_user(request)
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
async def network_scan(request: Request) -> dict:
    require_user(request)
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
def network_telemetry(request: Request) -> dict:
    require_user(request)
    return {"history": list(state.network_telemetry)}


@app.get("/api/music")
def music(request: Request) -> dict:
    require_user(request)
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
def music_command(command: MusicCommand, request: Request) -> dict:
    require_user(request)
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
def memories(request: Request) -> dict:
    require_user(request)
    return {"memories": list(state.memories), "preferences": dict(state.preferences)}


@app.post("/api/memory")
def add_memory(memory: MemoryRequest, request: Request) -> dict:
    require_user(request)
    if not memory.content.strip():
        return JSONResponse({"error": "content is required"}, status_code=400)
    return state.add_memory(memory.content.strip(), memory.category.strip() or "note")


@app.delete("/api/memory/{memory_id}")
def delete_memory(memory_id: str, request: Request) -> dict:
    require_user(request)
    return {"deleted": state.remove_memory(memory_id)}


@app.put("/api/memory/preferences")
def update_preference(preference: PreferenceUpdate, request: Request) -> dict:
    require_user(request)
    if not preference.key.strip():
        return JSONResponse({"error": "key is required"}, status_code=400)
    state.preferences[preference.key.strip()] = preference.value.strip(); state._save()
    return {"preferences": dict(state.preferences)}


@app.get("/api/memory/export")
def export_memory(request: Request) -> JSONResponse:
    require_user(request)
    return JSONResponse({"memories": state.memories, "preferences": state.preferences})


@app.get("/api/briefings")
def briefings(request: Request) -> dict:
    require_user(request)
    return {"schedule": dict(state.briefing_schedule), "history": list(state.briefings)}


@app.put("/api/briefings/schedule")
def update_briefing_schedule(schedule: BriefingSchedule, request: Request) -> dict:
    require_user(request)
    state.briefing_schedule = schedule.model_dump()
    state._save()
    return state.briefing_schedule


@app.post("/api/briefings/{period}")
async def create_briefing(period: str, request: Request) -> dict:
    require_user(request)
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
    allowed = {"humor": {"off", "subtle", "balanced", "playful"}, "formality": {"casual", "polished", "formal"}, "response_length": {"brief", "standard", "detailed"}, "proactive_comments": {"never", "important", "occasionally"}}
    if any(key in changes and changes[key] not in values for key, values in allowed.items()):
        raise HTTPException(status_code=400, detail="Invalid personality setting.")
    state.grace_settings.update(changes); state._save()
    return dict(state.grace_settings)


@app.post("/api/detect")
def detect(request: Request) -> dict:
    require_user(request)
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


async def _run_chat_job(job: dict, message: str, user: dict) -> None:
    try:
        lower = message.lower()
        if lower.startswith(("remember that ", "save a note: ", "save note: ")):
            prefix = next(prefix for prefix in ("remember that ", "save a note: ", "save note: ") if lower.startswith(prefix))
            content = message[len(prefix):].strip()
            job["answer"] = "Tell me what you want remembered, and I will save it." if not content else f"Saved that note: {state.add_memory(content, 'chat note')['content']}"
        else:
            scene = state.snapshot()
            scene["memories"] = list(state.memories)
            async for part in ask_ollama_stream(message, scene):
                job["answer"] += part
        if not job["answer"]:
            job["answer"] = "No response."
        job["status"] = "complete"
        state.add_conversation_message(user["id"], user["username"], job["conversation_id"], "assistant", job["answer"])
    except Exception:
        job["status"] = "error"
        job["error"] = "G.R.A.C.E. could not complete that response."


@app.post("/api/chat/jobs", status_code=202)
async def create_chat_job(request: ChatRequest, http_request: Request) -> dict:
    user = require_user(http_request)
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="message is required")
    conversation_id = request.conversation_id or secrets.token_urlsafe(12)
    job_id = request.job_id or secrets.token_urlsafe(18)
    existing = chat_jobs.get(job_id)
    if existing:
        if existing["user_id"] != user["id"]:
            raise HTTPException(status_code=409, detail="Chat job ID is already in use.")
        return {"job_id": job_id, "conversation_id": existing["conversation_id"], "status": existing["status"]}
    job = {
        "id": job_id,
        "user_id": user["id"],
        "conversation_id": conversation_id,
        "status": "running",
        "answer": "",
        "error": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    chat_jobs[job_id] = job
    state.add_conversation_message(user["id"], user["username"], conversation_id, "user", message)
    task = asyncio.create_task(_run_chat_job(job, message, user))
    chat_tasks.add(task)
    task.add_done_callback(chat_tasks.discard)
    return {"job_id": job_id, "conversation_id": conversation_id, "status": job["status"]}


@app.get("/api/chat/jobs/{job_id}")
def chat_job(job_id: str, request: Request) -> dict:
    user = require_user(request)
    job = chat_jobs.get(job_id)
    if not job or job["user_id"] != user["id"]:
        raise HTTPException(status_code=404, detail="Chat response not found.")
    return {key: job[key] for key in ("id", "conversation_id", "status", "answer", "error")}


@app.get("/api/conversations")
def conversations(request: Request) -> dict:
    user = require_user(request)
    if user["role"] == "admin":
        return {"conversations": list(state.conversations)}
    return {"conversations": [item for item in state.conversations if item["user_id"] == user["id"]]}

