"""Enrolled desktop/CDP browser worker with telemetry and bounded test jobs."""
import argparse
import base64
import importlib.util
import json
import os
import platform
import shutil
import socket
import time
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("fleet_jobs", ROOT / "jobs.py")
jobs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(jobs)


def request(hub, token, route, data):
    req = urllib.request.Request(hub.rstrip("/") + route, data=json.dumps(data).encode(),
                                 headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.load(response)


def telemetry(connections=False):
    import psutil
    result = {"kind": "host agent", "platform": platform.platform(), "host": platform.node(),
              "cpu_percent": psutil.cpu_percent(), "memory_percent": psutil.virtual_memory().percent,
              "disk_free_gb": round(shutil.disk_usage(Path.home()).free / 1024**3, 2), "boot_time": psutil.boot_time()}
    counters = psutil.net_io_counters()
    result["network_bytes"] = {"sent": counters.bytes_sent, "received": counters.bytes_recv}
    result["addresses"] = [address.address for addresses in psutil.net_if_addrs().values() for address in addresses
                           if address.family == socket.AF_INET and not address.address.startswith("127.")]
    temperatures = getattr(psutil, "sensors_temperatures", lambda: {})()
    result["temperatures_c"] = {key: [item.current for item in values] for key, values in temperatures.items()}
    if connections:
        try:
            result["connections"] = [{"local": list(item.laddr), "remote": list(item.raddr), "status": item.status}
                                     for item in psutil.net_connections(kind="inet") if item.raddr][:100]
        except (psutil.AccessDenied, OSError) as error:
            result["connections_error"] = type(error).__name__
    return result


def execute(specification, cdp=None, browser_channel=None):
    from playwright.sync_api import sync_playwright
    specification = jobs.validate(specification, specification.get("allowed_origins", []))
    started = time.monotonic()
    errors, steps = [], []
    result = {"status": "failed", "steps": steps, "console_errors": errors}
    with sync_playwright() as playwright:
        browser = playwright.chromium.connect_over_cdp(cdp) if cdp else playwright.chromium.launch(headless=True, channel=browser_channel)
        context = browser.contexts[0] if cdp else browser.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=False)
        page = context.new_page()
        page.set_default_timeout(5000)
        def guard(route):
            try:
                permitted = jobs.origin(route.request.url) in specification["allowed_origins"]
            except ValueError:
                permitted = route.request.url.startswith(("data:", "blob:"))
            route.continue_() if permitted else route.abort()
        page.route("**/*", guard)
        page.on("pageerror", lambda error: errors.append(str(error)[:1000]))
        try:
            for step in specification["steps"]:
                if time.monotonic() - started > 55:
                    raise TimeoutError("Job time budget exhausted")
                action = step["action"]
                if action == "goto":
                    page.goto(step["url"], wait_until="domcontentloaded", timeout=10000)
                elif action == "click":
                    page.locator(step["selector"]).click()
                elif action == "fill":
                    page.locator(step["selector"]).fill(step["text"])
                elif action == "assert_text":
                    page.get_by_text(step["text"], exact=False).first.wait_for()
                if page.url != "about:blank" and jobs.origin(page.url) not in specification["allowed_origins"]:
                    raise ValueError("Navigation left the allowed origins")
                steps.append({"action": action, "status": "passed"})
            result.update(status="passed" if not errors else "failed", summary=f"Completed {len(steps)} steps", title=page.title(),
                          page_text=page.locator("body").inner_text()[:12000], final_url=page.url)
        except Exception as error:
            result["error"] = str(error)[:3000]
        finally:
            try:
                result["screenshot"] = base64.b64encode(page.screenshot(type="png", full_page=False, timeout=5000)).decode()
            except Exception as error:
                result["screenshot_error"] = str(error)[:500]
            page.close()
            if not cdp:
                context.close()
                browser.close()
    result["elapsed_seconds"] = round(time.monotonic() - started, 3)
    result["execution_host"] = platform.node()
    result["browser_path"] = "remote CDP browser" if cdp else "worker-host Chromium; not a physical phone"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hub", default="http://127.0.0.1:8790")
    parser.add_argument("--cdp", help="Explicitly enrolled local Chrome remote-debugging URL")
    parser.add_argument("--browser-channel", choices=("chrome", "msedge"), help="Use an installed desktop browser instead of bundled Chromium")
    parser.add_argument("--connections", action="store_true", help="Opt in to reporting observed host network connections")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    token = os.environ.get("GARAGE_DEVICE_KEY")
    if not token:
        parser.error("Set GARAGE_DEVICE_KEY to this worker's paired device key")
    last_heartbeat = 0
    while True:
        try:
            if time.monotonic() - last_heartbeat >= 10:
                request(args.hub, token, "/api/heartbeat", telemetry(args.connections))
                last_heartbeat = time.monotonic()
            job = request(args.hub, token, "/api/jobs/claim", {})["job"]
            if job:
                result = {"status": "passed", "summary": "Device diagnostics captured", "telemetry": telemetry(args.connections)} if job["kind"] == "diagnostics" else execute(job["spec"], args.cdp, args.browser_channel)
                request(args.hub, token, "/api/jobs/finish", {"id": job["id"], "result": result})
                print(json.dumps({"job": job["id"], "status": result["status"]}), flush=True)
        except Exception as error:
            print(json.dumps({"error": str(error)}), flush=True)
            if args.once:
                raise SystemExit(1)
        if args.once:
            return
        time.sleep(3)


if __name__ == "__main__":
    main()
