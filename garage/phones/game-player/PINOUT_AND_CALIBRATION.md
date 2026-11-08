# Pi Zero three-axis wiring and calibration

This controller assumes three **5 V 28BYJ-48 motors with ULN2003 boards** and a
Raspberry Pi Zero with a standard 40-pin header. Confirm the motor labels before
connecting power. No limit switches are required. Motors are controlled one axis
at a time using half-steps; positions are motor half-steps, not millimetres or pixels.

## Pinout

Connect each ULN2003 board's inputs using these **GPIO pin numbers**:

| Driver input | X: left/right | Y: screen up/down | Z: stylus touch/lift |
| --- | --- | --- | --- |
| IN1 | GPIO 5 | GPIO 12 | GPIO 17 |
| IN2 | GPIO 6 | GPIO 16 | GPIO 18 |
| IN3 | GPIO 13 | GPIO 20 | GPIO 22 |
| IN4 | GPIO 19 | GPIO 21 | GPIO 23 |

Connect all three boards' **GND / -** terminals to the motor supply's negative
terminal and any **GND** pin on the Pi.

GPIO numbers identify the signals used by `robot.py`. A physical pin number is
only the position on the 40-pin connector: for example, GPIO 5 is at physical
position 29. Follow GPIO labels when using the table above; use the diagram below
to locate those signals on the connector.

Physical header diagram: component side of board, pin 1 identified by the square
pad / board marking. Confirm pin 1 on your board; do not infer orientation from
where the USB connector is in a photograph.

```text
                  odd     even
             3V3   1 [ ] [ ] 2   5V       (unused here)
           GPIO2   3 [ ] [ ] 4   5V       (unused here)
           GPIO3   5 [ ] [ ] 6   GND
           GPIO4   7 [ ] [ ] 8   GPIO14
             GND   9 [ ] [ ] 10  GPIO15
      Z IN1 / 17  11 [ ] [ ] 12  GPIO18 / Z IN2
          GPIO27  13 [ ] [ ] 14  GND
      Z IN3 / 22  15 [ ] [ ] 16  GPIO23 / Z IN4
             3V3  17 [ ] [ ] 18  GPIO24
          GPIO10  19 [ ] [ ] 20  GND
           GPIO9  21 [ ] [ ] 22  GPIO25
          GPIO11  23 [ ] [ ] 24  GPIO8
             GND  25 [ ] [ ] 26  GPIO7
           GPIO0  27 [ ] [ ] 28  GPIO1
       X IN1 / 5  29 [ ] [ ] 30  GND
       X IN2 / 6  31 [ ] [ ] 32  GPIO12 / Y IN1
      X IN3 / 13  33 [ ] [ ] 34  GND
      X IN4 / 19  35 [ ] [ ] 36  GPIO16 / Y IN2
          GPIO26  37 [ ] [ ] 38  GPIO20 / Y IN3
      common GND  39 [ ] [ ] 40  GPIO21 / Y IN4
```

Power wiring:

```text
Pi GPIOs ----------------------------> ULN2003 IN1..IN4 (each board)
Pi GND (pin 39) -----------+
                          +----------> X / Y / Z board GND or -
External regulated 5V (-) -+
External regulated 5V (+) ------------> X / Y / Z board +5V or +
Each motor's 5-pin plug --------------> Its ULN2003 board motor socket
Pi power connector ------------------> Separate suitable Pi power supply
```

Do not power motors from GPIO or the Pi's 3.3 V rail. Use an external regulated
5 V supply rated for all three motors holding simultaneously, with wiring sized
for that current. Do not connect that supply's positive output to the Pi when the
Pi is separately powered. Check board power labels and jumper instructions.
Never apply 5 V to a GPIO input. This pin allocation leaves the CSI camera
connector available. A Zero without populated headers needs a suitable header.

## Install and launch over SSH

On Raspberry Pi OS, install GPIO support:

```sh
sudo apt update
sudo apt install python3-gpiozero
cd /path/to/home-lab/garage/phones/game-player
python3 robot.py --dry-run
# After checking wiring and mechanically clearing the stylus:
python3 robot.py
```

Use an interactive SSH session. EOF/disconnection or Ctrl+C exits and releases
coils. Do not install automatic movement at boot. Idle/startup never moves motors.
An SSH/network failure may take time to become visible; it is not an emergency
stop. Keep a physical motor-power disconnect accessible. Coils remain energized
while the program is idle to preserve position; check motor/driver temperatures.
On exit or power failure, Z must not fall onto the glass: use a spring or other
mechanical support. Software cannot guarantee retraction after power loss.

