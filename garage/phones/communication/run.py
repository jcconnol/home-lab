"""Token-paired HTTP mailboxes with durable messages and recipient acknowledgments."""
import argparse
import hmac
import json
import os
import sqlite3
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


def handler_factory(database, tokens):
    class Handler(BaseHTTPRequestHandler):
        def reply(self, status, payload):
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def device(self):
            provided = self.headers.get("Authorization", "")
            return next((name for name, token in tokens.items()
                         if hmac.compare_digest(provided, "Bearer " + token)), None)

        def do_GET(self):
            device = self.device()
            if not device:
                return self.reply(401, {"error": "Device token required"})
            route = urlparse(self.path).path
            if route not in ("/messages", "/sent"):
                return self.reply(404, {"error": "Unknown route"})
            with sqlite3.connect(database) as db:
                db.row_factory = sqlite3.Row
                column = "recipient" if route == "/messages" else "sender"
                rows = db.execute(f"SELECT * FROM messages WHERE {column}=? ORDER BY id DESC LIMIT 100", (device,))
                self.reply(200, [dict(row) for row in rows])

        def do_POST(self):
            device = self.device()
            if not device:
                return self.reply(401, {"error": "Device token required"})
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 16384:
                    raise ValueError("Body must be 1..16384 bytes")
                data = json.loads(self.rfile.read(size))
                route = urlparse(self.path).path
                with sqlite3.connect(database) as db:
                    if route == "/messages":
                        recipient, text = data["recipient"], data["text"]
                        if recipient not in tokens or not isinstance(text, str) or not 0 < len(text) <= 4000:
                            raise ValueError("Known recipient and text of 1..4000 characters required")
                        cursor = db.execute("INSERT INTO messages(sender,recipient,text,sent_at) VALUES(?,?,?,?)",
                                            (device, recipient, text, datetime.now(timezone.utc).isoformat()))
                        result = {"id": cursor.lastrowid, "status": "queued", "note": "Delivery is not acknowledged yet"}
                    elif route == "/ack":
                        cursor = db.execute("UPDATE messages SET acknowledged_at=? WHERE id=? AND recipient=?",
                                            (datetime.now(timezone.utc).isoformat(), int(data["id"]), device))
                        if not cursor.rowcount:
                            return self.reply(404, {"error": "Message not found for this recipient"})
                        result = {"acknowledged": True}
                    else:
                        return self.reply(404, {"error": "Unknown route"})
                self.reply(200, result)
            except (ValueError, KeyError, TypeError) as error:
                self.reply(400, {"error": str(error)})

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8761)
    parser.add_argument("--db", type=Path, default=Path(__file__).parent / "runtime/messages.sqlite")
    args = parser.parse_args()
    tokens = json.loads(os.environ.get("GARAGE_DEVICE_TOKENS", "{}"))
    if not isinstance(tokens, dict) or len(tokens) < 2 or any(not isinstance(token, str) or len(token) < 24 for token in tokens.values()) or len(set(tokens.values())) != len(tokens):
        parser.error('Set GARAGE_DEVICE_TOKENS to JSON mapping at least two device names to unique tokens of 24+ characters')
    args.db.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(args.db) as db:
        db.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, sender TEXT, recipient TEXT, text TEXT, sent_at TEXT, acknowledged_at TEXT)")
    server = ThreadingHTTPServer((args.host, args.port), handler_factory(args.db, tokens))
    server.daemon_threads = True
    print(f"Mailboxes listening on {args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
