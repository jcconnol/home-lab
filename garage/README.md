# Garage project starters

The [browser dashboard](garage-dashboard/README.md) is ready for a first Pi deployment: run `python3 garage/garage-dashboard/run.py` from the repo root and open `http://127.0.0.1:8780` on that device. It includes a visual terrarium, experiment notebook, and configured service checks. Other data views need the inputs described in its run guide.

Each idea also has its own folder, independent `run.py`, and README. These individual scripts are backend/CLI prototypes. All use the Python standard library; no root-level GRACE dependencies are needed. Python 3.11+ is the target (also checked here with Python 3.10).

Run commands from a project's folder, for example:

```sh
cd garage/garage-dashboard/terrarium
python run.py --ticks 10 --food 10
```

Use `python3` instead of `python` where appropriate. Each script supports `--help`. Runtime files default to ignored `runtime/` folders next to the script; custom output paths must also remain outside Git. Back up runtime data separately. Run only one writer per state file or storage directory.

## Dashboard projects

| Folder | Working first slice |
| --- | --- |
| `garage-dashboard/terrarium` | Saved ecosystem with energy, feeding, births, deaths, and lineage |
| `garage-dashboard/anomaly-observatory` | Per-source historical deviation detection and stale-data handling |
| `garage-dashboard/network-radar` | Explicit TCP service inventory and configured relationship graph |
| `garage-dashboard/space-command` | Countdown/scheduling for imported satellite passes |
| `garage-dashboard/garage-universe` | Device-state-to-planet scene data |
| `garage-dashboard/signal-detective` | Cross-source event coincidence detection |
| `garage-dashboard/time-machine` | Chronological merging and filtering of recorded events |
| `garage-dashboard/science-missions` | Durable predictions and append-only observations |
| `garage-dashboard/apartment-twin` | Read-only room/entity join with exported Home Assistant states |
| `garage-dashboard/grace-health` | Independent HTTP availability and latency checks |

The individual scripts emit JSON; the browser dashboard renders their data and supplies shared local controls. Sample files are fictional fixtures, not live telemetry. Live public feeds, orbital calculations, automatic Home Assistant collection, and resource agents remain future work. Run collection/simulation on the tower or Mac if needed; device capability does not dictate repository structure. Multiple lightweight scripts can coexist on a device later.

## Phone projects

| Folder | Working first slice |
| --- | --- |
| `phones/photo-journal` | Original-file import, SHA-256 deduplication, and project timeline |
| `phones/communication` | HTTP mailboxes with separate device tokens and acknowledgments |
| `phones/game-player` | Fresh-observation validation and an action-proposal audit log |
| `phones/battle-arena` | Persistent two-agent arena, authenticated moves, and two example bot clients |

The HTTP services bind to loopback by default. For device trials, explicitly bind to the host's Tailscale address after Tailscale is configured, and use device-specific tokens and network access rules. Tailscale has not been installed or configured by these changes. Raw HTTP tokens should travel only inside the private encrypted connection or behind an HTTPS proxy. There is no public exposure or automatic service installation.

Phone browser clients, camera capture/upload, voice transport, local model runtimes, and hardware drivers remain to implement after confirming phone/OS/mechanism details. The Python clients can be tested on the tower now; do not assume an old phone can run Python or a particular inference runtime.

## Verification

From the repository root:

```sh
python -m pytest tests/test_garage_projects.py tests/test_garage_dashboard.py
python -m compileall -q app garage
git diff --check
```
