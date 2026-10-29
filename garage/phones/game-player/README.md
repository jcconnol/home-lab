# Game action review

Run from this folder with Python 3.11+ (standard library only):

```sh
python run.py observation.sample.json --action left
```

Validates a requested action against allowed_actions and observation age, then appends a proposal to runtime/proposals.jsonl. The sample is intentionally stale and must be rejected. Replace captured_at with the actual observation time and id with a real frame ID. No model calls, screen capture, physical input, or actuation are implemented. Every accepted proposal says executed=false.

Use `python run.py --help` for options. See [the garage run guide](../../README.md) for deployment boundaries.
