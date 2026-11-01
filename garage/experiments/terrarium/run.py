"""Persistent, discrete-time ecosystem. Each invocation advances explicit ticks."""
import argparse
import json
import random
from pathlib import Path


def advance(state, rng):
    state["tick"] += 1
    state["plants"] = min(100, state["plants"] + 5)
    survivors = []
    events = []
    for creature in state["creatures"]:
        creature["age"] += 1
        creature["energy"] -= 2
        if state["plants"] >= 2:
            state["plants"] -= 2
            creature["energy"] += 4
        if creature["energy"] <= 0 or creature["age"] >= 40:
            events.append({"type": "death", "id": creature["id"]})
            continue
        survivors.append(creature)
        if creature["energy"] >= 16 and rng.random() < 0.25:
            creature["energy"] -= 8
            child = {"id": state["next_id"], "parent": creature["id"],
                     "age": 0, "energy": 8}
            state["next_id"] += 1
            survivors.append(child)
            events.append({"type": "birth", "id": child["id"], "parent": creature["id"]})
    state["creatures"] = survivors
    state["events"] = (state["events"] + [dict(event, tick=state["tick"]) for event in events])[-100:]
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, default=Path(__file__).parent / "runtime/state.json")
    parser.add_argument("--ticks", type=int, default=1)
    parser.add_argument("--food", type=int, default=0, help="Additional plant energy, 0..100")
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()
    if not 0 <= args.ticks <= 10000 or not 0 <= args.food <= 100:
        parser.error("ticks must be 0..10000 and food 0..100")
    state = json.loads(args.state.read_text()) if args.state.exists() else {
        "tick": 0, "plants": 40, "next_id": 3,
        "creatures": [{"id": i, "parent": None, "age": 0, "energy": 10} for i in (1, 2)],
        "events": [],
    }
    state["plants"] = min(100, state["plants"] + args.food)
    rng = random.Random(args.seed)
    for _ in range(args.ticks):
        advance(state, rng)
    args.state.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.state.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, indent=2))
    temporary.replace(args.state)
    print(json.dumps(state))


if __name__ == "__main__":
    main()
