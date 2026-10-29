"""Two-agent simultaneous-turn arena with persistent state and token pairing."""
import argparse
import copy
import hmac
import json
import os
import random
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ACTIONS = ("strike", "guard", "charge", "repair")


def initial_state():
    return {"round": 1, "players": {name: {"hp": 12, "energy": 3} for name in ("a", "b")},
            "pending": {}, "winner": None, "history": []}


def submit(state, player, action):
    """Return a new state; invalid moves never mutate the original."""
    if player not in ("a", "b") or action not in ACTIONS:
        raise ValueError("Unknown player or action")
    if state["winner"] is not None:
        raise ValueError("Match has finished")
    if player in state["pending"]:
        raise ValueError("Already submitted for this round")
    cost = {"strike": 2, "repair": 3}.get(action, 0)
    if state["players"][player]["energy"] < cost:
        raise ValueError("Not enough energy")
    result = copy.deepcopy(state)
    result["pending"][player] = action
    if len(result["pending"]) < 2:
        return result
    moves = result["pending"]
    for name, move in moves.items():
        stats = result["players"][name]
        stats["energy"] -= {"strike": 2, "repair": 3}.get(move, 0)
        if move == "charge":
            stats["energy"] = min(5, stats["energy"] + 2)
        if move == "repair":
            stats["hp"] = min(12, stats["hp"] + 2)
    for name, move in moves.items():
        target = "b" if name == "a" else "a"
        if move == "strike":
            damage = 1 if moves[target] == "guard" else 4
            result["players"][target]["hp"] = max(0, result["players"][target]["hp"] - damage)
    alive = [name for name, stats in result["players"].items() if stats["hp"] > 0]
    if len(alive) < 2:
        result["winner"] = alive[0] if alive else "draw"
    elif result["round"] >= 50:
        hp = result["players"]
        result["winner"] = "draw" if hp["a"]["hp"] == hp["b"]["hp"] else max(hp, key=lambda name: hp[name]["hp"])
    result["history"].append({"round": result["round"], "actions": dict(moves),
                              "players": copy.deepcopy(result["players"])})
    result["round"] += 1
    result["pending"] = {}
    return result


def public_state(state, player):
    return {"round": state["round"], "players": state["players"], "winner": state["winner"],
            "history": state["history"], "you": player,
            "submitted": player in state["pending"],
            "waiting_count": len(state["pending"]), "allowed_actions": list(ACTIONS)}


def handler_factory(path, tokens):
    lock = threading.Lock()
    state = json.loads(path.read_text()) if path.exists() else initial_state()

    class Handler(BaseHTTPRequestHandler):
        def reply(self, code, data):
            payload = json.dumps(data).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def player(self):
            provided = self.headers.get("Authorization", "")
            return next((name for name, token in tokens.items()
                         if hmac.compare_digest(provided, "Bearer " + token)), None)

        def do_GET(self):
            player = self.player()
            if not player:
                return self.reply(401, {"error": "Player token required"})
            if self.path != "/state":
                return self.reply(404, {"error": "Unknown route"})
            with lock:
                self.reply(200, public_state(state, player))

        def do_POST(self):
            nonlocal state
            player = self.player()
            if not player:
                return self.reply(401, {"error": "Player token required"})
            if self.path != "/action":
                return self.reply(404, {"error": "Unknown route"})
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 1024:
                    raise ValueError("Body must be 1..1024 bytes")
                data = json.loads(self.rfile.read(size))
                with lock:
                    if data["round"] != state["round"]:
                        raise ValueError("Stale round; fetch /state again")
                    next_state = submit(state, player, data["action"])
                    path.parent.mkdir(parents=True, exist_ok=True)
                    temporary = path.with_suffix(".tmp")
                    temporary.write_text(json.dumps(next_state))
                    temporary.replace(path)
                    state = next_state
                    self.reply(200, public_state(state, player))
            except (ValueError, KeyError, TypeError) as error:
                self.reply(400, {"error": str(error)})

    return Handler


def request(url, token, data=None):
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, headers={"Authorization": "Bearer " + token,
                                                        "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8762)
    serve.add_argument("--state", type=Path, default=Path(__file__).parent / "runtime/match.json")
    bot = commands.add_parser("bot")
    bot.add_argument("--url", default="http://127.0.0.1:8762")
    bot.add_argument("--seed", type=int)
    bot.add_argument("--max-wait", type=float, default=120, help="Stop after this many seconds without a new round")
    args = parser.parse_args()
    if args.command == "serve":
        tokens = {name: os.environ.get("BATTLE_TOKEN_" + name.upper(), "") for name in ("a", "b")}
        if any(len(token) < 24 for token in tokens.values()) or tokens["a"] == tokens["b"]:
            parser.error("Set unique BATTLE_TOKEN_A and BATTLE_TOKEN_B, each 24+ characters")
        server = ThreadingHTTPServer((args.host, args.port), handler_factory(args.state, tokens))
        server.daemon_threads = True
        print(f"Arena listening on {args.host}:{args.port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
    else:
        token = os.environ.get("BATTLE_TOKEN", "")
        if not token:
            parser.error("Set BATTLE_TOKEN to this player's token")
        rng = random.Random(args.seed)
        deadline = time.monotonic() + args.max_wait
        previous_round = None
        while time.monotonic() < deadline:
            state = request(args.url.rstrip("/") + "/state", token)
            if state["winner"] is not None:
                print(json.dumps(state))
                return
            if state["round"] != previous_round:
                deadline = time.monotonic() + args.max_wait
                previous_round = state["round"]
            if not state["submitted"]:
                stats = state["players"][state["you"]]
                choices = ["guard", "charge"]
                if stats["energy"] >= 2:
                    choices.append("strike")
                if stats["energy"] >= 3 and stats["hp"] < 12:
                    choices.append("repair")
                action = rng.choice(choices)
                result = request(args.url.rstrip("/") + "/action", token,
                                 {"round": state["round"], "action": action})
                print(json.dumps({"round": state["round"], "action": action, "winner": result["winner"]}), flush=True)
            time.sleep(0.1)
        raise SystemExit("Opponent stalled; stopped without inventing moves")


if __name__ == "__main__":
    main()
