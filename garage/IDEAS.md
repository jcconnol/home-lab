# Garage lab ideas

This is a planning backlog, not a list of implemented features. Treat `home-lab` as the monorepo for GRACE and the devices it coordinates. The garage is a location/project containing multiple devices, rather than the name of one Raspberry Pi.

## Organization

Keep the existing tower service in `app/` and phone app in `mobile_app/`. As garage components are implemented, put their code and instructions under `garage/`, with folders such as `camera-node/`, `workbench-display/`, and `sensors/`. Give physical devices stable names in configuration so several devices can run the same component without duplicated code.

Each component should document its supported hardware/OS, dependencies, local configuration, setup, run, and restart/update steps. On ordinary Linux devices, the intended workflow is clone once, pull updates, and run the component for that device. Install only that component's dependencies. Keep credentials, recordings, generated audio, model weights, and runtime data outside Git.

## Available hardware and possible jobs

| Hardware | Possible role | Still to confirm |
| --- | --- | --- |
| Tower running GRACE | Vision models, person recognition, language model, speech generation, event history, dashboard | Available compute and model latency |
| Raspberry Pi Zero | Garage camera and audio playback node | Exact Zero model, camera, network connection, speaker/audio hardware |
| Raspberry Pi 4 running Home Assistant OS | Existing home automation and garage sensor/lighting integration | Available integrations; use supported apps/add-ons for extra services |
| Raspberry Pi 2 | Door/environment sensor gateway, buttons, status lights, or a small display | OS, networking, and chosen peripherals |
| Old Mac | Garage console, local event storage, or service host when the tower is unavailable | Model, supported OS, storage, and power use |
| Old phones | Extra camera angles, touch panels, microphones, speakers, or portable inspection cameras | OS versions, app/browser support, battery condition, and charging arrangement |

These are candidate assignments, not requirements to use every device immediately. Home Assistant OS needs its own deployment approach rather than a generic host setup script.

## Core garage monitoring

- See the latest garage image, its capture time, and whether each camera is online. Show stale/offline state clearly instead of presenting an old image as live.
- Request a fresh snapshot; later add live video and short event clips if useful.
- Track garage-door open/closed state, vehicle arrival/departure, motion, and how long the door has been open. Prefer a door contact sensor for actual door state, with vision as supporting context.
- Ask GRACE questions such as "How is the garage doing?", "Did I leave the door open?", "When did the car arrive?", and "What changed since this morning?"
- Keep a timestamped event timeline and optional daily summary, with configurable retention and local storage outside the repo.
- Add temperature, humidity, water-leak, and device-health readings as sensors become available.

## Garage voice and presence

- Camera node sends snapshots or event clips to the tower; the tower performs most processing and returns audio for a garage speaker.
- Recognize enrolled household members and say things such as "Hello Elizabeth" when someone arrives. Use opt-in enrollment, a confidence threshold, and a greeting cooldown; uncertain recognition gets a generic greeting.
- Support quiet hours, volume limits, mute, and a visible camera/microphone state. Keep camera framing within the intended garage area.
- Add push-to-talk first: "GRACE, where did I put the socket wrench?" or "Read me the next step." Explore a wake word later.
- Choose the output device explicitly: garage speaker, old phone, Mac, or the requesting device.
- Treat identity recognition as a convenience signal. It must not by itself authorize opening the garage door or other sensitive actions.

## Remote check-in from outside home

Goal: sign in from a phone away from home and see garage status, current snapshots, recent events, and eventually live video. Start with viewing; consider remote physical controls separately.

- Candidate first approach: a private Tailscale connection between the personal phone and the supported host serving GRACE. Keep application sign-in and permissions as well as network access controls. Tailscale supplies connectivity; GRACE still needs to serve the dashboard.
- If a device cannot run Tailscale, consider a supported always-on host as a subnet router, granting access only to the needed destinations.
- Home Assistant's hosted remote-access option is an alternative for its own dashboard; it does not automatically publish the separate GRACE service.
- Do not forward the development server or unauthenticated camera streams directly onto the public internet. Use supported, updated hosts for the remote entry point.
- Acceptance check: with Wi-Fi disabled on the viewing phone, sign in, request a new snapshot, verify its timestamp, view recent events, and confirm an unauthorized device/account cannot access them.
- Show camera, tower, and connection failures separately. If the tower is asleep or offline, say so; an always-on Mac fallback is a later option if its OS can be supported.

