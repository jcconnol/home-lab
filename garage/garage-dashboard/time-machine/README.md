# Time machine

Run from this folder with Python 3.11+ (standard library only):

```sh
python run.py sample.json
python run.py sample.json --source tower --since 2026-01-01T00:00:00Z
```

Accepts one or more JSON arrays with timestamp and source fields, merges chronologically, and optionally filters by source/time. It preserves imported event records and does not fill gaps. No timeline renderer or live event subscription yet.

Use `python run.py --help` for options. See [the garage run guide](../../README.md) for deployment boundaries.
