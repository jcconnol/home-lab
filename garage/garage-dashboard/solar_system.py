"""Geometric heliocentric positions, with cached, serialized JPL Horizons queries."""
import csv
import copy
import io
import json
import math
import re
import threading
import time
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path


CORE = [
    ("sun", "Sun", "sun", None, "sun", "#ffd06d"),
    ("mercury", "Mercury", "planet", "sun", "mercury", "#b8aaa0"),
    ("venus", "Venus", "planet", "sun", "venus", "#e9bb76"),
    ("earth", "Earth", "planet", "sun", "earth", "#64c7f0"),
    ("moon", "Moon", "moon", "earth", "moon", "#cbd3df"),
    ("mars", "Mars", "planet", "sun", "mars", "#f48c66"),
    ("jupiter", "Jupiter", "planet", "sun", "jupiter barycenter", "#ddb18d"),
    ("saturn", "Saturn", "planet", "sun", "saturn barycenter", "#ead295"),
    ("uranus", "Uranus", "planet", "sun", "uranus barycenter", "#91e1dd"),
    ("neptune", "Neptune", "planet", "sun", "neptune barycenter", "#798ff4"),
    ("pluto", "Pluto", "dwarf", "sun", "pluto barycenter", "#bfaaa0"),
]
EXTENDED = [
    ("phobos", "Phobos", "401", "moon", "mars"), ("deimos", "Deimos", "402", "moon", "mars"),
    ("io", "Io", "501", "moon", "jupiter"), ("europa", "Europa", "502", "moon", "jupiter"),
    ("ganymede", "Ganymede", "503", "moon", "jupiter"), ("callisto", "Callisto", "504", "moon", "jupiter"),
    ("mimas", "Mimas", "601", "moon", "saturn"), ("enceladus", "Enceladus", "602", "moon", "saturn"),
    ("tethys", "Tethys", "603", "moon", "saturn"), ("dione", "Dione", "604", "moon", "saturn"),
    ("rhea", "Rhea", "605", "moon", "saturn"), ("titan", "Titan", "606", "moon", "saturn"),
    ("iapetus", "Iapetus", "608", "moon", "saturn"),
    ("ariel", "Ariel", "701", "moon", "uranus"), ("umbriel", "Umbriel", "702", "moon", "uranus"),
    ("titania", "Titania", "703", "moon", "uranus"), ("oberon", "Oberon", "704", "moon", "uranus"),
    ("miranda", "Miranda", "705", "moon", "uranus"), ("triton", "Triton", "801", "moon", "neptune"),
    ("charon", "Charon", "901", "moon", "pluto"),
    ("ceres", "Ceres", "1;", "dwarf", "sun"), ("vesta", "Vesta", "4;", "asteroid", "sun"),
    ("pallas", "Pallas", "2;", "asteroid", "sun"), ("hygiea", "Hygiea", "10;", "asteroid", "sun"),
    ("eris", "Eris", "136199;", "dwarf", "sun"), ("haumea", "Haumea", "136108;", "dwarf", "sun"),
    ("makemake", "Makemake", "136472;", "dwarf", "sun"), ("sedna", "Sedna", "90377;", "small_body", "sun"),
]
PARENT_CENTERS = {"jupiter": "599", "saturn": "699", "uranus": "799", "neptune": "899", "pluto": "999"}


def parse_vectors(payload):
    version = payload.get("signature", {}).get("version")
    if version not in ("1.2", "1.3"):
        raise ValueError(f"Unsupported Horizons API version: {version}")
    result = payload.get("result", "")
    if payload.get("error") or "$$SOE" not in result or "$$EOE" not in result:
        raise ValueError(str(payload.get("error", "No vector ephemeris returned"))[:250])
    rows = []
    for row in csv.reader(io.StringIO(result.split("$$SOE", 1)[1].split("$$EOE", 1)[0].strip())):
        if not row:
            continue
        values = [float(row[index]) for index in (0, 2, 3, 4)]
        if not all(math.isfinite(value) for value in values):
            raise ValueError("Non-finite Horizons vector")
        rows.append({"jd": values[0], "xyz_au": values[1:]})
    if not rows:
        raise ValueError("Horizons returned no positions")
    return rows


