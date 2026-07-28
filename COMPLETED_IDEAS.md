# Completed ideas

This file records backlog ideas that have been implemented and validated.

## 2026-07-27

### Personality

- Added `GRACE_PERSONALITY` configuration.
- Included the personality in Ollama prompts.
- Kept the default calm, capable, lightly witty, technically clear, and uncertainty-aware style.

### Weather integration

- Added a read-only Open-Meteo current-weather integration.
- Added configurable location, coordinates, and cache duration.
- Added a cached `/api/weather` endpoint and `/weather` chat command.
- Added a refreshable weather card to the dashboard.
- Offline or unconfigured weather fails gracefully without affecting the dashboard.
