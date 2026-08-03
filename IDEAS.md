# G.R.A.C.E. ideas backlog

This file is a living list of future capabilities. Ideas should be promoted into a dated specification only when the hardware, safety model, and privacy boundaries are clear.

## First priority ideas

1. **[Authentication-first UI refactor](UI_REFACTOR.md)** — require sign-in before showing app content, persist secure long-lived sessions across server restarts, and present a role-aware dashboard containing only the features each user may access.

2. **IR TV and Apple TV control** — add an IR sensor/transmitter pointed at the TV and Apple TV so the user can log into Grace from a phone, press controls in the app, and have Grace control common media and power functions.
3. **Standalone wearable Grace controller** — explore a watch, armband, or similar phone-independent device for quick Grace interactions, potentially including gesture controls, a physical action button, microphone, and audio or haptic feedback.

## Difficulty-ranked backlog

The ideas below remain grouped by domain for readability. This ranking orders every idea from easiest to most difficult based on the effort to deliver a safe, private, reliable home-lab version (not merely a prototype).

### Level 2 — Moderate


### Level 3 — Challenging

9. **Always-listening keyword** — continuous local audio processing, clear microphone state, and mute controls.
10. **Garmin activity integration** — third-party data access, local health-data handling, and explainable recommendations.
11. **Smart wall-plug control** — device discovery, local protocols, safe switching, schedules, and failure reporting.
12. **Automated cat feeder** — physical-device integration with durable scheduling, limits, sensing, and failure alerts.

### Level 4 — Hard

13. **Private personal phone app** — a secure mobile client, push/voice features, and remote access.
14. **Voice identity guardrail** — speaker verification plus reliable second-factor and permission workflows.
15. **Spatial wrist-mount home-lab controller** — a companion-device or custom-hardware integration with a wrist-mounted display, spatial interaction, audio, battery, and physical controls for operating G.R.A.C.E. around the lab.
16. **Remote manual drone control** — secure remote control, video, loss-of-connection failsafes, and physical safety.

### Level 5 — Very hard

17. **Integrated camera/display glasses** — comfortable 3D-printed frames combining a camera, an ESP32 controller, and a monocular waveguide optics module, with phone integration and clear privacy indicators.
18. **Controlled self-improvement** — sandboxing, approval gates, testing, secure rollback, and strict safety boundaries.
19. **Autonomous indoor drone** — indoor localization, obstacle avoidance, docking, reliable autonomy, and high safety risk.

## Newly requested ideas

### Voice conversation (Level 2 - Moderate)

Let the user talk to Grace from the phone and hear Grace's response without typing. Start with an explicit push-to-talk control in the mobile web app/PWA: capture a short voice message, convert it to text, send the text through the existing Grace chat flow, and play Grace's response using text-to-speech.

Requirements:

- Keep microphone access opt-in and visibly indicate recording, processing, and playback states.
- Do not enable continuous listening or wake-word detection as part of this feature.
- Prefer local/browser speech recognition and synthesis where supported; provide a clear fallback when a phone or browser does not support them.
- Preserve the same conversation history and authentication rules as typed chat.
- Keep recordings transient by default, do not retain raw audio unless explicitly enabled, and provide a stop/mute control.
- Allow voice playback to be disabled or interrupted at any time.
- Let the user choose whether Grace speaks through the device that captured the request or through configured computer speakers; show the active output destination and require explicit opt-in before routing audio to another device.

### Grace settings home page (Level 2 - Moderate)

Add a dedicated home page where the user can review and edit Grace's personality, response style, preferred name, enabled capabilities, privacy defaults, and connected integrations. Changes should be previewable, validated, and saved locally. Sensitive settings should require confirmation, and the page should show the current configuration, reset controls, and an audit trail of changes.

### Smart wall-plug control (Level 3 — Challenging)

Connect Grace to compatible smart wall plugs so it can report power state and perform approved on/off actions. Start with local-network protocols and an explicit device-pairing step. Each plug should have a friendly name, room, current state, and safety policy. Require confirmation for potentially disruptive actions, provide schedules and timeout safeguards, and report unreachable devices or failed commands clearly.

