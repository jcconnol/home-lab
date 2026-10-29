"""Hardware-free checks for garage persistence, isolation, and game rules."""
import importlib.util
import json
import random
import sqlite3
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
GARAGE = ROOT / "garage"


def load(folder):
    path = GARAGE / folder / "run.py"
    spec = importlib.util.spec_from_file_location(folder.replace("/", "_").replace("-", "_"), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cli(folder, *arguments):
    return subprocess.run([sys.executable, str(GARAGE / folder / "run.py"), *map(str, arguments)],
                          capture_output=True, text=True, timeout=15, check=True)


@contextmanager
def serving(handler):
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def http(url, token, data=None):
    request = urllib.request.Request(url, data=json.dumps(data).encode() if data is not None else None,
                                     headers={"Authorization": "Bearer " + token,
                                              "Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=3) as response:
        return json.load(response)


def test_terrarium_survives_restart(tmp_path):
    path = tmp_path / "state.json"
    first = json.loads(cli("garage-dashboard/terrarium", "--state", path, "--ticks", 5, "--seed", 1).stdout)
    second = json.loads(cli("garage-dashboard/terrarium", "--state", path, "--ticks", 0).stdout)
    assert first == second
    third = json.loads(cli("garage-dashboard/terrarium", "--state", path, "--ticks", 1).stdout)
    assert third["tick"] == 6


def test_terrarium_energy_and_population_stay_bounded():
    module = load("garage-dashboard/terrarium")
    state = {"tick": 0, "plants": 0, "next_id": 2,
             "creatures": [{"id": 1, "parent": None, "age": 0, "energy": 2}], "events": []}
    for _ in range(500):
        module.advance(state, random.Random(7))
        assert 0 <= state["plants"] <= 100
        assert all(creature["energy"] > 0 for creature in state["creatures"])
        assert len(state["events"]) <= 100


def test_anomalies_separate_sources_and_handle_stale_data():
    module = load("garage-dashboard/anomaly-observatory")
    now = datetime.now(timezone.utc)
    rows = [{"source": "weather", "location": "home", "metric": "temperature", "unit": "C",
             "timestamp": (now - timedelta(minutes=6-i)).isoformat(), "value": value}
            for i, value in enumerate([20, 20, 20, 20, 20, 35])]
    rows.append(dict(rows[-1], source="other-station"))
    results = module.detect(rows)
    assert results[0]["status"] == "anomaly"
    assert results[0]["baseline_stddev"] == 0
    assert results[1]["status"] == "unknown"
    assert module.detect(rows, max_age=1)[0]["status"] == "unknown"


def test_missing_apartment_entity_is_unknown():
    module = load("garage-dashboard/apartment-twin")
    result = module.build_twin({"rooms": [{"name": "garage", "devices": [{"entity_id": "light.absent"}]}]}, [], 60)
    assert result["rooms"][0]["devices"][0]["state"] == "unknown"
    assert result["read_only"] is True


def test_photo_import_is_idempotent_and_preserves_bytes(tmp_path):
    module = load("phones/photo-journal")
    source = tmp_path / "photo.jpg"
    source.write_bytes(b"original photo fixture")
    storage = tmp_path / "journal"
    first = module.ingest(storage, source, "phone-a", "robot", "2026-10-28T12:00:00Z")
    second = module.ingest(storage, source, "phone-a", "robot", "2026-10-28T12:00:00+00:00")
    assert first == second
    assert Path(first["original"]).read_bytes() == source.read_bytes()
    with sqlite3.connect(storage / "journal.sqlite") as db:
        assert db.execute("SELECT COUNT(*) FROM photos").fetchone()[0] == 1


def test_game_player_rejects_stale_or_unlisted_actions():
    module = load("phones/game-player")
    now = datetime.now(timezone.utc)
    observation = {"id": "frame", "captured_at": now.isoformat(), "allowed_actions": ["left"]}
    assert module.proposal(observation, "left", now, 5)["executed"] is False
    with pytest.raises(ValueError):
        module.proposal(observation, "right", now, 5)
    with pytest.raises(ValueError):
        module.proposal(observation, "left", now + timedelta(seconds=6), 5)


def test_mission_observations_append(tmp_path):
    db = tmp_path / "missions.sqlite"
    folder = "garage-dashboard/science-missions"
    cli(folder, "--db", db, "create", "Question?", "Prediction")
    cli(folder, "--db", db, "observe", 1, "First result")
    cli(folder, "--db", db, "observe", 1, "Second result")
    result = json.loads(cli(folder, "--db", db, "list").stdout)
    assert len(result[0]["observations"]) == 2


def test_mailbox_isolation_and_acknowledgments(tmp_path):
    module = load("phones/communication")
    database = tmp_path / "messages.sqlite"
    with sqlite3.connect(database) as db:
        db.execute("CREATE TABLE messages (id INTEGER PRIMARY KEY, sender TEXT, recipient TEXT, text TEXT, sent_at TEXT, acknowledged_at TEXT)")
    with serving(module.handler_factory(database, {"a": "a" * 32, "b": "b" * 32})) as url:
        with pytest.raises(urllib.error.HTTPError) as error:
            http(url + "/messages", "wrong")
        assert error.value.code == 401
        sent = http(url + "/messages", "a" * 32, {"recipient": "b", "text": "Inspect this"})
        assert http(url + "/messages", "a" * 32) == []
        assert http(url + "/messages", "b" * 32)[0]["sender"] == "a"
        with pytest.raises(urllib.error.HTTPError) as error:
            http(url + "/ack", "a" * 32, {"id": sent["id"]})
        assert error.value.code == 404
        http(url + "/ack", "b" * 32, {"id": sent["id"]})
        assert http(url + "/sent", "a" * 32)[0]["acknowledged_at"]
    with serving(module.handler_factory(database, {"a": "a" * 32, "b": "b" * 32})) as url:
        assert len(http(url + "/messages", "b" * 32)) == 1


def test_battle_hides_moves_and_rejects_duplicate():
    module = load("phones/battle-arena")
    state = module.initial_state()
    pending = module.submit(state, "a", "strike")
    assert state["pending"] == {}
    assert "pending" not in module.public_state(pending, "b")
    assert module.public_state(pending, "b")["submitted"] is False
    with pytest.raises(ValueError):
        module.submit(pending, "a", "guard")
    result = module.submit(pending, "b", "guard")
    assert result["players"]["b"]["hp"] == 11
    assert result["players"]["a"]["energy"] == 1
    with pytest.raises(ValueError):
        module.submit(result, "a", "strike")


def test_battle_simultaneous_knockout_draws():
    module = load("phones/battle-arena")
    state = module.initial_state()
    for player in state["players"].values():
        player["hp"] = 4
    state = module.submit(module.submit(state, "a", "strike"), "b", "strike")
    assert state["winner"] == "draw"
    with pytest.raises(ValueError):
        module.submit(state, "a", "charge")


def test_battle_http_persistence_and_full_match(tmp_path):
    module = load("phones/battle-arena")
    path = tmp_path / "match.json"
    tokens = {"a": "a" * 32, "b": "b" * 32}
    with serving(module.handler_factory(path, tokens)) as url:
        with pytest.raises(urllib.error.HTTPError) as error:
            http(url + "/state", "wrong")
        assert error.value.code == 401
        http(url + "/action", tokens["a"], {"round": 1, "action": "strike"})
    with serving(module.handler_factory(path, tokens)) as url:
        assert http(url + "/state", tokens["a"])["submitted"] is True
        opponent_view = http(url + "/state", tokens["b"])
        assert "pending" not in opponent_view
        assert opponent_view["history"] == []
        assert opponent_view["submitted"] is False
        http(url + "/action", tokens["b"], {"round": 1, "action": "charge"})
        with pytest.raises(urllib.error.HTTPError) as error:
            http(url + "/action", tokens["a"], {"round": 1, "action": "guard"})
        assert error.value.code == 400
        for _ in range(49):
            state = http(url + "/state", tokens["a"])
            if state["winner"] is not None:
                break
            action = "strike" if state["players"]["a"]["energy"] >= 2 else "charge"
            http(url + "/action", tokens["a"], {"round": state["round"], "action": action})
            http(url + "/action", tokens["b"], {"round": state["round"], "action": "charge"})
        final = http(url + "/state", tokens["a"])
        assert final["winner"] == "a"
        assert len(final["history"]) >= 3
    assert json.loads(path.read_text())["winner"] == "a"


def test_timeline_sorts_absolute_instants(tmp_path):
    path = tmp_path / "events.json"
    path.write_text(json.dumps([{"timestamp": "2026-01-01T10:00:00+02:00", "source": "first"},
                                {"timestamp": "2026-01-01T09:00:00Z", "source": "second"}]))
    events = json.loads(cli("garage-dashboard/time-machine", path).stdout)["events"]
    assert [event["source"] for event in events] == ["first", "second"]


def test_signal_detective_respects_window_and_sources():
    module = load("garage-dashboard/signal-detective")
    events = [{"timestamp": f"2026-01-01T00:{minute}:00Z", "source": source}
              for minute, source in [("00", "a"), ("00", "a"), ("01", "b"), ("05", "c")]]
    assert len(module.correlate(events, 60)) == 2


@pytest.mark.parametrize("folder,arguments", [
    ("anomaly-observatory", ["sample.json"]),
    ("network-radar", ["sample.json"]),
    ("grace-health", ["sample.json"]),
    ("apartment-twin", ["layout.sample.json", "states.sample.json"]),
    ("space-command", ["sample.json"]),
    ("garage-universe", ["sample.json"]),
    ("signal-detective", ["sample.json"]),
    ("time-machine", ["sample.json"]),
])
def test_dashboard_sample_commands(folder, arguments):
    directory = GARAGE / "garage-dashboard" / folder
    result = cli("garage-dashboard/" + folder, *(directory / argument for argument in arguments))
    assert json.loads(result.stdout) is not None


def test_every_starter_has_help_and_readme():
    scripts = list(GARAGE.glob("*/*/run.py"))
    assert len(scripts) == 14
    for script in scripts:
        assert script.with_name("README.md").is_file()
        subprocess.run([sys.executable, str(script), "--help"], capture_output=True, check=True, timeout=5)
