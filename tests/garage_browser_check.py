"""End-to-end checks with two isolated browser clients; no physical devices claimed."""
import argparse
import base64
import io
import json
import tempfile
import time
from pathlib import Path

from PIL import Image
from playwright.sync_api import expect, sync_playwright

from test_garage_projects import GARAGE, load, serving


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--channel", default="msedge")
    parser.add_argument("--output", type=Path, default=GARAGE / "runtime/validation")
    parser.add_argument("--live-fixture", type=Path, help="Use recorded public-source data for screenshots; otherwise synthetic fixtures")
    parser.add_argument("--board-only", action="store_true", help="Validate only the observatory UI")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    hub, dashboard = load("phones/hub"), load("garage-dashboard")
    with tempfile.TemporaryDirectory(prefix="garage-browser-") as temporary:
        root = Path(temporary)
        store = hub.Store(root / "hub")
        first, second = store.pair("Camera terminal"), store.pair("Workbench terminal")
        with serving(hub.handler_factory(store)) as hub_url:
            store.config["allowed_origins"] = [hub_url]
            control = dashboard.Dashboard({}, root / "dashboard")
            from observatory_fixtures import snapshot
            fixture = json.loads(args.live_fixture.read_text(encoding="utf-8")) if args.live_fixture else snapshot()
            location = fixture["settings"]["location"]
            control.search_location = lambda query: [location]
            control.solar.search = lambda query: [{"id": "1000036", "name": "Test comet", "tracked": False}]
            with serving(dashboard.handler_factory(control)) as dashboard_url, sync_playwright() as playwright:
                browser = playwright.chromium.launch(channel=args.channel, headless=True)
                errors = []
                def page(context):
                    result = context.new_page()
                    result.on("pageerror", lambda error: errors.append(str(error)))
                    return result
                desktop = page(browser.new_context(viewport={"width": 1440, "height": 1050}))
                desktop.goto(dashboard_url)
                desktop.get_by_label("City or ZIP code").fill(location["name"])
                desktop.get_by_role("button", name="Find location", exact=True).click()
                desktop.locator("#location-results button").first.click()
                expect(desktop.locator("#setup")).to_be_hidden()
                assert control.snapshot()["configured"] is True
                with control.lock:
                    control.feeds = fixture["feeds"]
                desktop.reload()
                expect(desktop.locator("#weather")).to_contain_text("humidity")
                expect(desktop.locator("#aircraft-count")).not_to_have_text("—")
                expect(desktop.locator("#iss")).to_contain_text("km altitude")
                assert "terrarium" not in desktop.locator("body").inner_text().lower()
                assert "GRACE" not in desktop.locator("body").inner_text()
                desktop.get_by_role("button", name="°F / mph", exact=True).click()
                expect(desktop.locator("#units-button")).to_have_text("°C / km/h")
                expect(desktop.locator("#weather")).to_contain_text("°C")
                desktop.get_by_role("button", name="°C / km/h", exact=True).click()
                desktop.locator('nav a[href="#solar"]').click()
                desktop.locator('#solar-catalog button').filter(has_text="Moon").first.wait_for()
                desktop.get_by_role("button", name="Moon", exact=True).click()
                expect(desktop.locator("#solar-selected")).to_contain_text("From Earth")
                expect(desktop.locator("#solar-focus")).to_have_value("earth")
                desktop.locator("#solar-focus").select_option("sun")
                canvas = desktop.locator("#solar-canvas")
                canvas.focus()
                desktop.wait_for_timeout(150)
                before = canvas.evaluate("canvas => canvas.toDataURL()")
                desktop.keyboard.press("ArrowLeft")
                desktop.wait_for_timeout(150)
                assert before != canvas.evaluate("canvas => canvas.toDataURL()")
                desktop.screenshot(path=str(args.output / "solar-1440.png"), full_page=True)
                for width, height in ((1440, 1050), (1280, 720), (390, 844)):
                    desktop.set_viewport_size({"width": width, "height": height})
                    for view in ("board", "solar"):
                        desktop.locator(f'nav a[href="#{view}"]').click()
                        expect(desktop.locator("#"+view)).to_be_visible()
                        assert desktop.evaluate("document.documentElement.scrollWidth<=window.innerWidth"), (width, view)
                    desktop.locator('nav a[href="#board"]').click()
                    expect(desktop.locator("#board")).to_be_visible()
                    if width == 1280:
                        assert desktop.evaluate("document.documentElement.scrollHeight<=window.innerHeight+2"), desktop.evaluate("() => [...document.querySelectorAll('header,.toolbar,.board-grid,.panel,footer')].map(e=>({name:e.className,height:e.getBoundingClientRect().height,top:e.getBoundingClientRect().top}))")
                    desktop.screenshot(path=str(args.output / f"dashboard-{width}.png"), full_page=True)
                desktop.locator('nav a[href="#solar"]').click()
                desktop.get_by_label("Add another JPL body").fill("Test comet")
                desktop.get_by_role("button", name="Search JPL", exact=True).click()
                desktop.locator("#body-results button").first.click()
                expect(desktop.locator("#body-results")).to_be_empty()
                assert control.settings["extra_bodies"][0]["id"] == "1000036"
                with control.lock:
                    control.feeds["aircraft"] = dict(control.feeds["aircraft"], status="error", error="Test source outage")
                desktop.locator('nav a[href="#board"]').click()
                desktop.reload()
                expect(desktop.locator("#aircraft-status")).to_contain_text("last good data")
                if args.board_only:
                    browser.close()
                    assert not errors, errors
                    print(json.dumps({"views": ["local board", "3D solar system"], "widths": [1440, 1280, 390], "720p_no_scroll": True,
                                      "checks": ["location setup", "units", "forecast", "aircraft", "ISS", "3D rotation", "Moon focus", "add body", "source outage"], "page_errors": errors}))
                    return
                contexts = [browser.new_context(viewport={"width": 390, "height": 844}) for _ in range(2)]
                a, b = [page(context) for context in contexts]
                for client, identity in ((a, first), (b, second)):
                    client.goto(hub_url)
                    client.get_by_label("Device key").fill(identity["token"])
                    client.get_by_role("button", name="Connect", exact=True).click()
                    expect(client.locator("#device-name")).to_have_text(identity["name"])
                a.locator('nav a[href="#photos"]').click()
                image = io.BytesIO()
                Image.new("RGB", (50, 40), "#b7f85d").save(image, "PNG")
                a.locator('input[name="image"]').set_input_files({"name": "fixture.png", "mimeType": "image/png", "buffer": image.getvalue()})
                a.locator('input[name="caption"]').fill("Verified browser photo")
                a.get_by_role("button", name="Save original").click()
                b.locator('nav a[href="#photos"]').click()
                expect(b.locator("#photos")).to_contain_text("Verified browser photo", timeout=10000)
                a.locator('nav a[href="#messages"]').click()
                a.locator('#message-form select[name="recipient"]').select_option(second["id"])
                a.locator('#message-form input[name="text"]').fill("Inspect the workbench")
                a.get_by_role("button", name="Send message").click()
                b.locator('nav a[href="#messages"]').click()
                expect(b.locator("#messages")).to_contain_text("Inspect the workbench", timeout=10000)
                b.get_by_role("button", name="Acknowledge", exact=True).click()
                expect(a.locator("#messages")).to_contain_text("acknowledged", timeout=10000)
                contexts[0].set_offline(True)
                a.locator('#message-form input[name="text"]').fill("Offline dispatch")
                a.get_by_role("button", name="Send message").click()
                a.wait_for_timeout(300)
                contexts[0].set_offline(False)
                expect(b.locator("#messages")).to_contain_text("Offline dispatch", timeout=15000)
                for client in (a, b):
                    client.locator('nav a[href="#matches"]').click()
                a.get_by_role("button", name="Battle arena", exact=True).click()
                b.get_by_role("button", name="Join match", exact=True).wait_for(timeout=10000)
                b.get_by_role("button", name="Join match", exact=True).click()
                a.get_by_role("button", name="strike", exact=True).wait_for(timeout=10000)
                a.get_by_role("button", name="strike", exact=True).click()
                b.get_by_role("button", name="guard", exact=True).click()
                expect(a.locator("#matches")).to_contain_text("B: 11 HP", timeout=10000)
                a.get_by_role("button", name="Chess match", exact=True).click()
                b.get_by_role("button", name="Join match", exact=True).wait_for(timeout=10000)
                b.get_by_role("button", name="Join match", exact=True).click()
                a.locator('form[data-chess] select').wait_for(timeout=10000)
                a.locator('form[data-chess] select').select_option("e2e4")
                a.get_by_role("button", name="Play move", exact=True).click()
                b.locator('form[data-chess] select').wait_for(timeout=10000)
                b.locator('form[data-chess] select').select_option("c7c5")
                b.get_by_role("button", name="Play move", exact=True).click()
                a.get_by_role("button", name="Split neural network", exact=True).click()
                b.get_by_role("button", name="Join match", exact=True).wait_for(timeout=10000)
                b.get_by_role("button", name="Join match", exact=True).click()
                a.get_by_role("button", name="Compute my layer on this device").wait_for(timeout=10000)
                a.get_by_role("button", name="Compute my layer on this device").click()
                b.get_by_role("button", name="Compute my layer on this device").wait_for(timeout=10000)
                b.get_by_role("button", name="Compute my layer on this device").click()
                expect(a.locator("#matches")).to_contain_text("Verified output", timeout=10000)
                for mode in ("devices", "photos", "messages", "matches", "network", "operator"):
                    a.locator(f'nav a[href="#{mode}"]').click()
                    assert a.evaluate("document.documentElement.scrollWidth<=window.innerWidth"), mode
                a.locator('nav a[href="#matches"]').click()
                a.screenshot(path=str(args.output / "phone-matches.png"), full_page=True)
                a.locator('nav a[href="#devices"]').click()
                a.wait_for_timeout(150)
                a.screenshot(path=str(args.output / "phone-fleet.png"), full_page=True)
                b.locator('nav a[href="#network"]').click()
                b.get_by_label("Receive and verify chunks addressed to this device").check()
                a.locator('nav a[href="#network"]').click()
                a.locator('#benchmark-form select').select_option(second["id"])
                a.get_by_role("button", name="Start transfer", exact=True).click()
                deadline = time.monotonic() + 12
                while time.monotonic() < deadline:
                    transfers = store.benchmarks(first["id"])
                    if transfers and transfers[0]["acknowledged"] > 0:
                        break
                    a.wait_for_timeout(200)
                assert store.benchmarks(first["id"])[0]["acknowledged"] > 0
                assert store.benchmarks(first["id"])[0]["uploaded"] <= 2 * 1024**2
                a.get_by_role("button", name="Run fixture test", exact=True).click()
                expect(a.locator("#lab-progress")).to_contain_text("1 intentional fixture failures", timeout=10000)
                a.get_by_role("button", name="Stop test", exact=True).click()
                expect(a.locator("#lab-progress")).to_contain_text("Fixture stopped", timeout=10000)
                worker = load("phones/fleet-operator")
                specification = {"steps": [{"action": "goto", "url": hub_url + "/lab/page"},
                                             {"action": "fill", "selector": "#name", "text": "Garage"},
                                             {"action": "click", "selector": "#greet"},
                                             {"action": "assert_text", "text": "Hello Garage"}, {"action": "screenshot"}],
                                 "allowed_origins": [hub_url]}
                # A separate browser worker is exercised after closing the active Playwright context below.
                browser.close()
            result = worker.execute(specification, browser_channel=args.channel)
            assert result["status"] == "passed", result.get("error")
            identifier = store.create_job(first["id"], {"device": second["id"], "spec": specification})["id"]
            store.claim_job(second["id"])
            store.finish_job(second["id"], {"id": identifier, "result": result})
            assert store.jobs()[0]["result"]["artifact"]
            assert not errors, errors
    print(json.dumps({"dashboard_views": ["local board", "3D solar system"], "viewports": [1440, 390], "two_browser_clients": True,
                      "checks": ["location setup", "weather and forecast", "aircraft radar", "ISS", "3D rotate and planet focus", "add JPL body", "source outage", "photo transfer", "message acknowledgment", "offline queue replay", "battle", "chess moves", "split inference", "bounded relay transfer", "fixture faults and stop", "operator browser job and screenshot"], "page_errors": errors}))


if __name__ == "__main__":
    main()
