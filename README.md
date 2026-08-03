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

## HTTPS and phone microphone setup

Phone browsers require HTTPS before a LAN website can use the microphone. Install the dependencies, then start the secure server:

```powershell
pip install -r requirements.txt
powershell -NoProfile -ExecutionPolicy Bypass -File .\start-https.ps1
```

On the phone, first open `http://<your-computer-ip>:8000/certificate` using the temporary HTTP server. Download and trust the public G.R.A.C.E. certificate using the instructions on that page. Then use `https://<your-computer-ip>:8443` for the app and grant microphone permission when prompted.

Certificates and private keys are generated under the ignored `.certs/` directory. Never commit or share `.certs/grace-ca-key.pem` or `.certs/grace-server-key.pem`. If the computer's LAN IP changes, rerun `py scripts/create_https_cert.py`; it keeps the same phone-trusted CA and replaces only the server certificate.

When a feature is complete and validated, the workflow calls for staging the feature files, reviewing the staged diff, committing with a focused message, and pushing to the GitHub `main` branch. Any authentication, remote, or branch-policy blocker should be recorded in `JOHNS_TODO.md`.

See [initial_setup.md](initial_setup.md) for the product specification and phased roadmap.

See [IDEAS.md](IDEAS.md) for the longer-term robotics, interface, networking, personality, media, pet-care, and wearable backlog.
