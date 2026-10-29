# Phone communication mailboxes

A standard-library HTTP server with per-device bearer tokens, durable SQLite messages, and recipient acknowledgments. No phone browser client, audio transport, image attachments, or automatic pairing UI yet.

Run from this folder. Generate two different secret tokens (for example, run `python -c "import secrets; print(secrets.token_urlsafe(32))"` twice). Put them in environment variables, not committed files.

PowerShell:

```powershell
$env:GARAGE_DEVICE_TOKENS = '{"bench":"REPLACE_WITH_SECRET_TOKEN_ONE","camera":"REPLACE_WITH_SECRET_TOKEN_TWO"}'
python run.py
```

Linux/macOS:

```sh
export GARAGE_DEVICE_TOKENS='{"bench":"REPLACE_WITH_SECRET_TOKEN_ONE","camera":"REPLACE_WITH_SECRET_TOKEN_TWO"}'
python3 run.py
```

Replace the example strings with actual secrets. Defaults to `127.0.0.1:8761`; add `--host <host-tailscale-ip>` only after configuring your private network. Data lives under ignored `runtime/`. Run one server per database. Requests need `Authorization: Bearer <this-device-token>` and JSON bodies:

- `POST /messages` with `{"recipient":"camera","text":"Take a wiring photo"}` queues a message. The sender is determined from the token.
- `GET /messages` lists the latest 100 messages addressed to this device, including acknowledgment timestamps.
- `GET /sent` lists the latest 100 sent messages so a sender can check acknowledgments.
- `POST /ack` with `{"id":1}` acknowledges a message belonging to this recipient.

Offline recipients retain their mail until they poll. Queued is not delivered. Retry deduplication, pagination, attachments, presence tracking, and a phone-friendly client remain future work. Use short ordinary messages; do not send credentials through the demo. Requests are capped at 16 KiB. The private network/HTTPS deployment requirements are in [the garage run guide](../../README.md).
