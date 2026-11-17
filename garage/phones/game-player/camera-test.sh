#!/bin/sh
# Run with: sh camera-test.sh. Stop with Ctrl+C.
set -eu

if command -v rpicam-still >/dev/null 2>&1; then
    camera=rpicam-still
elif command -v libcamera-still >/dev/null 2>&1; then
    camera=libcamera-still
else
    echo 'No camera tool found. Install rpicam-apps on Raspberry Pi OS.' >&2
    exit 1
fi

output="$HOME/camera-test/$(date +%Y-%m-%d_%H-%M-%S_%N)"
mkdir -p "$output"
cd "$output"
printf 'Saving photos in %s\nStop with Ctrl+C.\n' "$output"
# Keep the camera running between shots. --datetime names JPEGs MMDDhhmmss.jpg;
# the enclosing session folder supplies the year and separates test runs.
exec "$camera" --nopreview --timeout 0 --timelapse 1000 --datetime \
    --width 1280 --height 720 --output .
