# G.R.A.C.E. Home Lab

**G.R.A.C.E.** means **Generally Reliable Assistant for Computing and Engineering**. It is configurable because the name is expected to evolve.

The first milestone is a local Wi-Fi dashboard that can inspect a room, remember recent object changes, accept typed commands, and optionally ask a local Ollama model for richer answers. The design targets a future GTX 1070: low-rate vision sampling and compact local models keep the GPU workload bounded.

## Run the scaffold

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000`. Without OpenCV and Ultralytics installed, the app remains usable with an empty scene. To enable local vision, install `opencv-python` and `ultralytics`; to enable richer chat, install and run Ollama with the configured model.

The dashboard now includes a workflow guide and a `JOHNS_TODO` handoff file, both reachable from the UI and downloadable as markdown. The frontend also registers as a PWA, so you can install it from the browser and open the local server on your phone with `http://<your-computer-ip>:8000` while you are on the same network.

## Garage device projects

`garage/` contains a [browser dashboard for the Pi](garage/garage-dashboard/README.md) and independent projects including a persistent terrarium, network/GRACE checks, photo journal, messaging, and a two-agent battle arena. Each project has its own script and run instructions. Start with [the garage run guide](garage/README.md); remaining device interfaces and live integrations are tracked in the idea files.

## Android companion app

`mobile_app/` contains a Flutter wrapper for the same dashboard plus an Android home-screen widget for the four lighting layouts. Build instructions are in [mobile_app/README.md](mobile_app/README.md). Once a release APK is copied to `app/web/downloads/grace-mobile.apk`, users can download it from **Account → Android app** in the dashboard.

## HTTPS and phone microphone setup

Phone browsers require HTTPS before a LAN website can use the microphone. Install the dependencies, then start the secure server:

```powershell
pip install -r requirements.txt
powershell -NoProfile -ExecutionPolicy Bypass -File .\start-https.ps1
```

On the phone, first open `http://<your-computer-ip>:8000/certificate` using the temporary HTTP server. Download and trust the public G.R.A.C.E. certificate using the instructions on that page. Then use `https://<your-computer-ip>:8443` for the app and grant microphone permission when prompted.

## Keep the server running

The ordinary HTTP and HTTPS commands run in the foreground, so they stop when the PowerShell window is closed. To keep both listeners available after a restart and before sign-in, open **PowerShell as Administrator**, change to this project directory, and install the watchdog once:

```powershell
cd C:\Users\Jon\Desktop\software_eng\home-lab
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install-grace-watchdog.ps1
```

It creates `G.R.A.C.E. Server Watchdog Startup` to start the listeners immediately at Windows startup and `G.R.A.C.E. Server Watchdog Minute Check` to check ports `8000` and `8443` every minute. Both run as the local SYSTEM account, so they cannot open terminal windows on your desktop. Output is written under the ignored `logs/` directory; inspect `logs/grace-http.error.log`, `logs/grace-https.error.log`, and `logs/watchdog.log` after a restart or failure.

The legacy `G.R.A.C.E. Server Watchdog` user task should remain disabled. It runs in the signed-in desktop session and can show a terminal window.

Certificates and private keys are generated under the ignored `.certs/` directory. Never commit or share `.certs/grace-ca-key.pem` or `.certs/grace-server-key.pem`. If the computer's LAN IP changes, rerun `py scripts/create_https_cert.py`; it keeps the same phone-trusted CA and replaces only the server certificate.

When a feature is complete and validated, the workflow calls for staging the feature files, reviewing the staged diff, committing with a focused message, and pushing to the GitHub `main` branch. Any authentication, remote, or branch-policy blocker should be recorded in `JOHNS_TODO.md`.

See [initial_setup.md](initial_setup.md) for the product specification and phased roadmap.

See [IDEAS.md](IDEAS.md) for the longer-term robotics, interface, networking, personality, media, pet-care, and wearable backlog.

## Zigbee light switch

The Raspberry Pi can connect the Third Reality switch to G.R.A.C.E. through Home Assistant. The USB dongle is the Zigbee coordinator; pair the switch to Home Assistant using either ZHA or Zigbee2MQTT, but do not run both coordinators against the same dongle/network.

With ZHA, add the integration under **Settings → Devices & services**, select the USB dongle, then use **Add device**. Put the switch into pairing mode by holding its button until the blue LED flashes rapidly, then select the discovered device. Zigbee2MQTT follows the same pairing concept: configure the dongle as its coordinator, enable **Permit join**, and pair the switch while its LED is flashing.

After pairing, create a Home Assistant long-lived access token from your user profile and set these values in G.R.A.C.E.'s `.env`:

```dotenv
GRACE_HOME_ASSISTANT_TOKEN=your-long-lived-access-token
GRACE_SMART_SWITCH_ENTITY_ID=switch.the_entity_id_shown_by_home_assistant
GRACE_SMART_SWITCH_NAME=Living room light
```

Use the entity ID shown in Home Assistant; it may be `switch.*` or `light.*`. Restart G.R.A.C.E. and use the **Light switch** card on the home page. The Pi and the G.R.A.C.E. host must be able to reach Home Assistant over the LAN. Never commit the token or `.env`.

G.R.A.C.E. connects through `http://homeassistant.local`, so no Home Assistant IP address needs to be stored in `.env`.
