"""Interactive, manually referenced three-axis ULN2003 controller."""
import argparse
import json
import shlex
import time
from pathlib import Path

PINS = {"x": (5, 6, 13, 19), "y": (12, 16, 20, 21), "z": (17, 18, 22, 23)}
SEQUENCE = ((1, 0, 0, 0), (1, 1, 0, 0), (0, 1, 0, 0), (0, 1, 1, 0),
            (0, 0, 1, 0), (0, 0, 1, 1), (0, 0, 0, 1), (1, 0, 0, 1))
CONFIG = Path(__file__).parent / "runtime/robot.json"


class Driver:
    def __init__(self, dry_run, delay):
        self.delay = delay
        self.phase = dict.fromkeys(PINS, 0)
        self.outputs = {}
        if not dry_run:
            from gpiozero import OutputDevice
            try:
                for axis, pins in PINS.items():
                    self.outputs[axis] = []
                    for pin in pins:
                        self.outputs[axis].append(OutputDevice(pin, initial_value=False))
            except Exception:
                self.close()
                raise

    def step(self, axis, direction):
        self.phase[axis] = (self.phase[axis] + direction) % len(SEQUENCE)
        for output, value in zip(self.outputs.get(axis, ()), SEQUENCE[self.phase[axis]]):
            output.value = value
        if self.outputs:
            time.sleep(self.delay)

    def close(self):
        for outputs in self.outputs.values():
            for output in outputs:
                output.close()


class Robot:
    def __init__(self, driver, config):
        self.driver = driver
        self.config = config
        self.position = dict.fromkeys(PINS, 0)
        self.referenced = False
        self.active = False

    def configure(self, x, y, z, touch):
        if min(x, y, z, touch) <= 0 or touch > z:
            raise ValueError("Limits must be positive; touch must be within Z travel")
        self.config = {"limits": dict(zip(PINS, (x, y, z))), "touch": touch}
        self.active = False
        self.referenced = False

    def jog(self, axis, steps):
        if axis not in PINS or abs(steps) > 100:
            raise ValueError("Jog requires x/y/z and at most 100 half-steps")
        if self.active:
            raise ValueError("Pause before jogging")
        if self.referenced:
            self.move(axis, self.position[axis] + steps)
        else:
            self._steps(axis, steps)

    def _steps(self, axis, steps):
        try:
            for _ in range(abs(steps)):
                self.driver.step(axis, 1 if steps > 0 else -1)
                self.position[axis] += 1 if steps > 0 else -1
        except BaseException:
            self.active = False
            self.referenced = False
            raise

    def move(self, axis, target):
        if not self.referenced:
            raise ValueError("Establish the manual reference first")
        if axis not in PINS or not 0 <= target <= self.config["limits"][axis]:
            raise ValueError("Target exceeds software travel limits")
        if axis in ("x", "y") and self.position["z"] != 0:
            raise ValueError("Raise Z to zero before moving X/Y")
        self._steps(axis, target - self.position[axis])

    def command(self, parts):
        match parts:
            case ["limits", x, y, z, touch]:
                self.configure(*map(int, (x, y, z, touch)))
            case ["reference", "confirm"]:
                if not self.config:
                    raise ValueError("Set limits first")
                self.active = False
                self.position = dict.fromkeys(PINS, 0)
                self.referenced = True
            case ["jog", axis, steps]:
                self.jog(axis, int(steps))
            case ["move", axis, target]:
                self.move(axis, int(target))
            case ["start"]:
                if not self.referenced or self.position["z"] != 0:
                    raise ValueError("Reference and raise Z before starting")
                self.active = True
            case ["pause"]:
                self.active = False
            case ["tap", x, y]:
                if not self.active:
                    raise ValueError("Issue start before tapping")
                # Validate both targets before any movement.
                targets = {"x": int(x), "y": int(y)}
                for axis, target in targets.items():
                    if not 0 <= target <= self.config["limits"][axis]:
                        raise ValueError("Target exceeds software travel limits")
                self.move("z", 0)
                for axis, target in targets.items():
                    self.move(axis, target)
                self.move("z", self.config["touch"])
                time.sleep(0.1)
                self.move("z", 0)
            case _:
                raise ValueError("Unknown command or arguments; type help")


HELP = """limits X_MAX Y_MAX Z_MAX TOUCH   Set positive half-step limits; invalidates reference
jog x|y|z STEPS                 Small signed move, at most 100 half-steps
reference confirm              Set current X/Y to origin and Z to raised clearance
move x|y|z POSITION             Absolute bounded move (also available while paused)
save                           Save limits/touch only, never current position
status                         Show session position and readiness
start / pause                  Enable/disable manual tap commands; no AI loop is installed
tap X Y                        Move, touch for 0.1 seconds, retract
quit                           Exit and release coils; reference will be lost
Positive X/Y = away from origin; positive Z = toward screen. Verify directions first.
Before reference: jogging has NO absolute travel protection. Watch every movement.
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="No GPIO access or motor movement")
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--step-delay", type=float, default=0.005)
    args = parser.parse_args()
    if args.step_delay < 0.003:
        parser.error("Use a step delay of at least 0.003 seconds")
    driver = Driver(args.dry_run, args.step_delay)
    try:
        robot = Robot(driver, {})
        if args.config.exists():
            saved = json.loads(args.config.read_text())
            robot.configure(*(saved["limits"][axis] for axis in PINS), saved["touch"])
        print("DRY RUN" if args.dry_run else "LIVE GPIO: keep motor power disconnect accessible")
        print(HELP)
        while True:
            try:
                parts = shlex.split(input("robot> "))
                if not parts:
                    continue
                if parts == ["quit"]:
                    break
                if parts == ["help"]:
                    print(HELP)
                elif parts == ["status"]:
                    print(json.dumps({"position": robot.position, "referenced": robot.referenced,
                                      "active": robot.active, "config": robot.config}))
                elif parts == ["save"]:
                    if not robot.config:
                        raise ValueError("Set limits first")
                    args.config.parent.mkdir(parents=True, exist_ok=True)
                    args.config.write_text(json.dumps(robot.config, indent=2) + "\n")
                else:
                    robot.command(parts)
                    print("OK", robot.position)
            except ValueError as error:
                print("Rejected:", error)
    except (EOFError, KeyboardInterrupt):
        print("\nStopped; coils released. Re-reference before further operation.")
    finally:
        driver.close()


if __name__ == "__main__":
    main()
