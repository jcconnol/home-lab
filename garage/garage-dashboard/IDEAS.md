# Garage dashboard ideas

Use the Pi 2 and its monitor as a lightweight dashboard terminal. The tower or supported Mac collects data, stores history, runs simulations, and prepares updates. Start with a simple 2D browser display; measure performance on the actual Pi before adding animation or large graphs. Provide selectable modes and an optional rotation, with real alerts visible across modes. These are proposed features, not existing integrations.

## Dashboard idea list

Independent Python starters live in the folders below. A [browser dashboard](README.md) now renders these modes, with a working terrarium, notebook, and configured service checks. Imported-data modes still need their source files; automatic live-feed integrations remain future work. See [the garage run guide](../README.md) for commands and current limitations.

1. [Artificial-life terrarium](terrarium/README.md).
2. [Local and planetary anomaly observatory](anomaly-observatory/README.md).
3. [Digital radar for the home network](network-radar/README.md).
4. [Satellite and space command center](space-command/README.md).
5. [Garage universe driven by device status](garage-universe/README.md).
6. [Signal detective](signal-detective/README.md) for correlated service and network events.
7. [Time machine wall](time-machine/README.md) for reviewing recorded history.
8. [Daily science missions](science-missions/README.md).
9. [Digital twin of the apartment](apartment-twin/README.md).
10. [GRACE health status](grace-health/README.md).

## GRACE health status

- Show an at-a-glance healthy, degraded, unavailable, or unknown status, with the last successful check and a plain-language explanation.
- Check the GRACE API, database, model service, Home Assistant connection, camera nodes, and voice nodes independently. Distinguish disabled integrations from failed ones.
- Display uptime, recent errors, request latency, and model queue/activity where instrumentation is available; link tower resource readings from the network radar.
- Keep a short incident/recovery timeline and show stale data explicitly. If GRACE itself is down, the independently hosted dashboard should still report that failure.
- First milestone: stop a test GRACE instance, verify the dashboard detects it, then restart it and verify recovery is shown.

## Digital twin of the apartment

A room-by-room map showing existing Zigbee lights, device states, and automation activity. Start with a lightweight 2D floor plan suitable for the Pi 2; consider an optional 3D view after measuring performance.

- Place Home Assistant entities on the map using their stable entity IDs and room assignments. Show light on/off state, brightness where available, device availability, and last update.
- Show recent automation activity in the relevant room, including its trigger and outcome when reported by the source. Distinguish requested actions from confirmed device state.
- Let users select a room or device to see details and history. Begin with a read-only map; any later controls use the same authentication and permissions as the rest of GRACE.
- Eventually connect GRACE object tracking: show last observed locations, observation times, and confidence rather than implying a continuously known position.
- Add voice-node locations, availability, mute state, and current playback/interaction state.
- Explore context-aware room behavior through explicit rules, such as an opted-in arrival greeting or task lighting. Show which observation and rule caused an action, with manual override and cooldowns.
- First milestone: place the existing Zigbee lights on a manually configured floor plan and verify that changes made through Home Assistant appear in the correct room, including unavailable/stale state.

## Artificial-life terrarium

A persistent simulated ecosystem that can be watched and cared for over weeks. Creatures forage, rest, reproduce, compete, and adapt within simple rules; plants grow and resources cycle. Give the inhabitants recognizable appearances and let the user follow individual lineages.

- Care controls: add food, plant vegetation, provide shelter, adjust light and water, and introduce a species. Make consequences visible rather than requiring constant attention.
- Display births, population trends, food availability, habitat conditions, family trees, and notable events such as a new trait spreading.
- Start with plants, herbivores, food/energy accounting, and a day/night cycle; add predators, inheritance, mutation, and multiple habitats later.
- Save simulation state and event history on the host. Define offline behavior explicitly: start with pausing while the simulation host is off, rather than unexpectedly losing the ecosystem.
- Keep the simulation independent of the language model. GRACE can narrate recorded events, but should not invent ecological changes or control every creature through model calls.
- Optional "alien weather" mode maps selected real weather or space-weather measurements into bounded simulation effects. Label that mapping as fictional and make it opt-in.
- First milestone: care for a saved ecosystem, restart the host, and resume the same inhabitants; show why a population is thriving or declining.

