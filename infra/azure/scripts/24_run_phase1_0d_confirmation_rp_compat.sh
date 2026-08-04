#!/usr/bin/env bash
# Execute the frozen Phase 1.0D generation launcher unchanged while normalizing
# one Azure Resource Provider readback artifact. Current ARM GET responses add
# resources.ephemeralStorage="" even when the submitted Job body omits it.
#
# This shim intercepts only the launcher's final, unqueried GET for the unique
# generation Job. The filter rejects every resource shape except exact
# 8 CPU/56Gi with ephemeralStorage absent or empty, then removes only the empty
# platform field so the frozen launcher's strict comparison can proceed. Every
# other Azure CLI call is delegated byte-for-byte to the trusted real binary.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../" && pwd)"
FROZEN_LAUNCHER="$SCRIPT_DIR/19_run_phase1_0d_confirmation.sh"
NORMALIZER="$PROJECT_ROOT/scripts/normalize_phase1_0d_job_readback.py"
EXPECTED_FROZEN_LAUNCHER_SHA256="ce448d818b3f8d24d131bf7fcece0d1be383f9c1dd033642271ec049b0174adc"

REAL_AZ="$(type -P az)"
REAL_AZ="$(/usr/bin/readlink -f "$REAL_AZ")"
COMPAT_PYTHON="$(/usr/bin/readlink -f /usr/bin/python3)"
for trusted_binary in "$REAL_AZ" "$COMPAT_PYTHON" /usr/bin/bash; do
    if [[ ! -x "$trusted_binary" ]]; then
        echo "[FAIL] Required compatibility-shim binary is unavailable"
        exit 1
    fi
    owner="$(/usr/bin/stat -c '%u' "$trusted_binary")"
    mode="$(/usr/bin/stat -c '%a' "$trusted_binary")"
    if [[ "$owner" != "0" || ! "$mode" =~ ^[0-7]{3,4}$ ]] \
        || (( (8#$mode & 8#022) != 0 )); then
        echo "[FAIL] Compatibility-shim binary is not root-owned and immutable"
        exit 1
    fi
done
if [[ ! "$REAL_AZ" =~ ^/usr/(local/)?bin/az$ \
    || ! "$COMPAT_PYTHON" =~ ^/usr/bin/python3([.][0-9]+)?$ ]]; then
    echo "[FAIL] Compatibility-shim binaries resolved outside trusted paths"
    exit 1
fi

ACTUAL_FROZEN_LAUNCHER_SHA256="$(
    /usr/bin/sha256sum "$FROZEN_LAUNCHER" | /usr/bin/awk '{print $1}'
)"
if [[ "$ACTUAL_FROZEN_LAUNCHER_SHA256" != "$EXPECTED_FROZEN_LAUNCHER_SHA256" ]]; then
    echo "[FAIL] Frozen generation launcher bytes changed"
    exit 1
fi
if ! git -C "$PROJECT_ROOT" diff --quiet \
    || ! git -C "$PROJECT_ROOT" diff --cached --quiet \
    || ! git -C "$PROJECT_ROOT" ls-files --error-unmatch \
        "${NORMALIZER#"$PROJECT_ROOT/"}" >/dev/null; then
    echo "[FAIL] Compatibility shim requires a clean tracked checkout"
    exit 1
fi

export REAL_AZ COMPAT_PYTHON NORMALIZER
az() {
    if (( $# == 7 )) \
        && [[ "$1" == "rest" \
            && "$2" == "--method" \
            && "$3" == "get" \
            && "$4" == "--url" \
            && "$5" =~ ^https://management[.]azure[.]com/.*/resourceGroups/rg-jspace-observation-sea/providers/Microsoft[.]App/jobs/job-jspace-p10d-confirmation[?]api-version=2024-03-01$ \
            && "$6" == "--output" \
            && "$7" == "json" ]]; then
        local raw_file result
        raw_file="$(/usr/bin/mktemp)"
        if "$REAL_AZ" "$@" >"$raw_file"; then
            result=0
        else
            result=$?
            /usr/bin/rm -f -- "$raw_file"
            return "$result"
        fi
        if "$COMPAT_PYTHON" -I "$NORMALIZER" <"$raw_file"; then
            result=0
        else
            result=$?
        fi
        /usr/bin/rm -f -- "$raw_file"
        return "$result"
    fi
    "$REAL_AZ" "$@"
}
export -f az
readonly -f az

echo "[NOTE] Exact frozen launcher retained; strict empty-field RP compatibility enabled"
exec /usr/bin/bash "$FROZEN_LAUNCHER"
