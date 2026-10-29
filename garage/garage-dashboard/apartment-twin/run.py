"""Join a manually mapped apartment with a Home Assistant state export."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def build_twin(layout, states, max_age):
    by_id = {item["entity_id"]: item for item in states}
    rooms = []
    for room in layout["rooms"]:
        devices = []
        for position in room["devices"]:
            state = by_id.get(position["entity_id"])
            device = dict(position, state="unknown", freshness="missing")
            if state:
                observed = datetime.fromisoformat(state["last_updated"].replace("Z", "+00:00"))
                if observed.tzinfo is None:
                    raise ValueError("last_updated must include timezone")
                age = (datetime.now(timezone.utc) - observed).total_seconds()
                device.update(state=state["state"], last_updated=state["last_updated"],
                              attributes=state.get("attributes", {}),
                              freshness="fresh" if 0 <= age <= max_age else "stale")
            devices.append(device)
        rooms.append(dict(room, devices=devices))
    return {"rooms": rooms, "read_only": True,
            "note": "State age reflects last_updated in the supplied export, not a live connection heartbeat."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("layout", type=Path)
    parser.add_argument("states", type=Path)
    parser.add_argument("--max-age", type=float, default=3600)
    args = parser.parse_args()
    print(json.dumps(build_twin(json.loads(args.layout.read_text()), json.loads(args.states.read_text()), args.max_age), indent=2))


if __name__ == "__main__":
    main()
