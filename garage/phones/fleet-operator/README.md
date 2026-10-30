# Enrolled device browser operator

On a supported Windows/macOS/Linux host with Python 3.10+:

```sh
python3 garage/install.py operator --browser
export GARAGE_DEVICE_KEY='YOUR_PAIRED_WORKER_KEY'
garage/runtime/venv/bin/python garage/phones/fleet-operator/run.py --hub https://YOUR-HUB
```

Use `python` / `Scripts/python.exe` and `$env:GARAGE_DEVICE_KEY='...'` on Windows. Create the worker's key with the hub `pair` command. `--once` polls once for smoke testing. `--browser-channel chrome` or `msedge` uses an installed desktop browser instead of bundled Chromium. Browser/system dependencies must be supported by the worker OS; this is not an iOS background agent.

The worker reports host CPU/memory/storage/network counters and temperatures when available. `--connections` explicitly opts in to observed network-connection reporting; permission failures are reported rather than hidden. Telemetry and approved diagnostics never run arbitrary shell commands.

Queue a reviewed browser job from the phone hub. The worker performs bounded navigation/click/fill/assertion steps, captures a screenshot/page text/errors/timing, and returns evidence. Every network request and navigation is restricted to the job's allowlisted origins. Jobs use fresh local browser contexts by default; use test accounts. A job lease expires rather than rerunning indefinitely.

`--cdp http://127.0.0.1:9222` attaches to a separately enrolled Chromium debugging endpoint. For compatible Android Chrome, enable developer debugging and use your local Android tools to forward that phone's debugging socket before selecting its CDP endpoint. This depends on the exact phone/browser and is not claimed tested on physical phones. iOS/Safari automation needs a different adapter and remains unimplemented. Worker reports distinguish host Chromium from remote CDP execution.

Optional local/cloud model planning uses the hub configuration. The model drafts a plan; a human reviews it before queuing. Cloud artifact uploads and unrestricted autonomous command execution are not enabled. See [job format and model setup](../hub/README.md).
