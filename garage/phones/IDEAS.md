# Garage phone ideas

Treat the old phones as individually named devices with different capabilities, rather than assuming they all support the same software. Coordinate them through the tower initially; direct phone-to-phone connections can be explored if needed.

## Runnable project starters

- [Photo journal](photo-journal/README.md): local original-photo import, deduplication, and project listing.
- [Communication](communication/README.md): paired HTTP mailboxes and recipient acknowledgments.
- [Game player](game-player/README.md): timestamp-checked action proposals; no hardware execution yet.
- [Phone battle arena](battle-arena/README.md): a playable two-agent software arena with persistent rounds and example agents.

## Several phones form one larger neural network

- Explore model partitioning: each phone stores and executes a different group of layers, passing intermediate activations to the next phone. Together they perform inference for one model rather than running unrelated copies.
- Start with a tiny fixed neural network split across two devices, verify that its output matches an unsplit reference, and measure communication time separately from computation time.
- Inventory phone OS, memory, supported inference runtimes, and networking before choosing a model or partition format. Different devices may need different layer allocations.
- Distinguish aggregate memory capacity from speed: intermediate tensors, repeated token-by-token transfers, and heterogeneous phones can make a distributed model slower than a single host. Model size does not automatically equal better answers.
- Keep a coordinator responsible for ordered execution, request IDs, tensor shape/type validation, timeouts, and reporting a missing stage. A disconnected phone should fail the request clearly rather than fabricate an output.
- Later investigate pipeline scheduling, quantized activation transfer, and a dashboard showing which layers run on each phone, stage latency, and memory usage.
- This is an experimental research idea; no distributed runtime or phone model deployment is implemented yet.
- First milestone: two compatible phones execute separate stages of one small network, reproduce the reference output within a defined numeric tolerance, and report end-to-end latency.

## Two phones battle each other

- Start with a software arena: each phone receives its observation, chooses an action, and submits it to an authoritative referee. Separate tokens identify the two players; hide pending moves until both have committed.
- The starter uses scripted agents choosing strike, guard, charge, or repair. Small on-device models or tower models can later replace action selection without changing the referee's rules.
- Confirm phone model, OS, and available memory before choosing a local inference runtime. Model installation and on-device inference are not implemented yet.
- Later add model-versus-model tournaments, strategy comparisons, narrated replays, and a spectator display.
- Hardware version: phones can be the brains/cameras of two small 3D-printed tabletop robots. Start with a non-contact contest such as reaching a marker, claiming colored zones, or aiming light at a target. Confirm chassis, sensors, and actuators before adding drivers.
- Keep the referee independent of model claims and score observable outcomes. For moving hardware, bound speed/travel, provide a stop control, and stop on stale observations or lost connection.
- First milestone: two separately authenticated agents complete and replay a software match. Test those clients on the actual phones before adding models or motors.

## Phone-to-phone throughput competition

- Pair two or more phones for timed transfers in both directions, then compare useful bytes delivered, latency under load, fairness, retransmissions where observable, and energy/temperature readings where supported.
- Add tournament modes: fastest verified file transfer, best throughput within a bandwidth budget, or lowest latency while both sides send traffic. Verify received content rather than trusting a sender's claimed score.
- Record whether the path is direct Wi-Fi, through the access point, or through a VPN/relay. Shared radio airtime, signal strength, and background traffic can affect results independently of the phone's software.
- First milestone: one short, rate-limited transfer between two explicitly paired phones, with byte counts, duration, and a dashboard result. No throughput generator is implemented yet.

## Chess with a model on each phone

- Each phone runs its own chess engine or compatible small model and sends moves to a shared referee. Keep inference local to the phones when testing that mode; label tower/cloud-assisted entrants separately.
- The referee owns board state, legal-move validation, clocks, draw rules, and results. Invalid model moves should trigger a defined retry/time penalty rather than change the board.
- Compare dedicated chess engines, language models, and hybrid strategies under equal time or compute budgets. Save move history and PGN replays for the Pi dashboard.
- First milestone: two agents finish a legal game through the referee, with a replay and explicit handling of invalid moves and disconnections. Phone inference support remains to confirm.

## Isolated network attack-and-defense arena

