from typing import Any

import httpx

from .config import settings
from .state import LabState


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
    payload = {
        "model": settings.ollama_model,
        "stream": False,
        "prompt": (
            f"You are {settings.name}, a concise local home-lab assistant.\n"
            f"Current camera detections:\n{context}\n"
            f"Watch mode: {scene['watch_mode']}\nUser request: {prompt}"
        ),
    }
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(f"{settings.ollama_url}/api/generate", json=payload)
            response.raise_for_status()
            return response.json().get("response", "Ollama returned no response.").strip()
    except (httpx.HTTPError, ValueError):
        return "The local language model is unavailable. Start Ollama or use the scene endpoints."


def frame_to_jpeg(frame: Any) -> bytes:
    import cv2

    ok, encoded = cv2.imencode(".jpg", frame)
    if not ok:
        raise ValueError("Could not encode camera frame")
    return encoded.tobytes()
