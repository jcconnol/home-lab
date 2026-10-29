"""Standalone, dependency-free garage dashboard server."""
import argparse
import copy
import hmac
import importlib.util
import json
import os
import platform
import random
import secrets
import shutil
import sqlite3
import threading
import time
from datetime import datetime, timezone
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parent


def module(folder):
    spec = importlib.util.spec_from_file_location(folder.replace("-", "_"), ROOT / folder / "run.py")
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def now():
    return datetime.now(timezone.utc).isoformat()


class Dashboard:
    def __init__(self, config, storage, config_dir=None, interval=30, tick_seconds=20):
        self.config = config
        self.storage = Path(storage)
        self.storage.mkdir(parents=True, exist_ok=True)
        self.config_dir = Path(config_dir or ROOT)
        self.interval = interval
        self.tick_seconds = tick_seconds
        self.started = time.monotonic()
        self.lock = threading.RLock()
        self.stop = threading.Event()
        self.rng = random.Random()
        self.ecology = module("terrarium")
        self.state_file = self.storage / "terrarium.json"
        self.terrarium = json.loads(self.state_file.read_text()) if self.state_file.exists() else {
            "tick": 0, "plants": 40, "next_id": 3, "paused": False,
            "creatures": [{"id": i, "parent": None, "age": 0, "energy": 10} for i in (1, 2)], "events": []}
        self.terrarium.setdefault("paused", False)
        self.data = {"health": {"status": "checking"}, "network": {"nodes": [], "edges": []},
                     "modules": {}, "checked_at": None, "events": []}
        self.events_file = self.storage / "events.json"
        self.events = json.loads(self.events_file.read_text()) if self.events_file.exists() else []
        self.missions_db = self.storage / "missions.sqlite"
        with sqlite3.connect(self.missions_db) as db:
            db.execute("CREATE TABLE IF NOT EXISTS missions (id INTEGER PRIMARY KEY, question TEXT, prediction TEXT, created_at TEXT)")
            db.execute("CREATE TABLE IF NOT EXISTS observations (id INTEGER PRIMARY KEY, mission_id INTEGER, outcome TEXT, observed_at TEXT)")

    def save(self, path, value):
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(value), encoding="utf-8")
        temporary.replace(path)

    def care(self, action):
        with self.lock:
            if action == "feed":
                self.terrarium["plants"] = min(100, self.terrarium["plants"] + 10)
            elif action == "pause":
                self.terrarium["paused"] = not self.terrarium["paused"]
            elif action == "step":
                self.ecology.advance(self.terrarium, self.rng)
            elif action == "introduce":
                self.terrarium["creatures"].append({"id": self.terrarium["next_id"], "parent": None, "age": 0, "energy": 10})
                self.terrarium["next_id"] += 1
            else:
                raise ValueError("Unknown care action")
            self.save(self.state_file, self.terrarium)
            return copy.deepcopy(self.terrarium)

    def read_input(self, name):
        path = self.config.get("inputs", {}).get(name)
        if not path:
            return None
        return json.loads((self.config_dir / path).read_text(encoding="utf-8"))

    def collect(self):
        grace_url = self.config.get("grace_url", "").strip()
        health = module("grace-health").check({"name": "GRACE", "url": grace_url}) if grace_url else {
            "name": "GRACE", "status": "not_configured"}
        network = module("network-radar").scan({"services": self.config.get("services", []),
                                                "relationships": self.config.get("relationships", [])})
        modules = {}
        tasks = {
            "observatory": ("anomaly_readings", lambda data: module("anomaly-observatory").detect(data)),
            "space": ("satellite_passes", lambda data: module("space-command").upcoming(data, datetime.now(timezone.utc))),
            "twin": ("apartment_layout", lambda data: module("apartment-twin").build_twin(data, self.read_input("apartment_states") or [], 3600)),
        }
        for name, (input_name, compute) in tasks.items():
            try:
                data = self.read_input(input_name)
                modules[name] = {"status": "not_configured"} if data is None else {"status": "loaded", "data": compute(data)}
            except (ValueError, OSError, KeyError, TypeError) as error:
                modules[name] = {"status": "error", "error": str(error)}
        try:
            imported = self.read_input("events") or []
            if not isinstance(imported, list):
                raise ValueError("events must be a JSON array")
            for event in imported:
                instant = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
                if instant.tzinfo is None:
                    raise ValueError("Event timestamps must include timezone")
        except (ValueError, OSError, KeyError, TypeError) as error:
            imported = []
            modules["timeline"] = {"status": "error", "error": str(error)}
        with self.lock:
            previous = {item["id"]: item["status"] for item in self.data["network"]["nodes"]}
            for item in network["nodes"]:
                if item["id"] in previous and previous[item["id"]] != item["status"]:
                    self.events.append({"timestamp": now(), "source": item["id"], "event": item["status"]})
            if self.data["checked_at"] and self.data["health"]["status"] != health["status"]:
                self.events.append({"timestamp": now(), "source": "grace", "event": health["status"]})
            self.events = self.events[-500:]
            self.save(self.events_file, self.events)
            events = sorted(self.events + imported, key=lambda event: datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00")))
            modules["detective"] = {"status": "loaded", "data": module("signal-detective").correlate(events[-100:], 60)[-50:]}
            self.data = {"health": health, "network": network, "modules": modules,
                         "checked_at": now(), "events": events[-500:]}

    def mission(self, data):
        with sqlite3.connect(self.missions_db) as db:
            if data.get("action") == "create":
                question, prediction = data.get("question"), data.get("prediction")
                if not all(isinstance(value, str) and 0 < len(value.strip()) <= 2000 for value in (question, prediction)):
                    raise ValueError("Question and prediction are required (up to 2000 characters)")
                db.execute("INSERT INTO missions(question,prediction,created_at) VALUES(?,?,?)", (question, prediction, now()))
            elif data.get("action") == "observe":
                outcome = data.get("outcome")
                if not isinstance(outcome, str) or not 0 < len(outcome.strip()) <= 2000:
                    raise ValueError("Outcome required (up to 2000 characters)")
                if not db.execute("SELECT id FROM missions WHERE id=?", (data.get("id"),)).fetchone():
                    raise ValueError("Mission not found")
                db.execute("INSERT INTO observations(mission_id,outcome,observed_at) VALUES(?,?,?)", (data["id"], outcome, now()))
            else:
                raise ValueError("Unknown mission action")

    def snapshot(self):
        with self.lock:
            result = copy.deepcopy(self.data)
            result["terrarium"] = copy.deepcopy(self.terrarium)
        with sqlite3.connect(self.missions_db) as db:
            db.row_factory = sqlite3.Row
            result["missions"] = [dict(row) for row in db.execute("SELECT * FROM missions ORDER BY id DESC")]
            for mission in result["missions"]:
                mission["observations"] = [dict(row) for row in db.execute("SELECT * FROM observations WHERE mission_id=? ORDER BY id", (mission["id"],))]
        usage = shutil.disk_usage(self.storage)
        result["host"] = {"name": platform.node(), "uptime_seconds": int(time.monotonic() - self.started),
                          "disk_free_gb": round(usage.free / 1024**3, 1), "system": platform.system()}
        result["server_time"] = now()
        result["refresh_seconds"] = self.interval
        return result

    def run(self):
        next_check = next_tick = 0
        while not self.stop.is_set():
            clock = time.monotonic()
            if clock >= next_check:
                try:
                    self.collect()
                except Exception as error:
                    with self.lock:
                        self.data["collection_error"] = str(error)
                next_check = time.monotonic() + self.interval
            if clock >= next_tick:
                with self.lock:
                    if next_tick and not self.terrarium["paused"]:
                        self.ecology.advance(self.terrarium, self.rng)
                    self.save(self.state_file, self.terrarium)
                next_tick = time.monotonic() + self.tick_seconds
            self.stop.wait(1)


def handler_factory(dashboard, password=""):
    session = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def send(self, code, payload, content_type="application/json", cookie=None):
            body = json.dumps(payload).encode() if content_type == "application/json" else payload
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; frame-ancestors 'none'")
            if cookie:
                self.send_header("Set-Cookie", cookie)
            self.end_headers()
            self.wfile.write(body)

        def authenticated(self):
            if not password:
                return True
            cookies = SimpleCookie()
            try:
                cookies.load(self.headers.get("Cookie", ""))
                value = cookies.get("garage_session")
                return bool(value and hmac.compare_digest(value.value, session))
            except Exception:
                return False

        def do_GET(self):
            path = urlsplit(self.path).path
            if path == "/api/status":
                if not self.authenticated():
                    return self.send(401, {"error": "Sign in required"})
                return self.send(200, dashboard.snapshot())
            files = {"/": ("index.html", "text/html; charset=utf-8"),
                     "/app.js": ("app.js", "text/javascript; charset=utf-8"),
                     "/style.css": ("style.css", "text/css; charset=utf-8")}
            if path not in files:
                return self.send(404, {"error": "Not found"})
            name, content_type = files[path]
            self.send(200, (ROOT / "web" / name).read_bytes(), content_type)

        def do_POST(self):
            origin = self.headers.get("Origin")
            if origin and urlsplit(origin).netloc != self.headers.get("Host"):
                return self.send(403, {"error": "Cross-origin writes are not allowed"})
            if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
                return self.send(415, {"error": "JSON required"})
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 8192:
                    raise ValueError("Body must be 1..8192 bytes")
                data = json.loads(self.rfile.read(size))
                if not isinstance(data, dict):
                    raise ValueError("Expected a JSON object")
                if self.path == "/api/login":
                    provided = data.get("password", "")
                    if not isinstance(provided, str) or not hmac.compare_digest(provided.encode(), password.encode()):
                        return self.send(401, {"error": "Incorrect access key"})
                    return self.send(200, {"ok": True}, cookie=f"garage_session={session}; HttpOnly; SameSite=Strict; Path=/")
                if not self.authenticated():
                    return self.send(401, {"error": "Sign in required"})
                if self.path == "/api/terrarium":
                    return self.send(200, dashboard.care(data["action"]))
                if self.path == "/api/missions":
                    dashboard.mission(data)
                    return self.send(200, {"ok": True})
                self.send(404, {"error": "Not found"})
            except (ValueError, KeyError, TypeError) as error:
                self.send(400, {"error": str(error)})

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8780)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--storage", type=Path, default=ROOT / "runtime")
    parser.add_argument("--grace-url", help="Public GRACE landing page URL; HTTP availability only")
    parser.add_argument("--interval", type=int, default=30)
    parser.add_argument("--tick-seconds", type=int, default=20)
    args = parser.parse_args()
    if args.interval < 5 or args.tick_seconds < 1:
        parser.error("interval must be >=5 and tick-seconds >=1")
    password = os.environ.get("GARAGE_DASHBOARD_KEY", "")
    if args.host not in ("127.0.0.1", "::1", "localhost") and len(password) < 24:
        parser.error("Non-loopback binding requires GARAGE_DASHBOARD_KEY of 24+ characters; use a private Tailscale address")
    config = json.loads(args.config.read_text(encoding="utf-8")) if args.config else {}
    if args.grace_url:
        config["grace_url"] = args.grace_url
    if len(config.get("services", [])) > 32:
        parser.error("At most 32 explicit service checks are supported")
    dashboard = Dashboard(config, args.storage, args.config.resolve().parent if args.config else ROOT,
                          args.interval, args.tick_seconds)
    server = ThreadingHTTPServer((args.host, args.port), handler_factory(dashboard, password))
    server.daemon_threads = True
    worker = threading.Thread(target=dashboard.run, daemon=True)
    worker.start()
    print(f"Garage dashboard: http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        dashboard.stop.set()
        server.server_close()
        worker.join(timeout=5)


if __name__ == "__main__":
    main()
