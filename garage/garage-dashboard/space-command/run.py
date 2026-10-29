"""Schedule imported satellite passes; this does not compute orbital predictions."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def upcoming(passes, now):
    result = []
    for event in passes:
        start = datetime.fromisoformat(event["start"].replace("Z", "+00:00"))
        if start.tzinfo is None:
            raise ValueError("pass start must include timezone")
        seconds = (start - now).total_seconds()
        if seconds >= 0:
            result.append(dict(event, countdown_seconds=round(seconds),
                               visibility="unverified", simulated_mission=True))
    return sorted(result, key=lambda event: event["countdown_seconds"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("passes", type=Path, help="JSON array of name, start, source, location")
    args = parser.parse_args()
    print(json.dumps({"passes": upcoming(json.loads(args.passes.read_text()), datetime.now(timezone.utc)),
                      "note": "Imported schedule only. Live orbital calculations and visibility checks are not implemented."}, indent=2))


if __name__ == "__main__":
    main()
