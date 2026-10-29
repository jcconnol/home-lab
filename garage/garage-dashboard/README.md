# Garage mission control dashboard

A lightweight browser dashboard served by one Python script. No pip/npm dependencies, GRACE server, GPU, or model runtime are required to run it. It can be hosted on the Pi or on the tower/Mac with the Pi acting as a browser display.

## Put it on the Pi now

Assuming Raspberry Pi OS with a desktop, Git, Python 3.11+, and a working browser:

```sh
git clone https://github.com/jcconnol/home-lab.git
cd home-lab
python3 garage/garage-dashboard/run.py
```

If already cloned, enter `home-lab` and run `git pull --ff-only` instead of cloning again. Authenticate to GitHub if the repository is private. Open **http://127.0.0.1:8780** in the Pi's browser. The default server is local to that machine. `Ctrl+C` stops it. No GRACE dependencies need installing.

Use a supported 32-bit Raspberry Pi OS release for older Pi 2 processors; check your exact revision. A desktop/browser must already be installed to display the page locally; OS Lite can run the server but does not provide a desktop browser. [Raspberry Pi OS documentation](https://www.raspberrypi.com/documentation/computers/os.html). Physical Pi/browser performance has not been measured yet.

## What works

- Overview with last-check time, stale/disconnected warnings, and host free storage.
- Visual terrarium with automatic ticks, feeding, pause/resume, manual steps, and creature introduction. State persists in `runtime/terrarium.json`; it pauses when the server is off.
- Science notebook with saved predictions and append-only observations.
- GRACE HTTP availability/latency and explicit TCP service checks after configuration, with service-change history.
- Network map with selectable nodes and a cosmetic fleet universe.
- Data-driven anomaly, apartment, satellite schedule, correlation, and history views after supplying the relevant JSON files. These display imported data, not automatic live public feeds or a live Home Assistant subscription.

The individual CLI starters remain in their own folders. Run only one dashboard against its storage directory. The dashboard has its own terrarium and notebook storage, separate from the standalone CLI defaults.

## Connect GRACE and devices

For a quick GRACE check:

```sh
python3 garage/garage-dashboard/run.py --grace-url http://YOUR-TOWER-IP:8000/
```

Replace the placeholder with a reachable LAN/Tailscale address. This checks the public landing page, not authenticated database/model health. `127.0.0.1` on the Pi means the Pi, not your tower.

For the full configuration, run from the repository root:

```sh
mkdir -p garage/garage-dashboard/runtime
cp garage/garage-dashboard/config.sample.json garage/garage-dashboard/runtime/config.json
nano garage/garage-dashboard/runtime/config.json
python3 garage/garage-dashboard/run.py --config garage/garage-dashboard/runtime/config.json
```

Example configuration (replace addresses with your own):

```json
{
  "grace_url": "http://YOUR-TOWER-IP:8000/",
  "services": [
    {"id": "grace", "name": "GRACE tower", "host": "YOUR-TOWER-IP", "port": 8000},
    {"id": "home-assistant", "name": "Home Assistant", "host": "YOUR-HA-IP", "port": 8123}
  ],
  "relationships": [{"source": "grace", "target": "home-assistant"}],
  "inputs": {}
}
```

Checks refresh every 30 seconds; the page polls the local server every 5 seconds. Config changes require a server restart. Relationships are configured, not discovered traffic. At most 32 services are accepted.

Optional `inputs` paths resolve relative to the config file. Set `anomaly_readings`, `apartment_layout`, `apartment_states`, `satellite_passes`, and/or `events` to your own JSON files. The corresponding project folders document the formats. Sample fixtures are explicitly fictional/historical; the dashboard does not load them automatically. Input-file errors are shown on the relevant page.

## Keep it running

On Raspberry Pi OS/Linux with systemd, from the repository root:

```sh
sh garage/garage-dashboard/install-service.sh
```

This installs and starts a **user** service on loopback, creates the ignored config if absent, and refuses to overwrite an existing unit. It starts with your user session. For startup before sign-in, explicitly run `sudo loginctl enable-linger "$USER"`. The installer does not change desktop autologin or browser startup.

```sh
systemctl --user status garage-dashboard
journalctl --user -u garage-dashboard -n 50
systemctl --user restart garage-dashboard
```

Open the dashboard browser and press F11 for fullscreen. If Chromium is installed, `chromium --kiosk http://127.0.0.1:8780` can be launched from a desktop terminal; some older installations name the executable `chromium-browser`. Automatic browser startup depends on your desktop/OS and is not installed here.

To update: `git pull --ff-only` in the repo, then restart the service. To disable: `systemctl --user disable --now garage-dashboard`. Runtime data is retained. Back up `garage/garage-dashboard/runtime/` separately from Git.

## Host on the tower / use Tailscale

Set a random access key of 24+ characters using `GARAGE_DASHBOARD_KEY`, then explicitly bind to the server's private Tailscale address:

```sh
export GARAGE_DASHBOARD_KEY='REPLACE_WITH_A_LONG_RANDOM_SECRET'
python3 garage/garage-dashboard/run.py --host YOUR-TAILSCALE-IP
```

In PowerShell use `$env:GARAGE_DASHBOARD_KEY = 'your-secret'` instead. On the Pi, open `http://YOUR-TAILSCALE-IP:8780` and enter the key. Non-loopback binding requires the key. Use Tailscale access rules or an HTTPS proxy; do not forward this HTTP server to the public internet. Tailscale itself still needs installation/configuration. The supplied user-service installer defaults to local-only operation and does not manage a remote access key.

## Current limits

No automatic public weather/earthquake/lightning/air-quality feeds, orbit calculations, Home Assistant subscription, CPU/GPU agents, phone camera streaming, or model/physical control. The UI exposes these as unconfigured or describes its measurement scope. The application is browser-tested locally; deployment on your actual Pi is the next hardware check.