## First calibration (manual)

1. Open `help` and `status`. The program begins unreferenced and paused.
2. With the stylus physically clear of the phone, try `jog x 10`, `jog y 10`, and
   `jog z 10` separately. Positive X/Y must move away from your chosen origin;
   positive Z must move toward the screen. If an axis runs backward, power down
   and reverse that axis's tuple in `PINS` (IN4, IN3, IN2, IN1); verify again.
3. Carefully jog to a repeatable reference: X/Y at a marked point near a screen
   corner, Z at a marked raised clearance position. Before referencing, there
   are no absolute software limits; each jog is limited to 100 half-steps.
4. Establish conservative maximum X/Y/Z travel and Z touch depth through small,
   supervised movements. Count signed half-steps from the reference, then return
   to it. Z touch depth is relative to the raised reference, not an additional
   amount of travel. Use a compliant stylus; never search indefinitely for touch.
5. Enter `limits X_MAX Y_MAX Z_MAX TOUCH`, replacing names with measured positive
   integers. This invalidates any prior reference. **There are no universal safe
   numbers for a printed gear mechanism.** Keep limits inside mechanical travel.
6. At the physical reference, enter `reference confirm`, then `save`. Saving
   persists limits and touch depth only. Reference is a manual assertion; the
   software cannot check it or detect a motor stall.
7. With a touch-test app open, enter `start` then `tap X Y` using a measured test
   target. It raises Z, moves X then Y, lowers to TOUCH, holds 0.1 seconds and
   retracts to Z=0. Both X/Y targets are checked before movement.
8. Enter `pause` while switching to the game, then `start` to enable manual taps.
   `move` and `jog` remain available during setup while paused. `pause` disables
   subsequent taps; it does not release coils or automatically retract Z.

Commands execute synchronously. To interrupt a movement, use Ctrl+C; the program
exits and its position reference is discarded. A `pause` typed while a command is
running is processed only after that command finishes. This is not a real-time
motor controller or an emergency-stop interface.

On later startups: load saved settings automatically, physically establish the
same reference, run `reference confirm`, and verify touches before use. After a
stall, manual repositioning, or interrupted motion, stop and re-reference. Never
trust persisted position after restart. Dry-run and live use the same settings
file by default; use `--config runtime/practice.json` to keep practice separate.

## What is implemented versus planned

Implemented: GPIO half-stepping, small jogs, manual session referencing, persisted
travel settings, software limits, Z clearance checks, manually requested taps,
and hardware-free dry run. The existing `run.py` remains a proposal-only tool;
it does not execute actions through this controller.

Not implemented: camera capture, camera/screen mapping, a calibration phone app,
backlash measurement, model requests, or autonomous game play. `start` only enables
manual taps. It does not launch a game-playing loop.

A future calibration page should show corner markers and report actual touch
coordinates. Pair those coordinates with motor positions over a grid, verify
additional targets, and store a screen-to-motor mapping. Camera interpretation
cannot replace the manual initial Z reference. Keep the phone rigidly mounted
and orientation locked. Start with taps; drags require additional control logic.

Pin numbering references: [Raspberry Pi GPIO documentation](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html)
and [GPIO Zero output devices](https://gpiozero.readthedocs.io/en/stable/api_output.html).

## One-motor-at-a-time wiring test

Stop `robot.py` first. With motor power disconnected, select which ULN2003 board
receives external 5 V. Leave all GPIO inputs and common grounds connected. Give
the motor room to rotate, with the stylus clear of the phone and mechanism clear
of travel ends. This test bypasses calibration and travel limits.

```sh
cd /path/to/home-lab/garage/phones/game-player
python3 stepper_test.py
```

The script sends **all three boards** forward half-steps for 5 seconds, holds for
1 second, then sends reverse half-steps for 5 seconds and exits. Only the powered
board should move; powering multiple boards makes those motors move together.
Coils hold during the pause and outputs are released on exit or Ctrl+C. The
half-step interval is 5 ms. This is a timed direction test, not a guarantee of an
exact return position. Disconnect motor power before changing board power wiring,
then rerun for the next motor. Re-reference before using the normal controller.
For a hardware-free timing check, use `python3 stepper_test.py --dry-run`.