- Explore phone-versus-phone bandwidth competition, connection/resource exhaustion, and recovery as controlled lab matches against deliberately provisioned test services on owned devices.
- Put the contestants on a separate test network with an explicit destination allowlist. Keep the household network, Home Assistant, GRACE's normal services, and unrelated internet hosts outside the arena.
- A referee sets traffic, connection, duration, and resource budgets, monitors both contestants and the network, and provides an independent stop control. Stop when a budget is exceeded or monitoring is lost.
- Score useful service availability, response latency, successful legitimate requests, detection time, and recovery time. Start with bounded load tests and synthetic failure injection before exploring more adversarial strategies.
- Preserve match logs and distinguish actual target failure from a congested shared access point or failed observer. Models may choose from approved test actions; they do not get unrestricted network or shell access.
- First milestone: a short bounded load test against one disposable lab service, verified automatic stop, and a recovery report. This is an idea only; no attack or exhaustion tooling is implemented or run here.

## AI operator for the old-device fleet

- Let a local or cloud AI coordinate explicitly enrolled phones, the old Mac, and Pis: open approved websites, click through test flows, run approved jobs, and gather screenshots, page text, browser errors, timings, and device-health information.
- Use actual old-device browsers to test responsive layouts, touch targets, compatibility, and performance. A desktop browser resized to phone dimensions is a separate test category, not a substitute for the physical phone.
- Keep a coordinator on the tower or another supported host, with a small authenticated device agent or supported automation connection on each device. Check the OS and browser's automation capabilities before choosing adapters.
- Give jobs a device, allowed sites/actions, time limit, expected result, and artifact destination. Record what the operator attempted, what actually happened, and why it stopped; report offline devices and unsupported actions clearly.
- Begin with read-only inspection and test accounts. Require explicit approval for purchases, sending messages, destructive changes, or other consequential actions; website content cannot expand the operator's permissions.
- Keep credentials on the device or in an appropriate secret store. For cloud models, explicitly choose what screenshots/page content may leave the network and redact sensitive material before uploading.
- Treat website instructions and downloaded content as untrusted input. Separate observations from executable commands; use allowlisted job types rather than unrestricted AI-generated shell commands.
- First milestone: ask the operator to open an owned test website on two enrolled devices, complete a harmless navigation flow, and return device-labeled screenshots and pass/fail evidence. Fleet control and cloud integration are not implemented yet.

## Shared photo journal

- Capture photos from each phone and organize them by device, project, session, and capture time. Preserve the original image and distinguish capture time from upload time.
- Queue uploads while disconnected and avoid duplicate entries when a phone reconnects. Keep originals outside Git with a defined backup and retention policy.
- Add captions, tags, search, and links to project notes. Tower-generated descriptions should remain editable and distinguish inferred details from user-provided facts.
- Compare photos across a build: first assembly, wiring changes, print results, and final state. Let a phone show a reference photo captured by another phone.
- First milestone: take photos on two phones, upload them to one project timeline, and retrieve the original image from either device.

## Phones that communicate and cooperate

- Send named-device messages, photos, project instructions, and acknowledgments through GRACE: "Send this wiring photo to the workbench phone."
- Add push-to-talk audio between stations, a call/request-attention button, and visible connection/mute state.
- Coordinate capture sessions across camera angles. Record timestamps and actual timing differences; do not claim precise synchronization without measuring it.
- Give each phone a role such as overhead camera, close-up camera, reference display, or game camera, and show its last check-in and supported actions on the dashboard.
- Start with authenticated, explicitly paired devices and a small set of supported messages. Verify browser/background behavior on each phone before relying on unattended operation.
- First milestone: send a photo and a text instruction from one phone to another and receive an acknowledgment, with clear failure state if the recipient is offline.

## Tower model plays games on a phone

An in-progress hardware idea: one phone is being paired with 3D-printed parts so a model running on the tower can play games on it. The printed mechanism and input method still need to be documented; do not assume software control or a particular actuator.

- Build an observe-decide-act loop: capture the phone's game state, send it to the tower, choose a bounded action, apply that action through the chosen interface, and observe the result.
- Possible interfaces to evaluate: a camera observing the screen with physical touch actuators, or supported screen capture and software input on a compatible phone. Choose based on the actual print and phone.
- Show the live game view, selected action, model explanation if available, score, latency, and recent action history on the Pi dashboard.
- Start with a simple offline game, one action at a time, and manual approval. Add autonomous play only after observation, action accuracy, and stop behavior work reliably.
- If the mechanism touches the screen, define travel/force limits and a stop control before unattended testing. Pause on stale images or lost connection instead of repeating an action indefinitely.
- Compare models or strategies using repeated runs and recorded outcomes. Keep model-reported success separate from observed game results.
- Other phones can act as spectators, scoreboards, alternate camera angles, or human controllers challenging the tower.
- First milestone: document the printed mechanism, capture one game state, execute one intended action, verify its result, and stop reliably.
