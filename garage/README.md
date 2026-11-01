# Garage project starters

The [Garage Observatory](garage-dashboard/README.md) is the Pi display for weather, aircraft, ISS and hourly 3D solar-system positions. Install with `python3 garage/install.py dashboard`, then use the installed interpreter to run the dashboard. Select your city in the browser. Phone workflows are separate.

The [phone fleet hub](phones/hub/README.md) now supplies browser photo sharing, messages, battles, chess, split-network inference, bounded network tests, and reviewed operator jobs. Run it on a supported host and pair each phone browser separately. See [READINESS.md](READINESS.md) before assuming any hardware/model feature is complete, and [DESIGN.md](DESIGN.md) for the shared sci-fi visual style.

Install optional live/hub dependencies with `python3 garage/install.py dashboard` or `python3 garage/install.py hub`. For the browser worker, use `python3 garage/install.py operator --browser`. Each command creates a workspace-local virtual environment and preserves existing runtime data.

Each idea also has its own folder, independent `run.py`, and README. These individual scripts are backend/CLI prototypes. The standalone prototypes use the Python standard library; no root-level GRACE dependencies are needed. Python 3.11+ is the target (also checked here with Python 3.10).

Run commands from a project's folder, for example:

```sh
cd garage/experiments/terrarium
python run.py --ticks 10 --food 10
```

Use `python3` instead of `python` where appropriate. Each script supports `--help`. Runtime files default to ignored `runtime/` folders next to the script; custom output paths must also remain outside Git. Back up runtime data separately. Run only one writer per state file or storage directory.

## Dashboard projects

| Folder | Working first slice |
| --- | --- |
| `experiments/terrarium` | Saved ecosystem with energy, feeding, births, deaths, and lineage |
| `garage-dashboard/anomaly-observatory` | Per-source historical deviation detection and stale-data handling |
| `garage-dashboard/network-radar` | Explicit TCP service inventory and configured relationship graph |
| `garage-dashboard/space-command` | Countdown/scheduling for imported satellite passes |
| `garage-dashboard/garage-universe` | Device-state-to-planet scene data |
| `garage-dashboard/signal-detective` | Cross-source event coincidence detection |
| `garage-dashboard/time-machine` | Chronological merging and filtering of recorded events |
| `garage-dashboard/science-missions` | Durable predictions and append-only observations |
| `garage-dashboard/apartment-twin` | Read-only room/entity join with exported Home Assistant states |
| `garage-dashboard/grace-health` | Independent HTTP availability and latency checks |

The individual scripts above are independent experiments, not Observatory modes. The terrarium is archived. Their source/configuration requirements remain in their own READMEs.

## Phone projects

| Folder | Working first slice |
| --- | --- |
| `phones/photo-journal` | Original-file import, SHA-256 deduplication, and project timeline |
| `phones/communication` | HTTP mailboxes with separate device tokens and acknowledgments |
| `phones/game-player` | Fresh-observation validation and an action-proposal audit log |
| `phones/battle-arena` | Persistent two-agent arena, authenticated moves, and two example bot clients |

The HTTP services bind to loopback by default. For device trials, explicitly bind to the host's Tailscale address after Tailscale is configured, and use device-specific tokens and network access rules. Tailscale has not been installed or configured by these changes. Raw HTTP tokens should travel only inside the private encrypted connection or behind an HTTPS proxy. There is no public exposure or automatic service installation.

The phone hub adds the browser workflows to these standalone starters. Audio transport, pretrained on-phone model runtimes, video, and physical drivers still need implementation/device details. Do not assume an old phone can run Python or a particular inference runtime.

## Verification

From the repository root:

```sh
garage/runtime/venv/bin/python -m pip install -r garage/test-requirements.txt
garage/runtime/venv/bin/python -m pytest tests/test_garage_projects.py tests/test_garage_dashboard.py tests/test_garage_fleet.py
garage/runtime/venv/bin/python tests/garage_browser_check.py --channel chrome
python -m compileall -q app garage
git diff --check
```
