# Garage Observatory

A standalone Pi display for weather, nearby aircraft, ISS tracking and an interactive 3D solar system. It runs independently of the tower AI. Phone applications remain in `garage/phones`.

## Install or update

Use Raspberry Pi OS with a desktop/browser, Git and Python 3.11+. From the repository root:

```sh
git pull --ff-only
python3 garage/install.py dashboard
garage/runtime/venv/bin/python garage/garage-dashboard/run.py
```

For a fresh checkout, first clone `https://github.com/jcconnol/home-lab.git` and enter `home-lab`. If venv support is missing, install `python3-venv` with apt. Open **http://127.0.0.1:8780** and choose your city or ZIP code. Settings are saved locally; editing JSON is unnecessary. Ctrl+C stops the server. Restart an existing user service with `systemctl --user restart garage-dashboard` after updating.

On Windows use `garage/runtime/venv/Scripts/python.exe`. Physical Pi performance remains unmeasured; local browser checks cover 1280x720. Your Pi 2 revision may require a supported 32-bit OS.

## Full-screen display at startup (Raspberry Pi)

Use Raspberry Pi OS **with Desktop**, Chromium, and the dashboard dependencies installed above. In `sudo raspi-config`, enable **Desktop Auto Login** under the boot/auto-login options. Disable screen blanking there too if the display should stay on. A graphical desktop must be running; Raspberry Pi OS Lite alone is insufficient. Current Chromium requires a Pi 3 or newer with at least 1 GB RAM; the older Pi 2 mentioned above is not a supported Chromium kiosk target. See the [official Raspberry Pi kiosk guide](https://www.raspberrypi.com/tutorials/how-to-use-a-raspberry-pi-in-kiosk-mode/).

From the repository root, run this one command to launch the dashboard and Chromium full screen:

```sh
bash "$PWD/garage/garage-dashboard/kiosk.sh"
```

To launch at every boot, run `crontab -e` as your **normal desktop user**, without sudo, and add this line, replacing the checkout path with your actual absolute path:

```cron
@reboot /bin/bash /home/YOUR_USER/home-lab/garage/garage-dashboard/kiosk.sh
```

The launcher works from any directory, waits up to ten minutes for the Wayland or X11 desktop, starts the local server if needed, and waits for it before opening Chromium. It reuses an already running server, including the existing dashboard user service. Duplicate launcher invocations exit without opening another window. Chromium uses a separate profile, preserving the dashboard's normal browser settings. No cloud hosting is required.

Press **Alt+F4** to close the kiosk. Closing it also stops the server if this launcher started it; an existing service remains running. Remove the crontab line to disable startup. Logs are in `garage/garage-dashboard/runtime/kiosk.log` and `runtime/server.log`. Desktop auto-login leaves this local desktop accessible to anyone at the Pi.

## Features and limits

The display automatically alternates between the local and solar-system tabs every 60 seconds. You can still select either tab manually.

- Current weather, feels-like temperature, wind/gusts, precipitation, hourly outlook, five-day forecast, sunrise/sunset and regional modeled air quality.
- Nearby airborne aircraft radar with callsign, altitude, speed and distance. Volunteer receiver coverage varies; an empty display does not establish an empty sky.
- ISS position, observer elevation and upcoming potentially visible passes. Clouds and obstructions can prevent visibility.
- Rotatable, zoomable 3D positions for 39 curated bodies: Sun, planets, Moon, major planetary moons, Pluto and selected small bodies. Search JPL to add supported bodies. Planet-system views reveal moons.

Solar positions update at hourly epochs. Marker sizes are exaggerated, compressed distances are labeled, and circular guides represent distances rather than calculated orbital paths. This is a curated view, not every solar-system object. The first ephemeris download is about 17 MB; extended collection may take a minute or longer. Partial results and unavailable bodies are explicit.

Weather/air refresh every 15 minutes, aircraft every two minutes, ISS position every 30 seconds, and pass predictions/solar positions hourly. Independent workers prevent a slow source blocking others. Cached readings show timestamps and refresh failures.

## Storage and access

Runtime files are ignored by Git; updates preserve saved settings and old experiment data. Back them up separately. The [terrarium](../experiments/terrarium/README.md) is archived outside this display.

The server binds to localhost. For private Tailscale access, set `--host` to the Pi's Tailscale address and `GARAGE_DASHBOARD_KEY` to a random secret of at least 24 characters. Non-loopback binding requires this key. Configure Tailscale separately and restrict access to your private network or an HTTPS proxy.

Sources: [Open-Meteo](https://open-meteo.com/en/docs), [adsb.lol](https://www.adsb.lol/), [CelesTrak](https://celestrak.org/), [Skyfield](https://rhodesmill.org/skyfield/), [JPL Horizons](https://ssd.jpl.nasa.gov/horizons/). See [attribution](web/ATTRIBUTION.md) and [validation](../VALIDATION.md).
