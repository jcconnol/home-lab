# Local verification — 2026-10-29

Environment: Windows host, Python 3.10 isolated virtual environment, installed Microsoft Edge through Playwright. These results do not establish Pi performance or compatibility with unknown old phones/Mac operating systems.

## Automated checks

44 tests passed across `test_garage_projects.py`, `test_garage_dashboard.py`, and `test_garage_fleet.py`. Coverage includes saved-state restart, auth/session handling, original-photo integrity/deduplication, recipient isolation, retries, game legality/clocks, distributed-layer results, transfer integrity/stop limits, source caching/failures, Home Assistant fixtures, and model-output validation without unintended execution.

The browser check visits all 11 dashboard views at 1440px and 390px, checks horizontal layout, and exercises two distinct authenticated clients. It covers photo sharing, message acknowledgments, offline queue replay, battle and chess moves, actual browser-side layer computation, bounded relay transfer/SHA-256 verification, synthetic fixture failures/stop, and a separate browser worker returning a test-page screenshot. No JavaScript page errors were reported.

The dashboard, hub, and operator installer roles completed locally using the workspace virtual environment. Python compilation, JavaScript syntax, and Git whitespace checks passed. The Linux background-service script has not been run on an actual Pi; no Mac/iOS service or native phone inference installation is claimed.

## Live source checks

Public test location: Boulder-area coordinates (40, -105), not the user's home. Successful requests/parsing for Open-Meteo weather and air quality, USGS earthquake summaries, NOAA planetary Kp, and CelesTrak/Skyfield ISS passes. Orbital and solar files were cached outside Git.

Home Assistant uses fixture tests because credentials/device access are unavailable. No local Ollama server was reachable, so model integration is tested against an Ollama-shaped local fixture with both valid and invalid responses. Real model quality, cloud credentials, lightning-provider access, and physical-device CDP behavior still need deployment checks.

Screenshots from the browser validation are saved under ignored `garage/runtime/validation/`. They show real local test state, with test-device names and fixture imagery; they are not camera footage or evidence of physical-phone testing.