## Local and planetary anomaly observatory

Monitor public weather, earthquakes, lightning, geomagnetic conditions, and air quality. Explain what is unusual relative to the chosen location, season, recent history, and source coverage, rather than showing only current readings.

- Event examples: unusually rapid pressure change, a temperature departure from the local baseline, a nearby earthquake, a burst of lightning activity, elevated particulate readings, or increased geomagnetic activity.
- Every card should answer: what changed, where and when, how unusual it is, which measurements support it, and when the source last updated.
- Use deterministic checks or statistical baselines to identify candidate events. Give GRACE the actual readings and source links to explain them, separating observations, possible explanations, and uncertainty.
- Deduplicate related updates into one evolving event. Use cooldowns and severity levels so the screen stays useful during an active storm.
- Choose public feeds during implementation after checking coverage, access terms, update frequency, and location. Lightning data in particular may have access or coverage limits; a remote air-quality station does not measure the garage itself.
- Missing data is "unknown," not normal conditions. Distinguish global context from events near home, and coincident events from demonstrated causes.
- This is an informational experiment; show official alerts separately and link to their original source.
- First milestone: one location, weather and one additional feed, historical readings, and one reproducible anomaly explanation with source timestamps.

## Digital radar for the home network

An interactive map of owned computers, services, containers, and IoT devices, with a calm overview and drill-down details.

- Nodes show online/offline state, last seen, role, service health, and reported CPU/memory/disk use. Track containers only on hosts that explicitly expose that inventory.
- Edges distinguish configured relationships, observed traffic, and inferred relationships. A ping or network discovery result alone does not reveal which devices are communicating.
- Collect device heartbeats, service checks, optional host agents, and router/flow telemetry where supported. Restrict discovery to configured home-network ranges.
- Flag changes such as a new device, a normally available service disappearing, repeated restarts, rising disk use, or unusual traffic relative to that device's baseline.
- Keep stable identities and friendly names; account for DHCP changes and randomized phone addresses before calling something a new device.
- Start with a small inventory and status list, then add an interactive graph. Clicking a node opens its history and supported metrics; do not require a continuously animated graph on the Pi.
- No new hardware is assumed, but communication/traffic visibility depends on existing router capabilities or host instrumentation.
- First milestone: map the tower, Mac, Pis, and selected services; stop a test service and verify the correct node changes state with a timestamp.

## Satellite and space command center

- Display ISS and selected satellite positions, predicted passes for the configured observing location, astronomical events, and solar/geomagnetic activity.
- Distinguish a satellite being above the horizon from a potentially visible pass. Visibility predictions need observer location, lighting geometry, fresh orbital data, and an indication that clouds can spoil the view.
- Show countdowns, sky direction, elevation, prediction freshness, and an observation log. Use appropriate astronomy calculations rather than a language model to compute passes.
- Add explicitly simulated missions: select a pass, assign an old phone as the observation notebook, prepare a checklist, and record whether the satellite was actually seen.
- A themed "mission control" display can show fictional objectives alongside real telemetry, with simulation labels. It does not imply control of actual satellites.
- First milestone: one location, one satellite, a sourced pass prediction, and a manual observation log. Verify predictions against a trusted independent reference before adding alerts.

## Other observatory experiments

- **Garage universe:** each device becomes a planet; uptime, resource use, and service health change its appearance. Clicking it reveals real metrics, while the cosmetic mapping stays separate from the terrarium's ecology.
- **Signal detective:** correlate network slowdowns, host load, and service failures on one timeline, then propose testable explanations with the supporting evidence.
- **Time machine wall:** scrub through a day of garage events, network state, weather, and terrarium history, with independent source timestamps and visible gaps.
- **Daily science mission:** pick one observable event, predict an outcome, collect readings or an observation, and compare the prediction with what happened.

Build these as independent modes so a failed public feed or paused terrarium cannot interrupt garage monitoring. A sensible dashboard prototype is device status plus the terrarium, followed by one anomaly feed and then satellite passes.
