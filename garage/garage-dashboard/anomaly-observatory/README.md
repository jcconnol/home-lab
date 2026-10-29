# Anomaly observatory

Run from this folder with Python 3.11+ (standard library only):

```sh
python run.py sample.json
```

Groups readings by source, location, metric, and unit. Compares the latest reading with at least five earlier samples. Stale/future readings are unknown. The historical sample is intentionally stale. Supply recent timezone-aware timestamps to exercise live detection. This is a basic sample baseline, not a seasonal model or public-feed collector.

Use `python run.py --help` for options. See [the garage run guide](../../README.md) for deployment boundaries.
