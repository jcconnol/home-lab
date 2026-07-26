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

See [initial_setup.md](initial_setup.md) for the product specification and phased roadmap.

See [IDEAS.md](IDEAS.md) for the longer-term robotics, interface, networking, personality, media, pet-care, and wearable backlog.
