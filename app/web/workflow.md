# Workflow for Implementing Ideas

When someone says, "implement this idea," use this order:

1. Confirm the feature scope from the request and the backlog item.
2. Identify what is local-only, what is optional, and what depends on an external account, API key, device, or approval.
3. Build the largest safe local version first.
4. Validate quickly with the lightest useful check.
5. If something is blocked, write the blocker in `JOHNS_TODO.md` and stop at the best safe point.
6. Once the feature is complete and checks pass, add the changed files, commit them, and push the commit to the GitHub `main` branch.

## Build Rules

- Prefer a working local path over a perfect integration.
- Keep hardware integrations optional.
- Use mock data or simulation when a device or service is not available.
- Do not block the rest of the build on sign-up flows, secret creation, or physical hardware.
- Leave a clear handoff whenever outside input is needed.
- Keep commits focused on the completed feature and use a short imperative message (for example, `Add weather fallback panel`).
- Before pushing, confirm the intended remote and branch, review the staged diff, and run the relevant checks.
- If GitHub authentication, remote configuration, branch protection, or another external condition prevents the push, record the exact command or access needed in `JOHNS_TODO.md` after preserving the local commit.

## Completion and Git Handoff

A feature is complete when its local implementation is usable, its quick validation passes, and any remaining external dependency is documented in `JOHNS_TODO.md`. Then use this handoff:

```powershell
git add <feature-files>
git diff --cached --check
git commit -m "<short imperative feature message>"
git push origin main
```

Do not commit secrets, `.env` files, credentials, camera footage, model weights, or health data. If the repository uses a different remote name, protected branch, or pull-request policy, follow that repository policy and record the required John action in `JOHNS_TODO.md`.

## Per-Feature Workflow

### Easy local features

- Personality
  - Build: prompt, settings, and simple preference handling.
  - Validate: send a few local chat requests and confirm the output changes.
- Weather integration
  - Build: local weather panel with a provider abstraction and cached response path.
  - Validate: load the UI and confirm the fallback state works before any API key exists.

### Moderate features

- Music playback
  - Build: local playback controls and command parsing.
  - Validate: exercise play, pause, and stop paths with the available backend.
- Morning and afternoon briefings
  - Build: compose summaries from existing local state and schedule them.
  - Validate: manually trigger a briefing and check the output content.
- Personal memory and preferences
  - Build: local persistence, edit controls, export, and reset.
  - Validate: save a preference, reload, and confirm it persists.
- Cinematic command center
  - Build: a clearer dashboard for status, controls, and summaries.
  - Validate: confirm the main views stay reachable on desktop and phone.
- Network awareness
  - Build: local device discovery, privacy-safe reporting, and summary views.
  - Validate: scan the local network or use stubbed device data if needed.

### Challenging features

- Always-listening keyword
  - Build: wake-word pipeline, microphone state, and mute controls.
  - Validate: confirm the listening state changes cleanly and can be turned off.
- Garmin activity integration
  - Build: a data sync adapter and local summary view.
  - Validate: use stubbed activity data until the account connection exists.
- Automated cat feeder
  - Build: scheduling, safety limits, and device abstraction.
  - Validate: run the schedule in dry-run mode before any physical feeder is attached.

### Hard features

- Private personal phone app
  - Build: a mobile-friendly client, local auth, and network access.
  - Validate: open the app from a phone on the same network.
- Voice identity guardrail
  - Build: speaker verification plus a second approval signal for sensitive actions.
  - Validate: test enrollment and rejection paths with local sample voices.
- Wrist tool
  - Build: a companion UI and a hardware communication contract.
  - Validate: exercise the UI and message flow before any custom device exists.
- Remote manual drone control
  - Build: simulator-first controls, video handling, and connection loss failsafes.
  - Validate: confirm stop and disconnect behavior before real hardware is used.

### Very hard features

- 3D-printed camera glasses
  - Build: camera pipeline, battery-aware controls, and privacy indicators.
  - Validate: confirm the capture path and on-device status indicators first.
- Controlled self-improvement
  - Build: sandboxed execution, approval gates, tests, and rollback.
  - Validate: prove the approval flow and rollback logic with simulated changes.
- Autonomous indoor drone
  - Build: indoor localization, obstacle avoidance, docking, and safety controls.
  - Validate: simulation first, then staged hardware testing with strict limits.

## When A Feature Gets Blocked

Write the blocker in `JOHNS_TODO.md` when the work needs one of these:

- An account or sign-in flow.
- A new API key or service credential.
- Physical hardware, sensors, or a device on the network.
- A safety, privacy, or approval decision from John.

Keep the blocked item short and specific:

- what is needed,
- why it is needed,
- what already works locally,
- and what should happen next once the missing piece is available.
