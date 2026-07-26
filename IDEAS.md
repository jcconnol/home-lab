# G.R.A.C.E. ideas backlog

This file is a living list of future capabilities. Ideas should be promoted into a dated specification only when the hardware, safety model, and privacy boundaries are clear.

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

## Tony Stark-inspired command center

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

### Personality

Give G.R.A.C.E. a consistent, cool personality: calm, capable, lightly witty, technically clear, and honest about uncertainty.

Personality should be configurable separately from the system name, with controls for verbosity, humor, formality, and whether proactive notifications are enabled.

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

Build a wrist-worn interface with a microphone, speaker or bone-conduction output, a small display, and a physical mute/action control.

Potential interactions:

- Talk to G.R.A.C.E. while moving around the home.
- View alerts, camera snapshots, drone status, and feeder status.
- Trigger routines such as “lab mode” or “quiet mode.”
- Locate the phone, ask for a room view, or control music.

Start with a phone or smartwatch companion prototype before building custom hardware.

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

### 3D-printed camera glasses

Prototype lightweight 3D-printed glasses with a small camera and a phone connection so the user can interact with G.R.A.C.E. from a first-person view.

Possible flow:

1. The glasses camera sends a still image or short clip to the phone.
2. The phone handles connectivity, privacy controls, and local processing.
3. G.R.A.C.E. answers through the phone, earbuds, or a small glasses speaker.

Early prototypes should use a removable camera module, physical privacy shutter or disconnect, visible recording indicator, comfortable low-voltage components, and phone-side processing. Avoid continuous recording by default and clearly indicate when an image is being analyzed.

## Information and daily routines

### Weather integration

Give G.R.A.C.E. a local weather capability for current conditions, forecasts, severe-weather alerts, and outdoor planning.

Potential uses:

- Include weather in morning and afternoon briefings.
- Recommend indoor or outdoor workouts based on conditions.
- Suggest when to open or close windows.
- Warn about storms, extreme temperatures, or poor travel conditions.
- Use a cached forecast so basic information remains available during a short outage.

### Morning and afternoon briefings

Provide configurable daily briefings at wake-up and later in the day.

Morning briefing topics could include weather, calendar, Garmin recovery, workout recommendation, home status, and important alerts. The afternoon briefing could include schedule changes, network or system health, upcoming tasks, weather changes, and a reminder of unfinished priorities.

The user should control the time, delivery method, included topics, and whether G.R.A.C.E. is allowed to proactively speak.

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

1. Personality, music, and a polished dashboard.
2. Wi-Fi telemetry and event history.
3. Local wake word and wrist/phone interaction.
4. Cat feeder integration with safety limits.
5. Drone camera as a manually piloted, view-only experiment.
6. Carefully gated indoor autonomy and remote manual override.
7. Garmin data and daily workout recommendations.
8. Private phone app, followed by a camera-glasses prototype.
