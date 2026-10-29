"""Find contemporaneous events from different sources; no causal claims."""
import argparse
import json
from datetime import datetime
from pathlib import Path


def correlate(events, window):
    def timestamp(event):
        result = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
        if result.tzinfo is None:
            raise ValueError("timestamps must include timezone")
        return result
    ordered = sorted(events, key=timestamp)
    pairs = []
    for index, first in enumerate(ordered):
        for second in ordered[index + 1:]:
            seconds = (timestamp(second) - timestamp(first)).total_seconds()
            if seconds > window:
                break
            if first["source"] != second["source"]:
                pairs.append({"events": [first, second], "separation_seconds": seconds,
                              "explanation": "Observed close together; cause is unknown."})
    return pairs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("events", type=Path)
    parser.add_argument("--window", type=float, default=60)
    args = parser.parse_args()
    if args.window < 0:
        parser.error("window must be nonnegative")
    print(json.dumps(correlate(json.loads(args.events.read_text()), args.window), indent=2))


if __name__ == "__main__":
    main()