## Home presence and robotics

### Autonomous indoor drone

Build a small indoor drone with a camera that can navigate to a requested room and provide a live view.

Example: “G.R.A.C.E., show me the kitchen.”

Possible capabilities:

- Room-to-room navigation using visual markers, maps, or fixed beacons.
- Live video returned to the dashboard or wrist tool.
- Docking station for charging.
- Low-battery return-to-dock behavior.
- Obstacle avoidance and a strict indoor flight boundary.
- Manual emergency stop that always takes priority over autonomy.

Safety requirements:

- Start with tethered or manually piloted experiments.
- Use propeller guards, geofencing, speed limits, and no-fly zones around people, pets, stairs, and fragile objects.
- Do not enable autonomous flight when the drone cannot localize reliably.
- Keep recording and remote control visibly indicated.

### Remote manual drone control

Allow an authenticated user to manually override the drone from the remote website while away from home.

Design requirements:

- Authenticated, encrypted access through a deliberate remote-access gateway.
- Manual control must have a local emergency stop and a failsafe on connection loss.
- Show battery, signal strength, flight mode, and camera status before enabling controls.
- Default to “view only”; flight control should require an explicit unlock.

## Cinematic command center

Create a one-stop system overview with a polished cinematic interface inspired by a high-tech lab console.

Potential panels:

- G.R.A.C.E. status and personality greeting.
- Camera feeds and room presence.
- Drone location, battery, and flight mode.
- Wi-Fi health and network traffic.
- Home devices, automations, and alerts.
- Cat feeder status and feeding history.
- GPU, CPU, memory, storage, and temperature telemetry.
- Event timeline with severity and acknowledgement controls.

The visual style should remain readable and practical: dark panels, restrained accent colors, clear status states, keyboard accessibility, and a “calm mode” alongside the cinematic mode.

## Network awareness

Have G.R.A.C.E. monitor Wi-Fi and traffic across the home lab.

Possible capabilities:

- Connected-device inventory with friendly names.
- Signal strength, uptime, latency, and bandwidth trends.
- Local traffic summaries by device and protocol.
- Alerts for unknown devices, outages, unusual traffic, or bandwidth spikes.
- Historical graphs and exportable diagnostics.

Privacy boundary: collect metadata by default, avoid packet contents, and make retention and data sharing configurable.

## Conversational interaction

### Always-listening keyword

Add a local wake-word system so the user can say “G.R.A.C.E.” and receive a prompt such as, “What can I do for you?”

Suggested progression:

1. Push-to-talk browser control.
2. Local wake-word detection with no audio leaving the home.
3. Speech-to-text only after activation.
4. Visible listening, processing, and muted states.

The microphone should remain muted or locally buffered until the wake word is detected, with an immediate physical mute option.

## Media and household assistance

### Music playback

Allow G.R.A.C.E. to play, pause, skip, queue, and announce music through configured speakers.

Future integrations could include local files and supported music services. The system should identify the active room/speaker and require confirmation for destructive playlist changes.

### Automated cat feeder

Connect a timed or motorized feeder so G.R.A.C.E. can dispense food and report hopper, jam, and battery status.

Requirements:

- Scheduled feeding must work without the LLM or internet.
- Enforce daily quantity limits and cooldowns.
- Require confirmation for extra portions.
- Keep a feeding log and provide a physical manual control.
- Alert when food was not dispensed successfully.

## Wearable interface

### Wrist tool

Build a spatial wrist-mounted home-lab controller with a microphone, speaker or bone-conduction output, a small display, and physical mute/action controls. It should provide quick access to G.R.A.C.E. status, nearby devices, camera views, and lab routines without requiring a phone.

Potential interactions:

- Talk to G.R.A.C.E. while moving around the home.
- View alerts, camera snapshots, drone status, and feeder status.
- Trigger routines such as “lab mode” or “quiet mode.”
- Locate the phone, ask for a room view, or control music.

Start with a phone or smartwatch companion prototype before building custom hardware.

Possible spatial interactions:

