"""Turn network-radar results into a cosmetic planet scene description."""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("radar", type=Path, help="JSON output from network-radar")
    args = parser.parse_args()
    nodes = json.loads(args.radar.read_text())["nodes"]
    planets = [{"id": node["id"], "label": node.get("name", node["id"]),
                "orbit": index + 1, "color": "green" if node["status"] == "reachable" else "gray",
                "status": node["status"], "checked_at": node.get("checked_at")}
               for index, node in enumerate(nodes)]
    print(json.dumps({"cosmetic_mapping": True, "planets": planets}, indent=2))


if __name__ == "__main__":
    main()
