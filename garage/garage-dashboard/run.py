"""Garage Observatory: a standalone weather, aircraft, ISS, and solar-system board."""
import argparse
import copy
import hashlib
import hmac
import importlib.util
import json
import math
import os
import re
import secrets
import threading
import time
import urllib.parse
from datetime import datetime, timezone
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE_INTERVALS = {"weather": 900, "air": 900, "aircraft": 120, "iss": 30, "satellites": 3600, "solar_system": 3600}


def module(folder):
    path = ROOT / folder if folder.endswith(".py") else ROOT / folder / "run.py"
    spec = importlib.util.spec_from_file_location(folder.replace("-", "_").replace(".", "_"), path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def now():
    return datetime.now(timezone.utc).isoformat()


class Dashboard:
    def __init__(self, config, storage, config_dir=None, interval=30):
        self.config = copy.deepcopy(config)
        self.storage = Path(storage)
        self.storage.mkdir(parents=True, exist_ok=True)
        self.settings_file = self.storage / "display-settings.json"
        self.lock = threading.RLock()
        self.stop = threading.Event()
        self.generation = 0
        self.interval = interval
        self.collector_module = module("collectors.py")
        live = config.get("live", {})
        self.settings = {"location": live.get("location"), "units": config.get("units", "imperial"),
                         "aircraft_radius_nm": live.get("aircraft_radius_nm", 40), "solar_system": bool(live.get("enabled")),
                         "extended_bodies": True, "extra_bodies": []}
        if self.settings_file.exists():
            self.settings.update(json.loads(self.settings_file.read_text(encoding="utf-8")))
        self.feeds = {}
        self._configure_collectors()
        self.solar = module("solar_system.py").SolarSystem(self.storage / "solar", self.collector_module.fetch_json,
                                                          lambda: self.collectors.astronomy(), self.stop)

    def _configure_collectors(self):
        previous = getattr(self, "collectors", None)
        live = copy.deepcopy(self.config.get("live", {}))
        live.update(location=self.settings.get("location"), aircraft_radius_nm=self.settings["aircraft_radius_nm"], observatory_schema=2)
        fingerprint = hashlib.sha256(json.dumps(live, sort_keys=True).encode()).hexdigest()[:12]
        self.collectors = self.collector_module.Collectors(live, self.storage / "feeds" / fingerprint)
        if previous:
            self.collectors.astro_lock = previous.astro_lock
            self.collectors._astronomy = previous._astronomy
        # The solar/ISS ephemeris download is shared across location changes.
        self.collectors.storage = self.storage / "ephemeris"
        self.collectors.storage.mkdir(exist_ok=True)

    def has_location(self):
        location = self.settings.get("location") or {}
        return all(isinstance(location.get(key), (int, float)) and math.isfinite(location[key]) for key in ("latitude", "longitude"))

    def search_location(self, query):
        if not isinstance(query, str) or not 2 <= len(query.strip()) <= 100:
            raise ValueError("Enter a city or ZIP code (2..100 characters)")
        result = self.collector_module.fetch_json("https://geocoding-api.open-meteo.com/v1/search?" + urllib.parse.urlencode({"name": query.strip(), "count": 8, "language": "en"}))
        return [{"name": row["name"], "latitude": row["latitude"], "longitude": row["longitude"], "timezone": row.get("timezone", "UTC"),
                 "region": ", ".join(filter(None, [row.get("admin1"), row.get("country")]))} for row in result.get("results", [])]

    def save_settings(self, data):
        with self.lock:
            previous = self.settings
            settings = copy.deepcopy(previous)
            if "location" in data:
                location = data["location"]
                if not isinstance(location, dict):
                    raise ValueError("Choose a location")
                lat, lon = float(location["latitude"]), float(location["longitude"])
                if not math.isfinite(lat + lon) or not -90 <= lat <= 90 or not -180 <= lon <= 180:
                    raise ValueError("Invalid coordinates")
                settings["location"] = {"name": str(location["name"])[:100], "latitude": lat, "longitude": lon,
                                        "timezone": str(location.get("timezone", "UTC"))[:80], "region": str(location.get("region", ""))[:150]}
                settings["solar_system"] = True
            if "units" in data:
                if data["units"] not in ("imperial", "metric"):
                    raise ValueError("Choose imperial or metric units")
                settings["units"] = data["units"]
            if "aircraft_radius_nm" in data:
                radius = float(data["aircraft_radius_nm"])
                if not math.isfinite(radius) or not 5 <= radius <= 100:
                    raise ValueError("Aircraft radius must be 5..100 nautical miles")
                settings["aircraft_radius_nm"] = radius
            for key in ("solar_system", "extended_bodies"):
                if key in data:
                    if not isinstance(data[key], bool):
                        raise ValueError("Invalid display toggle")
                    settings[key] = data[key]
            if "add_body" in data:
                body = data["add_body"]
                identifier = str(body["id"])
                if not re.fullmatch(r"\d{1,9}", identifier) or not isinstance(body.get("name"), str) or not 1 <= len(body["name"]) <= 100:
                    raise ValueError("Select a valid JPL search result")
                if len(settings["extra_bodies"]) >= 50:
                    raise ValueError("At most 50 additional bodies can be tracked")
                if not any(row["id"] == identifier for row in settings["extra_bodies"]):
                    settings["extra_bodies"].append({"id": identifier, "name": body["name"]})
                settings["solar_system"] = True
            temporary = self.settings_file.with_suffix(".tmp")
            temporary.write_text(json.dumps(settings, indent=2), encoding="utf-8")
            temporary.replace(self.settings_file)
            self.settings = settings
            self.generation += 1
            if settings["location"] != previous["location"]:
                self._configure_collectors()
                self.feeds = {key: value for key, value in self.feeds.items() if key == "solar_system"}
            elif settings["aircraft_radius_nm"] != previous["aircraft_radius_nm"]:
                self._configure_collectors()
                self.feeds.pop("aircraft", None)
            if any(settings[key] != previous[key] for key in ("extra_bodies", "extended_bodies", "solar_system")):
                existing = self.feeds.get("solar_system")
                if existing:
                    self.feeds["solar_system"] = dict(existing, attempt=0, refreshing=True)
        return settings

    def enabled(self, name):
        return bool(self.settings["solar_system"]) if name == "solar_system" else self.has_location()

    def collect_source(self, name):
        with self.lock:
            if not self.enabled(name):
                return
            generation, collector, settings = self.generation, self.collectors, copy.deepcopy(self.settings)
            previous = self.feeds.get(name)
            if previous and time.time() - previous.get("attempt", 0) < SOURCE_INTERVALS[name]:
                return
            self.feeds[name] = dict(previous, refreshing=True) if previous else {"status": "loading", "started_at": now()}
        if name == "solar_system":
            key = name + "-" + hashlib.sha256(json.dumps([settings["extra_bodies"], settings["extended_bodies"]], sort_keys=True).encode()).hexdigest()[:12]
            result = collector.cached(key, lambda: self.solar.collect(settings["extra_bodies"], settings["extended_bodies"]), SOURCE_INTERVALS[name])
        else:
            result = collector.cached(name, getattr(collector, name), SOURCE_INTERVALS[name])
        with self.lock:
            if generation == self.generation:
                self.feeds[name] = result

    def collect(self):
        for source in SOURCE_INTERVALS:
            self.collect_source(source)

    def snapshot(self):
        with self.lock:
            result = {"settings": copy.deepcopy(self.settings), "configured": self.has_location(), "feeds": copy.deepcopy(self.feeds),
                      "server_time": now(), "refresh_seconds": self.interval, "solar_progress": dict(self.solar.progress)}
            if result["feeds"].get("solar_system", {}).get("status") == "loading" and self.solar.partial:
                result["feeds"]["solar_system"]["data"] = copy.deepcopy(self.solar.partial)
        return result

    def run(self):
        def worker(source):
            while not self.stop.is_set():
                try:
                    self.collect_source(source)
                except Exception as error:
                    with self.lock:
                        self.feeds[source] = {"status": "error", "error": str(error), "attempt": time.time()}
                self.stop.wait(2)
        workers = [threading.Thread(target=worker, args=(source,), daemon=True) for source in SOURCE_INTERVALS]
        for thread in workers:
            thread.start()
        self.stop.wait()
        for thread in workers:
            thread.join(timeout=0.1)


def handler_factory(dashboard, password=""):
    session = secrets.token_urlsafe(32)
    class Handler(BaseHTTPRequestHandler):
        def send(self, code, value, mime="application/json", cookie=None):
            body = json.dumps(value, allow_nan=False).encode() if mime == "application/json" else value
            self.send_response(code)
            self.send_header("Content-Type", mime)
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
            try:
                cookies = SimpleCookie()
                cookies.load(self.headers.get("Cookie", ""))
                value = cookies.get("garage_session")
                return bool(value and hmac.compare_digest(value.value, session))
            except Exception:
                return False

        def do_GET(self):
            parsed = urllib.parse.urlsplit(self.path)
            if parsed.path.startswith("/api/"):
                if not self.authenticated():
                    return self.send(401, {"error": "Sign in required"})
                try:
                    if parsed.path == "/api/status":
                        return self.send(200, dashboard.snapshot())
                    query = urllib.parse.parse_qs(parsed.query).get("q", [""])[0]
                    if parsed.path == "/api/location/search":
                        return self.send(200, {"results": dashboard.search_location(query)})
                    if parsed.path == "/api/bodies/search":
                        return self.send(200, {"results": dashboard.solar.search(query)})
                except (ValueError, OSError) as error:
                    return self.send(400, {"error": str(error)})
            files = {"/": ("index.html", "text/html; charset=utf-8"), "/app.js": ("app.js", "text/javascript; charset=utf-8"),
                     "/solar.js": ("solar.js", "text/javascript; charset=utf-8"), "/board.css": ("board.css", "text/css; charset=utf-8"),
                     "/style.css": ("style.css", "text/css; charset=utf-8")}
            files["/land.json"] = ("land.json", "application/json; charset=utf-8")
            if parsed.path not in files:
                return self.send(404, {"error": "Not found"})
            name, mime = files[parsed.path]
            self.send(200, (ROOT / "web" / name).read_bytes(), mime)

        def do_POST(self):
            origin = self.headers.get("Origin")
            if origin and urllib.parse.urlsplit(origin).netloc != self.headers.get("Host"):
                return self.send(403, {"error": "Cross-origin writes are not allowed"})
            if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
                return self.send(415, {"error": "JSON required"})
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 16384:
                    raise ValueError("Invalid request size")
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
                if self.path == "/api/settings":
                    return self.send(200, dashboard.save_settings(data))
                return self.send(404, {"error": "Not found"})
            except (ValueError, KeyError, TypeError, OSError) as error:
                self.send(400, {"error": str(error)})
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8780)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--storage", type=Path, default=ROOT / "runtime")
    parser.add_argument("--interval", type=int, default=30)
    args = parser.parse_args()
    if args.interval < 5:
        parser.error("interval must be >=5")
    password = os.environ.get("GARAGE_DASHBOARD_KEY", "")
    if args.host not in ("127.0.0.1", "localhost") and len(password) < 24:
        parser.error("Non-loopback binding requires GARAGE_DASHBOARD_KEY of 24+ characters")
    config = json.loads(args.config.read_text(encoding="utf-8")) if args.config else {}
    dashboard = Dashboard(config, args.storage, interval=args.interval)
    server = ThreadingHTTPServer((args.host, args.port), handler_factory(dashboard, password))
    server.daemon_threads = True
    worker = threading.Thread(target=dashboard.run, daemon=True)
    worker.start()
    print(f"Garage Observatory: http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        dashboard.stop.set()
        server.server_close()
        worker.join(timeout=2)


if __name__ == "__main__":
    main()
