# Space command center

Run from this folder with Python 3.11+ (standard library only):

```sh
python run.py sample.json
```

Sorts future imported passes and computes countdowns. The sample is fictional and deliberately dated far in the future. No orbit propagation, satellite API, or visibility calculations are implemented. Import trusted location-specific predictions with provenance; visibility is always marked unverified.

Use `python run.py --help` for options. See [the garage run guide](../../README.md) for deployment boundaries.
