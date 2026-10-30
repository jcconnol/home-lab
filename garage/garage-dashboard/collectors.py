"""Live, cached observatory collectors. A failed source never becomes 'normal'."""
import json
import math
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path


def utc(value=None):
    if value is None:
        return datetime.now(timezone.utc)
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed


def fetch_json(url, headers=None):
    request = urllib.request.Request(url, headers={"User-Agent": "GarageLab/1.0 (personal observatory)", **(headers or {})})
    with urllib.request.urlopen(request, timeout=12) as response:
        raw = response.read(8 * 1024 * 1024 + 1)
    if len(raw) > 8 * 1024 * 1024:
        raise ValueError("Source response exceeds 8 MiB")
    return json.loads(raw)


def distance_km(lat1, lon1, lat2, lon2):
    a, b = math.radians(lat1), math.radians(lat2)
    dlat, dlon = b - a, math.radians(lon2 - lon1)
    h = math.sin(dlat / 2) ** 2 + math.cos(a) * math.cos(b) * math.sin(dlon / 2) ** 2
    return 6371 * 2 * math.asin(min(1, math.sqrt(h)))


class Collectors:
    def __init__(self, config, storage, fetch=fetch_json):
        self.config, self.fetch = config, fetch
        self.storage = Path(storage)
        self.storage.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.storage / "feed-cache.json"
        self.cache = json.loads(self.cache_file.read_text()) if self.cache_file.exists() else {}

    def cached(self, key, work, ttl=900):
        previous = self.cache.get(key, {})
        if time.time() - previous.get("attempt", 0) < ttl:
            return previous
        try:
            entry = {"status": "live", "data": work(), "fetched_at": utc().isoformat(), "attempt": time.time()}
        except Exception as error:
            entry = {"status": "error", "error": str(error), "attempt": time.time()}
            if "data" in previous:
                entry.update(data=previous["data"], fetched_at=previous.get("fetched_at"), stale=True)
        self.cache[key] = entry
        temporary = self.cache_file.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.cache), encoding="utf-8")
        temporary.replace(self.cache_file)
        return entry

    def location(self):
        location = self.config.get("location")
        if not location:
            raise ValueError("Set location.latitude and location.longitude first")
        lat, lon = float(location["latitude"]), float(location["longitude"])
        if not math.isfinite(lat + lon) or not -90 <= lat <= 90 or not -180 <= lon <= 180:
            raise ValueError("Invalid coordinates")
        return lat, lon, location.get("name", "Home")

    def weather(self):
        lat, lon, name = self.location()
        query = urllib.parse.urlencode({"latitude": lat, "longitude": lon, "current": "temperature_2m,pressure_msl,wind_speed_10m",
                                        "hourly": "temperature_2m,pressure_msl,wind_speed_10m", "past_days": 2, "forecast_days": 1, "timezone": "UTC"})
        data = self.fetch("https://api.open-meteo.com/v1/forecast?" + query)
        rows = []
        current = utc(data["current"]["time"])
        for metric in ("temperature_2m", "pressure_msl", "wind_speed_10m"):
            unit = data["hourly_units"][metric]
            for timestamp, value in zip(data["hourly"]["time"], data["hourly"][metric]):
                if value is not None and current - timedelta(hours=24) <= utc(timestamp) < current:
                    rows.append({"source": "Open-Meteo modeled weather", "location": name, "metric": metric,
                                 "unit": unit, "timestamp": utc(timestamp).isoformat(), "value": value})
            value = data["current"].get(metric)
            if value is not None:
                rows.append({"source": "Open-Meteo modeled weather", "location": name, "metric": metric,
                             "unit": unit, "timestamp": current.isoformat(), "value": value})
        return {"readings": rows, "source_url": "https://open-meteo.com/", "attribution": "Weather data by Open-Meteo.com (CC BY 4.0). Modeled estimates, not garage sensors."}

    def air(self):
        lat, lon, name = self.location()
        query = urllib.parse.urlencode({"latitude": lat, "longitude": lon, "current": "pm2_5,us_aqi",
                                        "hourly": "pm2_5,us_aqi", "past_days": 2, "forecast_days": 1, "timezone": "UTC"})
        data = self.fetch("https://air-quality-api.open-meteo.com/v1/air-quality?" + query)
        current = utc(data["current"]["time"])
        rows = []
        for metric in ("pm2_5", "us_aqi"):
            for timestamp, value in zip(data["hourly"]["time"], data["hourly"][metric]):
                if value is not None and current - timedelta(hours=24) <= utc(timestamp) < current:
                    rows.append({"source": "CAMS via Open-Meteo", "location": name, "metric": metric,
                                 "unit": data["hourly_units"][metric], "timestamp": utc(timestamp).isoformat(), "value": value})
            if data["current"].get(metric) is not None:
                rows.append({"source": "CAMS via Open-Meteo", "location": name, "metric": metric,
                             "unit": data["hourly_units"][metric], "timestamp": current.isoformat(), "value": data["current"][metric]})
        return {"readings": rows, "source_url": "https://open-meteo.com/en/docs/air-quality-api", "attribution": "CAMS ENSEMBLE / CAMS GLOBAL via Open-Meteo (CC BY 4.0). Regional modeled air quality, not an indoor measurement."}

    def earthquakes(self):
        lat, lon, name = self.location()
        data = self.fetch("https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson")
        result = []
        for feature in data["features"]:
            props = feature["properties"]
            qlon, qlat, depth = feature["geometry"]["coordinates"]
            distance = distance_km(lat, lon, qlat, qlon)
            magnitude = props.get("mag")
            if magnitude is None:
                continue
            nearby = distance <= float(self.config.get("earthquake_radius_km", 500))
            if nearby or magnitude >= 5:
                result.append({"id": "usgs:" + feature["id"], "source": "USGS", "timestamp": datetime.fromtimestamp(props["time"] / 1000, timezone.utc).isoformat(),
                               "event": f"M{magnitude:g} earthquake: {props.get('place', 'unknown location')}",
                               "magnitude": magnitude, "depth_km": depth, "distance_km": round(distance), "scope": "nearby" if nearby else "global",
                               "source_url": props["url"], "explanation": f"USGS reports magnitude {magnitude:g}, about {distance:.0f} km from {name}. This does not establish local damage or felt shaking."})
        return {"events": sorted(result, key=lambda event: event["timestamp"], reverse=True)[:40], "source_url": "https://earthquake.usgs.gov/"}

    def geomagnetic(self):
        data = self.fetch("https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json")
        if data and isinstance(data[0], list):
            data = [dict(zip(data[0], row)) for row in data[1:]]
        rows = []
        for item in data:
            value = item.get("Kp", item.get("kp"))
            if value is not None:
                rows.append({"source": "NOAA SWPC", "location": "planetary", "metric": "Kp", "unit": "index", "timestamp": utc(item["time_tag"]).isoformat(), "value": float(value)})
        return {"readings": rows[-24:], "source_url": "https://www.swpc.noaa.gov/products/planetary-k-index", "attribution": "NOAA Space Weather Prediction Center"}

    def lightning(self):
        url = self.config.get("lightning_url")
        if not url:
            raise ValueError("Lightning needs a provider JSON URL in live.lightning_url; no global unauthenticated source is assumed")
        data = self.fetch(url)
        lat, lon, name = self.location()
        result = []
        for event in data:
            age = (utc() - utc(event["timestamp"])).total_seconds()
            distance = distance_km(lat, lon, float(event["latitude"]), float(event["longitude"]))
            if 0 <= age <= 3600 and distance <= float(self.config.get("lightning_radius_km", 100)):
                result.append({"id": str(event["id"]), "source": "Configured lightning provider", "timestamp": utc(event["timestamp"]).isoformat(),
                               "event": f"Lightning report {distance:.0f} km from {name}", "distance_km": round(distance), "source_url": url})
        return {"events": result[-100:], "source_url": url}

    def home_assistant(self):
        settings = self.config.get("home_assistant", {})
        url = settings.get("url", "").rstrip("/")
        token = os.environ.get(settings.get("token_env", "GARAGE_HA_TOKEN"), "")
        if not url or not token:
            raise ValueError("Home Assistant needs live.home_assistant.url and the configured token environment variable")
        states = self.fetch(url + "/api/states", {"Authorization": "Bearer " + token})
        allowed = settings.get("entities", [])
        selected = [state for state in states if state["entity_id"] in allowed or (not allowed and state["entity_id"].startswith(("light.", "switch.", "automation.")))]
        return {"states": selected, "polled_at": utc().isoformat(), "source_url": url}

    def satellites(self):
        from skyfield.api import EarthSatellite, Loader, wgs84
        lat, lon, name = self.location()
        loader = Loader(str(self.storage / "skyfield"))
        ts = loader.timescale(builtin=True)
        tle = self.cached("tle", lambda: self.fetch("https://celestrak.org/NORAD/elements/gp.php?CATNR=25544&FORMAT=json"), 21600)
        if tle["status"] != "live":
            raise ValueError("Current orbital elements unavailable: " + tle.get("error", "unknown error"))
        element = tle["data"][0]
        from sgp4 import omm
        from sgp4.api import Satrec
        record = Satrec()
        omm.initialize(record, element)
        satellite = EarthSatellite.from_satrec(record, ts)
        age = abs((utc() - satellite.epoch.utc_datetime()).total_seconds()) / 86400
        if age > 14:
            raise ValueError(f"Orbital elements are {age:.1f} days old; refusing stale pass prediction")
        observer = wgs84.latlon(lat, lon)
        start = ts.from_datetime(utc())
        end = ts.from_datetime(utc() + timedelta(days=2))
        times, events = satellite.find_events(observer, start, end, altitude_degrees=10)
        # Solar ephemeris is downloaded once and cached by Skyfield (~17 MiB).
        eph = loader("de421.bsp")
        passes = []
        pending = None
        for instant, kind in zip(times, events):
            altitude, azimuth, _ = (satellite - observer).at(instant).altaz()
            if kind == 0:
                pending = {"name": element.get("OBJECT_NAME", "ISS"), "start": instant.utc_datetime().isoformat(), "location": name,
                           "azimuth_degrees": round(azimuth.degrees), "source": "CelesTrak OMM / Skyfield SGP4",
                           "element_epoch": satellite.epoch.utc_datetime().isoformat(), "visibility": "not_visible", "simulated_mission": False}
            if pending is not None and kind == 1:
                sun_alt = (eph["earth"] + observer).at(instant).observe(eph["sun"]).apparent().altaz()[0].degrees
                visible = bool(satellite.at(instant).is_sunlit(eph)) and sun_alt < -6
                pending.update(max_elevation_degrees=round(altitude.degrees), visibility="potentially_visible" if visible else "not_visible")
            if pending is not None and kind == 2:
                pending["end"] = instant.utc_datetime().isoformat()
                passes.append(pending)
                pending = None
        position = satellite.at(start).subpoint()
        return {"passes": passes, "position": {"latitude": position.latitude.degrees, "longitude": position.longitude.degrees},
                "source_url": "https://celestrak.org/", "note": "Potential visibility uses darkness and satellite sunlight at culmination; clouds and local obstructions can still prevent observation."}

    def fleet(self):
        settings = self.config.get("fleet", {})
        url = settings.get("url", "").rstrip("/")
        token = os.environ.get(settings.get("token_env", "GARAGE_FLEET_KEY"), "")
        if not url or not token:
            raise ValueError("Fleet source needs live.fleet.url and a paired-device key in its token environment variable")
        state = self.fetch(url + "/api/state", {"Authorization": "Bearer " + token})
        return {"devices": state["devices"], "source_url": url, "note": "Enrolled agent/browser heartbeats; telemetry is available only when reported by a host agent."}

    def collect(self):
        result = {}
        if not self.config.get("enabled"):
            return result
        for name in ("weather", "air", "earthquakes", "geomagnetic", "lightning", "home_assistant", "satellites", "fleet"):
            setting = self.config.get(name, name in ("weather", "air", "earthquakes", "geomagnetic"))
            enabled = setting.get("enabled", False) if isinstance(setting, dict) else bool(setting)
            if enabled:
                result[name] = self.cached(name, getattr(self, name), 3600 if name == "satellites" else 30 if name in ("home_assistant", "fleet") else 900)
        return result
