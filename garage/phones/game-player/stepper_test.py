"""Run all three ULN2003 channels forward, pause, then reverse once."""
import argparse
import time

from robot import Driver, PINS


def run(driver):
    for direction, label in ((1, "Forward"), (-1, "Reverse")):
        print(f"{label}: all three drivers for 5 seconds", flush=True)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            for axis in PINS:
                driver.step(axis, direction)
            time.sleep(0.005)
        if direction == 1:
            print("Pause: 1 second (coils hold position)", flush=True)
            time.sleep(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Run timing without accessing GPIO")
    args = parser.parse_args()
    print("DRY RUN: no GPIO" if args.dry_run else "LIVE: all three driver channels receive signals", flush=True)
    # Apply each half-step to all axes, then wait once in run().
    driver = Driver(args.dry_run, delay=0)
    try:
        run(driver)
    except KeyboardInterrupt:
        print("\nInterrupted", flush=True)
    finally:
        driver.close()
        print("Finished; GPIO outputs released. Re-reference before normal use.", flush=True)


if __name__ == "__main__":
    main()
