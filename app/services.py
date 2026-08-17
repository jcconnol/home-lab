import time
import re
import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from .config import settings
from .state import LabState


_weather_cache: tuple[float, dict] | None = None
_ASSISTANT_STYLE = (
    "Be composed, highly competent, discreet, and quietly confident, like a refined cinematic household assistant. "
    "Use formal but warm language, subtle dry wit only when it helps, concise answers, and practical next steps. "
    "Never pretend certainty, never be theatrical, and never claim to have performed an action you did not perform."
)
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


def _without_thinking(text: str) -> str:
    """Hide model reasoning blocks that may be returned despite think=false."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.IGNORECASE | re.DOTALL)


def _clean_model_answer(text: str) -> str:
    """Return only the final answer when a model exposes its drafting process."""
    cleaned = _without_thinking(_without_emojis(text)).strip()
    # Some Qwen builds emit a closing marker without the opening marker.
    closing_marker = list(re.finditer(r"</think>", cleaned, flags=re.IGNORECASE))
    if closing_marker:
        cleaned = cleaned[closing_marker[-1].end():].strip()
    matches = list(re.finditer(r"(?im)^\s*(?:final\s+answer|answer)\s*:\s*", cleaned))
    if matches:
        cleaned = cleaned[matches[-1].end():].strip().strip('"')
    return cleaned


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


def _conversation_context(messages: list[dict] | None) -> str:
    if not messages:
        return "- no earlier messages in this conversation"
    return "\n".join(
        f"{('User' if item.get('role') == 'user' else 'G.R.A.C.E.')}: {item.get('content', '')}"
        for item in messages
        if item.get("role") in {"user", "assistant"} and item.get("content")
    ) or "- no earlier messages in this conversation"


async def ask_ollama(prompt: str, scene: dict, conversation: list[dict] | None = None) -> str:
    context = "\n".join(
        f'- {item["label"]} (confidence {item["confidence"]})'
        for item in scene["current_objects"]
    ) or "- nothing detected"
    memory_context = "\n".join(f'- {item["content"]}' for item in scene.get("memories", [])) or "- no saved memories"
    payload = {
        "model": settings.ollama_model,
        "stream": False,
        "think": False,
        "keep_alive": "30m",
        "prompt": (
            f"You are {settings.name}, a concise local home-lab assistant. Answer the user's request directly. Do not narrate generation, emit progress updates, or provide unsolicited status reports.\n"
            f"Your personality is {scene.get('grace_settings', {}).get('personality', settings.personality)}. "
            f"Humor is {scene.get('grace_settings', {}).get('humor', 'balanced')}; use either a direct or characterful response as fits the moment, not a mandatory status-and-joke pair. "
            f"Always be serious for warnings, security, and sensitive actions.\nBehavior guidance: {_ASSISTANT_STYLE}\n"
            f"Current camera detections:\n{context}\n"
            f"Watch mode: {scene['watch_mode']}\nSaved user memories (use only when relevant):\n{memory_context}\n"
            f"Earlier messages in this conversation:\n{_conversation_context(conversation)}\nUser request: {prompt}"
        ),
    }
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(300, connect=10)) as client:
            response = await client.post(f"{settings.ollama_url}/api/generate", json=payload)
            response.raise_for_status()
            return _clean_model_answer(response.json().get("response", "Ollama returned no response."))
    except (httpx.HTTPError, ValueError):
        return "The local language model is unavailable. Start Ollama or use the scene endpoints."


async def ask_ollama_stream(prompt: str, scene: dict, conversation: list[dict] | None = None) -> AsyncIterator[str]:
    """Yield visible response chunks as Ollama generates them."""
    context = "\n".join(f'- {item["label"]} (confidence {item["confidence"]})' for item in scene["current_objects"]) or "- nothing detected"
    memory_context = "\n".join(f'- {item["content"]}' for item in scene.get("memories", [])) or "- no saved memories"
    personality = scene.get("grace_settings", {})
    payload = {"model": settings.ollama_model, "stream": True, "think": False, "keep_alive": "30m", "prompt": f"You are {settings.name}, a concise local home-lab assistant. Answer the user's request directly. Do not narrate generation, emit progress updates, or provide unsolicited status reports.\nYour personality is {personality.get('personality', settings.personality)}. Humor is {personality.get('humor', 'balanced')}; use either a direct or characterful response as fits the moment, not a mandatory status-and-joke pair. Always be serious for warnings, security, and sensitive actions. Formality is {personality.get('formality', 'polished')} and response length is {personality.get('response_length', 'standard')}.\nBehavior guidance: {_ASSISTANT_STYLE}\nCurrent camera detections:\n{context}\nWatch mode: {scene['watch_mode']}\nSaved user memories (use only when relevant):\n{memory_context}\nEarlier messages in this conversation:\n{_conversation_context(conversation)}\nUser request: {prompt}"}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(300, connect=10)) as client:
            async with client.stream("POST", f"{settings.ollama_url}/api/generate", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        # Newer Ollama/Qwen streams can put reasoning in a
                        # separate `thinking` field even when think=false.
                        if chunk.get("thinking"):
                            continue
                        text = re.sub(r"[\U0001F000-\U0001FAFF\u2600-\u27BF]", "", chunk.get("response", ""))
                    except (TypeError, ValueError):
                        continue
                    if not text:
                        continue
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


def _smart_switch_configured() -> bool:
    entity_id = settings.smart_switch_entity_id
    return bool(
        settings.home_assistant_url
        and settings.home_assistant_token
        and (entity_id.startswith("switch.") or entity_id.startswith("light."))
    )


async def _home_assistant_request(method: str, path: str, **kwargs: Any) -> httpx.Response:
    """Send a request through Home Assistant's LAN hostname."""
    async with httpx.AsyncClient(timeout=10, trust_env=False) as client:
        response = await client.request(method, f"{settings.home_assistant_url}{path}", **kwargs)
        response.raise_for_status()
        return response


