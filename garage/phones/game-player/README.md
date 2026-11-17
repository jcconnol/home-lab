# Game action review

Run from this folder with Python 3.11+ (standard library only):

```sh
python run.py observation.sample.json --action left
```

Validates a requested action against allowed_actions and observation age, then appends a proposal to runtime/proposals.jsonl. The sample is intentionally stale and must be rejected. Replace captured_at with the actual observation time and id with a real frame ID. No model calls, screen capture, physical input, or actuation are implemented. Every accepted proposal says executed=false.

Use `python run.py --help` for options. See [the garage run guide](../../README.md) for deployment boundaries.

## Raspberry Pi motor controller

For the three-axis 5 V ULN2003/28BYJ-48 mechanism, use `python3 robot.py` on
Raspberry Pi OS, or `python robot.py --dry-run` without hardware. This is a
separate manual controller; the proposal script above remains unchanged.
See [pinout, power wiring, and manual calibration](PINOUT_AND_CALIBRATION.md).
No limit switches are required. Every session needs a manual reference; no
position is trusted after restart. Camera calibration and AI game play are not
implemented yet.

## Camera test over SSH

Assumes a ribbon-connected Pi camera and Raspberry Pi OS with `rpicam-still`
(or the older `libcamera-still`). This test does not operate the motors.

First, on the Pi over SSH, check detection and take one photo:

```sh
rpicam-still --list-cameras
rpicam-still --nopreview --timeout 2000 --output ~/camera-test.jpg
```

Use `libcamera-still` instead if that is the installed command. If neither is
installed, install `rpicam-apps` with `sudo apt install rpicam-apps` on a current
Raspberry Pi OS. A USB webcam needs a different capture tool.

For repeated photos, run from this folder on the Pi:

```sh
sh camera-test.sh
```

The script requests one photo per second until Ctrl+C. Actual speed depends on
the Pi and camera; a Zero may take longer. Photos go under
`~/camera-test/YYYY-MM-DD_HH-MM-SS_nanoseconds/`, with filenames such as
`1116142530.jpg` (November 16, 14:25:30). The session folder includes the year.
Use this for a short test and stop it when finished to limit SD card usage.

To view photos without transferring them, open a second SSH connection from
Windows PowerShell (replace `USER` and `PI_HOST` with your SSH username and Pi
hostname or IP):

```powershell
ssh -L 8081:127.0.0.1:8081 USER@PI_HOST
```

In that second connection, serve only the test photo folder:

```sh
python3 -m http.server 8081 --bind 127.0.0.1 --directory ~/camera-test
```

On the PC, open `http://localhost:8081`, click the session folder, and open a
JPEG. Refresh the folder listing to see new photos. Keep both SSH sessions
open while testing. Ctrl+C stops the photo server. For the single test photo,
copy it from Windows PowerShell and open it locally:

```powershell
scp USER@PI_HOST:camera-test.jpg .
Start-Process .\camera-test.jpg
```

At 3–4 inches above the screen, check focus and whether the whole screen fits.
Focus adjustment depends on the camera module; identify the module before
changing lens settings.
