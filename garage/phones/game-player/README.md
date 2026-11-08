# Game action review

Run from this folder with Python 3.11+ (standard library only):

```sh
python run.py observation.sample.json --action left
```

Validates a requested action against allowed_actions and observation age, then appends a proposal to runtime/proposals.jsonl. The sample is intentionally stale and must be rejected. Replace captured_at with the actual observation time and id with a real frame ID. No model calls, screen capture, physical input, or actuation are implemented. Every accepted proposal says executed=false.

Use `python run.py --help` for options. See [the garage run guide](../../README.md) for deployment boundaries.

## Raspberry Pi motor controller

For the three-axis 5 V ULN2003/28BYJ-48 mechanism, use `python3 robot.py` on
Raspberry Pi OS, or `python robot.py --dry-run` without hardware. This is a
separate manual controller; the proposal script above remains unchanged.
See [pinout, power wiring, and manual calibration](PINOUT_AND_CALIBRATION.md).
No limit switches are required. Every session needs a manual reference; no
position is trusted after restart. Camera calibration and AI game play are not
implemented yet.
