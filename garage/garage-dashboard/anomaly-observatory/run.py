"""Detect departures in source-tagged readings, using historical baselines."""
import argparse
import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path


def detect(readings, threshold=3.0, max_age=3600):
    groups = {}
    for reading in readings:
        value = float(reading["value"])
        if not math.isfinite(value):
            raise ValueError("readings must contain finite values")
        key = (reading["source"], reading["location"], reading["metric"], reading["unit"])
        groups.setdefault(key, []).append(reading)
    results = []
    for key, rows in groups.items():
        rows.sort(key=lambda row: datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00")))
        current = rows[-1]
        observed = datetime.fromisoformat(current["timestamp"].replace("Z", "+00:00"))
        if observed.tzinfo is None:
            raise ValueError("timestamps must include timezone")
        age = (datetime.now(timezone.utc) - observed).total_seconds()
        values = [float(row["value"]) for row in rows[:-1]]
        result = {"source": key[0], "location": key[1], "metric": key[2], "unit": key[3],
                  "timestamp": current["timestamp"], "value": current["value"]}
        if age < -60 or age > max_age:
            result.update(status="unknown", explanation="Reading is stale or future-dated.")
        elif len(values) < 5:
            result.update(status="unknown", explanation="Need at least five earlier readings.")
        else:
            mean = statistics.mean(values)
            deviation = statistics.pstdev(values)
            difference = abs(float(current["value"]) - mean)
            unusual = difference > 0 if deviation == 0 else difference >= threshold * deviation
            result.update(status="anomaly" if unusual else "normal", baseline_mean=mean,
                          baseline_stddev=deviation,
                          explanation=f"Current reading differs from the {len(values)}-sample mean by {difference:.3g} {key[3]}. Cause is not established.")
        results.append(result)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("readings", type=Path, help="JSON array; see sample.json")
    parser.add_argument("--threshold", type=float, default=3)
    parser.add_argument("--max-age", type=float, default=3600)
    args = parser.parse_args()
    if args.threshold <= 0 or args.max_age <= 0:
        parser.error("threshold and max-age must be positive")
    print(json.dumps(detect(json.loads(args.readings.read_text()), args.threshold, args.max_age), indent=2))


if __name__ == "__main__":
    main()
