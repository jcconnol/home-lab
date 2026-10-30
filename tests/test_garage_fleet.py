"""Device-independent integration tests for the installable fleet software."""
import base64
import hashlib
import importlib.util
import io
import json
import time
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from http.server import BaseHTTPRequestHandler
from pathlib import Path

import pytest

pytest.importorskip("chess")
from PIL import Image
from test_garage_projects import GARAGE, http, load, serving


def file_module(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def fleet(tmp_path):
    hub = load("phones/hub")
    store = hub.Store(tmp_path)
    a, b = store.pair("phone-a"), store.pair("phone-b")
    store.heartbeat(a["id"], {"platform": "test"})
    store.heartbeat(b["id"], {"platform": "test"})
    return hub, store, a, b


def test_pairing_sessions_and_persistence(fleet):
    hub, store, a, b = fleet
    assert store.identity(a["token"]) == a["id"]
    assert store.identity("invalid") is None
    session = store.login(a["token"])
    assert store.identity(session, session=True) == a["id"]
    assert hub.Store(store.root).identity(session, session=True) == a["id"]
    store.logout(session)
    assert store.identity(session, session=True) is None
    with pytest.raises(ValueError):
        store.pair("phone-a")
    with serving(hub.handler_factory(store)) as url:
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
        login = urllib.request.Request(url + "/api/login", data=json.dumps({"token": a["token"]}).encode(), headers={"Content-Type": "application/json"})
        with opener.open(login) as response:
            assert response.status == 200
        with opener.open(url + "/api/state") as response:
            assert json.load(response)["you"] == a["id"]
        logout = urllib.request.Request(url + "/api/logout", data=b"{}", headers={"Content-Type": "application/json"})
        with opener.open(logout) as response:
            assert response.status == 200
        with pytest.raises(urllib.error.HTTPError) as error:
            opener.open(url + "/api/state")
        assert error.value.code == 401


def test_original_photo_roundtrip_and_deduplication(fleet):
    _, store, a, _ = fleet
    image = io.BytesIO()
    Image.new("RGB", (10, 10), "green").save(image, format="PNG")
    raw = image.getvalue()
    data = {"image": base64.b64encode(raw).decode(), "project": "robot", "captured_at": "2026-10-28T12:00:00Z"}
    first = store.add_photo(a["id"], data)
    second = store.add_photo(a["id"], data)
    assert first["id"] == second["id"]
    assert store.photo(first["digest"])[0] == raw
    with pytest.raises(OSError):
        store.add_photo(a["id"], dict(data, image=base64.b64encode(b"not an image").decode()))


def test_message_retry_and_recipient_ack(fleet):
    _, store, a, b = fleet
    message = {"id": "retry-id", "recipient": b["id"], "text": "hello"}
    store.send_message(a["id"], message)
    store.send_message(a["id"], message)
    assert len(store.messages(a["id"])) == 1
    with pytest.raises(ValueError):
        store.acknowledge(a["id"], "retry-id")
    store.acknowledge(b["id"], "retry-id")
    assert store.messages(a["id"])[0]["acknowledged_at"]


def test_two_devices_resolve_hidden_battle(fleet):
    _, store, a, b = fleet
    match = store.create_match(a["id"], "battle")["id"]
    store.join(b["id"], match)
    store.act(a["id"], {"id": match, "round": 1, "action": "strike"})
    view = store.public_match(store.match(match), b["id"])
    assert "pending" not in view["data"]
    assert view["data"]["history"] == []
    result = store.act(b["id"], {"id": match, "round": 1, "action": "guard"})
    assert result["data"]["players"]["b"]["hp"] == 11


def test_chess_legal_game_and_pgn(fleet):
    _, store, a, b = fleet
    match = store.create_match(a["id"], "chess")["id"]
    store.join(b["id"], match)
    with pytest.raises(ValueError):
        store.act(a["id"], {"id": match, "move": "e2e5"})
    for device, move in [(a, "f2f3"), (b, "e7e5"), (a, "g2g4"), (b, "d8h4")]:
        view = store.act(device["id"], {"id": match, "move": move})
    assert view["data"]["winner"] == "1"
    assert "Qh4#" in view["data"]["pgn"]


def test_chess_timeout_and_wrong_turn(fleet):
    _, store, a, b = fleet
    match_id = store.create_match(a["id"], "chess")["id"]
    store.join(b["id"], match_id)
    with pytest.raises(ValueError):
        store.act(b["id"], {"id": match_id, "move": "e7e5"})
    match = store.match(match_id)
    match["state"]["turn_started"] = time.time() - 301
    store.update_match(match)
    assert store.public_match(store.match(match_id), a["id"])["data"]["winner"] == "1"


def test_distributed_layers_verify_reference(fleet):
    _, store, a, b = fleet
    match = store.create_match(a["id"], "network")["id"]
    store.join(b["id"], match)
    with pytest.raises(ValueError):
        store.act(b["id"], {"id": match, "stage": 0, "values": [1, 2, 3, 4]})
    for player in (a, b):
        task = store.public_match(store.match(match), player["id"])["data"]["task"]
        output = store.network.layer(task["input"], task["layer"])
        view = store.act(player["id"], {"id": match, "stage": task["stage"], "values": output})
    assert view["data"]["finished"] is True
    assert view["data"]["values"] == view["data"]["reference"]


def test_throughput_integrity_and_stop(fleet):
    _, store, a, b = fleet
    match = store.benchmark(a["id"], b["id"])["id"]
    raw = b"verified bytes" * 100
    chunk = store.chunk(a["id"], {"id": match, "data": base64.b64encode(raw).decode()})["id"]
    with pytest.raises(ValueError):
        store.receive_chunk(a["id"], chunk)
    received = store.receive_chunk(b["id"], chunk)
    assert base64.b64decode(received["data"]) == raw
    store.ack_chunk(b["id"], {"id": chunk, "sha256": hashlib.sha256(raw).hexdigest()})
    assert store.benchmarks(a["id"])[0]["acknowledged"] == len(raw)
    store.stop_benchmark(b["id"], match)
    with pytest.raises(ValueError):
        store.chunk(a["id"], {"id": match, "data": base64.b64encode(raw).decode()})


def test_operator_job_lease_and_origin_permissions(fleet):
    _, store, a, b = fleet
    store.config["allowed_origins"] = ["http://127.0.0.1:8790"]
    with pytest.raises(ValueError):
        store.create_job(a["id"], {"device": b["id"], "spec": {"steps": [{"action": "goto", "url": "https://unapproved.example"}]}})
    identifier = store.create_job(a["id"], {"device": b["id"], "spec": {"steps": [{"action": "goto", "url": "http://127.0.0.1:8790/lab/page"}]}})["id"]
    assert store.claim_job(a["id"])["job"] is None
    assert store.claim_job(b["id"])["job"]["id"] == identifier
    assert store.claim_job(b["id"])["job"] is None
    store.finish_job(b["id"], {"id": identifier, "result": {"status": "passed"}})
    assert store.jobs()[0]["state"] == "passed"


def test_hub_http_and_bounded_lab(fleet):
    hub, store, a, _ = fleet
    with serving(hub.handler_factory(store)) as url:
        with pytest.raises(urllib.error.HTTPError) as error:
            http(url + "/api/state", "wrong")
        assert error.value.code == 401
        assert http(url + "/api/state", a["token"])["you"] == a["id"]
        lab = http(url + "/api/lab/start", a["token"], {})
        assert http(url + "/api/lab/request", a["token"], {"id": lab["id"]})["synthetic_fault"] is False
        with pytest.raises(urllib.error.HTTPError) as error:
            http(url + "/api/lab/request", a["token"], {"id": lab["id"]})
        assert error.value.code == 429
        http(url + "/api/lab/stop", a["token"], {"id": lab["id"]})
        with pytest.raises(urllib.error.HTTPError):
            http(url + "/api/lab/request", a["token"], {"id": lab["id"]})


def test_live_sources_cache_failures_and_noaa_formats(tmp_path):
    collectors = file_module(GARAGE / "garage-dashboard/collectors.py")
    calls = []
    def fetch(url):
        calls.append(url)
        return [["time_tag", "Kp"], ["2026-10-29T00:00:00", "5.3"]]
    app = collectors.Collectors({}, tmp_path, fetch)
    assert app.geomagnetic()["readings"][0]["value"] == 5.3
    first = app.cached("noaa", app.geomagnetic)
    app.cached("noaa", app.geomagnetic)
    assert len(calls) == 2
    app.cache["noaa"]["attempt"] = 0
    def failure():
        raise OSError("offline")
    second = app.cached("noaa", failure)
    assert second["status"] == "error" and second["stale"] is True
    assert second["data"] == first["data"]


def test_live_weather_and_air_have_historical_context(tmp_path):
    collectors = file_module(GARAGE / "garage-dashboard/collectors.py")
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    names = ["temperature_2m", "pressure_msl", "wind_speed_10m", "pm2_5", "us_aqi"]
    fixture = {"current": {"time": now.isoformat(), **dict.fromkeys(names, 20)}, "hourly_units": dict.fromkeys(names, "test-unit"),
               "hourly": {"time": [(now-timedelta(hours=i)).isoformat() for i in range(24, 0, -1)], **{name: [10]*24 for name in names}}}
    app = collectors.Collectors({"location": {"latitude": 0, "longitude": 0}}, tmp_path, lambda url: fixture)
    assert len(app.weather()["readings"]) == 75
    assert len(app.air()["readings"]) == 50


def test_home_assistant_live_state(tmp_path, monkeypatch):
    module = load("garage-dashboard")
    monkeypatch.setenv("TEST_HA_KEY", "private-test-key")
    app = module.Dashboard({"live": {"enabled": True, "weather": False, "air": False, "earthquakes": False, "geomagnetic": False,
                                     "home_assistant": {"enabled": True, "url": "http://home-assistant.test", "token_env": "TEST_HA_KEY", "rooms": {"Living room": ["light.test"]}}}}, tmp_path)
    def fetch(url, headers):
        assert headers["Authorization"] == "Bearer private-test-key"
        return [{"entity_id": "light.test", "state": "on", "last_updated": "2026-01-01T00:00:00Z", "attributes": {"brightness": 128}}]
    app.collectors.fetch = fetch
    app.collect()
    room = app.snapshot()["modules"]["twin"]["data"]["rooms"][0]
    assert room["name"] == "Living room"
    assert room["devices"][0]["freshness"] == "fresh"


def test_operator_plan_rejects_executable_actions(fleet):
    _, store, _, _ = fleet
    jobs = file_module(GARAGE / "phones/fleet-operator/jobs.py")
    with pytest.raises(ValueError):
        jobs.validate({"steps": [{"action": "goto", "url": "http://test.local"}, {"action": "evaluate", "code": "fetch('/secret')"}]}, ["http://test.local"])


def test_model_proposals_are_validated_and_do_not_execute(fleet):
    hub, store, a, b = fleet
    answer = {"action": "e2e4"}
    class Model(BaseHTTPRequestHandler):
        def do_POST(self):
            request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            assert request["stream"] is False
            raw = json.dumps({"message": {"content": json.dumps(answer)}}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
    match = store.create_match(a["id"], "chess")["id"]
    store.join(b["id"], match)
    with serving(Model) as model_url, serving(hub.handler_factory(store)) as url:
        store.config["model"] = {"url": model_url, "name": "fixture"}
        proposed = http(url + "/api/model/move", a["token"], {"id": match})
        assert proposed["action"] == "e2e4"
        assert store.match(match)["state"]["moves"] == []
        answer["action"] = "run shell command"
        with pytest.raises(urllib.error.HTTPError) as error:
            http(url + "/api/model/move", a["token"], {"id": match})
        assert error.value.code == 400
        assert store.match(match)["state"]["moves"] == []
