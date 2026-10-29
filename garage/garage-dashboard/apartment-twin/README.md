# Apartment digital twin

Run from this folder with Python 3.11+ (standard library only):

```sh
python run.py layout.sample.json states.sample.json
```

Joins manually positioned room entities with a Home Assistant-style JSON state array. Missing entities are unknown and old last_updated timestamps are stale. Old last_updated alone does not prove an offline device: live polling/heartbeat still needs implementation. Read-only JSON output, no Home Assistant token, control calls, or floor-plan renderer.

Use `python run.py --help` for options. See [the garage run guide](../../README.md) for deployment boundaries.
