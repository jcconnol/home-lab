# Garage application visual language

Garage Observatory uses its own `garage-dashboard/web/board.css`: a compact dark sky/weather instrument panel. Phone apps retain `garage-dashboard/web/style.css`. The Pi display has no game or phone controls. The solar canvas redraws on interaction/data updates rather than continuous animation.

- Deep blue-black surfaces, a static technical grid, angular frames and corner brackets, compact monospace telemetry, and clear status labels.
- Cyan for command/network surfaces, lime for the living biosphere, amber for experiments/arena, and violet for space modes.
- Keep the actual measurement scope and stale/unknown states legible. No invented traffic, temperatures, uptime, or diagnostic charts to make a screen look busy.
- Prefer static CSS/SVG to continuous particle systems, blur filters, 3D scenes, or GPU-heavy effects on the Pi 2. Preserve keyboard focus and narrow-screen navigation.

Visual validation: run `tests/garage_browser_check.py` with the operator/test environment. Screenshots are written under ignored `garage/runtime/validation/` so they can be reviewed without committing local device information.
