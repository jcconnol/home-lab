# Garage application visual language

Direction: a precise sci-fi field terminal with an unruly alien laboratory inside it. All shipped browser apps share `garage-dashboard/web/style.css`; phone-specific layout extends that base rather than introducing a different theme.

- Deep blue-black surfaces, a static technical grid, angular frames and corner brackets, compact monospace telemetry, and clear status labels.
- Cyan for command/network surfaces, lime for the living biosphere, amber for experiments/arena, and violet for space modes.
- Terrarium inhabitants, alien plants, and a clearly cosmetic portal are drawn as lightweight SVG. These are visualization elements, not claims of measured physical phenomena.
- Keep the actual measurement scope and stale/unknown states legible. No invented traffic, temperatures, uptime, or diagnostic charts to make a screen look busy.
- Prefer static CSS/SVG to continuous particle systems, blur filters, 3D scenes, or GPU-heavy effects on the Pi 2. Preserve keyboard focus and narrow-screen navigation.

Visual validation: run `tests/garage_browser_check.py` with the operator/test environment. Screenshots are written under ignored `garage/runtime/validation/` so they can be reviewed without committing local device information.
