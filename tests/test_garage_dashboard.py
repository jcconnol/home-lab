"""Garage information-board contracts: setup, independent feeds, and real vectors."""
from datetime import datetime, timedelta, timezone
from http.cookiejar import CookieJar
import json
import threading
import time
import urllib.error
import urllib.request

import pytest

from test_garage_projects import GARAGE, http, load, serving


def dashboard(tmp_path, config=None):
    return load("garage-dashboard").Dashboard(config or {}, tmp_path)


LOCATION = {"name": "Test city", "latitude": 40, "longitude": -105, "timezone": "America/Denver"}


def test_no_games_or_ai_branding_in_the_information_board(tmp_path):
    existing = tmp_path / "terrarium.json"
    existing.write_text('{"old":"saved game"}')
    app = dashboard(tmp_path)
    app.collect()
    state = app.snapshot()
    assert state["configured"] is False
    assert state["feeds"] == {}
    assert "terrarium" not in state and "missions" not in state
    assert existing.read_text() == '{"old":"saved game"}'
    assert "GRACE" not in (GARAGE / "garage-dashboard/web/index.html").read_text()


def test_location_units_and_bodies_survive_restart(tmp_path):
    app = dashboard(tmp_path)
    app.save_settings({"location": LOCATION, "units": "metric", "aircraft_radius_nm": 20, "add_body": {"id": "1000036", "name": "Halley"}})
    restarted = dashboard(tmp_path)
    state = restarted.snapshot()
    assert state["configured"] is True
    assert state["settings"]["location"] == dict(LOCATION, region="")
    assert state["settings"]["units"] == "metric"
    assert state["settings"]["extra_bodies"][0]["name"] == "Halley"
    assert not (tmp_path / "terrarium.json").exists()


@pytest.mark.parametrize("value", [{"units": "kelvin"}, {"aircraft_radius_nm": 0}, {"aircraft_radius_nm": float("nan")},
                                   {"location": dict(LOCATION, latitude=100)}, {"location": dict(LOCATION, longitude=float("inf"))},
                                   {"add_body": {"id": "../secret", "name": "wrong"}}])
def test_invalid_settings_do_not_replace_saved_location(tmp_path, value):
    app = dashboard(tmp_path)
    app.save_settings({"location": LOCATION})
    before = app.settings_file.read_bytes()
    with pytest.raises((ValueError, TypeError)):
        app.save_settings(value)
    assert app.settings_file.read_bytes() == before


def test_location_search_returns_choices_not_an_assumed_home(tmp_path):
    app = dashboard(tmp_path)
    app.collector_module.fetch_json = lambda url: {"results": [dict(LOCATION, admin1="Colorado", country="United States")]}
    results = app.search_location("Test city")
    assert results[0]["region"] == "Colorado, United States"
    assert app.snapshot()["configured"] is False


def test_old_location_request_cannot_publish_after_settings_change(tmp_path):
    app = dashboard(tmp_path)
    app.save_settings({"location": LOCATION})
    entered, release = threading.Event(), threading.Event()
    def slow_weather():
        entered.set()
        release.wait(2)
        return {"old_city": True}
    app.collectors.weather = slow_weather
    worker = threading.Thread(target=app.collect_source, args=("weather",))
    worker.start()
    assert entered.wait(1)
    app.save_settings({"location": dict(LOCATION, name="New city", latitude=41)})
    release.set()
    worker.join(2)
    assert "weather" not in app.snapshot()["feeds"]


def test_sources_run_independently_and_stop(tmp_path):
    app = dashboard(tmp_path)
    app.save_settings({"location": LOCATION})
    entered, release, weather_ready = threading.Event(), threading.Event(), threading.Event()
    def source(name):
        if name == "solar_system":
            entered.set()
            release.wait(3)
        if name == "weather":
            weather_ready.set()
    app.collect_source = source
    worker = threading.Thread(target=app.run)
    worker.start()
    try:
        assert entered.wait(1)
        assert weather_ready.wait(1)
    finally:
        app.stop.set()
        release.set()
        worker.join(2)
    assert not worker.is_alive()


def test_routes_auth_and_cross_origin_settings(tmp_path):
    module = load("garage-dashboard")
    app = dashboard(tmp_path)
    with serving(module.handler_factory(app)) as url:
        assert http(url + "/api/status", "")["configured"] is False
        http(url + "/api/settings", "", {"location": LOCATION})
        for route in ("/", "/app.js", "/solar.js", "/board.css", "/style.css", "/land.json"):
            with urllib.request.urlopen(url + route) as response:
                assert response.status == 200
                assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
        request = urllib.request.Request(url + "/api/settings", data=b'{"units":"metric"}', headers={"Content-Type": "application/json", "Origin": "http://unrelated.example"})
        with pytest.raises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(request)
        assert error.value.code == 403
        assert app.settings["units"] == "imperial"
        with pytest.raises(urllib.error.HTTPError) as error:
            http(url + "/api/terrarium", "", {"action": "feed"})
        assert error.value.code == 404


