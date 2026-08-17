from collections import deque
from datetime import datetime, timezone
from threading import Lock
import json
import os
from pathlib import Path

try:
    import psycopg
except ImportError:  # Allows the service to start before dependencies are installed.
    psycopg = None


DEFAULT_LIGHT_SETTINGS = {
    "fixtures": [
        {"id": "bedroom", "name": "Bedroom Main Lightswitch", "entity_id": ""},
        {"id": "dining_room", "name": "Dining Room Light", "entity_id": ""},
        {"id": "kitchen", "name": "Kitchen Light", "entity_id": ""},
        {"id": "living_room", "name": "Living Room Light", "entity_id": ""},
        {"id": "stairway", "name": "Stair Light", "entity_id": ""},
    ],
    "presets": [
        {"id": "bedtime", "name": "Bedtime", "targets": {"kitchen": False, "dining_room": False, "living_room": False, "stairway": False, "bedroom": False}},
        {"id": "wind_down", "name": "Wind down", "targets": {"kitchen": False, "dining_room": False, "living_room": False, "stairway": False, "bedroom": True}},
        {"id": "movie_time", "name": "Movie time", "targets": {"kitchen": False, "dining_room": False, "living_room": False, "stairway": True, "bedroom": False}},
        {"id": "getting_home", "name": "Getting home", "targets": {"kitchen": True, "dining_room": True, "living_room": True, "stairway": True, "bedroom": False}},
    ],
}