References: [Tailscale device connectivity](https://tailscale.com/docs/how-to/connect-to-devices), [subnet routing for devices without Tailscale](https://tailscale.com/docs/use-cases/personal-or-at-home-use/access-devices-without-tailscale), [Home Assistant remote access](https://www.home-assistant.io/docs/configuration/remote/).

## Mad-scientist garage experiments

| Idea | What it does | Devices / first experiment |
| --- | --- | --- |
| The garage has a personality | GRACE delivers configurable arrival lines, project commentary, and a theatrical shutdown announcement | Tower generates speech; Zero or phone plays it. Start with one arrival greeting. |
| Mission control wall | Old phones become dedicated gauges: camera, weather, project checklist, device status, and a large "lab nominal" indicator | Mac serves a dashboard; phones display individual panels. Start with two screens. |
| "Where is my thing?" memory | Remember the last observed location of tools and show the supporting image and timestamp | Overhead phone/camera plus tower vision. Start with a fixed bench and three distinctive tools. |
| Garage black box | Reconstruct a project session as a timelapse and searchable event timeline: "Show the moment I removed that bracket" | Multiple phones/cameras and Mac storage. Start with one camera and manual session start/stop. |
| Portal between rooms | Two old phones act as a deliberate, push-to-talk audiovisual window between garage and house | Two phones plus GRACE signaling. Start with a call button and visible active state. |
| Exploded-view workbench | Take a photo of a disassembled object, label parts, and build a reassembly checklist with linked photos | Phone camera, tower model, Mac display. Start with manual labels and uncertain suggestions marked clearly. |
| Tool checkout tribunal | The lab politely interrogates you when a tool leaves its marked spot and celebrates its return | Camera or tagged tools, tower, speaker. Start with one tool and a printed marker. |
| Experiment flight recorder | Synchronize video, sensor readings, spoken notes, and a big physical "mark that" button | Pi 2 button/sensors, phone video, Mac timeline. Start with timestamped button events and notes. |
| Parking spacecraft HUD | Show a vehicle's approach on a phone display with distance bars and ridiculous docking announcements | Dedicated distance sensor, Pi, phone, speaker. Start with a parked-car test; retain ordinary driver judgment. |
| Tiny robot lab assistant | A slow rover carries a camera and gives a remote tour of the garage | Later rover hardware, phone/Zero camera, tower vision. Start with supervised manual driving and a stop control. |
| Reality-change detector | Compare the bench before and after a session and narrate what appeared, disappeared, or moved | Fixed camera and tower. Start with side-by-side images before automated interpretation. |
| Interdimensional scavenger hunt | GRACE invents puzzles tied to tagged bins, tools, screens, and lights around the garage | Printed markers, phone camera, Pi buttons, Home Assistant lights. Start with three manually authored clues. |
| Scientific instrument from junk phones | Use phone cameras and available sensors for vibration logging, close-up inspection, or comparing repeated experiments | One phone and Mac plots. First verify which sensors and capture controls that phone exposes. |
| Lab quest engine | Turn a real project into steps, timers, inventory checks, and dramatic mission updates across the wall screens | Tower, Mac, phones, speaker. Start with a manually written project checklist. |

The ambitious version combines these: walk in, get greeted, see the garage state on a wall of reused screens, ask where a part went, and replay the experiment that moved it.

## Component idea lists

- [Garage dashboard](garage-dashboard/IDEAS.md): Pi 2 monitor, artificial-life terrarium, anomaly observatory, network radar, and space command center.
- [Phones](phones/IDEAS.md): shared photo journal, device communication, and tower-controlled game phone with 3D-printed hardware.

## Suggested first build

1. Inventory exact device models, operating systems, cameras, audio connections, and usable power/network locations.
2. Bring up one camera node and show a fresh timestamped snapshot in GRACE; verify reconnect/offline behavior.
3. Add authenticated remote viewing and test from cellular data.
4. Send one tower-generated voice line back to the garage, then add arrival detection and greeting cooldowns.
5. Turn the Mac and one old phone into mission control, then choose the next experiment from actual use.
