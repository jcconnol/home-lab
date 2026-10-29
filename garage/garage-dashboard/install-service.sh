#!/bin/sh
# Install a user service on Raspberry Pi OS/Linux, without running as root.
set -eu
dashboard_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
python_bin=$(command -v python3)
if ! command -v systemctl >/dev/null 2>&1; then
    printf '%s\n' 'systemd is required. Use: sh start.sh'
    exit 1
fi
service_dir="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
mkdir -p "$service_dir" "$dashboard_dir/runtime"
if [ ! -f "$dashboard_dir/runtime/config.json" ]; then
    cp "$dashboard_dir/config.sample.json" "$dashboard_dir/runtime/config.json"
fi
unit_file="$service_dir/garage-dashboard.service"
if [ -e "$unit_file" ]; then
    printf '%s\n' "Service already exists: $unit_file. Review it before changing it."
    exit 1
fi
# systemd treats percent signs as specifiers; keep generated paths unambiguous.
case "$dashboard_dir$python_bin" in
    *'%'*|*'"'*|*'\'*) printf '%s\n' 'Use a checkout path without %, double quotes, or backslashes.'; exit 1 ;;
esac
cat > "$unit_file" <<EOF
[Unit]
Description=Garage mission control dashboard
After=network.target

[Service]
Type=simple
ExecStart="$python_bin" "$dashboard_dir/run.py" --config "$dashboard_dir/runtime/config.json"
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
EOF
systemctl --user daemon-reload
systemctl --user enable --now garage-dashboard.service
printf '%s\n' 'Dashboard is running at http://127.0.0.1:8780' 'Status: systemctl --user status garage-dashboard' 'For boot before sign-in: sudo loginctl enable-linger "$USER"'