class LabState:
    def __init__(self) -> None:
        self._lock = Lock()
        self._data_file = Path(__file__).parent / "grace_data.json"
        self._database_url = os.getenv("GRACE_DATABASE_URL", "")
        self.objects: list[dict] = []
        self.events: deque[dict] = deque(maxlen=100)
        self.watch_mode = False
        self.music = {"status": "stopped", "track": None, "volume": 50, "shuffle": False, "queue": ["Ambient Systems", "Morning Circuit", "Quiet Focus"], "index": 0, "updated_at": None}
        self.memories: list[dict] = []
        self.preferences: dict[str, str] = {}
        self.briefing_schedule = {"morning": "07:00", "afternoon": "13:00", "enabled": False}
        self.briefings: list[dict] = []
        self.network_telemetry: list[dict] = []
        self.grace_settings = {"personality": "composed, highly competent, discreet, quietly confident, warm but formal, subtly dry-witted, and honest about uncertainty", "voice": "local", "humor": "balanced", "formality": "polished", "response_length": "standard", "proactive_comments": "occasionally", "confirm_sensitive_actions": True}
        self.users: list[dict] = []
        self.sessions: list[dict] = []
        self.conversations: list[dict] = []
        self.saved_images: list[dict] = []
        self.light_settings = json.loads(json.dumps(DEFAULT_LIGHT_SETTINGS))
        self._load()

    def _load(self) -> None:
        if self._database_url and psycopg:
            try:
                with psycopg.connect(self._database_url) as connection:
                    self._ensure_database_schema(connection)
                    row = connection.execute("SELECT payload FROM grace_state WHERE id = TRUE").fetchone()
                    if row:
                        self._load_payload(row[0])
                        self._sync_light_settings(connection)
                        return
            except psycopg.Error:
                pass
        try:
            data = json.loads(self._data_file.read_text(encoding="utf-8"))
            self._load_payload(data)
        except (OSError, ValueError, TypeError):
            pass

    def _load_payload(self, data: dict) -> None:
        for key in ("music", "memories", "preferences", "briefing_schedule", "briefings", "network_telemetry", "grace_settings", "users", "sessions", "conversations", "saved_images", "light_settings"):
            if key in data:
                setattr(self, key, data[key])
        self.music.setdefault("shuffle", False)
        self.music.setdefault("queue", ["Ambient Systems", "Morning Circuit", "Quiet Focus"])
        self.music.setdefault("index", 0)
        self.grace_settings.setdefault("humor", "balanced")
        self.grace_settings.setdefault("formality", "polished")
        self.grace_settings.setdefault("response_length", "standard")
        self.grace_settings.setdefault("proactive_comments", "occasionally")
        fixture_names = {item["id"]: item["name"] for item in DEFAULT_LIGHT_SETTINGS["fixtures"]}
        for fixture in self.light_settings.get("fixtures", []):
            if fixture.get("id") in fixture_names:
                fixture["name"] = fixture_names[fixture["id"]]

    def _save(self) -> None:
        payload = {key: getattr(self, key) for key in ("music", "memories", "preferences", "briefing_schedule", "briefings", "network_telemetry", "grace_settings", "users", "sessions", "conversations", "saved_images", "light_settings")}
        try:
            if self._database_url and psycopg:
                with psycopg.connect(self._database_url) as connection:
                    self._ensure_database_schema(connection)
                    connection.execute("INSERT INTO grace_state (id, payload) VALUES (TRUE, %s::jsonb) ON CONFLICT (id) DO UPDATE SET payload = EXCLUDED.payload, updated_at = NOW()", (json.dumps(payload),))
                    self._sync_light_settings(connection)
                return
            self._data_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except (OSError, psycopg.Error if psycopg else RuntimeError):
            pass

    @staticmethod
    def _ensure_database_schema(connection: object) -> None:
        connection.execute("CREATE TABLE IF NOT EXISTS grace_state (id BOOLEAN PRIMARY KEY DEFAULT TRUE CHECK (id), payload JSONB NOT NULL, updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW())")
        connection.execute("CREATE TABLE IF NOT EXISTS light_fixtures (fixture_id TEXT PRIMARY KEY, name TEXT NOT NULL, entity_id TEXT NOT NULL, updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW())")
        connection.execute("CREATE TABLE IF NOT EXISTS light_presets (preset_id TEXT PRIMARY KEY, name TEXT NOT NULL, updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW())")
        connection.execute("CREATE TABLE IF NOT EXISTS light_preset_targets (preset_id TEXT NOT NULL REFERENCES light_presets(preset_id), fixture_id TEXT NOT NULL REFERENCES light_fixtures(fixture_id), desired_on BOOLEAN NOT NULL, PRIMARY KEY (preset_id, fixture_id))")

    def _sync_light_settings(self, connection: object) -> None:
        """Mirror the dashboard's lighting configuration into queryable tables."""
        with connection.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO light_fixtures (fixture_id, name, entity_id) VALUES (%s, %s, %s) ON CONFLICT (fixture_id) DO UPDATE SET name = EXCLUDED.name, entity_id = EXCLUDED.entity_id, updated_at = NOW()",
                [(item["id"], item["name"], item.get("entity_id", "")) for item in self.light_settings["fixtures"]],
            )
            cursor.executemany(
                "INSERT INTO light_presets (preset_id, name) VALUES (%s, %s) ON CONFLICT (preset_id) DO UPDATE SET name = EXCLUDED.name, updated_at = NOW()",
                [(item["id"], item["name"]) for item in self.light_settings["presets"]],
            )
            cursor.executemany(
                "INSERT INTO light_preset_targets (preset_id, fixture_id, desired_on) VALUES (%s, %s, %s) ON CONFLICT (preset_id, fixture_id) DO UPDATE SET desired_on = EXCLUDED.desired_on",
                [(preset["id"], fixture_id, desired_on) for preset in self.light_settings["presets"] for fixture_id, desired_on in preset["targets"].items()],
            )

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "current_objects": list(self.objects),
                "recent_events": list(self.events),
                "watch_mode": self.watch_mode,
                "music": dict(self.music), "memory_count": len(self.memories),
                "briefing_schedule": dict(self.briefing_schedule),
                "grace_settings": dict(self.grace_settings),
            }

    def update_music(self, **changes: object) -> dict:
        with self._lock:
            self.music.update(changes)
            self.music["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._save()
            return dict(self.music)

    def add_memory(self, content: str, category: str = "note") -> dict:
        with self._lock:
            item = {"id": datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f"), "content": content, "category": category, "created_at": datetime.now(timezone.utc).isoformat()}
            self.memories.append(item); self._save(); return item

    def remove_memory(self, memory_id: str) -> bool:
        with self._lock:
            old = len(self.memories); self.memories = [item for item in self.memories if item["id"] != memory_id]
            self._save(); return len(self.memories) != old

    def add_briefing(self, briefing: dict) -> None:
        with self._lock:
            self.briefings.append(briefing); self.briefings = self.briefings[-30:]; self._save()

    def record_network(self, summary: dict) -> None:
        with self._lock:
            self.network_telemetry.append(summary); self.network_telemetry = self.network_telemetry[-50:]; self._save()

    def add_saved_image(self, item: dict) -> dict:
        with self._lock:
            self.saved_images.append(item)
            self.saved_images = self.saved_images[-100:]
            self._save()
            return dict(item)

    def remove_saved_image(self, image_id: str) -> bool:
        with self._lock:
            old = len(self.saved_images)
            self.saved_images = [item for item in self.saved_images if item["id"] != image_id]
            self._save()
            return len(self.saved_images) != old

    def add_user(self, user: dict) -> None:
        with self._lock:
            self.users.append(user); self._save()

    def add_conversation_message(self, user_id: str, username: str, conversation_id: str, role: str, content: str) -> None:
        with self._lock:
            conversation = next((item for item in self.conversations if item["id"] == conversation_id and item["user_id"] == user_id), None)
            if conversation is None:
                conversation = {"id": conversation_id, "user_id": user_id, "username": username, "title": content[:32], "messages": [], "updated_at": None}
                self.conversations.append(conversation)
            conversation["messages"].append({"role": role, "content": content})
            conversation["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._save()

    def conversation_messages(self, user_id: str, conversation_id: str) -> list[dict]:
        """Return a user's saved messages for use as model context."""
        with self._lock:
            conversation = next((item for item in self.conversations if item["id"] == conversation_id and item["user_id"] == user_id), None)
            return list(conversation.get("messages", [])) if conversation else []

    def update_objects(self, objects: list[dict]) -> None:
        with self._lock:
            previous = {item["label"] for item in self.objects}
            current = {item["label"] for item in objects}
            for label in sorted(current - previous):
                self.events.append(self._event(f"{label} appeared"))
            for label in sorted(previous - current):
                self.events.append(self._event(f"{label} disappeared"))
            self.objects = objects

    def add_event(self, message: str) -> None:
        with self._lock:
            self.events.append(self._event(message))

    @staticmethod
    def _event(message: str) -> dict:
        return {"message": message, "timestamp": datetime.now(timezone.utc).isoformat()}

