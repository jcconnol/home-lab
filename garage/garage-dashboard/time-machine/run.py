"""Merge recorded event arrays into a timezone-aware, filterable timeline."""
import argparse
import json
from datetime import datetime
from pathlib import Path


def instant(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("timestamps must include timezone")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--source")
    parser.add_argument("--since", type=instant)
    args = parser.parse_args()
    events = [event for path in args.files for event in json.loads(path.read_text())]
    events = [event for event in events if (not args.source or event["source"] == args.source)
              and (not args.since or instant(event["timestamp"]) >= args.since)]
    print(json.dumps({"events": sorted(events, key=lambda event: instant(event["timestamp"])),
                      "coverage": "Imported events only; gaps are not reconstructed."}, indent=2))


if __name__ == "__main__":
    main()
