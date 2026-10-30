"""Validate bounded browser jobs. Models and page text cannot expand permissions."""
from urllib.parse import urlsplit


def origin(url):
    value = urlsplit(url)
    if value.scheme not in ("http", "https") or not value.hostname or value.username or value.password:
        raise ValueError("Use a plain HTTP(S) URL without credentials")
    return value.scheme + "://" + value.netloc.lower()


def validate(spec, allowed_origins):
    if not isinstance(spec, dict) or not isinstance(spec.get("steps"), list) or not 1 <= len(spec["steps"]) <= 12:
        raise ValueError("A browser job needs 1..12 steps")
    if spec["steps"][0].get("action") != "goto":
        raise ValueError("The first step must navigate to an approved site")
    clean = []
    for step in spec["steps"]:
        action = step.get("action")
        if action not in ("goto", "click", "fill", "assert_text", "screenshot"):
            raise ValueError("Unsupported browser action")
        result = {"action": action}
        if action == "goto":
            url = step.get("url", "")
            if len(url) > 2000 or origin(url) not in allowed_origins:
                raise ValueError("Website origin is not approved")
            result["url"] = url
        if action in ("click", "fill"):
            selector = step.get("selector")
            if not isinstance(selector, str) or not 0 < len(selector) <= 500:
                raise ValueError("Selector required")
            result["selector"] = selector
        if action in ("fill", "assert_text"):
            value = step.get("text")
            if not isinstance(value, str) or len(value) > 2000:
                raise ValueError("Text must be at most 2000 characters")
            result["text"] = value
        clean.append(result)
    return {"steps": clean, "timeout_seconds": 60, "allowed_origins": list(allowed_origins)}
