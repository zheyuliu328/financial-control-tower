#!/usr/bin/env bash
# Dependencies are installed explicitly before this offline runtime command.
set -euo pipefail
exec "${FCT_PYTHON:-python}" "$(dirname -- "${BASH_SOURCE[0]}")/main.py" --sample "$@"