def test_dashboard_login_and_cookie(tmp_path):
    module = load("garage-dashboard")
    app = dashboard(tmp_path)
    secret = "test-access-key-" * 3
    with serving(module.handler_factory(app, secret)) as url:
        with pytest.raises(urllib.error.HTTPError) as error:
            http(url + "/api/status", "")
        assert error.value.code == 401
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
        request = urllib.request.Request(url + "/api/login", data=json.dumps({"password": secret}).encode(), headers={"Content-Type": "application/json"})
        with opener.open(request) as response:
            assert "HttpOnly" in response.headers["Set-Cookie"]
        with opener.open(url + "/api/status") as response:
            assert json.load(response)["configured"] is False


def solar_module():
    return load("garage-dashboard").module("solar_system.py")


def vector_payload(rows):
    return {"signature": {"version": "1.3"}, "result": "$$SOE\n" + "\n".join(f"{jd}, A.D. timestamp, {x}, {y}, {z}, 0, 0, 0," for jd, x, y, z in rows) + "\n$$EOE"}


def test_horizons_vectors_use_exact_heliocentric_coordinates():
    module = solar_module()
    rows = module.parse_vectors(vector_payload([(2461343.5, -3.657034512911815, 3.857969541003422, .06564132947413473)]))
    assert rows[0]["xyz_au"] == [-3.657034512911815, 3.857969541003422, .06564132947413473]
    with pytest.raises(ValueError):
        module.parse_vectors({"signature": {"version": "1.3"}, "error": "No ephemeris", "result": ""})
    with pytest.raises(ValueError):
        module.parse_vectors({"signature": {"version": "99"}, "result": ""})


def test_daily_horizons_cache_serves_hourly_positions(tmp_path):
    module = solar_module()
    instant = datetime(2026, 10, 30, tzinfo=timezone.utc)
    jd = instant.timestamp()/86400 + 2440587.5
    calls = []
    def fetch(url):
        calls.append(url)
        return vector_payload([(jd, 1, 2, 3), (jd+1/24, 4, 5, 6)])
    app = module.SolarSystem(tmp_path, fetch, lambda: None)
    assert app.vectors("501", instant) == [1, 2, 3]
    assert app.vectors("501", instant+timedelta(hours=1)) == [4, 5, 6]
    assert len(calls) == 1
    assert "STEP_SIZE" in calls[0]


def test_jpl_search_filters_spacecraft_and_marks_existing_moons(tmp_path):
    module = solar_module()
    app = module.SolarSystem(tmp_path, lambda url: {"result": [{"spkid": "502", "name": "Europa"}, {"spkid": "-159", "name": "Europa Clipper"}, {"spkid": "20000052", "name": "52 Europa"}]}, lambda: None)
    result = app.search("Europa")
    assert len(result) == 2
    assert result[0]["tracked"] is True
    assert result[1]["tracked"] is False


def test_aircraft_filters_ground_stale_and_outside_radius(tmp_path):
    collectors = load("garage-dashboard").module("collectors.py")
    plane = {"hex": "abc123", "flight": "TEST42  ", "lat": 40.1, "lon": -105, "alt_baro": 12000, "gs": 250, "track": 90, "seen_pos": 2}
    fixture = {"now": time.time()*1000, "ac": [plane, dict(plane, hex="ground", alt_baro="ground"), dict(plane, hex="old", seen_pos=300),
                                                dict(plane, hex="far", lat=45), dict(plane, hex="missing", lat=None)]}
    app = collectors.Collectors({"location": LOCATION, "aircraft_radius_nm": 40}, tmp_path, lambda url: fixture)
    result = app.aircraft()
    assert len(result["aircraft"]) == 1
    assert result["aircraft"][0]["callsign"] == "TEST42"
    assert 10 < result["aircraft"][0]["distance_km"] < 12
    fixture["now"] = (time.time()-1000)*1000
    with pytest.raises(ValueError):
        app.aircraft()


def test_feed_cache_serializes_same_key_and_keeps_independent_results(tmp_path):
    collectors = load("garage-dashboard").module("collectors.py")
    app = collectors.Collectors({}, tmp_path)
    count = []
    def work():
        count.append(True)
        time.sleep(0.03)
        return {"observation": 42}
    workers = [threading.Thread(target=app.cached, args=("shared", work)) for _ in range(5)]
    for thread in workers:
        thread.start()
    for thread in workers:
        thread.join(1)
    assert len(count) == 1
    assert json.loads(app.cache_file.read_text())["shared"]["data"]["observation"] == 42
