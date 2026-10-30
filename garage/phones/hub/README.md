# Phone fleet hub

Run the hub on the tower, a supported Mac, or a Pi. Phones use the paired browser application and need no Python installation. The app shares the dashboard's cyan field-terminal / green biosphere design.

From the repository root:

```sh
python3 garage/install.py hub
garage/runtime/venv/bin/python garage/phones/hub/run.py pair garage-phone-a
garage/runtime/venv/bin/python garage/phones/hub/run.py pair garage-phone-b
garage/runtime/venv/bin/python garage/phones/hub/run.py --config garage/phones/hub/runtime/config.json serve
```

On Windows use `python` and `garage/runtime/venv/Scripts/python.exe`. Pairing prints one secret key per device; keep these outside Git. Pairing twice with the same name is rejected. Open `http://127.0.0.1:8790` locally and enter a device key. Different phones must use different keys for two-player matches.

For physical phones, expose the loopback server using authenticated private HTTPS, such as Tailscale Serve, then open its HTTPS URL on each phone. This repository does not configure Tailscale automatically. Explicit private-address binding is available with `serve --host YOUR-TAILSCALE-IP`; prefer HTTPS for browser integrity verification and future camera/microphone permissions. Do not expose this server to the public internet.

## Working browser features

- Photo capture/file picker, original image storage, project/caption metadata, content deduplication, and a shared gallery. JPEG/PNG/WebP up to 5 MiB and 20 MP; the file picker can capture on compatible phones. Upload times are separate from browser-supplied capture times. EXIF extraction, automatic interval capture, video streaming, and face recognition are not implemented.
- Device messages with optional photo attachment, stable retry IDs, offline browser queue, and explicit recipient acknowledgments. IndexedDB is required for offline queuing; keep browser storage until uploads finish. The server keeps originals and metadata in ignored `runtime/`, with a photo quota. No audio/intercom transport yet.
- Battle arena, chess with legal-move validation/clock/PGN, and a two-stage neural-network inference experiment. Phone-local agents are small JavaScript evaluators, not pretrained language models. A configured Ollama-compatible tower/cloud model can select battle/chess moves; invalid moves are rejected.
- Hub-relayed throughput test with at most 2 MiB/10 seconds. Recipient checks SHA-256 in the browser; HTTPS/localhost required. It does not measure direct Wi-Fi throughput. A separate synthetic fault fixture exercises bounded load/recovery; it cannot target arbitrary machines or perform network exhaustion attacks.
- Reviewed browser/diagnostic jobs for enrolled workers, results, and screenshots. Draft a plan with an optional model, review it, then queue it. A browser page cannot itself automate unrelated websites; install the worker on a supported host or configure an enrolled CDP browser.

Keep the phone browser foregrounded for heartbeats, automated play, and receiving benchmark chunks. OS background suspension is reported as offline; this is not a native background service. Browser requirements: current JavaScript, fetch, IndexedDB, and file APIs. Physical phone compatibility is still unverified until model/OS information is supplied.

## Models and operator jobs

Edit the ignored runtime config. `model.url` is an Ollama-compatible base URL, `model.name` selects an already installed model, and optional `model.token_env` names the credential environment variable. For cloud inference set both `cloud` and `allow_cloud_data` to true explicitly. Models receive game observations or the requested test prompt, not automatic uploads of the photo gallery. Source: [Ollama chat API](https://docs.ollama.com/api/chat).

`allowed_origins` contains the exact test website origins a worker may visit, including required asset origins. The default permits only the hub's local test fixture. Redirects/requests outside the job's allowed origins are blocked. Use test accounts and owned test sites; no unrestricted shell, purchases, or messaging actions are exposed by the worker.

All paired devices are trusted members of this personal lab and can see the shared photo gallery and job results. Use separate storage/configuration for mutually untrusted users. Back up `runtime/` separately. Run one hub per storage directory.
