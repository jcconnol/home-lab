# Local verification â€” 2026-10-29

Environment: Windows host, Python 3.10 isolated virtual environment, installed Microsoft Edge through Playwright. These results do not establish Pi performance or compatibility with unknown old phones/Mac operating systems.

## Automated checks

55 tests passed across `test_garage_projects.py`, `test_garage_dashboard.py`, and `test_garage_fleet.py`. Coverage includes saved-state restart, auth/session handling, original-photo integrity/deduplication, recipient isolation, retries, game legality/clocks, distributed-layer results, transfer integrity/stop limits, source caching/failures, Home Assistant fixtures, and model-output validation without unintended execution.

The Observatory browser check covers setup, saved units, aircraft/ISS/weather, solar rotation and Moon focus, body addition and source failures at 1440px, 1280x720 and 390px widths. The main board fits 1280x720 without scrolling. Separate phone regression checks cover photo sharing, acknowledgments, offline replay, battle/chess, distributed computation, bounded transfer and operator screenshots. No JavaScript page errors were reported.

The dashboard, hub, and operator installer roles completed locally using the workspace virtual environment. Python compilation, JavaScript syntax, and Git whitespace checks passed. The Linux background-service script has not been run on an actual Pi; no Mac/iOS service or native phone inference installation is claimed.

## Live source checks

Public test location: Boulder-area coordinates (40, -105), not the user's home. Successful requests/parsing for Open-Meteo weather and air quality, USGS earthquake summaries, NOAA planetary Kp, and CelesTrak/Skyfield ISS passes. Orbital and solar files were cached outside Git.

Home Assistant uses fixture tests because credentials/device access are unavailable. No local Ollama server was reachable, so model integration is tested against an Ollama-shaped local fixture with both valid and invalid responses. Real model quality, cloud credentials, lightning-provider access, and physical-device CDP behavior still need deployment checks.

Screenshots from the browser validation are saved under ignored `garage/runtime/validation/`. They show real local test state, with test-device names and fixture imagery; they are not camera footage or evidence of physical-phone testing.

## Observatory update

Live public Boulder-area checks also passed for adsb.lol aircraft, ISS position/passes and all 39 curated solar-system bodies using JPL Horizons/Skyfield. Source timestamps and partial failures are displayed; this is not a physical Pi performance test. New screenshots and optional live-check recordings are ignored under `garage/runtime/observatory-validation/`. Run `tests/garage_browser_check.py --board-only` for a scoped browser check and `tests/observatory_live_check.py --help` for the opt-in public-source check.
