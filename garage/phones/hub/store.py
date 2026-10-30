"""Durable phone-fleet state and authoritative referees."""
import base64
import copy
import hashlib
import importlib.util
import io
import json
import math
import secrets
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from contextlib import contextmanager


PHONES = Path(__file__).resolve().parents[1]


def load(relative):
    spec = importlib.util.spec_from_file_location(relative.replace("/", "_").replace(".", "_"), PHONES / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def text(value, maximum=2000):
    if not isinstance(value, str) or not 0 < len(value.strip()) <= maximum:
        raise ValueError(f"Text must contain 1..{maximum} characters")
    return value.strip()


def decode(value, limit):
    if not isinstance(value, str) or len(value) > (limit + 2) * 4 // 3 + 4:
        raise ValueError("Upload too large")
    result = base64.b64decode(value, validate=True)
    if not result or len(result) > limit:
        raise ValueError("Upload size is invalid")
    return result


class Store:
    def __init__(self, root, config=None):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.db_path = self.root / "fleet.sqlite"
        self.config = config or {}
        self.lock = threading.RLock()
        self.battle = load("battle-arena/run.py")
        self.chess = load("chess/model.py")
        self.network = load("distributed-network/model.py")
        with self.db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS devices(id TEXT PRIMARY KEY, name TEXT UNIQUE, token_hash TEXT, last_seen REAL, metadata TEXT);
                CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY, device TEXT, expires REAL);
                CREATE TABLE IF NOT EXISTS photos(id TEXT PRIMARY KEY, digest TEXT, device TEXT, project TEXT, captured_at TEXT, uploaded_at TEXT, caption TEXT, mime TEXT, UNIQUE(digest,device,project,captured_at));
                CREATE TABLE IF NOT EXISTS messages(id TEXT PRIMARY KEY, sender TEXT, recipient TEXT, text TEXT, attachment TEXT, sent_at TEXT, acknowledged_at TEXT);
                CREATE TABLE IF NOT EXISTS matches(id TEXT PRIMARY KEY, kind TEXT, players TEXT, state TEXT, created_at TEXT);
                CREATE TABLE IF NOT EXISTS benchmarks(id TEXT PRIMARY KEY, sender TEXT, recipient TEXT, started REAL, deadline REAL, budget INTEGER, uploaded INTEGER, acknowledged INTEGER, state TEXT);
                CREATE TABLE IF NOT EXISTS chunks(id TEXT PRIMARY KEY, benchmark TEXT, digest TEXT, bytes INTEGER, acknowledged REAL);
                CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, device TEXT, kind TEXT, spec TEXT, state TEXT, created REAL, lease REAL, result TEXT);
            """)

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.db_path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def pair(self, name):
        name = text(name, 80)
        token, device = secrets.token_urlsafe(32), uuid.uuid4().hex
        with self.db() as db:
            if db.execute("SELECT id FROM devices WHERE name=?", (name,)).fetchone():
                raise ValueError("Device name already exists; choose a new name")
            db.execute("INSERT INTO devices VALUES(?,?,?,?,?)", (device, name, hashlib.sha256(token.encode()).hexdigest(), 0, "{}"))
        return {"id": device, "name": name, "token": token}

    def identity(self, token, session=False):
        if not token or not isinstance(token, str):
            return None
        hashed = hashlib.sha256(token.encode()).hexdigest()
        with self.db() as db:
            if session:
                row = db.execute("SELECT device AS id FROM sessions WHERE token_hash=? AND expires>?", (hashed, time.time())).fetchone()
            else:
                row = db.execute("SELECT id FROM devices WHERE token_hash=?", (hashed,)).fetchone()
        return row["id"] if row else None

    def login(self, token):
        device = self.identity(token)
        if not device:
            raise PermissionError("Invalid device key")
        session = secrets.token_urlsafe(32)
        with self.db() as db:
            db.execute("DELETE FROM sessions WHERE expires<?", (time.time(),))
            db.execute("INSERT INTO sessions VALUES(?,?,?)", (hashlib.sha256(session.encode()).hexdigest(), device, time.time() + 7 * 86400))
        return session

    def heartbeat(self, device, metadata):
        if not isinstance(metadata, dict) or len(json.dumps(metadata)) > 20000:
            raise ValueError("Invalid metadata")
        with self.db() as db:
            db.execute("UPDATE devices SET last_seen=?,metadata=? WHERE id=?", (time.time(), json.dumps(metadata), device))

    def logout(self, session):
        if session:
            with self.db() as db:
                db.execute("DELETE FROM sessions WHERE token_hash=?", (hashlib.sha256(session.encode()).hexdigest(),))

    def devices(self):
        with self.db() as db:
            rows = db.execute("SELECT id,name,last_seen,metadata FROM devices ORDER BY name").fetchall()
        return [dict(row, metadata=json.loads(row["metadata"]), online=time.time() - row["last_seen"] < 45) for row in rows]

    def add_photo(self, device, data):
        from PIL import Image
        raw = decode(data["image"], 5 * 1024 * 1024)
        with Image.open(io.BytesIO(raw)) as image:
            if image.width * image.height > 20_000_000 or image.format not in ("JPEG", "PNG", "WEBP"):
                raise ValueError("Use JPEG, PNG, or WebP up to 20 megapixels")
            mime = Image.MIME[image.format]
            image.verify()
        project = text(data.get("project", "general"), 100)
        captured = datetime.fromisoformat(data["captured_at"].replace("Z", "+00:00"))
        if captured.tzinfo is None:
            raise ValueError("Capture time needs a timezone")
        digest = hashlib.sha256(raw).hexdigest()
        directory = self.root / "photos"
        directory.mkdir(exist_ok=True)
        destination = directory / digest
        if not destination.exists():
            if sum(path.stat().st_size for path in directory.iterdir()) + len(raw) > int(self.config.get("photo_quota_mb", 1024)) * 1024**2:
                raise ValueError("Photo storage quota reached; export/archive originals before adding more")
            destination.write_bytes(raw)
        with self.db() as db:
            db.execute("INSERT OR IGNORE INTO photos VALUES(?,?,?,?,?,?,?,?)", (uuid.uuid4().hex, digest, device, project, captured.isoformat(), timestamp(), str(data.get("caption", ""))[:2000], mime))
            row = db.execute("SELECT * FROM photos WHERE digest=? AND device=? AND project=? AND captured_at=?", (digest, device, project, captured.isoformat())).fetchone()
        return dict(row)

    def photos(self):
        with self.db() as db:
            return [dict(row) for row in db.execute("SELECT * FROM photos ORDER BY captured_at DESC LIMIT 200")]

    def photo(self, digest):
        with self.db() as db:
            row = db.execute("SELECT mime FROM photos WHERE digest=?", (digest,)).fetchone()
        if not row:
            raise ValueError("Photo not found")
        return (self.root / "photos" / digest).read_bytes(), row["mime"]

    def send_message(self, device, data):
        recipient = data["recipient"]
        with self.db() as db:
            if not db.execute("SELECT id FROM devices WHERE id=?", (recipient,)).fetchone():
                raise ValueError("Recipient is not paired")
            attachment = data.get("photo")
            if attachment and not db.execute("SELECT id FROM photos WHERE id=?", (attachment,)).fetchone():
                raise ValueError("Unknown photo")
            message_id = text(data.get("id", uuid.uuid4().hex), 80)
            old = db.execute("SELECT * FROM messages WHERE id=?", (message_id,)).fetchone()
            if old and old["sender"] != device:
                raise ValueError("Message identifier already belongs to another device")
            db.execute("INSERT OR IGNORE INTO messages VALUES(?,?,?,?,?,?,?)", (message_id, device, recipient, text(data["text"], 5000), attachment, timestamp(), None))
        return {"id": message_id, "status": "queued"}

    def messages(self, device):
        with self.db() as db:
            return [dict(row) for row in db.execute("SELECT * FROM messages WHERE recipient=? OR sender=? ORDER BY sent_at DESC LIMIT 200", (device, device))]

    def acknowledge(self, device, message):
        with self.db() as db:
            result = db.execute("UPDATE messages SET acknowledged_at=COALESCE(acknowledged_at,?) WHERE id=? AND recipient=?", (timestamp(), message, device))
            if not result.rowcount:
                raise ValueError("Message is not addressed to you")
        return {"ok": True}

    def create_match(self, device, kind):
        if kind not in ("battle", "chess", "network"):
            raise ValueError("Unknown match kind")
        state = self.battle.initial_state() if kind == "battle" else self.chess.create() if kind == "chess" else {
            "input": [0.2, 0.4, 0.6, 0.8], "values": [0.2, 0.4, 0.6, 0.8], "stage": 0,
            "history": [], "finished": False, "started": None, "deadline": None}
        match = uuid.uuid4().hex[:12]
        with self.db() as db:
            db.execute("INSERT INTO matches VALUES(?,?,?,?,?)", (match, kind, json.dumps([device]), json.dumps(state), timestamp()))
        return {"id": match}

    def match(self, match):
        with self.db() as db:
            row = db.execute("SELECT * FROM matches WHERE id=?", (match,)).fetchone()
        if not row:
            raise ValueError("Match not found")
        return dict(row, players=json.loads(row["players"]), state=json.loads(row["state"]))

    def update_match(self, match):
        with self.db() as db:
            db.execute("UPDATE matches SET players=?,state=? WHERE id=?", (json.dumps(match["players"]), json.dumps(match["state"]), match["id"]))

    def join(self, device, match_id):
        with self.lock:
            match = self.match(match_id)
            if device not in match["players"]:
                if len(match["players"]) >= 2:
                    raise ValueError("Match is full")
                match["players"].append(device)
                if match["kind"] == "chess":
                    match["state"]["turn_started"] = time.time()
                if match["kind"] == "network":
                    match["state"].update(started=time.time(), deadline=time.time() + 120)
                self.update_match(match)
            return self.public_match(match, device)

    def public_match(self, match, device):
        players, state = match["players"], match["state"]
        if match["kind"] == "battle":
            who = "a" if device in players and players.index(device) == 0 else "b" if device in players else "spectator"
            result = self.battle.public_state(state, who)
        elif match["kind"] == "chess":
            result = self.chess.public(state, players, device)
        else:
            result = copy.deepcopy(state)
            timed_out = state["deadline"] is not None and time.time() > state["deadline"] and not state["finished"]
            result["timed_out"] = timed_out
            stage = state["stage"]
            result["task"] = {"stage": stage, "input": state["values"], "layer": self.network.LAYERS[stage]} if len(players) == 2 and not state["finished"] and not timed_out and players[stage] == device else None
            if state["finished"]:
                result["reference"] = self.network.infer(state["input"])
        return {"id": match["id"], "kind": match["kind"], "players": players, "data": result}

    def act(self, device, data):
        with self.lock:
            match = self.match(data["id"])
            if device not in match["players"] or len(match["players"]) != 2:
                raise ValueError("Two joined players are required")
            side, state = match["players"].index(device), match["state"]
            if match["kind"] == "battle":
                if data["round"] != state["round"]:
                    raise ValueError("Stale round")
                match["state"] = self.battle.submit(state, "a" if side == 0 else "b", data["action"])
            elif match["kind"] == "chess":
                self.chess.move(state, side, data["move"], match["players"])
            else:
                if state["finished"] or time.time() > state["deadline"] or side != state["stage"] or data["stage"] != state["stage"]:
                    raise ValueError("Stage is finished, expired, or assigned to the other phone")
                expected = self.network.layer(state["values"], self.network.LAYERS[state["stage"]])
                values = data["values"]
                if not isinstance(values, list) or len(values) != len(expected) or any(not isinstance(v, (int, float)) or not math.isfinite(v) or abs(v-e) > 1e-6 for v, e in zip(values, expected)):
                    raise ValueError("Layer output fails the reference check")
                state["history"].append({"device": device, "stage": state["stage"], "elapsed_seconds": time.time() - state["started"], "values": values})
                state["values"], state["stage"] = values, state["stage"] + 1
                state["finished"] = state["stage"] == len(self.network.LAYERS)
            self.update_match(match)
            return self.public_match(match, device)

    def matches(self, device):
        with self.db() as db:
            rows = db.execute("SELECT id FROM matches ORDER BY created_at DESC LIMIT 30").fetchall()
        return [self.public_match(self.match(row["id"]), device) for row in rows]

    def benchmark(self, device, recipient):
        if recipient == device or recipient not in [row["id"] for row in self.devices() if row["online"]]:
            raise ValueError("Choose a different online paired device")
        with self.lock, self.db() as db:
            if db.execute("SELECT id FROM benchmarks WHERE (sender IN (?,?) OR recipient IN (?,?)) AND deadline>? AND state='active'", (device, recipient, device, recipient, time.time())).fetchone():
                raise ValueError("A transfer is already active for this device")
            match = uuid.uuid4().hex
            db.execute("INSERT INTO benchmarks VALUES(?,?,?,?,?,?,?,?,?)", (match, device, recipient, time.time(), time.time() + 10, 2 * 1024**2, 0, 0, "active"))
        return {"id": match, "budget": 2 * 1024**2, "duration_seconds": 10, "path": "hub-relayed; not direct phone-to-phone"}

    def chunk(self, device, data):
        raw = decode(data["data"], 64 * 1024)
        with self.lock, self.db() as db:
            row = db.execute("SELECT * FROM benchmarks WHERE id=? AND sender=?", (data["id"], device)).fetchone()
            if not row or row["state"] != "active" or time.time() > row["deadline"] or row["uploaded"] + len(raw) > row["budget"]:
                raise ValueError("Transfer stopped, expired, or over budget")
            if db.execute("SELECT COUNT(*) FROM chunks WHERE benchmark=?", (row["id"],)).fetchone()[0] >= 32:
                raise ValueError("Chunk budget reached")
            directory = self.root / "chunks"
            directory.mkdir(exist_ok=True)
            if sum(path.stat().st_size for path in directory.iterdir()) + len(raw) > 100 * 1024**2:
                raise ValueError("Benchmark storage quota reached; archive old lab data")
            chunk = uuid.uuid4().hex
            (directory / chunk).write_bytes(raw)
            db.execute("INSERT INTO chunks VALUES(?,?,?,?,?)", (chunk, row["id"], hashlib.sha256(raw).hexdigest(), len(raw), None))
            db.execute("UPDATE benchmarks SET uploaded=uploaded+? WHERE id=?", (len(raw), row["id"]))
        return {"id": chunk}

    def receive_chunk(self, device, chunk):
        with self.db() as db:
            row = db.execute("SELECT c.* FROM chunks c JOIN benchmarks b ON b.id=c.benchmark WHERE c.id=? AND b.recipient=?", (chunk, device)).fetchone()
        if not row:
            raise ValueError("Chunk not addressed to this phone")
        return {"id": chunk, "data": base64.b64encode((self.root / "chunks" / chunk).read_bytes()).decode(), "sha256": row["digest"]}

    def ack_chunk(self, device, data):
        with self.lock, self.db() as db:
            row = db.execute("SELECT c.*,b.deadline,b.state AS transfer_state FROM chunks c JOIN benchmarks b ON b.id=c.benchmark WHERE c.id=? AND b.recipient=?", (data["id"], device)).fetchone()
            if not row or data["sha256"] != row["digest"]:
                raise ValueError("Chunk integrity/recipient check failed")
            if row["acknowledged"] is None:
                db.execute("UPDATE chunks SET acknowledged=? WHERE id=?", (time.time(), row["id"]))
                if time.time() <= row["deadline"] and row["transfer_state"] == "active":
                    db.execute("UPDATE benchmarks SET acknowledged=acknowledged+? WHERE id=?", (row["bytes"], row["benchmark"]))
        return {"ok": True}

    def benchmarks(self, device):
        with self.db() as db:
            rows = [dict(row) for row in db.execute("SELECT * FROM benchmarks WHERE sender=? OR recipient=? ORDER BY started DESC LIMIT 20", (device, device))]
            for row in rows:
                row["state"] = row["state"] if row["state"] != "active" else "finished" if time.time() > row["deadline"] else "active"
                row["chunks"] = [dict(chunk) for chunk in db.execute("SELECT id,bytes FROM chunks WHERE benchmark=? AND acknowledged IS NULL", (row["id"],))] if device == row["recipient"] else []
                row["path"] = "hub-relayed"
                row["verified_mbps"] = round(row["acknowledged"] * 8 / max(0.001, min(time.time(), row["deadline"]) - row["started"]) / 1_000_000, 3)
        return rows

    def stop_benchmark(self, device, match):
        with self.db() as db:
            db.execute("UPDATE benchmarks SET state='stopped' WHERE id=? AND (sender=? OR recipient=?)", (match, device, device))
        return {"ok": True}

    def state(self, device):
        return {"you": device, "devices": self.devices(), "photos": self.photos(), "messages": self.messages(device),
                "matches": self.matches(device), "benchmarks": self.benchmarks(device), "jobs": self.jobs(), "time": timestamp()}

    def create_job(self, device, data):
        target = data["device"]
        if target not in [entry["id"] for entry in self.devices()]:
            raise ValueError("Target device is not paired")
        kind = data.get("kind", "browser")
        if kind == "browser":
            spec = load("fleet-operator/jobs.py").validate(data["spec"], self.config.get("allowed_origins", []))
        elif kind == "diagnostics":
            spec = {}
        else:
            raise ValueError("Only browser tests and diagnostics are supported")
        identifier = uuid.uuid4().hex
        with self.db() as db:
            db.execute("INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?)", (identifier, target, kind, json.dumps(spec), "queued", time.time(), None, None))
        return {"id": identifier}

    def jobs(self):
        with self.db() as db:
            rows = [dict(row) for row in db.execute("SELECT * FROM jobs ORDER BY created DESC LIMIT 50")]
        for row in rows:
            row["spec"] = json.loads(row["spec"])
            row["result"] = json.loads(row["result"]) if row["result"] else None
            if row["state"] == "running" and time.time() > row["lease"]:
                row["state"] = "expired"
        return rows

    def claim_job(self, device):
        with self.lock, self.db() as db:
            row = db.execute("SELECT * FROM jobs WHERE device=? AND state='queued' ORDER BY created LIMIT 1", (device,)).fetchone()
            if not row:
                return {"job": None}
            lease = time.time() + 90
            db.execute("UPDATE jobs SET state='running',lease=? WHERE id=?", (lease, row["id"]))
        return {"job": dict(row, spec=json.loads(row["spec"]), lease=lease)}

    def finish_job(self, device, data):
        result = data["result"]
        if not isinstance(result, dict) or result.get("status") not in ("passed", "failed"):
            raise ValueError("Job result must report passed or failed")
        with self.lock, self.db() as db:
            row = db.execute("SELECT * FROM jobs WHERE id=? AND device=? AND state='running'", (data["id"], device)).fetchone()
            if not row or time.time() > row["lease"]:
                raise ValueError("Job is not running or its lease expired")
            result = dict(result)
            image = result.pop("screenshot", None)
            if len(json.dumps(result)) > 50000:
                raise ValueError("Job report too large")
            if image:
                from PIL import Image
                raw = decode(image, 5 * 1024**2)
                with Image.open(io.BytesIO(raw)) as screenshot:
                    if screenshot.format != "PNG" or screenshot.width * screenshot.height > 20_000_000:
                        raise ValueError("Screenshot must be a bounded PNG")
                    screenshot.verify()
                directory = self.root / "artifacts"
                directory.mkdir(exist_ok=True)
                (directory / (row["id"] + ".png")).write_bytes(raw)
                result["artifact"] = row["id"] + ".png"
            db.execute("UPDATE jobs SET state=?,result=? WHERE id=?", (result["status"], json.dumps(result), row["id"]))
        return {"ok": True}
