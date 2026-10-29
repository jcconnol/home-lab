"""Probe only explicitly configured TCP services and report a network graph."""
import argparse
import json
import socket
from datetime import datetime, timezone
from pathlib import Path


def scan(config):
    nodes = []
    for service in config["services"]:
        try:
            with socket.create_connection((service["host"], service["port"]), timeout=2):
                status, reason = "reachable", None
        except OSError as error:
            status, reason = "unreachable", str(error)
        nodes.append(dict(service, status=status, error=reason,
                          checked_at=datetime.now(timezone.utc).isoformat()))
    return {"nodes": nodes, "edges": [dict(edge, kind="configured") for edge in config.get("relationships", [])],
            "note": "TCP reachability is not application health or observed traffic."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inventory", type=Path)
    args = parser.parse_args()
    print(json.dumps(scan(json.loads(args.inventory.read_text())), indent=2))


if __name__ == "__main__":
    main()
