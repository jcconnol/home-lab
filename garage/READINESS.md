# Garage release status

This is the authoritative distinction between software tested locally and hardware-specific work. A working software path does not mean an unknown old device has been tested or can run a particular model.

## Installable software paths

| Feature | Implemented path | Required setup / limits |
| --- | --- | --- |
| Dashboard and terrarium | Browser UI, saved ecosystem, care controls, notebook, history | Python host plus browser; Pi performance unmeasured |
| GRACE health | Independent HTTP/latency check | Configure tower URL; deep database/model health is not established by HTTP reachability |
| Digital radar / universe | TCP checks, paired agent heartbeats, host telemetry, optional observed-connection links | Configure services and/or fleet URL/key; it is not passive router-wide traffic capture |
| Weather / air / earthquakes / geomagnetic | Cached real feeds and statistical/threshold explanations | Configure location and enable sources; failures are explicit, cached stale readings are excluded from current anomaly results |
| Lightning | Adapter for a configured provider's timestamped coordinate reports | Provider URL/access still needed; no universal free source assumed |
| Satellite command | CelesTrak OMM, Skyfield SGP4 ISS passes and potential-visibility calculation | Location, internet, orbital/solar-file cache; clouds/obstructions not guaranteed |
| Apartment twin | Live read-only Home Assistant polling and room assignments | Home Assistant URL/token and entity/room configuration; physical floor plan and voice/object context remain to configure/build |
| Photo journal | Phone file/camera picker, original upload, shared gallery, deduplication, browser offline queue | Modern browser; 5 MiB/20 MP cap; no continuous video or face recognition |
| Phone messaging | Paired delivery, photo attachments, acknowledgments, offline retries | Keep client foregrounded; no audio intercom yet |
| Battle arena | Two real browser clients, legal simultaneous actions, saved rounds, local scripted/tower-model agents | Small local strategies are not pretrained phone LLMs |
| Chess | Authoritative rules, clocks, PGN, local evaluator or tower-model move selection | Local evaluator is a simple handcrafted engine; installable phone LLMs depend on hardware/runtime |
| Split neural network | Two browser devices execute distinct dense-network stages, with verified output | Tiny untrained demonstration network, not a distributed large language model |
| Throughput contest | Two browser clients exchange bounded chunks through the hub with SHA-256 checks | Relayed, not direct peer-to-peer Wi-Fi; HTTPS/localhost for browser hashing |
| Network attack/defense | Rate/byte/time-bounded disposable fault fixture with stop behavior | No unrestricted exhaustion/flood tooling or arbitrary remote targets |
| AI fleet operator | Reviewed structured plans, enrolled desktop/CDP worker, screenshots, page text, diagnostics | Optional Ollama-compatible model; actual phone CDP/iOS adapters depend on hardware and OS |

## Local verification

- Hardware-free unit/integration suite covers persistence, auth, message isolation/retries, game rules/clocks, split-stage validation, transfer integrity/limits, source failures, and Home Assistant fixtures.
- Two separate browser contexts exercise photo sharing, acknowledgments, offline replay, battle/chess moves, real per-browser dense-layer execution, and a separate browser worker with screenshot evidence.
- Dashboard views are checked at desktop and narrow widths. This is a browser viewport check, not a physical-phone compatibility claim.
- Official live-feed smoke checks use a public test location rather than assuming the user's home coordinates. Home Assistant credentials and a running inference server are not available for live checks; those paths use fixtures/validation and need deployment verification.
- No physical Pi, old Mac, old phone, camera mechanism, or robot has been connected or tested here.

## Required before declaring the entire idea list complete

Exact phone models/OS versions, Mac model/OS, Pi OS, camera/audio hardware, and the printed mechanism/actuator interface. These determine browser/automation support, native inference runtimes, and hardware drivers. Home location, a Home Assistant token, desired model endpoint, lightning provider, and Tailscale configuration are also deployment-specific inputs.

Still unimplemented: pretrained on-phone LLM deployment, a real large-model distributed runtime, physical phone-game actuation, continuous garage video, person recognition/greetings, audio intercom, and iOS/Safari remote automation. The generic software does not silently substitute simulations for these capabilities.
