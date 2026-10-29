"""Import original phone photos into a content-addressed local project journal."""
import argparse
import hashlib
import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def ingest(root, source, device, project, captured_at):
    captured = datetime.fromisoformat(captured_at.replace("Z", "+00:00"))
    if captured.tzinfo is None:
        raise ValueError("capture timestamp must include timezone")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    originals = root / "originals"
    originals.mkdir(parents=True, exist_ok=True)
    destination = originals / digest
    if not destination.exists():
        temporary = originals / (digest + ".tmp")
        shutil.copyfile(source, temporary)
        temporary.replace(destination)
    with sqlite3.connect(root / "journal.sqlite") as db:
        db.execute("CREATE TABLE IF NOT EXISTS photos (id INTEGER PRIMARY KEY, digest TEXT, device TEXT, project TEXT, captured_at TEXT, uploaded_at TEXT, original_name TEXT, UNIQUE(digest,device,project,captured_at))")
        db.execute("INSERT OR IGNORE INTO photos(digest,device,project,captured_at,uploaded_at,original_name) VALUES(?,?,?,?,?,?)",
                   (digest, device, project, captured.isoformat(), datetime.now(timezone.utc).isoformat(), source.name))
    return {"digest": digest, "original": str(destination)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storage", type=Path, default=Path(__file__).parent / "runtime")
    commands = parser.add_subparsers(dest="command", required=True)
    add = commands.add_parser("import")
    add.add_argument("file", type=Path)
    add.add_argument("--device", required=True)
    add.add_argument("--project", required=True)
    add.add_argument("--captured-at", required=True)
    listing = commands.add_parser("list")
    listing.add_argument("--project")
    args = parser.parse_args()
    if args.command == "import":
        print(json.dumps(ingest(args.storage, args.file, args.device, args.project, args.captured_at)))
    elif not (args.storage / "journal.sqlite").exists():
        print("[]")
    else:
        with sqlite3.connect(args.storage / "journal.sqlite") as db:
            db.row_factory = sqlite3.Row
            query = "SELECT * FROM photos"
            rows = db.execute(query + " WHERE project=? ORDER BY captured_at" if args.project else query + " ORDER BY captured_at",
                              (args.project,) if args.project else ())
            print(json.dumps([dict(row) for row in rows], indent=2))


if __name__ == "__main__":
    main()