class SolarSystem:
    def __init__(self, storage, fetch, resources, stop=None):
        self.storage = Path(storage)
        self.storage.mkdir(parents=True, exist_ok=True)
        self.fetch, self.resources = fetch, resources
        self.stop = stop or threading.Event()
        self.api_lock = threading.Lock()
        self.progress = {"loaded": 0, "total": len(CORE), "message": "Waiting for ephemeris"}
        self.retry_at = 0
        self.partial = None

    def request(self, parameters):
        # JPL's fair-use policy requires one request at a time, including searches.
        with self.api_lock:
            if time.time() < self.retry_at:
                raise ValueError("JPL requests are cooling down after a source failure")
            try:
                result = self.fetch("https://ssd.jpl.nasa.gov/api/" + parameters.pop("endpoint", "horizons.api") + "?" + urllib.parse.urlencode(parameters))
            except Exception:
                self.retry_at = time.time() + 300
                raise
            if self.stop.wait(0.15):
                raise InterruptedError("Solar-system collection stopped")
            return result

    def vectors(self, command, instant):
        if not re.fullmatch(r"\d{1,9};?", command):
            raise ValueError("Invalid Horizons object identifier")
        day = instant.replace(hour=0, minute=0, second=0, microsecond=0)
        path = self.storage / (command.replace(";", "s") + "-" + day.date().isoformat() + ".json")
        if path.exists():
            rows = json.loads(path.read_text(encoding="utf-8"))
        else:
            parameters = {"format": "json", "COMMAND": f"'{command}'", "CENTER": "'500@10'", "EPHEM_TYPE": "'VECTORS'",
                          "START_TIME": "'" + day.strftime("%Y-%m-%d %H:%M") + "'", "STOP_TIME": "'" + (day + timedelta(days=1)).strftime("%Y-%m-%d %H:%M") + "'",
                          "STEP_SIZE": "'1 h'", "TIME_TYPE": "'UT'", "OUT_UNITS": "'AU-D'", "REF_PLANE": "'ECLIPTIC'",
                          "REF_SYSTEM": "'ICRF'", "VEC_CORR": "'NONE'", "CSV_FORMAT": "'YES'", "VEC_TABLE": "'2'", "OBJ_DATA": "'NO'"}
            rows = parse_vectors(self.request(parameters))
            temporary = path.with_suffix(".tmp")
            temporary.write_text(json.dumps(rows), encoding="utf-8")
            temporary.replace(path)
        jd = instant.timestamp() / 86400 + 2440587.5
        row = min(rows, key=lambda entry: abs(entry["jd"] - jd))
        if abs(row["jd"] - jd) > 1 / 48:
            raise ValueError("No current-hour vector in the ephemeris table")
        return row["xyz_au"]

    def search(self, query):
        if not isinstance(query, str) or not 2 <= len(query.strip()) <= 80:
            raise ValueError("Enter 2..80 characters")
        payload = self.request({"endpoint": "horizons_lookup.api", "format": "json", "sstr": query.strip()})
        known = {"10", "199", "299", "399", "301", "499", "599", "699", "799", "899", "999"}
        for _, _, command, _, _ in EXTENDED:
            if command.endswith(";"):
                known.update({str(20000000 + int(command[:-1])), str(2000000 + int(command[:-1]))})
            else:
                known.add(command)
        return [{"id": str(row["spkid"]), "name": row["name"], "kind": "body", "parent": "sun",
                 "tracked": str(row["spkid"]) in known}
                for row in (payload.get("result") or [])[:15] if re.fullmatch(r"\d{1,9}", str(row.get("spkid", "")))]

    def collect(self, extras=None, extended=True, instant=None):
        instant = (instant or datetime.now(timezone.utc)).replace(minute=0, second=0, microsecond=0)
        self.partial = None
        _, ts, eph = self.resources()
        t = ts.from_datetime(instant)
        sun = eph["sun"]
        bodies, failures = [], []
        for identifier, name, kind, parent, target, color in CORE:
            vector = [0.0, 0.0, 0.0] if identifier == "sun" else [float(value) for value in (eph[target] - sun).at(t).ecliptic_xyz().au]
            bodies.append({"id": identifier, "name": name, "kind": kind, "parent": parent, "xyz_au": vector, "color": color,
                           "source": "JPL DE421 / Skyfield", "center": "system barycenter" if "barycenter" in target else "body center"})
        catalog = list(EXTENDED) if extended else []
        for body in extras or []:
            catalog.append(("custom-" + body["id"], body["name"], body["id"], "body", "sun"))
        self.progress = {"loaded": len(bodies), "total": len(CORE) + len(catalog), "message": "Loading major moons and small bodies"}
        metadata = {"epoch": instant.isoformat(), "frame": "Heliocentric geometric positions, J2000 ecliptic; AU", "catalog_count": len(CORE) + len(catalog),
                    "source_url": "https://ssd.jpl.nasa.gov/horizons/", "refresh_seconds": 3600,
                    "coverage": "Sun, eight planets, Moon, Pluto, selected major moons and small bodies; add more through JPL search. This is not every known solar-system object."}
        self.partial = dict(metadata, bodies=copy.deepcopy(bodies), unavailable=[])
        if extended:
            for body in bodies:
                if body["id"] in PARENT_CENTERS:
                    try:
                        body["xyz_au"] = self.vectors(PARENT_CENTERS[body["id"]], instant)
                        body.update(center="body center", source="JPL Horizons")
                    except Exception as error:
                        failures.append({"name": body["name"] + " physical center", "error": str(error)})
        for identifier, name, command, kind, parent in catalog:
            if self.stop.is_set():
                break
            try:
                bodies.append({"id": identifier, "name": name, "kind": kind, "parent": parent, "xyz_au": self.vectors(command, instant),
                               "color": "#b9c6d6" if kind == "moon" else "#b4a0ec", "source": "JPL Horizons", "center": "body center"})
            except Exception as error:
                failures.append({"name": name, "error": str(error)})
            self.progress["loaded"] = len(bodies)
            self.partial = dict(metadata, bodies=copy.deepcopy(bodies), unavailable=copy.deepcopy(failures))
        self.progress["message"] = "Positions ready"
        return dict(metadata, bodies=bodies, unavailable=failures)
