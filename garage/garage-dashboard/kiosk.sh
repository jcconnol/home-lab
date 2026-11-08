#!/bin/bash
# Run as the desktop user, including from their @reboot crontab.
set -eu
export PATH="/usr/local/bin:/usr/bin:/bin:${PATH:-}"
dashboard_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
runtime="$dashboard_dir/runtime"
mkdir -p "$runtime"
exec >>"$runtime/kiosk.log" 2>&1
if [ "$(id -u)" = 0 ]; then
    echo 'Run kiosk.sh as your desktop user, without sudo.'
    exit 1
fi
browser=$(command -v chromium || command -v chromium-browser || true)
if [ -z "$browser" ]; then
    echo 'Chromium is missing. Install it with: sudo apt install chromium'
    exit 1
fi
# Keep repeated cron/manual launches from opening multiple kiosk windows.
exec 9>"$runtime/kiosk.lock"
flock -n 9 || exit 0
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=$XDG_RUNTIME_DIR/bus}"

# Cron starts before desktop login and does not inherit its display variables.
# Read only the known display variables, never evaluate shell from the environment.
for ((attempt=0; attempt<300; attempt++)); do
    if command -v systemctl >/dev/null 2>&1; then
        while IFS='=' read -r key value; do
            case "$key" in
                DISPLAY|WAYLAND_DISPLAY|XAUTHORITY) export "$key=$value" ;;
            esac
        done < <(systemctl --user show-environment 2>/dev/null || true)
    fi
    if [ -z "${WAYLAND_DISPLAY:-}" ]; then
        for socket in "$XDG_RUNTIME_DIR"/wayland-*; do
            if [ -S "$socket" ]; then
                export WAYLAND_DISPLAY="${socket##*/}"
                break
            fi
        done
    fi
    wayland_socket="${WAYLAND_DISPLAY:-}"
    case "$wayland_socket" in
        /*) ;;
        *) wayland_socket="$XDG_RUNTIME_DIR/$wayland_socket" ;;
    esac
    if [ -n "${WAYLAND_DISPLAY:-}" ] && [ -S "$wayland_socket" ]; then
        platform=wayland
        break
    fi
    export DISPLAY="${DISPLAY:-:0}"
    export XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}"
    display_number="${DISPLAY#:}"
    if [ -S "/tmp/.X11-unix/X${display_number%%.*}" ] && [ -r "$XAUTHORITY" ]; then
        platform=x11
        break
    fi
    sleep 2
done
if [ -z "${platform:-}" ]; then
    echo 'No desktop appeared within 10 minutes. Enable desktop auto-login in sudo raspi-config.'
    exit 1
fi

python_bin=$(command -v python3)
if [ -x "$dashboard_dir/../runtime/venv/bin/python" ]; then
    python_bin="$dashboard_dir/../runtime/venv/bin/python"
fi
ready() {
    "$python_bin" -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8780/", timeout=2).close()' >/dev/null 2>&1
}
server_pid=
cleanup() {
    # Leave an existing dashboard service alone; stop only our own server.
    if [ -n "$server_pid" ]; then
        kill "$server_pid" 2>/dev/null || true
        wait "$server_pid" 2>/dev/null || true
    fi
}
trap cleanup EXIT
trap 'exit 0' INT TERM
if ! ready; then
    args=()
    if [ -f "$runtime/config.json" ]; then
        args=(--config "$runtime/config.json")
    fi
    "$python_bin" "$dashboard_dir/run.py" "${args[@]}" >>"$runtime/server.log" 2>&1 9>&- &
    server_pid=$!
fi
for ((attempt=0; attempt<60; attempt++)); do
    if ready; then
        break
    fi
    sleep 2
done
if ! ready; then
    echo 'Dashboard did not start. Check runtime/server.log.'
    exit 1
fi
"$browser" --ozone-platform="$platform" --kiosk --no-first-run --noerrdialogs \
    --disable-session-crashed-bubble --user-data-dir="$runtime/chromium-profile" \
    http://127.0.0.1:8780/ 9>&-