- Point, tap, or use a gesture to select a nearby device or dashboard panel.
- Show directional prompts for rooms, tools, alerts, or the drone's location.
- Use a physical action button and visible screen state for confirmation of hardware actions.

### Workshop VR helmet

Design and 3D-print a workshop helmet or protective headgear that integrates VR or mixed-reality viewing with other lab interfaces.

Possible capabilities:

- Hands-free access to G.R.A.C.E. status, instructions, timers, and camera views.
- Optional passthrough or visor display for overlays while working at the bench.
- Voice, gesture, or wrist-controller interaction with a physical emergency/mute control.
- Modular mounts for lighting, audio, tracking, or other sensors without obstructing safety equipment.

Safety requirements:

- Do not compromise impact, electrical, respiratory, or eye protection for electronics or 3D-printed mounts.
- Keep overlays unobtrusive and provide an immediate clear-vision mode.
- Start with a removable non-protective prototype before attaching anything to certified protective equipment.

## Personal health and fitness

### Garmin activity integration

Import the user's Garmin data into a private G.R.A.C.E. profile and use it to provide a daily workout recommendation.

Useful inputs could include:

- Recent activities, duration, pace, distance, and intensity.
- Heart-rate trends and recovery indicators.
- Sleep, stress, body battery, and training load where available.
- Calendar availability, preferred activities, and current goals.
- User feedback such as soreness, energy, and whether a workout was completed.

Example interaction:

> “G.R.A.C.E., what should I do today?”

> “Your recovery looks moderate and you had a hard run yesterday. I recommend 30 minutes of easy cycling or a rest day with mobility work.”

Design requirements:

- Store health data locally by default and make synchronization opt-in.
- Let the user inspect, correct, export, and delete imported data.
- Explain why a recommendation was made and allow the user to override it.
- Treat recommendations as general fitness guidance, not medical advice.
- Avoid recommending intense training when recovery, illness, injury, or user feedback suggests rest.

### Private personal phone app

Create a phone app dedicated to the user's G.R.A.C.E. instance rather than relying only on the browser dashboard.

Possible first features:

- Secure chat and voice interaction.
- Daily workout card and Garmin sync status.
- Camera view requests and snapshots.
- Music, home routines, cat feeder, and system alerts.
- Push-to-talk button and optional local wake-word support.
- Remote access through an authenticated, encrypted connection.

The phone should be the primary companion-device prototype before custom wearable hardware is built.

### Remote mobile companion (Level 4 — Hard)

Provide a mobile app that can securely connect to this Grace instance from outside the home Wi-Fi so the owner can chat, save memories, and receive answers while away. Prefer an AWS-hosted relay or gateway when it simplifies deployment, but keep the tower private and allow other providers if they provide a clearer security or maintenance model.

Requirements:

- Use authenticated, encrypted connections with short-lived tokens and a revocable device list.
- Keep the home server behind an outbound connection or deliberate tunnel rather than exposing an unauthenticated port.
- Limit remote capabilities by default; require explicit approval for hardware controls and sensitive data.
- Support offline queueing only for non-sensitive requests, with clear sync status.
- Document AWS cost, secrets, logging, retention, and an easy disconnect/purge process.

### Cat communicator (Level 4 — Hard)

Let the owner send a voice memo from the phone to a speaker at home so the cat can hear it, with optional local playback confirmation. Start with one-way playback and avoid treating the feature as a reliable way to monitor or control an animal.

Requirements:

- Authenticate the phone and home receiver; do not expose the speaker directly to the internet.
- Show whether the tower is online and whether playback completed.
- Add a local volume limit, cooldown, and physical mute/stop control to avoid startling or distressing the cat.
- Keep recordings local by default, set an automatic retention period, and provide delete/export controls.
- Consider a later two-way audio mode only after privacy, echo, and animal-welfare testing.

### Integrated glasses with waveguide display

Prototype lightweight 3D-printed frames with a small camera and a simple, single-color monocular HUD so the user can interact with G.R.A.C.E. from a first-person view. The display path would be:

`Raspberry Pi or phone → display driver board → single-color micro-OLED → collimating lens → waveguide or mirror → eye`

Possible flow:

