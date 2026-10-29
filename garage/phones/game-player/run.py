"""Record proposed game actions for review; never drives hardware or a phone."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def proposal(observation, action, now, max_age):
    captured = datetime.fromisoformat(observation["captured_at"].replace("Z", "+00:00"))
    if captured.tzinfo is None:
        raise ValueError("captured_at must include timezone")
    age = (now - captured).total_seconds()
    if not 0 <= age <= max_age:
        raise ValueError("Observation is stale or future-dated; no action proposed")
    if action not in observation["allowed_actions"]:
        raise ValueError("Action is not allowed by this observation")
    return {"observation_id": observation["id"], "action": action,
            "proposed_at": now.isoformat(), "executed": False, "requires_manual_review": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("observation", type=Path)
    parser.add_argument("--action", required=True)
    parser.add_argument("--max-age", type=float, default=5)
    parser.add_argument("--log", type=Path, default=Path(__file__).parent / "runtime/proposals.jsonl")
    args = parser.parse_args()
    try:
        result = proposal(json.loads(args.observation.read_text()), args.action, datetime.now(timezone.utc), args.max_age)
    except ValueError as error:
        parser.error(str(error))
    args.log.parent.mkdir(parents=True, exist_ok=True)
    with args.log.open("a") as stream:
        stream.write(json.dumps(result) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
