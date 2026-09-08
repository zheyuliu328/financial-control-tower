#!/usr/bin/env bash
# Compatibility alias for the non-destructive verification entry.
set -euo pipefail
exec bash "$(dirname -- "${BASH_SOURCE[0]}")/scripts/verify.sh" "$@"
