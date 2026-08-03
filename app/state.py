from collections import deque
from datetime import datetime, timezone
from threading import Lock
import json
from pathlib import Path


class LabState:
    def __init__(self) -> None:
        self._lock = Lock()
        self._data_file = Path(__file__).parent / "grace_data.json"
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
        self._load()

    def _load(self) -> None:
        try:
            data = json.loads(self._data_file.read_text(encoding="utf-8"))
            for key in ("music", "memories", "preferences", "briefing_schedule", "briefings", "network_telemetry", "grace_settings", "users", "sessions", "conversations", "saved_images"):
                if key in data:
                    setattr(self, key, data[key])
            self.music.setdefault("shuffle", False)
            self.music.setdefault("queue", ["Ambient Systems", "Morning Circuit", "Quiet Focus"])
            self.music.setdefault("index", 0)
            self.grace_settings.setdefault("humor", "balanced")
            self.grace_settings.setdefault("formality", "polished")
            self.grace_settings.setdefault("response_length", "standard")
            self.grace_settings.setdefault("proactive_comments", "occasionally")
        except (OSError, ValueError, TypeError):
            pass

    def _save(self) -> None:
        payload = {key: getattr(self, key) for key in ("music", "memories", "preferences", "briefing_schedule", "briefings", "network_telemetry", "grace_settings", "users", "sessions", "conversations", "saved_images")}
        try:
            self._data_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except OSError:
            pass

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
                conversation = {"id": conversation_id, "user_id": user_id, "username": username, "title": content[:32], "messages": []}
                self.conversations.append(conversation)
            conversation["messages"].append({"role": role, "content": content})
            self._save()

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

