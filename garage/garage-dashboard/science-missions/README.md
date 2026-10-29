# Science missions

Run from this folder with Python 3.11+ (standard library only):

```sh
python run.py create "Will the tower stay below 70 C?" "Yes, at idle"
python run.py observe 1 "Measured 45 C after ten minutes"
python run.py list
```

Stores questions, predictions, and timestamped observations in local SQLite. Observations append instead of overwriting earlier results. Listing includes every observation. The sample commands assume a new database. No sensor collection or automatic scientific conclusions.

Use `python run.py --help` for options. See [the garage run guide](../../README.md) for deployment boundaries.
