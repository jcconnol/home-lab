"""Opt-in public-source check; requires an explicitly chosen test location."""
import argparse
import importlib.util
import json
import threading
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--latitude", type=float, required=True)
    parser.add_argument("--longitude", type=float, required=True)
    parser.add_argument("--name", default="Public validation location")
    parser.add_argument("--output", type=Path, default=ROOT / "garage/runtime/observatory-validation")
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location("observatory", ROOT / "garage/garage-dashboard/run.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    args.output.mkdir(parents=True, exist_ok=True)
    app = module.Dashboard({}, args.output / "host")
    app.save_settings({"location": {"name": args.name, "latitude": args.latitude, "longitude": args.longitude, "timezone": "UTC"}})
    worker = threading.Thread(target=app.run, daemon=True)
    worker.start()
    previous, deadline = {}, time.monotonic() + 180
    try:
        while time.monotonic() < deadline:
            state = app.snapshot()
            statuses = {name: feed["status"] for name, feed in state["feeds"].items()}
            if statuses != previous:
                print(json.dumps(statuses), flush=True)
                previous = statuses
            if len(statuses) == 6 and all(status in ("live", "error") for status in statuses.values()):
                break
            time.sleep(.5)
        state = app.snapshot()
        (args.output / "live.json").write_text(json.dumps(state), encoding="utf-8")
        summary = {name: {"status": feed["status"], "error": feed.get("error"), "records": len(feed.get("data", {}).get("bodies", feed.get("data", {}).get("aircraft", [])))} for name, feed in state["feeds"].items()}
        print(json.dumps(summary), flush=True)
        if len(summary) != 6 or any(feed["status"] != "live" for feed in summary.values()):
            raise SystemExit(1)
    finally:
        app.stop.set()
        worker.join(2)


if __name__ == "__main__":
    main()
