from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    name: str = os.getenv("GRACE_NAME", "G.R.A.C.E.")
    expansion: str = os.getenv(
        "GRACE_EXPANSION",
        "Generally Reliable Assistant for Computing and Engineering",
    )
    host: str = os.getenv("GRACE_HOST", "0.0.0.0")
    port: int = int(os.getenv("GRACE_PORT", "8000"))
    camera_index: int = int(os.getenv("GRACE_CAMERA_INDEX", "0"))
    detection_interval_seconds: float = float(
        os.getenv("GRACE_DETECTION_INTERVAL_SECONDS", "2")
    )
    yolo_model: str = os.getenv("GRACE_YOLO_MODEL", "yolo11n.pt")
    ollama_url: str = os.getenv("GRACE_OLLAMA_URL", "http://127.0.0.1:11434")
    ollama_model: str = os.getenv("GRACE_OLLAMA_MODEL", "qwen2.5:7b")
    tts_enabled: bool = os.getenv("GRACE_TTS_ENABLED", "false").lower() == "true"


settings = Settings()

