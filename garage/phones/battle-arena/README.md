# Two-phone battle arena

A working software referee and scripted bot client. Each side can later be driven by a phone-local model, a tower model, or hardware observations. This starter does not install models, control motors, or run in a phone browser.

## Run a match on the tower first

From this folder, generate two unique secret tokens of 24+ characters. For example, run `python -c "import secrets; print(secrets.token_urlsafe(32))"` twice. In a server terminal set `BATTLE_TOKEN_A` and `BATTLE_TOKEN_B`, then run:

```sh
python run.py serve
```

Set environment variables with `$env:BATTLE_TOKEN_A = 'your-secret'` in PowerShell or `export BATTLE_TOKEN_A='your-secret'` in Linux/macOS. Repeat for B.

In two separate client terminals, set `BATTLE_TOKEN` to A's token in the first and B's token in the second:

```sh
python run.py bot --seed 1
```

Use a different seed for the second bot. Both clients choose valid moves until the referee declares a winner or draw. Each stops if a round stalls for 120 seconds. It prints move summaries and the final state including the replay history. Restarting the referee resumes `runtime/match.json`, including a partially submitted round. For a new match use a new path: `python run.py serve --state runtime/second-match.json`. Do not run two servers against the same file.

For real-device trials, explicitly bind the server to its Tailscale address with `--host` and pass `--url http://<host-tailscale-ip>:8762` to clients. The actual phone must have a compatible Python environment or a future native/browser client. Tailscale setup and phone compatibility are not implemented here.

## Rules and model interface

Both players start at 12 HP and 3 energy. Each submits exactly one hidden action per round. Both actions resolve together:

| Action | Effect |
| --- | --- |
| `strike` | Costs 2 energy; deals 4 damage, or 1 against guard |
| `guard` | Reduces this round's incoming strike damage |
| `charge` | Adds 2 energy, capped at 5 |
| `repair` | Costs 3 energy; heals 2 HP, capped at 12, before damage |

Zero HP loses; simultaneous knockout draws. After 50 resolved rounds the higher HP wins, with equal HP drawing. The referee validates energy, duplicates, stale rounds, and finished matches. It does not trust a model to report victory.

All API calls require `Authorization: Bearer <player-token>`:

- `GET /state`: current round, both players' stats, your player ID, whether you submitted, and resolved-round history. Pending action choices are not exposed.
- `POST /action`: `{"round":1,"action":"strike"}`. Identity comes from the token, not the request body. Fetch state again after an error; do not blindly retry an old round.

A model adapter only needs to read state, select a legal action, and submit it. The included bot uses seeded random choice rather than inference. A future spectator dashboard can render resolved history; no separate spectator identity or visual client exists yet.

## Hardware direction

Use the same referee pattern for phone-brained tabletop robots: observe, choose a bounded command, execute, then verify using independent observations. Begin with non-contact competitions such as marker capture or zone control. Actual mechanisms, scoring sensors, motor limits, and a stop control need specification before any driver is added. Keep the software arena working independently.
