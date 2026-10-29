"""Check configured HTTP health endpoints without starting GRACE integrations."""
import argparse
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


def check(service):
    if not service.get("enabled", True):
        return {"name": service["name"], "status": "disabled"}
    start = time.monotonic()
    try:
        request = urllib.request.Request(service["url"], method="GET")
        with urllib.request.urlopen(request, timeout=3) as response:
            status = response.status
        result = {"name": service["name"], "status": "healthy", "http_status": status}
    except urllib.error.HTTPError as error:
        result = {"name": service["name"], "status": "degraded", "http_status": error.code}
    except (OSError, urllib.error.URLError, ValueError) as error:
        result = {"name": service["name"], "status": "unavailable", "error": str(error)}
    result.update(latency_ms=round((time.monotonic() - start) * 1000),
                  checked_at=datetime.now(timezone.utc).isoformat())
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    args = parser.parse_args()
    checks = [check(service) for service in json.loads(args.config.read_text())["services"]]
    active = [item for item in checks if item["status"] != "disabled"]
    overall = "unknown" if not active else "healthy" if all(item["status"] == "healthy" for item in active) else "degraded"
    print(json.dumps({"status": overall, "checks": checks,
                      "scope": "HTTP availability only; database, models, and host metrics need their own checks."}, indent=2))


if __name__ == "__main__":
    main()
