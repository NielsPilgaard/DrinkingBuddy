#!/usr/bin/env bash
# Runs a two-device Maestro flow (match-and-call.yaml or report-block.yaml)
# on two Android emulators/devices in parallel. See
# run-two-device-flow.ps1 docstring. UNVERIFIED against a live Maestro run.
#
# Usage: ./run-two-device-flow.sh <flow-file> <device-a-serial> <device-b-serial> [api-base-url]
# Example: ./run-two-device-flow.sh match-and-call.yaml emulator-5554 emulator-5556
set -euo pipefail

FLOW_FILE="${1:?flow file required (e.g. match-and-call.yaml)}"
DEVICE_A="${2:?device A serial required}"
DEVICE_B="${3:?device B serial required}"
API_BASE_URL="${4:-http://10.0.2.2:8000}"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

maestro --device "$DEVICE_A" test "$DIR/$FLOW_FILE" \
  -e DEVICE_ROLE=a -e API_BASE_URL="$API_BASE_URL" &
PID_A=$!

maestro --device "$DEVICE_B" test "$DIR/$FLOW_FILE" \
  -e DEVICE_ROLE=b -e API_BASE_URL="$API_BASE_URL" &
PID_B=$!

status=0
wait "$PID_A" || status=1
wait "$PID_B" || status=1

exit $status
