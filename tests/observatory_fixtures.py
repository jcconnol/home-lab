"""Clearly synthetic source data for browser checks without internet access."""
from datetime import datetime, timedelta, timezone


def snapshot():
    now = datetime.now(timezone.utc)
    hourly = [now + timedelta(hours=i) for i in range(12)]
    daily = [now + timedelta(days=i) for i in range(7)]
    epoch = now.isoformat()
    def feed(data):
        return {"status": "live", "data": data, "fetched_at": epoch, "attempt": now.timestamp()}
    bodies = [
        {"id": "sun", "name": "Sun", "kind": "sun", "parent": None, "xyz_au": [0, 0, 0], "color": "#ffd06d"},
        {"id": "earth", "name": "Earth", "kind": "planet", "parent": "sun", "xyz_au": [1, 0, 0], "color": "#64c7f0"},
        {"id": "moon", "name": "Moon", "kind": "moon", "parent": "earth", "xyz_au": [1, .00257, 0], "color": "#cbd3df"},
        {"id": "jupiter", "name": "Jupiter", "kind": "planet", "parent": "sun", "xyz_au": [-3, 4, .1], "color": "#ddb18d"},
        {"id": "io", "name": "Io", "kind": "moon", "parent": "jupiter", "xyz_au": [-3.001, 4.002, .1], "color": "#cbd3df"},
    ]
    for body in bodies:
        body.update(source="Synthetic browser fixture", center="body center")
    return {"settings": {"location": {"name": "Fixture city", "latitude": 40, "longitude": -105, "timezone": "UTC"}, "units": "imperial"},
            "feeds": {
                "weather": feed({"current": {"time": now.timestamp(), "timestamp": epoch, "temperature_2m": 21.5, "apparent_temperature": 20,
                                               "relative_humidity_2m": 52, "weather_code": 2, "wind_speed_10m": 12, "wind_direction_10m": 315,
                                               "wind_gusts_10m": 22, "pressure_msl": 1012, "precipitation": 0}, "timezone": "UTC",
                                 "hourly": {"time": [t.timestamp() for t in hourly], "temperature_2m": [21+i%4 for i in range(12)],
                                            "weather_code": [2]*12, "precipitation_probability": [20]*12},
                                 "daily": {"time": [t.timestamp() for t in daily], "weather_code": [2]*7,
                                           "temperature_2m_max": [24]*7, "temperature_2m_min": [12]*7, "precipitation_probability_max": [20]*7,
                                           "sunrise": [(t-timedelta(hours=5)).timestamp() for t in daily], "sunset": [(t+timedelta(hours=5)).timestamp() for t in daily]}}),
                "air": feed({"current": {"us_aqi": 35, "pm2_5": 7}}),
                "aircraft": feed({"radius_nm": 40, "aircraft": [{"id": "abc123", "callsign": "TEST42", "type": "B738", "distance_km": 8.5,
                                                                  "bearing": 30, "track": 90, "altitude_ft": 12000, "speed_knots": 250}]}),
                "iss": feed({"latitude": 12, "longitude": 20, "altitude_km": 420, "observer_elevation": -30, "observer_azimuth": 120}),
                "satellites": feed({"passes": [{"name": "ISS", "start": (now+timedelta(hours=1)).isoformat(), "end": (now+timedelta(hours=1, minutes=8)).isoformat(),
                                                 "visibility": "potentially_visible", "azimuth_degrees": 320, "max_elevation_degrees": 70}]}),
                "solar_system": feed({"epoch": epoch, "frame": "Synthetic browser fixture, not current astronomical positions", "bodies": bodies,
                                       "catalog_count": len(bodies), "unavailable": [], "coverage": "Synthetic test catalog."}),
            }}