1. The glasses camera sends a still image or short clip to the phone.
2. The phone handles connectivity, privacy controls, and local processing.
3. G.R.A.C.E. answers through the phone, earbuds, or a small glasses speaker.

Hardware direction:

- Use the phone or a Raspberry Pi as the display source and application processor, depending on the prototype's size, power, and connectivity requirements.
- Use a dedicated driver board between the source device and the micro-OLED; keep the display intentionally single-color to reduce optical and software complexity.
- Route the emitted image through a collimating lens and then into a waveguide or mirror combiner positioned in front of one eye.
- Treat the optical system as a monocular notification and prompt display rather than a full-vision replacement.

Early prototypes should use a removable camera module, physical privacy shutter or disconnect, visible recording indicator, comfortable low-voltage components, and phone-side processing. Avoid continuous recording by default and clearly indicate when an image is being analyzed.

## Information and daily routines

### Morning and afternoon briefings

Provide configurable daily briefings at wake-up and later in the day.

Morning briefing topics could include weather, calendar, Garmin recovery, workout recommendation, home status, and important alerts. The afternoon briefing could include schedule changes, network or system health, upcoming tasks, weather changes, and a reminder of unfinished priorities.

The user should control the time, delivery method, included topics, and whether G.R.A.C.E. is allowed to proactively speak.

### Calendar integration

Connect G.R.A.C.E. to the user's calendar so it can answer schedule questions and include upcoming commitments in briefings.

Possible capabilities:

- Read today's and upcoming events, including start time, duration, location, and reminders.
- Answer questions such as “What is next?” or “Am I free this afternoon?”
- Include upcoming events in morning and afternoon briefings.
- Add, edit, or cancel events only after explicit confirmation.
- Support a local calendar first, with opt-in providers such as Google or Microsoft 365 later.

Privacy and safety requirements:

- Keep calendar data local by default and request the minimum read/write permissions.
- Show the connected account, granted scopes, last synchronization time, and stored data.
- Require confirmation before creating, changing, or deleting an event.
- Provide a disconnect, purge, and export control.

### Personal memory and preferences

Let G.R.A.C.E. remember useful personal preferences such as favorite music, rooms, routines, workout style, device names, communication style, and recurring tasks.

Requirements:

- Show what was remembered and why.
- Allow individual memories to be edited or deleted.
- Keep sensitive memories local by default.
- Support temporary conversations that are not remembered.
- Let the user set retention periods and export the memory store.

### Controlled self-improvement

Allow the user to tell G.R.A.C.E. to improve its prompts, skills, configuration, or code, but keep self-editing bounded and reviewable.

Possible workflow:

1. G.R.A.C.E. explains the proposed change in plain language.
2. It creates a backup or Git branch.
3. It runs tests and a security check in a sandbox.
4. It shows the diff and waits for approval before activation.
5. It supports rollback to the previous known-good version.

Core safety rules, access controls, backups, and emergency-stop behavior should not be editable by the model without explicit direct approval.

## Identity and permissions

### Voice identity guardrail

Use a local voice-identification or speaker-verification layer so G.R.A.C.E. can distinguish the owner from other people in the home.

Permission levels could include:

- **Owner:** configuration, private data, remote access, self-edit proposals, purchases, and hardware controls.
- **Trusted user:** approved home, music, and routine controls.
- **Guest:** general questions and limited, non-sensitive interactions.
- **Unknown speaker:** no privileged actions.

Voice recognition should be treated as a convenience signal rather than perfect authentication because recordings and imitation can bypass it. Sensitive actions should require a phone confirmation, PIN, physical button, or another second factor. Include a physical mute switch, visible listening indicator, access logs, and an easy way to revoke permissions.

## Suggested order

1. Music and a polished dashboard.
2. Wi-Fi telemetry and event history.
3. Local wake word and wrist/phone interaction.
4. Cat feeder integration with safety limits.
5. Drone camera as a manually piloted, view-only experiment.
6. Carefully gated indoor autonomy and remote manual override.
7. Garmin data and daily workout recommendations.
8. Private phone app, followed by a camera-glasses prototype.
