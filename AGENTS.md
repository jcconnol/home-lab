# Repository Guidelines

## Codex Working Standards

These guidelines reduce common coding mistakes. Apply them with the repository-specific rules below; use judgment for trivial tasks.

### Think Before Coding

- State assumptions before implementation.
- Surface ambiguity and meaningful tradeoffs instead of choosing silently.
- Mention simpler approaches when they fit better.
- If a requirement is genuinely unclear or risky, stop and ask rather than guessing.

### Simplicity First

Implement the minimum requested behavior. Avoid speculative features, abstractions for one use, unnecessary configurability, and defensive handling of impossible scenarios. If the solution feels overcomplicated, simplify it.

### Surgical Changes

Change only what the request requires and match the existing local style. Do not refactor unrelated code or remove pre-existing dead code. Remove imports, variables, or helpers only when the current change makes them unused. Every changed line should trace to the request or to verification of that change.

### Goal-Driven Execution

Define success criteria and verify them. For multi-step work, state a short plan with a check for each step:

```text
1. Implement the change → verify: focused test
2. Check integration → verify: relevant command
3. Review the diff → verify: git diff --check
```

For bug fixes, reproduce the problem with a test before fixing it when practical. Do not claim completion until the relevant checks pass or their limitations are clearly reported.

## Project Structure

- `app/` contains the Python FastAPI service.
  - `main.py` defines HTTP routes and request models.
  - `config.py` reads `GRACE_*` environment settings.
  - `state.py` holds in-memory scene and event state.
  - `services.py` integrates optional YOLO vision and Ollama chat.
  - `web/index.html` is the current dashboard frontend.
- `initial_setup.md` is the MVP product specification.
- `IDEAS.md` is the future-capabilities backlog.
- `requirements.txt` lists backend dependencies; optional hardware/inference packages are documented there.
- Tests should live under `tests/` as the project grows.

## Development Commands

Create an environment and install dependencies:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Run the local service:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Compile-check Python files without starting integrations:

```powershell
python -m compileall -q app
```

Use `/docs` for FastAPI’s interactive API documentation.

## Coding Style

Use Python 3.11+ style, four-space indentation, `snake_case` for functions and variables, `PascalCase` for classes, and concise type annotations. Keep hardware integrations optional and fail gracefully when devices, models, or services are unavailable. Prefer small modules and explicit data structures over speculative abstractions.

## Testing Guidelines

Use `pytest` for unit and API tests when adding the test suite. Name files `test_*.py` and keep hardware-dependent tests marked or isolated so ordinary tests run without a camera, GPU, or Ollama. At minimum, run `python -m compileall -q app` and `git diff --check` before submitting changes.

## Commits and Pull Requests

The repository has no established commit history yet. Use short imperative commit subjects, such as `Add scene status endpoint` or `Document feeder safety rules`. Pull requests should explain the behavior change, list verification commands, call out hardware or configuration requirements, and include dashboard screenshots for visual changes.

## Security and Configuration

Never commit `.env`, credentials, camera footage, model weights, or health data. Use `.env.example` for documented defaults. Treat voice identification as a convenience signal; require a second factor for sensitive actions. Preserve local-only defaults and explicit approval for remote control or self-modifying behavior.
