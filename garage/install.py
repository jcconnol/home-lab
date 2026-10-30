"""Install isolated garage dependencies; never installs into the system Python."""
import argparse
import json
import platform
import subprocess
import sys
import venv
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("role", choices=("dashboard", "hub", "operator"))
    parser.add_argument("--browser", action="store_true", help="Download Chromium for the operator role")
    args = parser.parse_args()
    if sys.version_info < (3, 10):
        parser.error("Python 3.10 or later required; 3.11+ recommended")
    if args.browser and args.role != "operator":
        parser.error("--browser applies only to operator")
    directory = ROOT / "runtime" / "venv"
    python = directory / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")
    if not python.exists():
        venv.EnvBuilder(with_pip=True).create(directory)
    requirements = ROOT / ("operator-requirements.txt" if args.role == "operator" else "requirements.txt")
    subprocess.run([str(python), "-m", "pip", "install", "-r", str(requirements)], check=True)
    if args.browser:
        subprocess.run([str(python), "-m", "playwright", "install", "chromium"], check=True)
    if args.role == "dashboard":
        runtime = ROOT / "garage-dashboard/runtime"
        template = ROOT / "garage-dashboard/config.sample.json"
    elif args.role == "hub":
        runtime = ROOT / "phones/hub/runtime"
        template = ROOT / "phones/hub/config.sample.json"
    else:
        print(f'Installed. Run: "{python}" "{ROOT / "phones/fleet-operator/run.py"}" --help')
        return
    runtime.mkdir(parents=True, exist_ok=True)
    config = runtime / "config.json"
    if not config.exists():
        config.write_text(template.read_text(encoding="utf-8"), encoding="utf-8")
    script = ROOT / ("garage-dashboard/run.py" if args.role == "dashboard" else "phones/hub/run.py")
    suffix = " serve" if args.role == "hub" else ""
    print(json.dumps({"installed": args.role, "config": str(config), "run": f'"{python}" "{script}" --config "{config}"{suffix}'}, indent=2))


if __name__ == "__main__":
    main()
