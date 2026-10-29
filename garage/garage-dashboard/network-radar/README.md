# Network radar

Run from this folder with Python 3.11+ (standard library only):

```sh
python run.py sample.json
```

Probes configured TCP services with a two-second timeout per entry. Outputs nodes and explicitly configured edges. No subnet scanning, resource agents, traffic capture, persistence, or graph rendering. Only configure owned/authorized destinations.

Use `python run.py --help` for options. See [the garage run guide](../../README.md) for deployment boundaries.
