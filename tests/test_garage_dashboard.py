"""Checks for the standalone dashboard server, persistence, and access controls."""
from http.cookiejar import CookieJar
import json
import urllib.error
import urllib.request

import pytest

from test_garage_projects import GARAGE, http, load, serving


def dashboard(tmp_path, config=None):
    return load("garage-dashboard").Dashboard(config or {}, tmp_path)


def test_dashboard_works_without_configuration(tmp_path):
    app = dashboard(tmp_path)
    app.collect()
    state = app.snapshot()
    assert state["health"]["status"] == "not_configured"
    assert state["network"]["nodes"] == []
    assert state["modules"]["observatory"]["status"] == "not_configured"
    assert state["host"]["disk_free_gb"] > 0


def test_dashboard_care_and_notebook_survive_restart(tmp_path):
    app = dashboard(tmp_path)
    app.care("feed")
    app.care("pause")
    app.care("step")
    app.mission({"action": "create", "question": "Will it persist?", "prediction": "Yes"})
    app.mission({"action": "observe", "id": 1, "outcome": "First reading"})
    app.mission({"action": "observe", "id": 1, "outcome": "Second reading"})
    restarted = dashboard(tmp_path)
    state = restarted.snapshot()
    assert state["terrarium"] == app.snapshot()["terrarium"]
    assert state["terrarium"]["paused"] is True
    assert len(state["missions"][0]["observations"]) == 2
    with pytest.raises(ValueError):
        app.care("reset_everything")


def test_dashboard_input_failure_does_not_hide_other_panels(tmp_path):
    app = dashboard(tmp_path, {"inputs": {"anomaly_readings": "missing.json"}})
    app.collect()
    state = app.snapshot()
    assert state["modules"]["observatory"]["status"] == "error"
    assert state["modules"]["space"]["status"] == "not_configured"
    assert state["health"]["status"] == "not_configured"


def test_dashboard_imported_views(tmp_path):
    app = dashboard(tmp_path, {"inputs": {
        "anomaly_readings": str(GARAGE / "garage-dashboard/anomaly-observatory/sample.json"),
        "apartment_layout": str(GARAGE / "garage-dashboard/apartment-twin/layout.sample.json"),
        "apartment_states": str(GARAGE / "garage-dashboard/apartment-twin/states.sample.json"),
        "satellite_passes": str(GARAGE / "garage-dashboard/space-command/sample.json"),
        "events": str(GARAGE / "garage-dashboard/time-machine/sample.json"),
    }})
    app.collect()
    state = app.snapshot()
    for name in ("observatory", "twin", "space", "detective"):
        assert state["modules"][name]["status"] == "loaded"
        assert state["modules"][name]["data"]


def test_dashboard_http_routes_and_cross_origin_write(tmp_path):
    module = load("garage-dashboard")
    app = dashboard(tmp_path)
    with serving(module.handler_factory(app)) as url:
        assert http(url + "/api/status", "")["terrarium"]["plants"] == 40
        http(url + "/api/terrarium", "", {"action": "feed"})
        assert app.snapshot()["terrarium"]["plants"] == 50
        for route in ("/", "/app.js", "/style.css"):
            with urllib.request.urlopen(url + route) as response:
                assert response.status == 200
                assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
        request = urllib.request.Request(url + "/api/terrarium", data=b'{"action":"feed"}',
                                         headers={"Content-Type": "application/json", "Origin": "http://unrelated.example"})
        with pytest.raises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(request)
        assert error.value.code == 403
        assert app.snapshot()["terrarium"]["plants"] == 50


def test_dashboard_login_and_cookie(tmp_path):
    module = load("garage-dashboard")
    app = dashboard(tmp_path)
    secret = "test-access-key-" * 3
    with serving(module.handler_factory(app, secret)) as url:
        with pytest.raises(urllib.error.HTTPError) as error:
            http(url + "/api/status", "")
        assert error.value.code == 401
        with pytest.raises(urllib.error.HTTPError) as error:
            http(url + "/api/login", "", {"password": "wrong"})
        assert error.value.code == 401
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
        request = urllib.request.Request(url + "/api/login", data=json.dumps({"password": secret}).encode(),
                                         headers={"Content-Type": "application/json"})
        with opener.open(request) as response:
            cookie = response.headers["Set-Cookie"]
            assert "HttpOnly" in cookie and "SameSite=Strict" in cookie
        with opener.open(url + "/api/status") as response:
            assert json.load(response)["terrarium"]["tick"] == 0
