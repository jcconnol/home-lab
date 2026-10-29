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
