# GRACE health

Run from this folder with Python 3.11+ (standard library only):

```sh
python run.py sample.json
```

Checks each configured HTTP URL independently. A 2xx response means reachable HTTP service; it does not verify database/model functionality. HTTP failures are degraded; connection failures are unavailable. The sample checks GRACE's public landing page on loopback and marks model checks disabled. Its `/api/status` route requires authentication and would return a degraded 401 without a session. Run this separately from GRACE so GRACE downtime can be observed.

Use `python run.py --help` for options. See [the garage run guide](../../README.md) for deployment boundaries.
