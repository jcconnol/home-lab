from collections import deque
from datetime import datetime, timezone
from threading import Lock


class LabState:
    def __init__(self) -> None:
        self._lock = Lock()
        self.objects: list[dict] = []
        self.events: deque[dict] = deque(maxlen=100)
        self.watch_mode = False

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "current_objects": list(self.objects),
                "recent_events": list(self.events),
                "watch_mode": self.watch_mode,
            }

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

