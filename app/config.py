from dataclasses import dataclass
import os

from dotenv import load_dotenv


load_dotenv()


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
    ollama_model: str = os.getenv("GRACE_OLLAMA_MODEL", "qwen3:4b")
    tts_enabled: bool = os.getenv("GRACE_TTS_ENABLED", "false").lower() == "true"
    personality: str = os.getenv(
        "GRACE_PERSONALITY",
        "composed, highly competent, discreet, quietly confident, warm but formal, subtly dry-witted, and honest about uncertainty; never use emojis",
    )
    weather_location: str = os.getenv("GRACE_WEATHER_LOCATION", "Home")
    weather_latitude: float = float(os.getenv("GRACE_WEATHER_LATITUDE", "0"))
    weather_longitude: float = float(os.getenv("GRACE_WEATHER_LONGITUDE", "0"))
    weather_cache_seconds: int = int(os.getenv("GRACE_WEATHER_CACHE_SECONDS", "900"))
    admin_username: str = os.getenv("GRACE_ADMIN_USERNAME", "admin")
    admin_password_hash: str = os.getenv("GRACE_ADMIN_PASSWORD_HASH", "")


settings = Settings()

