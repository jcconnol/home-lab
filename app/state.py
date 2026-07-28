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
        self.music = {"status": "stopped", "track": None, "volume": 50, "updated_at": None}
        self.memories: list[dict] = []
        self.preferences: dict[str, str] = {}
        self.briefing_schedule = {"morning": "07:00", "afternoon": "13:00", "enabled": False}
        self.briefings: list[dict] = []
        self.network_telemetry: list[dict] = []
        self.grace_settings = {"personality": "funny, dry-witted, calm, capable, technically clear", "voice": "local", "confirm_sensitive_actions": True}
        self._load()

    def _load(self) -> None:
        try:
            data = json.loads(self._data_file.read_text(encoding="utf-8"))
            for key in ("music", "memories", "preferences", "briefing_schedule", "briefings", "network_telemetry", "grace_settings"):
                if key in data:
                    setattr(self, key, data[key])
        except (OSError, ValueError, TypeError):
            pass

    def _save(self) -> None:
        payload = {key: getattr(self, key) for key in ("music", "memories", "preferences", "briefing_schedule", "briefings", "network_telemetry", "grace_settings")}
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

