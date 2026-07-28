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

## 2026-07-28

### Dashboard capability set

- Added provider-neutral music playback commands and local playback state at `/api/music`.
- Added manually triggerable and schedulable morning/afternoon briefings composed from scene, memory, and weather data.
- Added local JSON persistence for personal memories, preferences, deletion, and export.
- Added a mobile command-center overview for music, weather, memory, watch mode, and briefing state.
- Added persistent network scan telemetry summaries while retaining local-only discovery behavior.
- Added Grace settings controls for personality, voice mode, and sensitive-action confirmation.
- Added mobile dashboard navigation for each capability.

External speaker playback remains an adapter handoff: commands work locally and identify where a provider must be configured.