def _smart_switch_battery_entity_id() -> str:
    if settings.smart_switch_battery_entity_id:
        return settings.smart_switch_battery_entity_id
    entity_id = settings.smart_switch_entity_id
    if entity_id.startswith("switch."):
        return f"sensor.{entity_id[7:]}_battery"
    return ""


async def get_smart_switch() -> dict:
    """Read the configured switch state through Home Assistant's local API."""
    if not _smart_switch_configured():
        return {
            "available": False,
            "name": settings.smart_switch_name,
            "state": "unavailable",
            "message": "Configure the Home Assistant URL, token, and switch entity ID in .env.",
        }
    headers = {"Authorization": f"Bearer {settings.home_assistant_token}"}
    try:
        response = await _home_assistant_request(
            "GET", f"/api/states/{settings.smart_switch_entity_id}", headers=headers
        )
        payload = response.json()
        battery_level = None
        battery_entity_id = _smart_switch_battery_entity_id()
        if battery_entity_id:
            try:
                battery_response = await _home_assistant_request(
                    "GET", f"/api/states/{battery_entity_id}", headers=headers
                )
                battery_payload = battery_response.json()
                battery_value = battery_payload.get("state")
                if battery_value not in {None, "unknown", "unavailable"}:
                    try:
                        battery_level = float(battery_value)
                    except (TypeError, ValueError):
                        battery_level = battery_payload.get("attributes", {}).get("battery_level")
            except httpx.HTTPError:
                pass
        return {
            "available": payload.get("state") in {"on", "off"},
            "name": payload.get("attributes", {}).get("friendly_name") or settings.smart_switch_name,
            "state": payload.get("state", "unavailable"),
            "battery_level": battery_level,
            "message": "Connected through Home Assistant.",
        }
    except (httpx.HTTPError, TypeError, ValueError):
        return {
            "available": False,
            "name": settings.smart_switch_name,
            "state": "unavailable",
            "message": "Home Assistant or the configured switch is unavailable.",
        }


async def toggle_smart_switch() -> dict:
    """Toggle the configured switch, then return its confirmed state."""
    if not _smart_switch_configured():
        return await get_smart_switch()
    headers = {"Authorization": f"Bearer {settings.home_assistant_token}"}
    domain = settings.smart_switch_entity_id.split(".", 1)[0]
    try:
        await _home_assistant_request(
            "POST",
            f"/api/services/{domain}/toggle",
            headers=headers,
            json={"entity_id": settings.smart_switch_entity_id},
        )
    except httpx.HTTPError:
        return {
            "available": False,
            "name": settings.smart_switch_name,
            "state": "unavailable",
            "message": "Home Assistant could not toggle the switch.",
        }
    return await get_smart_switch()


def _light_configured(entity_id: str) -> bool:
    return bool(
        settings.home_assistant_url
        and settings.home_assistant_token
        and (entity_id.startswith("switch.") or entity_id.startswith("light."))
    )


async def get_light(entity_id: str, name: str) -> dict:
    """Read a configured light or switch from Home Assistant."""
    if not entity_id:
        return {"configured": False, "available": False, "name": name, "state": "not_configured", "message": "This light has not been configured yet."}
    if not _light_configured(entity_id):
        return {"configured": True, "available": False, "name": name, "state": "unavailable", "message": "Home Assistant is not configured for this light."}
    try:
        response = await _home_assistant_request(
            "GET",
            f"/api/states/{entity_id}",
            headers={"Authorization": f"Bearer {settings.home_assistant_token}"},
        )
        payload = response.json()
        return {
            "configured": True,
            "available": payload.get("state") in {"on", "off"},
            "name": payload.get("attributes", {}).get("friendly_name") or name,
            "state": payload.get("state", "unavailable"),
            "message": "Connected through Home Assistant.",
        }
    except (httpx.HTTPError, TypeError, ValueError):
        return {"configured": True, "available": False, "name": name, "state": "unavailable", "message": "Home Assistant or this light is unavailable."}


async def set_light(entity_id: str, name: str, on: bool) -> dict:
    """Set a configured Home Assistant light or switch, then confirm its state."""
    if not _light_configured(entity_id):
        return await get_light(entity_id, name)
    domain = entity_id.split(".", 1)[0]
    try:
        await _home_assistant_request(
            "POST",
            f"/api/services/{domain}/{'turn_on' if on else 'turn_off'}",
            headers={"Authorization": f"Bearer {settings.home_assistant_token}"},
            json={"entity_id": entity_id},
        )
    except httpx.HTTPError:
        return {"configured": True, "available": False, "name": name, "state": "unavailable", "message": "Home Assistant could not control this light."}
    return await get_light(entity_id, name)


async def toggle_light(entity_id: str, name: str) -> dict:
    current = await get_light(entity_id, name)
    if not current["available"]:
        return current
    return await set_light(entity_id, name, current["state"] != "on")


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
