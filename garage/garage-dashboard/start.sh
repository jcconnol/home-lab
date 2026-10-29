#!/bin/sh
# Run from any directory; no third-party Python packages required.
set -eu
dashboard_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec python3 "$dashboard_dir/run.py" "$@"
