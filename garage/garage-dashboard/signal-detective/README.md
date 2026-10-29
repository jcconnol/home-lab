# Signal detective

Run from this folder with Python 3.11+ (standard library only):

```sh
python run.py sample.json --window 60
```

Returns pairs of events from different sources within a time window. Timestamps must include a timezone. This establishes temporal proximity only, not causation. No model integration or continuous collection yet.

Use `python run.py --help` for options. See [the garage run guide](../../README.md) for deployment boundaries.
