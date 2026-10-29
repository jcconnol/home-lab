"""Persist predictions and observed outcomes as a small experiment notebook."""
import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path(__file__).parent / "runtime/missions.sqlite")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create")
    create.add_argument("question")
    create.add_argument("prediction")
    observe = commands.add_parser("observe")
    observe.add_argument("id", type=int)
    observe.add_argument("outcome")
    commands.add_parser("list")
    args = parser.parse_args()
    args.db.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(args.db) as db:
        db.row_factory = sqlite3.Row
        db.execute("CREATE TABLE IF NOT EXISTS missions (id INTEGER PRIMARY KEY, question TEXT, prediction TEXT, created_at TEXT)")
        db.execute("CREATE TABLE IF NOT EXISTS observations (id INTEGER PRIMARY KEY, mission_id INTEGER, outcome TEXT, observed_at TEXT)")
        now = datetime.now(timezone.utc).isoformat()
        if args.command == "create":
            cursor = db.execute("INSERT INTO missions(question,prediction,created_at) VALUES(?,?,?)", (args.question, args.prediction, now))
            print(json.dumps({"id": cursor.lastrowid}))
        elif args.command == "observe":
            if not db.execute("SELECT id FROM missions WHERE id=?", (args.id,)).fetchone():
                parser.error("mission does not exist")
            db.execute("INSERT INTO observations(mission_id,outcome,observed_at) VALUES(?,?,?)", (args.id, args.outcome, now))
            print(json.dumps({"recorded": True}))
        else:
            missions = [dict(row) for row in db.execute("SELECT * FROM missions ORDER BY id")]
            for mission in missions:
                mission["observations"] = [dict(row) for row in db.execute("SELECT * FROM observations WHERE mission_id=? ORDER BY id", (mission["id"],))]
            print(json.dumps(missions, indent=2))


if __name__ == "__main__":
    main()
