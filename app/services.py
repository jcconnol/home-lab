import time
import re
import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from .config import settings
from .state import LabState


_weather_cache: tuple[float, dict] | None = None
_WEATHER_CODES = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "foggy",
    48: "freezing fog",
    51: "light drizzle",
    53: "drizzle",
    55: "heavy drizzle",
    61: "light rain",
    63: "rain",
    65: "heavy rain",
    71: "light snow",
    73: "snow",
    75: "heavy snow",
    80: "light showers",
    81: "showers",
    82: "heavy showers",
    95: "thunderstorm",
    96: "thunderstorm with hail",
    99: "thunderstorm with heavy hail",
}


def _without_emojis(text: str) -> str:
    return re.sub(r"[\U0001F000-\U0001FAFF\u2600-\u27BF]", "", text).strip()


def detect_once(state: LabState) -> str:
    """Run one optional YOLO pass; leave the service usable without hardware."""
    try:
        from ultralytics import YOLO
        import cv2

        camera = cv2.VideoCapture(settings.camera_index)
        ok, frame = camera.read()
        camera.release()
        if not ok:
            return "Camera is unavailable."
        model = YOLO(settings.yolo_model)
        result = model(frame, verbose=False)[0]
        objects = []
        for box in result.boxes:
            label = result.names[int(box.cls[0])]
            objects.append({"label": label, "confidence": round(float(box.conf[0]), 2)})
        state.update_objects(objects)
        return f"Detected {len(objects)} object(s)."
    except ImportError:
        return "Vision is not installed yet; using an empty scene."
    except Exception as exc:  # hardware/model errors should not kill the API
        state.add_event(f"Vision error: {type(exc).__name__}")
        return "Vision is currently unavailable."


async def ask_ollama(prompt: str, scene: dict) -> str:
    context = "\n".join(
        f'- {item["label"]} (confidence {item["confidence"]})'
        for item in scene["current_objects"]
    ) or "- nothing detected"
    memory_context = "\n".join(f'- {item["content"]}' for item in scene.get("memories", [])) or "- no saved memories"
    payload = {
        "model": settings.ollama_model,
        "stream": False,
        "prompt": (
            f"You are {settings.name}, a concise local home-lab assistant.\n"
            f"Your personality is {settings.personality}.\n"
            f"Current camera detections:\n{context}\n"
            f"Watch mode: {scene['watch_mode']}\nSaved user memories (use only when relevant):\n{memory_context}\nUser request: {prompt}"
        ),
    }
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(f"{settings.ollama_url}/api/generate", json=payload)
            response.raise_for_status()
            return _without_emojis(response.json().get("response", "Ollama returned no response."))
    except (httpx.HTTPError, ValueError):
        return "The local language model is unavailable. Start Ollama or use the scene endpoints."


async def ask_ollama_stream(prompt: str, scene: dict) -> AsyncIterator[str]:
    """Yield Ollama response text as it is generated."""
    context = "\n".join(f'- {item["label"]} (confidence {item["confidence"]})' for item in scene["current_objects"]) or "- nothing detected"
    memory_context = "\n".join(f'- {item["content"]}' for item in scene.get("memories", [])) or "- no saved memories"
    payload = {"model": settings.ollama_model, "stream": True, "prompt": f"You are {settings.name}, a concise local home-lab assistant.\nYour personality is {settings.personality}.\nCurrent camera detections:\n{context}\nWatch mode: {scene['watch_mode']}\nSaved user memories (use only when relevant):\n{memory_context}\nUser request: {prompt}"}
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream("POST", f"{settings.ollama_url}/api/generate", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        text = _without_emojis(json.loads(line).get("response", ""))
                    except (TypeError, ValueError):
                        continue
                    if text:
                        yield text
    except (httpx.HTTPError, ValueError):
        yield "The local language model is unavailable. Start Ollama or use the scene endpoints."


async def get_weather(force_refresh: bool = False) -> dict:
    """Return cached current weather from Open-Meteo, or a useful offline error."""
    global _weather_cache
    now = time.monotonic()
    if (
        _weather_cache
        and not force_refresh
        and now - _weather_cache[0] < settings.weather_cache_seconds
    ):
        return _weather_cache[1]
    if settings.weather_latitude == 0 and settings.weather_longitude == 0:
        return {"available": False, "error": "Set GRACE_WEATHER_LATITUDE and GRACE_WEATHER_LONGITUDE."}
    params = {
        "latitude": settings.weather_latitude,
        "longitude": settings.weather_longitude,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m",
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "timezone": "auto",
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get("https://api.open-meteo.com/v1/forecast", params=params)
            response.raise_for_status()
            payload = response.json()
        current = payload["current"]
        result = {
            "available": True,
            "location": settings.weather_location,
            "updated_at": current["time"],
            "temperature_f": current["temperature_2m"],
            "feels_like_f": current["apparent_temperature"],
            "humidity_percent": current["relative_humidity_2m"],
            "wind_mph": current["wind_speed_10m"],
            "condition": _WEATHER_CODES.get(current["weather_code"], "unknown conditions"),
        }
        _weather_cache = (now, result)
        return result
    except (httpx.HTTPError, KeyError, TypeError, ValueError):
        return {"available": False, "error": "Weather is temporarily unavailable."}


def weather_summary(weather: dict) -> str:
    if not weather.get("available"):
        return weather.get("error", "Weather is unavailable.")
    return (
        f"{weather['location']}: {weather['condition']}, "
        f"{weather['temperature_f']}°F and feels like {weather['feels_like_f']}°F, "
        f"humidity {weather['humidity_percent']}%, wind {weather['wind_mph']} mph."
    )


def frame_to_jpeg(frame: Any) -> bytes:
    import cv2

    ok, encoded = cv2.imencode(".jpg", frame)
    if not ok:
        raise ValueError("Could not encode camera frame")
    return encoded.tobytes()
