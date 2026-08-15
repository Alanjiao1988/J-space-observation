#!/bin/sh
# The single entry point for the P0-R2 generation-1 successor.
#
# There is deliberately no default mode. A caller must name exactly one of:
#
#   preflight     model-free. Proves identity, verifies the delegated science
#                 by SHA-256, audits the image against Git, and proves the
#                 attempt prefix is unused. This is the first command a
#                 successor session runs, and it is safe to run repeatedly.
#
#   live-replay   consumes the one-shot replay envelope. Runs the replay gate
#                 and publishes the four canonical artifacts. Irreversible.
#
#   launch-pilot  requires a built authorization derived from a completed
#                 replay. Creates and starts the bounded GPU pilot.
#
# Every mode fails closed: an unset variable, an unreadable lock, or an
# unrecognised word stops the container before it does anything.

set -eu

STAGE="STUDY3-P0-R2"
SRC="${P0_R2_SRC:-/opt/jspace/src}"
R2="${SRC}/studies/study3/pilot/p0_r2"
PYTHONPATH="${R2}:${SRC}/studies/study3/pilot/p0_r1"
export PYTHONPATH

MODE="${1:-${P0_R2_REPLAY_MODE:-}}"

usage() {
    echo "usage: p0_r2_successor_v1.sh {preflight|live-replay|launch-pilot}" >&2
    echo "there is no default mode; name the one you mean" >&2
}

if [ -z "${MODE}" ]; then
    echo "P0_R2_SUCCESSOR_REFUSED=1 no mode was named" >&2
    usage
    exit 2
fi

echo "P0_R2_SUCCESSOR_MODE=${MODE}"
echo "P0_R2_STAGE=${STAGE}"

case "${MODE}" in
    preflight)
        exec /usr/local/bin/p0_r2_canary_v1.sh preflight
        ;;
    live-replay)
        if [ "${P0_R2_LIVE_REPLAY_AUTHORIZED:-0}" != "1" ]; then
            echo "P0_R2_SUCCESSOR_REFUSED=1 live-replay consumes the one-shot" \
                 "envelope and requires P0_R2_LIVE_REPLAY_AUTHORIZED=1" >&2
            exit 3
        fi
        exec /usr/local/bin/p0_r2_replay_v1.sh
        ;;
    launch-pilot)
        if [ "${P0_R2_PILOT_AUTHORIZED:-0}" != "1" ]; then
            echo "P0_R2_SUCCESSOR_REFUSED=1 launch-pilot requires a built" \
                 "authorization and P0_R2_PILOT_AUTHORIZED=1" >&2
            exit 3
        fi
        exec /usr/local/bin/p0_r2_model_pilot_v1.sh
        ;;
    *)
        echo "P0_R2_SUCCESSOR_REFUSED=1 unrecognised mode ${MODE}" >&2
        usage
        exit 2
        ;;
esac
