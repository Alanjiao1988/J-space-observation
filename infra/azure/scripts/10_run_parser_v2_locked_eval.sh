#!/bin/bash -p
set +x
set +v
# Launch or recover one protected parser-v2 ACA execution.

set -euo pipefail

readonly CLEAN_PATH="/usr/local/bin:/usr/bin:/bin"
readonly APPROVED_ORIGIN_URL="https://github.com/Alanjiao1988/J-space-observation.git"
PATH="$CLEAN_PATH"
GIT_NO_REPLACE_OBJECTS=1
export PATH GIT_NO_REPLACE_OBJECTS
environment_is_clean=true
if [[ "${JSPACE_PV2_LAUNCH_CLEAN_REEXEC:-}" != "1" \
    || -n "$(builtin compgen -A function)" ]]; then
    environment_is_clean=false
fi
while IFS= builtin read -r -d '' environment_entry; do
    environment_name="${environment_entry%%=*}"
    case "$environment_name" in
        HOME|LANG|LC_ALL|PATH|PWD|SHLVL|_|MSYSTEM|SYSTEMROOT|WINDIR|\
        AZURE_CONFIG_DIR|GIT_NO_REPLACE_OBJECTS|\
        PARSER_EVAL_STAGE|PARSER_EVAL_VERIFY_ONLY|\
        PARSER_EVAL_CLOSE_INVALID_ONLY|\
        PARSER_EVAL_VERIFICATION_STATE|PARSER_EVAL_RETRY_KIND|\
        PARSER_EVAL_RECOVER_CLAIM_NAME|PARSER_EVAL_INITIAL_BOOTSTRAP|\
        PARSER_EVAL_RUNTIME_CONFIG_FILE|PARSER_EVAL_CONFIG_SHA256|\
        PARSER_EVAL_IMPLEMENTATION_MANIFEST_FILE|\
        PARSER_EVAL_IMPLEMENTATION_MANIFEST_SHA256|\
        PARSER_EVAL_IMAGE_BINDING_FILE|PARSER_EVAL_IMAGE_BINDING_SHA256|\
        PARSER_EVAL_AUTHORIZATION_LOCK_SHA256|\
        PARSER_EVAL_AUTHORIZATION_MANIFEST_SHA256|\
        PARSER_EVAL_BOOTSTRAP_STATE_RECEIPT_SHA256|\
        PARSER_EVAL_UNSEAL_RECEIPT_SHA256|\
        PARSER_EVAL_LOCKED_INPUT_SHA256|\
        PARSER_EVAL_LOCKED_INPUT_MANIFEST_SHA256|\
        PARSER_EVAL_PREDICTIONS_RECEIPT_SHA256|\
        PARSER_EVAL_PREDICTION_MANIFEST_SHA256|\
        PARSER_EVAL_LABELS_SHA256|PARSER_EVAL_LABELS_MANIFEST_SHA256|\
        PARSER_EVAL_SCORES_MANIFEST_SHA256|\
        PARSER_EVAL_CLOSED_RECEIPT_SHA256|PARSER_EVAL_BUILD_RECORD_DIR|\
        PARSER_EVAL_BASE_IMAGE|JSPACE_PV2_LAUNCH_CLEAN_REEXEC|\
        JSPACE_PV2_VERIFIED_REEXEC|JSPACE_PV2_PROJECT_ROOT|\
        JSPACE_PV2_SNAPSHOT_DIR|JSPACE_PV2_HEAD_SHA|JSPACE_PV2_CORE_PATH) ;;
        *) environment_is_clean=false ;;
    esac
done < <(/usr/bin/env -0)
if [[ "$environment_is_clean" != "true" ]]; then
    clean_environment=(
        "HOME=${HOME:-/nonexistent}"
        "LANG=C.UTF-8"
        "LC_ALL=C.UTF-8"
        "PATH=$CLEAN_PATH"
        "GIT_NO_REPLACE_OBJECTS=1"
        "JSPACE_PV2_LAUNCH_CLEAN_REEXEC=1"
    )
    for name in \
        AZURE_CONFIG_DIR PARSER_EVAL_STAGE PARSER_EVAL_VERIFY_ONLY \
        PARSER_EVAL_CLOSE_INVALID_ONLY \
        PARSER_EVAL_VERIFICATION_STATE PARSER_EVAL_RETRY_KIND \
        PARSER_EVAL_RECOVER_CLAIM_NAME PARSER_EVAL_INITIAL_BOOTSTRAP \
        PARSER_EVAL_RUNTIME_CONFIG_FILE PARSER_EVAL_CONFIG_SHA256 \
        PARSER_EVAL_IMPLEMENTATION_MANIFEST_FILE \
        PARSER_EVAL_IMPLEMENTATION_MANIFEST_SHA256 \
        PARSER_EVAL_IMAGE_BINDING_FILE PARSER_EVAL_IMAGE_BINDING_SHA256 \
        PARSER_EVAL_AUTHORIZATION_LOCK_SHA256 \
        PARSER_EVAL_AUTHORIZATION_MANIFEST_SHA256 \
        PARSER_EVAL_BOOTSTRAP_STATE_RECEIPT_SHA256 \
        PARSER_EVAL_UNSEAL_RECEIPT_SHA256 \
        PARSER_EVAL_LOCKED_INPUT_SHA256 \
        PARSER_EVAL_LOCKED_INPUT_MANIFEST_SHA256 \
        PARSER_EVAL_PREDICTIONS_RECEIPT_SHA256 \
        PARSER_EVAL_PREDICTION_MANIFEST_SHA256 \
        PARSER_EVAL_LABELS_SHA256 PARSER_EVAL_LABELS_MANIFEST_SHA256 \
        PARSER_EVAL_SCORES_MANIFEST_SHA256 \
        PARSER_EVAL_CLOSED_RECEIPT_SHA256 PARSER_EVAL_BUILD_RECORD_DIR \
        PARSER_EVAL_BASE_IMAGE JSPACE_PV2_VERIFIED_REEXEC \
        JSPACE_PV2_PROJECT_ROOT JSPACE_PV2_SNAPSHOT_DIR \
        JSPACE_PV2_HEAD_SHA JSPACE_PV2_CORE_PATH; do
        if [[ -v "$name" ]]; then
            clean_environment+=("$name=${!name}")
        fi
    done
    builtin exec /usr/bin/env -i "${clean_environment[@]}" \
        /bin/bash --noprofile --norc -p "$0" "$@"
fi
while IFS= builtin read -r function_name; do
    builtin unset -f "$function_name"
done < <(builtin compgen -A function)
builtin unset BASH_ENV ENV CDPATH GLOBIGNORE PYTHONPATH PYTHONHOME PYTHONSTARTUP
builtin unset PYTHONWARNINGS PYTHONINSPECT PYTHONBREAKPOINT PYTHONUSERBASE
builtin unset PYTHONCASEOK PYTHONEXECUTABLE PYTHONCOERCECLOCALE PYTHONUTF8
builtin unset PYTHONMALLOC PYTHONPLATLIBDIR
readonly PYTHON_BIN="$(/usr/bin/readlink -f /usr/bin/python3)"
readonly PYTHON_MODE="$(/usr/bin/stat -c '%a' "$PYTHON_BIN" 2>/dev/null || true)"
if [[ ! "$PYTHON_BIN" =~ ^/usr/bin/python3([.][0-9]+)?$ \
    || ! -x "$PYTHON_BIN" \
    || "$(/usr/bin/stat -c '%u' "$PYTHON_BIN" 2>/dev/null || true)" != "0" \
    || ! "$PYTHON_MODE" =~ ^[0-7]{3,4}$ ]]; then
    echo "[FAIL] Authenticated absolute Python interpreter is unavailable"
    exit 1
fi
if (( (8#$PYTHON_MODE & 8#022) != 0 )); then
    echo "[FAIL] Authenticated absolute Python interpreter is unavailable"
    exit 1
fi
python() {
    "$PYTHON_BIN" -I "$@"
}
readonly -f python

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${JSPACE_PV2_VERIFIED_REEXEC:-}" == "1" ]]; then
    PROJECT_ROOT="${JSPACE_PV2_PROJECT_ROOT:?Verified launcher project root is missing}"
    SNAPSHOT_DIR="${JSPACE_PV2_SNAPSHOT_DIR:?Verified launcher snapshot is missing}"
    SNAPSHOT_SOURCE_ROOT="$SNAPSHOT_DIR/sources"
    AZURE_HELPER="$SNAPSHOT_SOURCE_ROOT/scripts/parser_v2_azure_contract.py"
    BOOTSTRAP="$SNAPSHOT_SOURCE_ROOT/scripts/bootstrap_parser_v2_locked_evaluation.py"
    CORE_FILE="$SNAPSHOT_SOURCE_ROOT/src/jspace_observation/parser_v2_locked_evaluation.py"
    RUNTIME_CONFIG_SNAPSHOT_FILE="$SNAPSHOT_DIR/runtime-config.snapshot.json"
    IMPLEMENTATION_MANIFEST_SNAPSHOT_FILE="$SNAPSHOT_DIR/implementation-manifest.snapshot.json"
    IMAGE_BINDING_SNAPSHOT_FILE="$SNAPSHOT_DIR/image-binding.snapshot.json"
    HELPER_SNAPSHOT_MANIFEST_FILE="$SNAPSHOT_DIR/helper-snapshots.json"
else
    PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../" && pwd)"
    SNAPSHOT_DIR=""
    SNAPSHOT_SOURCE_ROOT=""
    AZURE_HELPER="$PROJECT_ROOT/scripts/parser_v2_azure_contract.py"
    BOOTSTRAP="$PROJECT_ROOT/scripts/bootstrap_parser_v2_locked_evaluation.py"
    CORE_FILE="$PROJECT_ROOT/src/jspace_observation/parser_v2_locked_evaluation.py"
fi
STAGE="${PARSER_EVAL_STAGE:?Set PARSER_EVAL_STAGE to P or E}"
VERIFY_ONLY="${PARSER_EVAL_VERIFY_ONLY:-false}"
CLOSE_INVALID_ONLY="${PARSER_EVAL_CLOSE_INVALID_ONLY:-false}"
VERIFICATION_STATE="${PARSER_EVAL_VERIFICATION_STATE:-CLOSED}"
RETRY_KIND="${PARSER_EVAL_RETRY_KIND:-none}"
RECOVER_CLAIM_NAME="${PARSER_EVAL_RECOVER_CLAIM_NAME:-}"
INITIAL_BOOTSTRAP="${PARSER_EVAL_INITIAL_BOOTSTRAP:-false}"
RUNTIME_CONFIG_SOURCE_FILE="${PARSER_EVAL_RUNTIME_CONFIG_FILE:?Set PARSER_EVAL_RUNTIME_CONFIG_FILE}"
CONFIG_SHA256="${PARSER_EVAL_CONFIG_SHA256:?Set PARSER_EVAL_CONFIG_SHA256}"
IMPLEMENTATION_MANIFEST_SOURCE_FILE="${PARSER_EVAL_IMPLEMENTATION_MANIFEST_FILE:?Set PARSER_EVAL_IMPLEMENTATION_MANIFEST_FILE}"
IMPLEMENTATION_MANIFEST_SHA256="${PARSER_EVAL_IMPLEMENTATION_MANIFEST_SHA256:?Set PARSER_EVAL_IMPLEMENTATION_MANIFEST_SHA256}"
IMAGE_BINDING_SOURCE_FILE="${PARSER_EVAL_IMAGE_BINDING_FILE:?Set PARSER_EVAL_IMAGE_BINDING_FILE}"
IMAGE_BINDING_SHA256="${PARSER_EVAL_IMAGE_BINDING_SHA256:?Set PARSER_EVAL_IMAGE_BINDING_SHA256}"
AUTHORIZATION_LOCK_SHA256="${PARSER_EVAL_AUTHORIZATION_LOCK_SHA256:-}"
AUTHORIZATION_MANIFEST_SHA256="${PARSER_EVAL_AUTHORIZATION_MANIFEST_SHA256:-}"
BOOTSTRAP_STATE_RECEIPT_SHA256="${PARSER_EVAL_BOOTSTRAP_STATE_RECEIPT_SHA256:-}"
SCRATCH_DIR=""
AUTHENTICATED_VERIFICATION_RETRY_EXECUTION_ID=""
SNAPSHOT_CLEANUP_ARMED="false"

cleanup() {
    if [[ -n "$SCRATCH_DIR" ]]; then
        rm -rf -- "$SCRATCH_DIR"
    fi
    if [[ "$SNAPSHOT_CLEANUP_ARMED" == "true" && -n "$SNAPSHOT_DIR" ]]; then
        rm -rf -- "$SNAPSHOT_DIR"
    fi
}
trap cleanup EXIT

scalar() {
    local value
    value="$("$@" | tr -d '\r')"
    if [[ "$value" == *$'\n'* ]]; then
        echo "[FAIL] Scalar helper returned more than one line" >&2
        return 1
    fi
    printf '%s' "$value"
}

raw_arm_request_once() {
    local method="$1"
    local url="$2"
    local body_file="$3"
    local response_file="$4"
    local create_only="${5:-false}"
    local token status
    local -a headers=()
    if [[ ! "$method" =~ ^(PUT|POST)$ \
        || "$url" != https://management.azure.com/* \
        || ! -f "$body_file" \
        || ! "$create_only" =~ ^(true|false)$ ]]; then
        echo "[FAIL] Refusing an invalid one-shot ARM request" >&2
        return 1
    fi
    if [[ "$create_only" == "true" ]]; then
        headers+=(--header "If-None-Match: *")
    fi
    if ! token="$(scalar az account get-access-token \
        --resource https://management.azure.com/ \
        --query accessToken -o tsv 2>/dev/null)"; then
        echo "[FAIL] ARM token retrieval failed" >&2
        return 1
    fi
    if [[ -z "$token" || "$token" == *'"'* || "$token" == *'\'* ]]; then
        unset token
        echo "[FAIL] ARM returned an invalid access token" >&2
        return 1
    fi
    if ! status="$(
        printf 'header = "Authorization: Bearer %s"\n' "$token" \
            | curl --disable --config - --silent --show-error \
                --proto '=https' --proto-redir '=https' \
                --retry 0 --max-redirs 0 \
                --connect-timeout 30 --max-time 120 \
                --request "$method" \
                --header "Accept: application/json" \
                --header "Content-Type: application/json" \
                "${headers[@]}" \
                --data-binary "@$body_file" \
                --output "$response_file" \
                --write-out '%{http_code}' "$url"
    )"; then
        unset token
        return 1
    fi
    unset token
    if [[ ! "$status" =~ ^[0-9]{3}$ ]]; then
        return 1
    fi
    printf '%s' "$status"
}
readonly -f raw_arm_request_once

raw_arm_get_once() {
    local url="$1"
    local response_file="$2"
    local token status
    if [[ "$url" != https://management.azure.com/* ]]; then
        echo "[FAIL] Refusing an invalid exact ARM GET" >&2
        return 1
    fi
    if ! token="$(scalar az account get-access-token \
        --resource https://management.azure.com/ \
        --query accessToken -o tsv 2>/dev/null)"; then
        echo "[FAIL] ARM token retrieval failed" >&2
        return 1
    fi
    if [[ -z "$token" || "$token" == *'"'* || "$token" == *'\'* ]]; then
        unset token
        echo "[FAIL] ARM returned an invalid access token" >&2
        return 1
    fi
    if ! status="$(
        printf 'header = "Authorization: Bearer %s"\n' "$token" \
            | curl --disable --config - --silent --show-error \
                --proto '=https' --proto-redir '=https' \
                --retry 0 --max-redirs 0 \
                --connect-timeout 30 --max-time 120 \
                --request GET --header "Accept: application/json" \
                --output "$response_file" \
                --write-out '%{http_code}' "$url"
    )"; then
        unset token
        return 1
    fi
    unset token
    if [[ ! "$status" =~ ^[0-9]{3}$ ]]; then
        return 1
    fi
    printf '%s' "$status"
}
readonly -f raw_arm_get_once

case "${STAGE}:${VERIFY_ONLY}:${RETRY_KIND}" in
    P:false:none|P:false:infrastructure_pre_input|P:false:prediction_adoption|\
    E:false:none|E:false:scorer_infrastructure|E:true:verification_only) ;;
    *)
        echo "[FAIL] Stage/mode does not match a frozen retry kind"
        exit 1
        ;;
esac
if [[ "$VERIFY_ONLY" != "true" && "$VERIFY_ONLY" != "false" ]]; then
    echo "[FAIL] PARSER_EVAL_VERIFY_ONLY must be true or false"
    exit 1
fi
if [[ "$CLOSE_INVALID_ONLY" != "true" \
    && "$CLOSE_INVALID_ONLY" != "false" ]]; then
    echo "[FAIL] PARSER_EVAL_CLOSE_INVALID_ONLY must be true or false"
    exit 1
fi
if [[ "$CLOSE_INVALID_ONLY" == "true" \
    && "${STAGE}:${VERIFY_ONLY}:${RETRY_KIND}" \
        != "E:true:verification_only" ]]; then
    echo "[FAIL] INVALID closure must use isolated Stage-E verification routing"
    exit 1
fi
if [[ "$INITIAL_BOOTSTRAP" != "true" && "$INITIAL_BOOTSTRAP" != "false" ]]; then
    echo "[FAIL] PARSER_EVAL_INITIAL_BOOTSTRAP must be true or false"
    exit 1
fi
if [[ "$STAGE" == "P" && "$VERIFICATION_STATE" != "CLOSED" ]]; then
    echo "[FAIL] Stage P verification state must remain CLOSED"
    exit 1
fi
if [[ "$VERIFY_ONLY" == "true" \
    && ! "$VERIFICATION_STATE" \
        =~ ^(PREDICTIONS_VERIFIED|LABELS_READ|SCORES_VERIFIED|CLOSED)$ ]]; then
    echo "[FAIL] Verification state is not registered"
    exit 1
fi
if [[ "$INITIAL_BOOTSTRAP" == "true" \
    && "${STAGE}:${RETRY_KIND}:${RECOVER_CLAIM_NAME}" != "P:none:" ]]; then
    echo "[FAIL] Initial custodian bootstrap is valid only before primary Stage P"
    exit 1
fi
if [[ ! "$CONFIG_SHA256" =~ ^[0-9a-f]{64}$ \
    || ! "$IMPLEMENTATION_MANIFEST_SHA256" =~ ^[0-9a-f]{64}$ \
    || ! "$IMAGE_BINDING_SHA256" =~ ^[0-9a-f]{64}$ ]]; then
    echo "[FAIL] Persisted runtime/implementation/image hashes are malformed"
    exit 1
fi

is_allowed_parser_eval_environment_name() {
    case "$1" in
        PARSER_EVAL_STAGE|PARSER_EVAL_VERIFY_ONLY|\
        PARSER_EVAL_CLOSE_INVALID_ONLY|\
        PARSER_EVAL_VERIFICATION_STATE|PARSER_EVAL_RETRY_KIND|\
        PARSER_EVAL_RECOVER_CLAIM_NAME|PARSER_EVAL_INITIAL_BOOTSTRAP|\
        PARSER_EVAL_RUNTIME_CONFIG_FILE|PARSER_EVAL_CONFIG_SHA256|\
        PARSER_EVAL_IMPLEMENTATION_MANIFEST_FILE|\
        PARSER_EVAL_IMPLEMENTATION_MANIFEST_SHA256|\
        PARSER_EVAL_IMAGE_BINDING_FILE|PARSER_EVAL_IMAGE_BINDING_SHA256|\
        PARSER_EVAL_AUTHORIZATION_LOCK_SHA256|\
        PARSER_EVAL_AUTHORIZATION_MANIFEST_SHA256|\
        PARSER_EVAL_BOOTSTRAP_STATE_RECEIPT_SHA256|\
        PARSER_EVAL_UNSEAL_RECEIPT_SHA256|\
        PARSER_EVAL_LOCKED_INPUT_SHA256|\
        PARSER_EVAL_LOCKED_INPUT_MANIFEST_SHA256|\
        PARSER_EVAL_PREDICTIONS_RECEIPT_SHA256|\
        PARSER_EVAL_PREDICTION_MANIFEST_SHA256|\
        PARSER_EVAL_LABELS_SHA256|\
        PARSER_EVAL_LABELS_MANIFEST_SHA256|\
        PARSER_EVAL_SCORES_MANIFEST_SHA256|\
        PARSER_EVAL_CLOSED_RECEIPT_SHA256|\
        PARSER_EVAL_BUILD_RECORD_DIR|PARSER_EVAL_BASE_IMAGE)
            return 0
            ;;
    esac
    return 1
}
while IFS='=' read -r environment_name _; do
    if [[ "$environment_name" == PARSER_EVAL_* ]] \
        && ! is_allowed_parser_eval_environment_name "$environment_name"; then
        echo "[FAIL] Stage environment contains an unregistered channel"
        exit 1
    fi
done < <(/usr/bin/env | tr -d '\r')

if [[ "${JSPACE_PV2_VERIFIED_REEXEC:-}" == "1" ]]; then
    CANONICAL_PROJECT_ROOT="$(cd "$PROJECT_ROOT" && pwd -P)"
    GIT_TOPLEVEL_RAW="$(scalar git -C "$PROJECT_ROOT" rev-parse --show-toplevel)"
    GIT_PRIVATE_ROOT_RAW="$(scalar git -C "$PROJECT_ROOT" rev-parse --absolute-git-dir)"
    CANONICAL_GIT_TOPLEVEL="$(cd "$GIT_TOPLEVEL_RAW" && pwd -P)"
    CANONICAL_GIT_PRIVATE_ROOT="$(cd "$GIT_PRIVATE_ROOT_RAW" && pwd -P)"
    SNAPSHOT_BASENAME="$(basename "$SNAPSHOT_DIR")"
    SNAPSHOT_PARENT="$(cd "$(dirname "$SNAPSHOT_DIR")" && pwd -P)"
    CANONICAL_SNAPSHOT_DIR="$(cd "$SNAPSHOT_DIR" && pwd -P)"
    CURRENT_LAUNCHER_PATH="$(
        cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P
    )/$(basename "${BASH_SOURCE[0]}")"
    EXPECTED_LAUNCHER_PATH="$SNAPSHOT_PARENT/$SNAPSHOT_BASENAME/sources/infra/azure/scripts/10_run_parser_v2_locked_eval.sh"
    if [[ "$CANONICAL_PROJECT_ROOT" != "$CANONICAL_GIT_TOPLEVEL" \
        || "$SNAPSHOT_PARENT" != "$CANONICAL_GIT_PRIVATE_ROOT" \
        || "$CANONICAL_SNAPSHOT_DIR" \
            != "$CANONICAL_GIT_PRIVATE_ROOT/$SNAPSHOT_BASENAME" \
        || ! "$SNAPSHOT_BASENAME" =~ ^parser-v2-launch-inputs-[0-9a-f]{32}$ \
        || ! -d "$SNAPSHOT_DIR" || -L "$SNAPSHOT_DIR" \
        || "$CURRENT_LAUNCHER_PATH" != "$EXPECTED_LAUNCHER_PATH" ]]; then
        echo "[FAIL] Verified launcher re-exec path is not a private Git snapshot"
        exit 1
    fi
fi

if [[ "$STAGE" == "P" && "$RETRY_KIND" == "prediction_adoption" ]]; then
    EVALUATION_MODE="prediction_adoption"
elif [[ "$STAGE" == "P" ]]; then
    EVALUATION_MODE="prediction"
elif [[ "$CLOSE_INVALID_ONLY" == "true" ]]; then
    EVALUATION_MODE="invalid_closure"
elif [[ "$VERIFY_ONLY" == "true" ]]; then
    EVALUATION_MODE="verification"
else
    EVALUATION_MODE="finalization"
fi

if [[ "${JSPACE_PV2_VERIFIED_REEXEC:-}" == "1" ]]; then
    HEAD_SHA="${JSPACE_PV2_HEAD_SHA:?Verified launcher source commit is missing}"
    ORIGIN_MAIN_SHA="$(scalar git -C "$PROJECT_ROOT" rev-parse refs/remotes/origin/main)"
    if [[ "$HEAD_SHA" != "$ORIGIN_MAIN_SHA" \
        || "$(scalar git -C "$PROJECT_ROOT" rev-parse HEAD)" != "$HEAD_SHA" ]]; then
        echo "[FAIL] Verified launcher source refs changed"
        exit 1
    fi
else
    ORIGIN_URL="$(scalar git -C "$PROJECT_ROOT" remote get-url origin)"
    if [[ "$ORIGIN_URL" != "$APPROVED_ORIGIN_URL" ]]; then
        echo "[FAIL] Launcher origin is not the approved repository"
        exit 1
    fi
    git -C "$PROJECT_ROOT" fetch --no-tags "$APPROVED_ORIGIN_URL" \
        refs/heads/main:refs/remotes/origin/main
    HEAD_SHA="$(scalar git -C "$PROJECT_ROOT" rev-parse HEAD)"
    ORIGIN_MAIN_SHA="$(scalar git -C "$PROJECT_ROOT" rev-parse refs/remotes/origin/main)"
    if [[ -n "$(git -C "$PROJECT_ROOT" status --porcelain=v1 --untracked-files=all | tr -d '\r')" \
        || "$HEAD_SHA" != "$ORIGIN_MAIN_SHA" ]]; then
        echo "[FAIL] Launcher requires committed clean HEAD == origin/main"
        exit 1
    fi
fi

umask 077
if [[ "${JSPACE_PV2_VERIFIED_REEXEC:-}" != "1" ]]; then
    SNAPSHOT_NONCE="$(scalar python -c \
        'import secrets; print(secrets.token_hex(16))')"
    if [[ ! "$SNAPSHOT_NONCE" =~ ^[0-9a-f]{32}$ ]]; then
        echo "[FAIL] Launch snapshot nonce is malformed"
        exit 1
    fi
    GIT_PRIVATE_ROOT="$(scalar git -C "$PROJECT_ROOT" rev-parse --absolute-git-dir)"
    SNAPSHOT_DIR="$GIT_PRIVATE_ROOT/parser-v2-launch-inputs-${SNAPSHOT_NONCE}"
    mkdir "$SNAPSHOT_DIR"
    SNAPSHOT_CLEANUP_ARMED="true"
    SNAPSHOT_SOURCE_ROOT="$SNAPSHOT_DIR/sources"
    RUNTIME_CONFIG_SNAPSHOT_FILE="$SNAPSHOT_DIR/runtime-config.snapshot.json"
    IMPLEMENTATION_MANIFEST_SNAPSHOT_FILE="$SNAPSHOT_DIR/implementation-manifest.snapshot.json"
    IMAGE_BINDING_SNAPSHOT_FILE="$SNAPSHOT_DIR/image-binding.snapshot.json"
    HELPER_SNAPSHOT_MANIFEST_FILE="$SNAPSHOT_DIR/helper-snapshots.json"
    python - "$PROJECT_ROOT" "$HEAD_SHA" \
        "$RUNTIME_CONFIG_SOURCE_FILE" "$RUNTIME_CONFIG_SNAPSHOT_FILE" \
        "$CONFIG_SHA256" "$IMPLEMENTATION_MANIFEST_SOURCE_FILE" \
        "$IMPLEMENTATION_MANIFEST_SNAPSHOT_FILE" \
        "$IMPLEMENTATION_MANIFEST_SHA256" "$IMAGE_BINDING_SOURCE_FILE" \
        "$IMAGE_BINDING_SNAPSHOT_FILE" "$IMAGE_BINDING_SHA256" \
        "$SNAPSHOT_SOURCE_ROOT" "$HELPER_SNAPSHOT_MANIFEST_FILE" <<'PY'
import hashlib
import json
import os
import pathlib
import stat
import subprocess
import sys


def stable_read(path):
    source = pathlib.Path(path)
    try:
        path_state = source.lstat()
    except OSError:
        raise SystemExit("launcher input is unavailable") from None
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    descriptor = os.open(source, flags)
    try:
        before = os.fstat(descriptor)
        if stat.S_ISLNK(path_state.st_mode) or not stat.S_ISREG(before.st_mode):
            raise SystemExit("launcher input is not a nonsymlink regular file")
        chunks = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    def path_identity(value):
        return (
            value.st_dev,
            value.st_ino,
            value.st_size,
            value.st_mtime_ns,
        )
    def descriptor_identity(value):
        return (
            *path_identity(value),
            value.st_ctime_ns,
        )
    if (
        descriptor_identity(before) != descriptor_identity(after)
        or path_identity(path_state) != path_identity(before)
    ):
        raise SystemExit("launcher input changed during atomic snapshot")
    data = b"".join(chunks)
    if len(data) != before.st_size:
        raise SystemExit("launcher input snapshot is incomplete")
    return data


def publish(path, data):
    target = pathlib.Path(path)
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = target.with_name(target.name + ".part")
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_BINARY", 0)
    )
    descriptor = os.open(temporary, flags, 0o600)
    try:
        view = memoryview(data)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise SystemExit("launcher input snapshot write failed")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.chmod(temporary, 0o400)
    os.replace(temporary, target)


(
    project_root,
    head,
    runtime_source,
    runtime_target,
    runtime_sha,
    implementation_source,
    implementation_target,
    implementation_sha,
    image_source,
    image_target,
    image_sha,
    source_root,
    manifest_path,
) = sys.argv[1:]
pairs = (
    (runtime_source, runtime_target, runtime_sha, "runtime config"),
    (
        implementation_source,
        implementation_target,
        implementation_sha,
        "implementation manifest",
    ),
    (image_source, image_target, image_sha, "image binding"),
)
snapshots = {}
for source, target, expected_sha256, name in pairs:
    data = stable_read(source)
    if hashlib.sha256(data).hexdigest() != expected_sha256:
        raise SystemExit(f"{name} hash mismatch")
    publish(target, data)
    snapshots[name] = data

expected_paths = (
    "Dockerfile.parser-v2-eval",
    "requirements-parser-v2-eval.txt",
    "infra/azure/scripts/09_build_parser_v2_eval.sh",
    "infra/azure/scripts/10_run_parser_v2_locked_eval.sh",
    "scripts/create_parser_v2_runtime_config.py",
    "scripts/bootstrap_parser_v2_locked_evaluation.py",
    "scripts/parser_v2_azure_contract.py",
    "scripts/parser_v2_process_worker.py",
    "scripts/run_parser_v2_locked_predictions.py",
    "scripts/finalize_parser_v2_locked_evaluation.py",
    "scripts/stage_p_entrypoint.sh",
    "scripts/stage_p_adopt_entrypoint.sh",
    "scripts/stage_e_entrypoint.sh",
    "src/jspace_observation/evaluator_validation.py",
    "src/jspace_observation/eval_parsing.py",
    "src/jspace_observation/eval_parsing_v2.py",
    "src/jspace_observation/parser_v2_locked_evaluation.py",
)


def reject_duplicates(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise SystemExit("runtime config contains a duplicate JSON field")
        value[key] = item
    return value


try:
    runtime = json.loads(
        snapshots["runtime config"].decode("ascii"),
        object_pairs_hook=reject_duplicates,
    )
except (UnicodeError, ValueError):
    raise SystemExit("runtime config snapshot is invalid") from None
canonical = (
    json.dumps(runtime, sort_keys=True, separators=(",", ":")) + "\n"
).encode("ascii")
if canonical != snapshots["runtime config"]:
    raise SystemExit("runtime config snapshot is not canonical")
bindings = runtime.get("source_bindings")
if (
    runtime.get("schema_version") != "phase1-parser-v2-runtime-config/v5"
    or runtime.get("source_commit") != head
    or not isinstance(bindings, dict)
    or set(bindings) != set(expected_paths)
):
    raise SystemExit("runtime helper snapshot registration is incomplete")
source_root_path = pathlib.Path(source_root)
source_root_path.mkdir(mode=0o700)
checked = {}
for relative_path in expected_paths:
    binding = bindings[relative_path]
    if (
        not isinstance(binding, dict)
        or set(binding) != {"git_blob_oid", "sha256"}
        or not isinstance(binding["git_blob_oid"], str)
        or len(binding["git_blob_oid"]) not in {40, 64}
        or any(c not in "0123456789abcdef" for c in binding["git_blob_oid"])
        or not isinstance(binding["sha256"], str)
        or len(binding["sha256"]) != 64
        or any(c not in "0123456789abcdef" for c in binding["sha256"])
    ):
        raise SystemExit(f"runtime helper binding is invalid: {relative_path}")
    oid = subprocess.run(
        ["git", "-C", project_root, "rev-parse", f"{head}:{relative_path}"],
        check=True,
        capture_output=True,
    ).stdout.decode("ascii").replace("\r", "").strip()
    kind = subprocess.run(
        ["git", "-C", project_root, "cat-file", "-t", oid],
        check=True,
        capture_output=True,
    ).stdout.decode("ascii").replace("\r", "").strip()
    data = subprocess.run(
        ["git", "-C", project_root, "cat-file", "blob", oid],
        check=True,
        capture_output=True,
    ).stdout
    if (
        kind != "blob"
        or oid != binding["git_blob_oid"]
        or hashlib.sha256(data).hexdigest() != binding["sha256"]
    ):
        raise SystemExit(f"registered helper Git blob differs: {relative_path}")
    publish(source_root_path / relative_path, data)
    checked[relative_path] = dict(binding)
manifest = (
    json.dumps(checked, sort_keys=True, separators=(",", ":")) + "\n"
).encode("ascii")
if hashlib.sha256(manifest).hexdigest() != runtime.get(
    "helper_snapshot_set_sha256"
):
    raise SystemExit("helper snapshot-set hash differs from runtime config")
publish(manifest_path, manifest)
PY
    SNAPSHOT_LAUNCHER="$SNAPSHOT_SOURCE_ROOT/infra/azure/scripts/10_run_parser_v2_locked_eval.sh"
    if [[ ! -r "$SNAPSHOT_LAUNCHER" ]]; then
        echo "[FAIL] Verified launcher snapshot is missing"
        exit 1
    fi
    snapshot_environment=(
        "HOME=${HOME:-/nonexistent}"
        "LANG=C.UTF-8"
        "LC_ALL=C.UTF-8"
        "PATH=$CLEAN_PATH"
        "GIT_NO_REPLACE_OBJECTS=1"
        "JSPACE_PV2_LAUNCH_CLEAN_REEXEC=1"
        "JSPACE_PV2_VERIFIED_REEXEC=1"
        "JSPACE_PV2_PROJECT_ROOT=$PROJECT_ROOT"
        "JSPACE_PV2_SNAPSHOT_DIR=$SNAPSHOT_DIR"
        "JSPACE_PV2_HEAD_SHA=$HEAD_SHA"
        "JSPACE_PV2_CORE_PATH=$SNAPSHOT_SOURCE_ROOT/src/jspace_observation/parser_v2_locked_evaluation.py"
    )
    for name in \
        AZURE_CONFIG_DIR PARSER_EVAL_STAGE PARSER_EVAL_VERIFY_ONLY \
        PARSER_EVAL_CLOSE_INVALID_ONLY \
        PARSER_EVAL_VERIFICATION_STATE PARSER_EVAL_RETRY_KIND \
        PARSER_EVAL_RECOVER_CLAIM_NAME PARSER_EVAL_INITIAL_BOOTSTRAP \
        PARSER_EVAL_RUNTIME_CONFIG_FILE PARSER_EVAL_CONFIG_SHA256 \
        PARSER_EVAL_IMPLEMENTATION_MANIFEST_FILE \
        PARSER_EVAL_IMPLEMENTATION_MANIFEST_SHA256 \
        PARSER_EVAL_IMAGE_BINDING_FILE PARSER_EVAL_IMAGE_BINDING_SHA256 \
        PARSER_EVAL_AUTHORIZATION_LOCK_SHA256 \
        PARSER_EVAL_AUTHORIZATION_MANIFEST_SHA256 \
        PARSER_EVAL_BOOTSTRAP_STATE_RECEIPT_SHA256 \
        PARSER_EVAL_UNSEAL_RECEIPT_SHA256 \
        PARSER_EVAL_LOCKED_INPUT_SHA256 \
        PARSER_EVAL_LOCKED_INPUT_MANIFEST_SHA256 \
        PARSER_EVAL_PREDICTIONS_RECEIPT_SHA256 \
        PARSER_EVAL_PREDICTION_MANIFEST_SHA256 \
        PARSER_EVAL_LABELS_SHA256 PARSER_EVAL_LABELS_MANIFEST_SHA256 \
        PARSER_EVAL_SCORES_MANIFEST_SHA256 \
        PARSER_EVAL_CLOSED_RECEIPT_SHA256 PARSER_EVAL_BUILD_RECORD_DIR \
        PARSER_EVAL_BASE_IMAGE; do
        if [[ -v "$name" ]]; then
            snapshot_environment+=("$name=${!name}")
        fi
    done
    builtin exec /usr/bin/env -i "${snapshot_environment[@]}" \
        /bin/bash --noprofile --norc -p "$SNAPSHOT_LAUNCHER"
fi
unset RUNTIME_CONFIG_SOURCE_FILE IMPLEMENTATION_MANIFEST_SOURCE_FILE
unset IMAGE_BINDING_SOURCE_FILE

verify_immutable_launch_inputs() {
    python - "$RUNTIME_CONFIG_SNAPSHOT_FILE" "$CONFIG_SHA256" \
        "$IMPLEMENTATION_MANIFEST_SNAPSHOT_FILE" \
        "$IMPLEMENTATION_MANIFEST_SHA256" "$IMAGE_BINDING_SNAPSHOT_FILE" \
        "$IMAGE_BINDING_SHA256" "$HELPER_SNAPSHOT_MANIFEST_FILE" \
        "$SNAPSHOT_SOURCE_ROOT" "${BODY_FILE:-}" \
        "${JOB_BODY_SHA256:-}" <<'PY'
import hashlib
import json
import pathlib
import sys

pairs = (
    (sys.argv[1], sys.argv[2], "runtime config snapshot"),
    (sys.argv[3], sys.argv[4], "implementation manifest snapshot"),
    (sys.argv[5], sys.argv[6], "image binding snapshot"),
)
if sys.argv[10]:
    if not sys.argv[9]:
        raise SystemExit("derived job body snapshot binding is incomplete")
    pairs += ((sys.argv[9], sys.argv[10], "derived job body"),)
for path, expected, name in pairs:
    try:
        actual = hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
    except OSError:
        raise SystemExit(f"{name} is unavailable") from None
    if actual != expected:
        raise SystemExit(f"{name} changed after validation")
runtime = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="ascii"))
manifest_bytes = pathlib.Path(sys.argv[7]).read_bytes()
if hashlib.sha256(manifest_bytes).hexdigest() != runtime.get(
    "helper_snapshot_set_sha256"
):
    raise SystemExit("helper snapshot-set manifest changed after validation")
manifest = json.loads(manifest_bytes)
if manifest != runtime.get("source_bindings"):
    raise SystemExit("helper snapshot-set membership changed after validation")
root = pathlib.Path(sys.argv[8])
for relative_path, binding in manifest.items():
    try:
        data = (root / relative_path).read_bytes()
    except OSError:
        raise SystemExit(f"helper snapshot is unavailable: {relative_path}") from None
    if hashlib.sha256(data).hexdigest() != binding["sha256"]:
        raise SystemExit(f"helper snapshot changed after validation: {relative_path}")
PY
}

verify_snapshot_git_bindings() {
    python - "$PROJECT_ROOT" "$HEAD_SHA" "$RUNTIME_CONFIG_SNAPSHOT_FILE" \
        "$CONFIG_SHA256" "$HELPER_SNAPSHOT_MANIFEST_FILE" \
        "$SNAPSHOT_SOURCE_ROOT" <<'PY'
import hashlib
import json
import pathlib
import stat
import subprocess
import sys


def reject_duplicates(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise SystemExit("verified launcher input has a duplicate JSON field")
        value[key] = item
    return value


project_root, head, runtime_path, runtime_sha, manifest_path, source_root = (
    sys.argv[1:]
)
expected_paths = (
    "Dockerfile.parser-v2-eval",
    "requirements-parser-v2-eval.txt",
    "infra/azure/scripts/09_build_parser_v2_eval.sh",
    "infra/azure/scripts/10_run_parser_v2_locked_eval.sh",
    "scripts/create_parser_v2_runtime_config.py",
    "scripts/bootstrap_parser_v2_locked_evaluation.py",
    "scripts/parser_v2_azure_contract.py",
    "scripts/parser_v2_process_worker.py",
    "scripts/run_parser_v2_locked_predictions.py",
    "scripts/finalize_parser_v2_locked_evaluation.py",
    "scripts/stage_p_entrypoint.sh",
    "scripts/stage_p_adopt_entrypoint.sh",
    "scripts/stage_e_entrypoint.sh",
    "src/jspace_observation/evaluator_validation.py",
    "src/jspace_observation/eval_parsing.py",
    "src/jspace_observation/eval_parsing_v2.py",
    "src/jspace_observation/parser_v2_locked_evaluation.py",
)
try:
    runtime_bytes = pathlib.Path(runtime_path).read_bytes()
    manifest_bytes = pathlib.Path(manifest_path).read_bytes()
    runtime = json.loads(
        runtime_bytes.decode("ascii"), object_pairs_hook=reject_duplicates
    )
    manifest = json.loads(
        manifest_bytes.decode("ascii"), object_pairs_hook=reject_duplicates
    )
except (OSError, UnicodeError, ValueError):
    raise SystemExit("verified launcher Git snapshot metadata is invalid") from None
canonical_runtime = (
    json.dumps(runtime, sort_keys=True, separators=(",", ":")) + "\n"
).encode("ascii")
canonical_manifest = (
    json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n"
).encode("ascii")
bindings = runtime.get("source_bindings")
if (
    runtime_bytes != canonical_runtime
    or hashlib.sha256(runtime_bytes).hexdigest() != runtime_sha
    or runtime.get("schema_version") != "phase1-parser-v2-runtime-config/v5"
    or runtime.get("source_commit") != head
    or not isinstance(bindings, dict)
    or set(bindings) != set(expected_paths)
    or manifest != bindings
    or manifest_bytes != canonical_manifest
    or hashlib.sha256(manifest_bytes).hexdigest()
    != runtime.get("helper_snapshot_set_sha256")
):
    raise SystemExit("verified launcher Git snapshot metadata differs")
root = pathlib.Path(source_root)
for relative_path in expected_paths:
    binding = bindings[relative_path]
    if (
        not isinstance(binding, dict)
        or set(binding) != {"git_blob_oid", "sha256"}
        or not isinstance(binding["git_blob_oid"], str)
        or len(binding["git_blob_oid"]) not in {40, 64}
        or any(c not in "0123456789abcdef" for c in binding["git_blob_oid"])
        or not isinstance(binding["sha256"], str)
        or len(binding["sha256"]) != 64
        or any(c not in "0123456789abcdef" for c in binding["sha256"])
    ):
        raise SystemExit(f"verified launcher Git binding is invalid: {relative_path}")
    oid = subprocess.run(
        ["git", "-C", project_root, "rev-parse", f"{head}:{relative_path}"],
        check=True,
        capture_output=True,
    ).stdout.decode("ascii").replace("\r", "").strip()
    kind = subprocess.run(
        ["git", "-C", project_root, "cat-file", "-t", oid],
        check=True,
        capture_output=True,
    ).stdout.decode("ascii").replace("\r", "").strip()
    committed = subprocess.run(
        ["git", "-C", project_root, "cat-file", "blob", oid],
        check=True,
        capture_output=True,
    ).stdout
    snapshot_path = root / relative_path
    try:
        snapshot_state = snapshot_path.lstat()
        snapshot = snapshot_path.read_bytes()
    except OSError:
        raise SystemExit(
            f"verified launcher helper snapshot is unavailable: {relative_path}"
        ) from None
    if (
        kind != "blob"
        or oid != binding["git_blob_oid"]
        or hashlib.sha256(committed).hexdigest() != binding["sha256"]
        or stat.S_ISLNK(snapshot_state.st_mode)
        or not stat.S_ISREG(snapshot_state.st_mode)
        or snapshot != committed
    ):
        raise SystemExit(
            f"verified launcher helper differs from Git: {relative_path}"
        )
PY
}

verify_snapshot_git_bindings || exit 1
verify_immutable_launch_inputs || exit 1
SNAPSHOT_CLEANUP_ARMED="true"

RUNTIME_VALUES_FILE="$SCRATCH_DIR/runtime_values.txt"
python - "$CORE_FILE" "$RUNTIME_CONFIG_SNAPSHOT_FILE" "$CONFIG_SHA256" \
        "$IMPLEMENTATION_MANIFEST_SNAPSHOT_FILE" \
        "$IMPLEMENTATION_MANIFEST_SHA256" "$IMAGE_BINDING_SNAPSHOT_FILE" \
        "$IMAGE_BINDING_SHA256" \
        "$PROJECT_ROOT" "$HEAD_SHA" <<'PY' | tr -d '\r' \
        >"$RUNTIME_VALUES_FILE" || exit 1
import hashlib
import importlib.util
import pathlib
import subprocess
import sys

(
    core_path,
    config_path,
    config_sha,
    implementation_path,
    implementation_sha,
    image_binding_path,
    image_binding_sha,
    project_root,
    head,
) = sys.argv[1:]
spec = importlib.util.spec_from_file_location("_pv2_launcher_core", core_path)
if spec is None or spec.loader is None:
    raise SystemExit("cannot load locked evaluation core")
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)
runtime_bytes = pathlib.Path(config_path).read_bytes()
implementation_bytes = pathlib.Path(implementation_path).read_bytes()
image_binding_bytes = pathlib.Path(image_binding_path).read_bytes()
if core.sha256_bytes(runtime_bytes) != config_sha:
    raise SystemExit("runtime config hash mismatch")
if core.sha256_bytes(implementation_bytes) != implementation_sha:
    raise SystemExit("implementation manifest hash mismatch")
if core.sha256_bytes(image_binding_bytes) != image_binding_sha:
    raise SystemExit("image binding hash mismatch")
implementation = core.validate_implementation_manifest(implementation_bytes)
image_binding = core.validate_image_binding(
    image_binding_bytes,
    expected_sha256=image_binding_sha,
    expected_source_commit=head,
)
for path, binding in image_binding["files"].items():
    oid = subprocess.run(
        ["git", "-C", project_root, "rev-parse", f"{head}:{path}"],
        check=True,
        capture_output=True,
    ).stdout.decode("ascii").replace("\r", "").strip()
    data = subprocess.run(
        ["git", "-C", project_root, "cat-file", "blob", oid],
        check=True,
        capture_output=True,
    ).stdout
    if (
        oid != binding["git_blob_oid"]
        or len(data) != binding["size"]
        or hashlib.sha256(data).hexdigest() != binding["sha256"]
    ):
        raise SystemExit(f"image source Git blob differs: {path}")
raw = core.parse_json_strict(runtime_bytes, "runtime config")
bindings = raw.get("bindings", {})
source_bindings = {}
for path in core.RUNTIME_SOURCE_BINDING_PATHS:
    oid_result = subprocess.run(
        ["git", "-C", project_root, "rev-parse", f"{head}:{path}"],
        check=True,
        capture_output=True,
    )
    oid = oid_result.stdout.decode("ascii").replace("\r", "").strip()
    data = subprocess.run(
        ["git", "-C", project_root, "cat-file", "blob", oid],
        check=True,
        capture_output=True,
    ).stdout
    source_bindings[path] = {
        "git_blob_oid": oid,
        "sha256": hashlib.sha256(data).hexdigest(),
    }
launcher = source_bindings[
    "infra/azure/scripts/10_run_parser_v2_locked_eval.sh"
]
runtime = core.validate_runtime_configuration(
    runtime_bytes,
    expected_sha256=config_sha,
    source_commit=head,
    parent_prefix=bindings.get("registered_parent_prefix"),
    authorization_id=bindings.get("authorization_id"),
    launcher_sha256=launcher["sha256"],
    launcher_git_blob_oid=launcher["git_blob_oid"],
    expected_image_digest=implementation["image_digest"],
    image_binding_bytes=image_binding_bytes,
    expected_image_binding_sha256=image_binding_sha,
)
if (
    runtime["source_bindings"] != source_bindings
    or implementation["implementation_commit"] != head
    or implementation["config_sha256"] != config_sha
    or implementation["image_digest"] != image_binding["image_digest"]
    or runtime["image_binding"] != image_binding
):
    raise SystemExit(
        "runtime/implementation/image bytes differ from committed source"
    )
d = runtime["azure_destination"]
n = d["network"]
c = d["coordination"]
values = (
    runtime["source_commit"],
    bindings["registered_parent_prefix"],
    bindings["authorization_id"],
    bindings["predictions_prefix"],
    bindings["scores_prefix"],
    bindings["state_prefix"],
    bindings["visibility_prefix"],
    launcher["sha256"],
    launcher["git_blob_oid"],
    runtime["azure_destination_sha256"],
    d["subscription_id"],
    d["resource_group"],
    d["location"],
    d["container_apps"]["environment_name"],
    d["container_apps"]["environment_resource_id"],
    d["container_apps"]["job_name"],
    d["container_apps"]["job_resource_id"],
    d["container_apps"]["workload_profile"],
    d["managed_identity"]["name"],
    d["managed_identity"]["resource_id"],
    d["managed_identity"]["client_id"],
    d["managed_identity"]["principal_id"],
    d["storage"]["account_name"],
    d["storage"]["resource_id"],
    d["storage"]["blob_endpoint"],
    d["storage"]["container"],
    n["vnet_resource_id"],
    n["infrastructure_subnet_resource_id"],
    n["private_endpoint_subnet_resource_id"],
    n["private_endpoint_resource_id"],
    n["private_endpoint_name"],
    n["private_endpoint_resource_group"],
    n["private_link_connection_name"],
    n["storage_private_endpoint_connection_name"],
    n["storage_private_endpoint_connection_resource_id"],
    n["private_link_group_id"],
    n["private_link_subresource"],
    core.canonical_json_text(n["private_endpoint_nic_private_ips"]),
    n["private_dns_zone_name"],
    n["private_dns_zone_resource_id"],
    n["private_dns_zone_group_name"],
    n["private_dns_vnet_link_name"],
    d["registry"]["name"],
    d["registry"]["resource_id"],
    d["registry"]["login_server"],
    d["registry"]["repository"],
    d["image"]["digest"],
    d["image"]["reference"],
    d["image"]["base_image"],
    runtime["image_binding_sha256"],
    runtime["helper_snapshot_set_sha256"],
    image_binding["build_provenance_sha256"],
    image_binding["build_provenance"]["acr"]["location"],
    image_binding["acr_build_task_run_name"],
    image_binding["acr_build_task_run_resource_id"],
    image_binding["acr_build_run_id"],
    image_binding["build_run_request_sha256"],
    image_binding["staging_image_tag"],
    image_binding["remote_source_location"],
    image_binding["image_tag"],
    image_binding["oci_verification_sha256"],
    c["zone_name"],
    c["zone_resource_id"],
    c["zone_location"],
    c["zone_internal_id"],
    c["private_dns_api_version"],
    str(c["record_ttl"]),
    str(c["expected_vnet_link_count"]),
    c["lock_name"],
    c["lock_resource_id"],
    c["lock_level"],
    c["management_lock_api_version"],
    core.coordination_binding_sha256(c),
)
for value in values:
    if "\r" in value or "\n" in value:
        raise SystemExit("runtime binding is not scalar")
    print(value)
PY
mapfile -t RUNTIME_VALUES <"$RUNTIME_VALUES_FILE"
if [[ "${#RUNTIME_VALUES[@]}" -ne 73 ]]; then
    echo "[FAIL] Runtime destination extraction is incomplete"
    exit 1
fi
SOURCE_SHA="${RUNTIME_VALUES[0]}"
PARENT_PREFIX="${RUNTIME_VALUES[1]}"
AUTHORIZATION_ID="${RUNTIME_VALUES[2]}"
PREDICTIONS_ROOT_PREFIX="${RUNTIME_VALUES[3]}"
SCORES_ROOT_PREFIX="${RUNTIME_VALUES[4]}"
STATE_PREFIX="${RUNTIME_VALUES[5]}"
VISIBILITY_ROOT_PREFIX="${RUNTIME_VALUES[6]}"
LAUNCHER_CONTENT_SHA256="${RUNTIME_VALUES[7]}"
LAUNCHER_GIT_BLOB_OID="${RUNTIME_VALUES[8]}"
AZURE_DESTINATION_SHA256="${RUNTIME_VALUES[9]}"
SUBSCRIPTION_ID="${RUNTIME_VALUES[10]}"
RESOURCE_GROUP="${RUNTIME_VALUES[11]}"
LOCATION="${RUNTIME_VALUES[12]}"
CONTAINER_APP_ENV="${RUNTIME_VALUES[13]}"
ENVIRONMENT_ID="${RUNTIME_VALUES[14]}"
JOB_NAME="${RUNTIME_VALUES[15]}"
JOB_ID="${RUNTIME_VALUES[16]}"
WORKLOAD_PROFILE="${RUNTIME_VALUES[17]}"
IDENTITY_NAME="${RUNTIME_VALUES[18]}"
IDENTITY_ID="${RUNTIME_VALUES[19]}"
IDENTITY_CLIENT_ID="${RUNTIME_VALUES[20]}"
IDENTITY_PRINCIPAL_ID="${RUNTIME_VALUES[21]}"
BLOB_ACCOUNT="${RUNTIME_VALUES[22]}"
STORAGE_ID="${RUNTIME_VALUES[23]}"
ACCOUNT_URL="${RUNTIME_VALUES[24]}"
BLOB_CONTAINER="${RUNTIME_VALUES[25]}"
ENVIRONMENT_VNET_ID="${RUNTIME_VALUES[26]}"
ENVIRONMENT_SUBNET_ID="${RUNTIME_VALUES[27]}"
PRIVATE_ENDPOINT_SUBNET_ID="${RUNTIME_VALUES[28]}"
PRIVATE_ENDPOINT_ID="${RUNTIME_VALUES[29]}"
BLOB_PRIVATE_ENDPOINT_NAME="${RUNTIME_VALUES[30]}"
BLOB_PRIVATE_ENDPOINT_RESOURCE_GROUP="${RUNTIME_VALUES[31]}"
PRIVATE_LINK_CONNECTION_NAME="${RUNTIME_VALUES[32]}"
STORAGE_PRIVATE_ENDPOINT_CONNECTION_NAME="${RUNTIME_VALUES[33]}"
STORAGE_PRIVATE_ENDPOINT_CONNECTION_ID="${RUNTIME_VALUES[34]}"
PRIVATE_LINK_GROUP_ID="${RUNTIME_VALUES[35]}"
PRIVATE_LINK_SUBRESOURCE="${RUNTIME_VALUES[36]}"
PRIVATE_ENDPOINT_IPS_JSON="${RUNTIME_VALUES[37]}"
BLOB_PRIVATE_DNS_ZONE_NAME="${RUNTIME_VALUES[38]}"
PRIVATE_DNS_ZONE_ID="${RUNTIME_VALUES[39]}"
BLOB_PRIVATE_DNS_ZONE_GROUP_NAME="${RUNTIME_VALUES[40]}"
BLOB_PRIVATE_DNS_LINK_NAME="${RUNTIME_VALUES[41]}"
ACR_NAME="${RUNTIME_VALUES[42]}"
ACR_ID="${RUNTIME_VALUES[43]}"
LOGIN_SERVER="${RUNTIME_VALUES[44]}"
IMAGE_REPOSITORY="${RUNTIME_VALUES[45]}"
IMAGE_DIGEST="${RUNTIME_VALUES[46]}"
IMAGE_REF="${RUNTIME_VALUES[47]}"
BASE_IMAGE="${RUNTIME_VALUES[48]}"
IMAGE_BINDING_SHA256="${RUNTIME_VALUES[49]}"
HELPER_SNAPSHOT_SET_SHA256="${RUNTIME_VALUES[50]}"
BUILD_PROVENANCE_SHA256="${RUNTIME_VALUES[51]}"
ACR_LOCATION="${RUNTIME_VALUES[52]}"
ACR_BUILD_TASK_RUN_NAME="${RUNTIME_VALUES[53]}"
ACR_BUILD_TASK_RUN_RESOURCE_ID="${RUNTIME_VALUES[54]}"
ACR_BUILD_RUN_ID="${RUNTIME_VALUES[55]}"
BUILD_RUN_REQUEST_SHA256="${RUNTIME_VALUES[56]}"
STAGING_IMAGE_TAG="${RUNTIME_VALUES[57]}"
REMOTE_SOURCE_LOCATION="${RUNTIME_VALUES[58]}"
FINAL_IMAGE_TAG="${RUNTIME_VALUES[59]}"
OCI_VERIFICATION_SHA256="${RUNTIME_VALUES[60]}"
COORDINATION_ZONE_NAME="${RUNTIME_VALUES[61]}"
COORDINATION_ZONE_RESOURCE_ID="${RUNTIME_VALUES[62]}"
COORDINATION_ZONE_LOCATION="${RUNTIME_VALUES[63]}"
COORDINATION_ZONE_INTERNAL_ID="${RUNTIME_VALUES[64]}"
COORDINATION_DNS_API_VERSION="${RUNTIME_VALUES[65]}"
COORDINATION_RECORD_TTL="${RUNTIME_VALUES[66]}"
COORDINATION_EXPECTED_LINK_COUNT="${RUNTIME_VALUES[67]}"
COORDINATION_LOCK_NAME="${RUNTIME_VALUES[68]}"
COORDINATION_LOCK_RESOURCE_ID="${RUNTIME_VALUES[69]}"
COORDINATION_LOCK_LEVEL="${RUNTIME_VALUES[70]}"
COORDINATION_LOCK_API_VERSION="${RUNTIME_VALUES[71]}"
COORDINATION_BINDING_SHA256="${RUNTIME_VALUES[72]}"
if [[ -n "${AZURE_CLIENT_ID:-}" \
    && "$AZURE_CLIENT_ID" != "$IDENTITY_CLIENT_ID" ]]; then
    echo "[FAIL] Caller managed-identity client ID differs from runtime binding"
    exit 1
fi
AZURE_CLIENT_ID="$IDENTITY_CLIENT_ID"
export AZURE_CLIENT_ID
if [[ ! "$ACR_BUILD_TASK_RUN_NAME" \
        =~ ^[a-z0-9][a-z0-9-]{3,48}[a-z0-9]$ \
    || ! "$ACR_LOCATION" =~ ^[a-z0-9][a-z0-9-]{0,62}$ \
    || "${ACR_BUILD_TASK_RUN_RESOURCE_ID,,}" \
        != "${ACR_ID,,}/taskruns/${ACR_BUILD_TASK_RUN_NAME}" \
    || ! "$ACR_BUILD_RUN_ID" \
        =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$ \
    || ! "$BUILD_RUN_REQUEST_SHA256" =~ ^[0-9a-f]{64}$ ]]; then
    echo "[FAIL] Runtime ACR TaskRun binding is malformed"
    exit 1
fi
IMPLEMENTATION_COMMIT="$SOURCE_SHA"
RUN_ID="${PARENT_PREFIX##*/}"
RECORD_DIR="$PROJECT_ROOT/results/runs/parser-v2-eval-${AUTHORIZATION_ID}"

if [[ "$STAGE" == "P" ]]; then
    if [[ "$RETRY_KIND" == "prediction_adoption" ]]; then
        AUTH_STATE="INPUTS_READ"
        STAGE_PRIOR_RECEIPT_SHA256="$BOOTSTRAP_STATE_RECEIPT_SHA256"
        AUTH_RECEIPT_SHA256="$BOOTSTRAP_STATE_RECEIPT_SHA256"
    else
        AUTH_STATE="UNSEAL_AUTHORIZED"
    fi
    if [[ "$RETRY_KIND" == "none" ]]; then
        STAGE_PRIOR_RECEIPT_SHA256="${PARSER_EVAL_UNSEAL_RECEIPT_SHA256:-$BOOTSTRAP_STATE_RECEIPT_SHA256}"
        AUTH_RECEIPT_SHA256="$STAGE_PRIOR_RECEIPT_SHA256"
    elif [[ "$RETRY_KIND" == "infrastructure_pre_input" ]]; then
        STAGE_PRIOR_RECEIPT_SHA256="${PARSER_EVAL_UNSEAL_RECEIPT_SHA256:-}"
        AUTH_RECEIPT_SHA256="$BOOTSTRAP_STATE_RECEIPT_SHA256"
    fi
elif [[ "$VERIFY_ONLY" == "true" ]]; then
    AUTH_STATE="$VERIFICATION_STATE"
    STAGE_PRIOR_RECEIPT_SHA256="${PARSER_EVAL_PREDICTIONS_RECEIPT_SHA256:-}"
    case "$AUTH_STATE" in
        PREDICTIONS_VERIFIED|LABELS_READ|SCORES_VERIFIED)
            AUTH_RECEIPT_SHA256="$BOOTSTRAP_STATE_RECEIPT_SHA256"
            ;;
        CLOSED)
            AUTH_RECEIPT_SHA256="${PARSER_EVAL_CLOSED_RECEIPT_SHA256:-$BOOTSTRAP_STATE_RECEIPT_SHA256}"
            ;;
    esac
else
    AUTH_STATE="PREDICTIONS_VERIFIED"
    STAGE_PRIOR_RECEIPT_SHA256="${PARSER_EVAL_PREDICTIONS_RECEIPT_SHA256:-}"
    if [[ "$RETRY_KIND" == "none" ]]; then
        AUTH_RECEIPT_SHA256="${STAGE_PRIOR_RECEIPT_SHA256:-$BOOTSTRAP_STATE_RECEIPT_SHA256}"
    else
        AUTH_RECEIPT_SHA256="$BOOTSTRAP_STATE_RECEIPT_SHA256"
    fi
fi

INVOCATION_ID="$(scalar python "$AZURE_HELPER" new-id)"
RECOVERY_ONLY="false"
RECOVERY_REQUESTED="false"
if [[ -n "$RECOVER_CLAIM_NAME" ]]; then
    RECOVERY_REQUESTED="true"
fi
if [[ ! "$INVOCATION_ID" =~ ^[0-9a-f]{32}$ ]]; then
    echo "[FAIL] Launch invocation ID is malformed"
    exit 1
fi
SCRATCH_NONCE="$(scalar python "$AZURE_HELPER" new-id)"
if [[ ! "$SCRATCH_NONCE" =~ ^[0-9a-f]{32}$ ]]; then
    echo "[FAIL] Launch scratch nonce is malformed"
    exit 1
fi
EXECUTION_ID="stage-${STAGE,,}-${INVOCATION_ID}"
ACTOR="stage-${STAGE,,}-managed-runtime"
if [[ "$RETRY_KIND" == "prediction_adoption" ]]; then
    ACTOR="stage-p-adoption-runtime"
fi
CONFIGURED_JOB_NAME="$JOB_NAME"
CONFIGURED_JOB_ID="$JOB_ID"

mkdir -p "$RECORD_DIR"
SCRATCH_DIR="$RECORD_DIR/launch-${STAGE}-${INVOCATION_ID}-${SCRATCH_NONCE}"
umask 077
mkdir "$SCRATCH_DIR"
BODY_FILE="$SCRATCH_DIR/job.json"
EXECUTIONS_FILE="$SCRATCH_DIR/executions.json"
PRIOR_EXECUTION_NAMES_FILE="$SCRATCH_DIR/prior_execution_names.json"
LIVE_JOB_FILE="$SCRATCH_DIR/live_job.json"
PRE_JOB_PUT_GET_FILE="$SCRATCH_DIR/pre_job_put_get.json"
JOB_PUT_RESPONSE_FILE="$SCRATCH_DIR/job_put_response.json"
EXPECTED_PROJECTION_FILE="$SCRATCH_DIR/expected_job_projection.json"
LIVE_PROJECTION_FILE="$SCRATCH_DIR/live_job_projection.json"
START_RESPONSE_FILE="$SCRATCH_DIR/start_response.json"
STAGE_BINDINGS_FILE="$SCRATCH_DIR/stage_bindings.json"
COORDINATION_BINDING_FILE="$SCRATCH_DIR/coordination_binding.json"
COORDINATION_ZONE_FILE="$SCRATCH_DIR/coordination_zone.json"
COORDINATION_LINKS_FILE="$SCRATCH_DIR/coordination_links.json"
COORDINATION_LOCK_FILE="$SCRATCH_DIR/coordination_lock.json"
COORDINATION_VALIDATION_FILE="$SCRATCH_DIR/coordination_validation.json"
BUILD_SLOT_BINDING_FILE="$SCRATCH_DIR/build_slot_binding.json"
BUILD_SLOT_LIVE_FILE="$SCRATCH_DIR/build_slot_live.json"
BUILD_SLOT_EVIDENCE_FILE="$SCRATCH_DIR/build_slot_evidence.json"
LAUNCH_DOMAIN_BINDING_FILE="$SCRATCH_DIR/launch_domain_binding.json"
LAUNCH_CLAIM_VALUES_FILE="$SCRATCH_DIR/launch_claim_values.json"
LAUNCH_CLAIM_ENVELOPE_FILE="$SCRATCH_DIR/launch_claim_envelope.json"
LAUNCH_TXT_BODY_FILE="$SCRATCH_DIR/launch_txt_body.json"
LAUNCH_TXT_CREATE_RESPONSE_FILE="$SCRATCH_DIR/launch_txt_create_response.json"
LAUNCH_TXT_LIVE_FILE="$SCRATCH_DIR/launch_txt_live.json"
LAUNCH_TXT_EVIDENCE_FILE="$SCRATCH_DIR/launch_txt_evidence.json"
DISPATCH_DOMAIN_BINDING_FILE="$SCRATCH_DIR/dispatch_domain_binding.json"
DISPATCH_CLAIM_VALUES_FILE="$SCRATCH_DIR/dispatch_claim_values.json"
DISPATCH_CLAIM_ENVELOPE_FILE="$SCRATCH_DIR/dispatch_claim_envelope.json"
DISPATCH_TXT_BODY_FILE="$SCRATCH_DIR/dispatch_txt_body.json"
DISPATCH_TXT_CREATE_RESPONSE_FILE="$SCRATCH_DIR/dispatch_txt_create_response.json"
DISPATCH_TXT_LIVE_FILE="$SCRATCH_DIR/dispatch_txt_live.json"
DISPATCH_TXT_EVIDENCE_FILE="$SCRATCH_DIR/dispatch_txt_evidence.json"
DISPATCH_MEMBERSHIP_FILE="$SCRATCH_DIR/dispatch_membership.json"
CURRENT_EXECUTION_MEMBERSHIP_FILE="$SCRATCH_DIR/current_execution_membership.json"
ADOPTED_EXECUTION_FILE="$SCRATCH_DIR/adopted_execution.json"
python - "$RUNTIME_CONFIG_SNAPSHOT_FILE" "$COORDINATION_BINDING_FILE" \
    "$BUILD_SLOT_BINDING_FILE" <<'PY'
import json
import pathlib
import sys

runtime = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
pathlib.Path(sys.argv[2]).write_text(
    json.dumps(
        runtime["azure_destination"]["coordination"],
        sort_keys=True,
        separators=(",", ":"),
    )
    + "\n",
    encoding="ascii",
)
pathlib.Path(sys.argv[3]).write_text(
    json.dumps(
        runtime["image_binding"]["build_slot"],
        sort_keys=True,
        separators=(",", ":"),
    )
    + "\n",
    encoding="ascii",
)
PY
BUILD_SLOT_RECORD_NAME="$(scalar python "$AZURE_HELPER" get \
    --json "$BUILD_SLOT_BINDING_FILE" --field record_name)"
BUILD_SLOT_DOMAIN_SHA256="$(scalar python "$AZURE_HELPER" get \
    --json "$BUILD_SLOT_BINDING_FILE" --field domain_sha256)"
BUILD_SLOT_RECORD_URL="https://management.azure.com${COORDINATION_ZONE_RESOURCE_ID}/TXT/${BUILD_SLOT_RECORD_NAME}?api-version=${COORDINATION_DNS_API_VERSION}"
if [[ ! "$BUILD_SLOT_DOMAIN_SHA256" =~ ^[0-9a-f]{64}$ \
    || "$BUILD_SLOT_RECORD_NAME" \
        != "build-${BUILD_SLOT_DOMAIN_SHA256:0:32}.${BUILD_SLOT_DOMAIN_SHA256:32:32}" ]]; then
    echo "[FAIL] Runtime build TXT slot is malformed"
    exit 1
fi

python - "$LAUNCH_DOMAIN_BINDING_FILE" "$AUTHORIZATION_ID" "$STAGE" \
    "$EVALUATION_MODE" "$RETRY_KIND" "$CONFIG_SHA256" \
    "$IMAGE_BINDING_SHA256" "$HELPER_SNAPSHOT_SET_SHA256" \
    "$IMPLEMENTATION_MANIFEST_SHA256" "$AZURE_DESTINATION_SHA256" \
    "$LAUNCHER_CONTENT_SHA256" "$COORDINATION_BINDING_SHA256" <<'PY'
import json
import pathlib
import sys

keys = (
    "authorization_id",
    "stage",
    "mode",
    "retry_kind",
    "config_sha256",
    "image_binding_sha256",
    "helper_snapshot_set_sha256",
    "implementation_manifest_sha256",
    "azure_destination_sha256",
    "launcher_sha256",
    "coordination_binding_sha256",
)
pathlib.Path(sys.argv[1]).write_text(
    json.dumps(
        dict(zip(keys, sys.argv[2:])),
        sort_keys=True,
        separators=(",", ":"),
    )
    + "\n",
    encoding="ascii",
)
PY
LAUNCH_DOMAIN_SHA256="$(scalar python "$AZURE_HELPER" claim-domain \
    --kind launch --binding "$LAUNCH_DOMAIN_BINDING_FILE")"
LAUNCH_RECORD_NAME="launch-${LAUNCH_DOMAIN_SHA256:0:32}.${LAUNCH_DOMAIN_SHA256:32:32}"
LAUNCH_RECORD_URL="https://management.azure.com${COORDINATION_ZONE_RESOURCE_ID}/TXT/${LAUNCH_RECORD_NAME}?api-version=${COORDINATION_DNS_API_VERSION}"
JOB_NAME="pv2-${STAGE,,}-${LAUNCH_DOMAIN_SHA256:0:24}"
JOB_ID="${CONFIGURED_JOB_ID%/*}/${JOB_NAME}"
JOB_URL="https://management.azure.com${JOB_ID}?api-version=2024-03-01"
EXECUTIONS_URL="https://management.azure.com${JOB_ID}/executions?api-version=2024-03-01"
CLAIM_NAME="$LAUNCH_RECORD_NAME"
if [[ ! "$LAUNCH_DOMAIN_SHA256" =~ ^[0-9a-f]{64}$ \
    || ! "$JOB_NAME" =~ ^[a-z0-9][a-z0-9-]{1,62}[a-z0-9]$ \
    || "$JOB_ID" == "$CONFIGURED_JOB_ID" ]]; then
    echo "[FAIL] Deterministic launch TXT/Job identity is malformed"
    exit 1
fi
if [[ "$RECOVERY_REQUESTED" == "true" \
    && "$RECOVER_CLAIM_NAME" != "$LAUNCH_RECORD_NAME" ]]; then
    echo "[FAIL] Recovery must name the deterministic launch TXT RecordSet"
    exit 1
fi
if az rest --method get --url "$LAUNCH_RECORD_URL" \
    --output json >"$LAUNCH_TXT_LIVE_FILE" 2>/dev/null; then
    python "$AZURE_HELPER" validate-txt-record \
        --record "$LAUNCH_TXT_LIVE_FILE" \
        --zone-resource-id "$COORDINATION_ZONE_RESOURCE_ID" \
        --record-name "$LAUNCH_RECORD_NAME" \
        --ttl "$COORDINATION_RECORD_TTL" \
        --expected-kind launch \
        --expected-domain-sha256 "$LAUNCH_DOMAIN_SHA256" \
        --output "$LAUNCH_TXT_EVIDENCE_FILE"
    INVOCATION_ID="$(scalar python "$AZURE_HELPER" get \
        --json "$LAUNCH_TXT_EVIDENCE_FILE" \
        --field envelope.claims.claim_nonce)"
    RECOVERY_ONLY="true"
elif [[ "$RECOVERY_REQUESTED" == "true" ]]; then
    echo "[FAIL] Requested launch TXT record does not exist"
    exit 1
fi
if [[ ! "$INVOCATION_ID" =~ ^[0-9a-f]{32}$ ]]; then
    echo "[FAIL] Launch contender nonce is malformed"
    exit 1
fi
EXECUTION_ID="stage-${STAGE,,}-${INVOCATION_ID}"

reauthenticate_runtime_destination() {
    verify_immutable_launch_inputs || return 1
    local storage_file="$SCRATCH_DIR/storage.json"
    local storage_container_file="$SCRATCH_DIR/storage_container.json"
    local environment_file="$SCRATCH_DIR/environment.json"
    local endpoint_file="$SCRATCH_DIR/private_endpoint.json"
    local private_link_resources_file="$SCRATCH_DIR/storage_private_link_resources.json"
    local connection_file="$SCRATCH_DIR/storage_connections.json"
    local zone_groups_file="$SCRATCH_DIR/dns_zone_groups.json"
    local links_file="$SCRATCH_DIR/dns_links.json"
    local record_file="$SCRATCH_DIR/dns_record.json"
    local nics_file="$SCRATCH_DIR/nics.json"
    local resolved_file="$SCRATCH_DIR/resolved_ips.json"
    local registry_file="$SCRATCH_DIR/registry.json"
    local identity_file="$SCRATCH_DIR/identity.json"
    local profiles_file="$SCRATCH_DIR/workload_profiles.json"
    local blob_roles_file="$SCRATCH_DIR/blob_roles.json"
    local acr_roles_file="$SCRATCH_DIR/acr_roles.json"
    local topology_file="$SCRATCH_DIR/private_topology.json"
    local acr_task_run_file="$SCRATCH_DIR/live_acr_task_run.json"
    local oci_manifest_file="$SCRATCH_DIR/live_oci_manifest.json"
    local oci_config_file="$SCRATCH_DIR/live_oci_config.json"
    local live_image_validation_file="$SCRATCH_DIR/live_image_validation.json"
    local nic_ids_file="$SCRATCH_DIR/nic_ids.txt"
    local active_subscription
    local authenticated_coordination_sha256

    : >"$COORDINATION_ZONE_FILE"
    : >"$COORDINATION_LINKS_FILE"
    : >"$COORDINATION_LOCK_FILE"
    : >"$COORDINATION_VALIDATION_FILE"
    : >"$BUILD_SLOT_LIVE_FILE"
    : >"$BUILD_SLOT_EVIDENCE_FILE"
    for evidence_file in \
        "$storage_file" "$storage_container_file" "$environment_file" \
        "$endpoint_file" "$private_link_resources_file" "$connection_file" \
        "$zone_groups_file" "$links_file" "$record_file" "$nics_file" \
        "$resolved_file" "$registry_file" "$identity_file" "$profiles_file" \
        "$blob_roles_file" "$acr_roles_file" "$topology_file" \
        "$acr_task_run_file" "$oci_manifest_file" "$oci_config_file" \
        "$live_image_validation_file" "$nic_ids_file"; do
        : >"$evidence_file" || return 1
    done
    active_subscription="$(scalar az account show --query id -o tsv)" \
        || return 1
    if [[ "${active_subscription,,}" != "${SUBSCRIPTION_ID,,}" ]]; then
        echo "[FAIL] Active Azure subscription differs from the runtime binding"
        exit 1
    fi

    az rest --method get \
        --url "https://management.azure.com${COORDINATION_ZONE_RESOURCE_ID}?api-version=${COORDINATION_DNS_API_VERSION}" \
        --output json >"$COORDINATION_ZONE_FILE" || return 1
    python "$AZURE_HELPER" arm-list \
        --url "https://management.azure.com${COORDINATION_ZONE_RESOURCE_ID}/virtualNetworkLinks?api-version=${COORDINATION_DNS_API_VERSION}" \
        --output "$COORDINATION_LINKS_FILE" || return 1
    az rest --method get \
        --url "https://management.azure.com${COORDINATION_LOCK_RESOURCE_ID}?api-version=${COORDINATION_LOCK_API_VERSION}" \
        --output json >"$COORDINATION_LOCK_FILE" || return 1
    authenticated_coordination_sha256="$(scalar python "$AZURE_HELPER" \
        validate-coordination-zone --binding "$COORDINATION_BINDING_FILE" \
        --zone "$COORDINATION_ZONE_FILE" --links "$COORDINATION_LINKS_FILE" \
        --lock "$COORDINATION_LOCK_FILE" \
        --output "$COORDINATION_VALIDATION_FILE")" || return 1
    if [[ "$authenticated_coordination_sha256" \
        != "$COORDINATION_BINDING_SHA256" ]]; then
        echo "[FAIL] Dedicated unlinked coordination zone changed"
        exit 1
    fi
    az rest --method get --url "$BUILD_SLOT_RECORD_URL" \
        --output json >"$BUILD_SLOT_LIVE_FILE" || return 1
    python "$AZURE_HELPER" validate-txt-record \
        --record "$BUILD_SLOT_LIVE_FILE" \
        --zone-resource-id "$COORDINATION_ZONE_RESOURCE_ID" \
        --record-name "$BUILD_SLOT_RECORD_NAME" \
        --ttl "$COORDINATION_RECORD_TTL" --expected-kind build \
        --expected-domain-sha256 "$BUILD_SLOT_DOMAIN_SHA256" \
        --output "$BUILD_SLOT_EVIDENCE_FILE" || return 1
    python - "$BUILD_SLOT_BINDING_FILE" "$BUILD_SLOT_EVIDENCE_FILE" \
        <<'PY' || return 1
import hashlib
import json
import pathlib
import sys

binding = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="ascii"))
evidence = json.loads(pathlib.Path(sys.argv[2]).read_text(encoding="ascii"))
expected = {
    "domain_sha256": evidence["domain_sha256"],
    "record_name": evidence["record_name"],
    "record_resource_id": evidence["record_resource_id"],
    "record_etag": evidence["record_etag"],
    "record_etag_sha256": evidence["record_etag_sha256"],
    "payload_sha256": evidence["payload_sha256"],
    "claim_nonce": evidence["envelope"]["claims"]["claim_nonce"],
    "record_ttl": evidence["record_ttl"],
}
if binding != expected:
    raise SystemExit("live build TXT slot differs from the image binding")
if hashlib.sha256(binding["record_etag"].encode("ascii")).hexdigest() != (
    binding["record_etag_sha256"]
):
    raise SystemExit("live build TXT slot ETag hash differs")
PY

    az rest --method get \
        --url "https://management.azure.com${STORAGE_ID}?api-version=2023-05-01" \
        --output json >"$storage_file" || return 1
    az rest --method get \
        --url "https://management.azure.com${STORAGE_ID}/blobServices/default/containers/${BLOB_CONTAINER}?api-version=2023-05-01" \
        --output json >"$storage_container_file" || return 1
    az rest --method get \
        --url "https://management.azure.com${ENVIRONMENT_ID}?api-version=2024-03-01" \
        --output json >"$environment_file" || return 1
    az rest --method get \
        --url "https://management.azure.com${PRIVATE_ENDPOINT_ID}?api-version=2023-09-01" \
        --output json >"$endpoint_file" || return 1
    python "$AZURE_HELPER" arm-list \
        --url "https://management.azure.com${STORAGE_ID}/privateLinkResources?api-version=2023-05-01" \
        --output "$private_link_resources_file" || return 1
    python "$AZURE_HELPER" arm-list \
        --url "https://management.azure.com${STORAGE_ID}/privateEndpointConnections?api-version=2023-05-01" \
        --output "$connection_file" || return 1
    python "$AZURE_HELPER" arm-list \
        --url "https://management.azure.com${PRIVATE_ENDPOINT_ID}/privateDnsZoneGroups?api-version=2023-09-01" \
        --output "$zone_groups_file" || return 1
    python "$AZURE_HELPER" arm-list \
        --url "https://management.azure.com${PRIVATE_DNS_ZONE_ID}/virtualNetworkLinks?api-version=2020-06-01" \
        --output "$links_file" || return 1
    az rest --method get \
        --url "https://management.azure.com${PRIVATE_DNS_ZONE_ID}/A/${BLOB_ACCOUNT}?api-version=2018-09-01" \
        --output json >"$record_file" || return 1
    python - "$endpoint_file" <<'PY' | tr -d '\r' >"$nic_ids_file" \
        || return 1
import json
import pathlib
import sys

record = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8").replace("\r", ""))
items = (record.get("properties") or {}).get("networkInterfaces")
if not isinstance(items, list) or not items:
    raise SystemExit("private endpoint has no NICs")
ids = sorted(item.get("id") for item in items if isinstance(item, dict))
if len(ids) != len(items) or any(not isinstance(item, str) or "\n" in item for item in ids):
    raise SystemExit("private endpoint NIC IDs are invalid")
print(*ids, sep="\n")
PY
    mapfile -t NIC_IDS <"$nic_ids_file" || return 1
    NIC_FILES=()
    local index=0
    local nic_id
    for nic_id in "${NIC_IDS[@]}"; do
        local nic_file="$SCRATCH_DIR/nic-${index}.json"
        az rest --method get \
            --url "https://management.azure.com${nic_id}?api-version=2023-09-01" \
            --output json >"$nic_file" || return 1
        NIC_FILES+=("$nic_file")
        index=$((index + 1))
    done
    python - "$nics_file" "${NIC_FILES[@]}" <<'PY' || return 1
import json
import pathlib
import sys

records = [
    json.loads(pathlib.Path(path).read_text(encoding="utf-8").replace("\r", ""))
    for path in sys.argv[2:]
]
pathlib.Path(sys.argv[1]).write_text(
    json.dumps(records, sort_keys=True, separators=(",", ":")) + "\n",
    encoding="utf-8",
)
PY
    python - "$ACCOUNT_URL" "$resolved_file" <<'PY' || return 1
import json
import pathlib
import socket
import sys
from urllib.parse import urlsplit

host = urlsplit(sys.argv[1]).hostname
answers = sorted({
    item[4][0]
    for item in socket.getaddrinfo(
        host, 443, family=socket.AF_INET, type=socket.SOCK_STREAM
    )
})
pathlib.Path(sys.argv[2]).write_text(
    json.dumps(answers, sort_keys=True, separators=(",", ":")) + "\n",
    encoding="utf-8",
)
PY
    python "$AZURE_HELPER" arm-list \
        --url "https://management.azure.com${ENVIRONMENT_ID}/workloadProfileStates?api-version=2024-03-01" \
        --output "$profiles_file" || return 1
    python "$AZURE_HELPER" verify-private \
        --runtime-config "$RUNTIME_CONFIG_SNAPSHOT_FILE" \
        --storage "$storage_file" \
        --storage-container "$storage_container_file" \
        --environment "$environment_file" \
        --workload-profile-states "$profiles_file" \
        --private-endpoint "$endpoint_file" \
        --storage-private-link-resources "$private_link_resources_file" \
        --storage-connections "$connection_file" \
        --dns-zone-groups "$zone_groups_file" --dns-links "$links_file" \
        --dns-record "$record_file" --nics "$nics_file" \
        --resolved-ips "$resolved_file" --output "$topology_file" || return 1

    az rest --method get \
        --url "https://management.azure.com${ACR_ID}?api-version=2023-07-01" \
        --output json >"$registry_file" || return 1
    az rest --method get \
        --url "https://management.azure.com${IDENTITY_ID}?api-version=2023-01-31" \
        --output json >"$identity_file" || return 1
    python "$AZURE_HELPER" arm-list \
        --url "https://management.azure.com${STORAGE_ID}/providers/Microsoft.Authorization/roleAssignments?api-version=2022-04-01" \
        --output "$blob_roles_file" || return 1
    python "$AZURE_HELPER" arm-list \
        --url "https://management.azure.com${ACR_ID}/providers/Microsoft.Authorization/roleAssignments?api-version=2022-04-01" \
        --output "$acr_roles_file" || return 1
    python - "$registry_file" "$identity_file" "$profiles_file" \
        "$blob_roles_file" "$acr_roles_file" "$ACR_ID" "$LOGIN_SERVER" \
        "$ACR_LOCATION" \
        "$IDENTITY_ID" "$IDENTITY_CLIENT_ID" "$IDENTITY_PRINCIPAL_ID" \
        "$WORKLOAD_PROFILE" "$ENVIRONMENT_ID" "$STORAGE_ID" \
        <<'PY' || return 1
import json
import pathlib
import sys

def load(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8").replace("\r", ""))

registry, identity, profiles, blob_roles, acr_roles = map(load, sys.argv[1:6])
(
    acr_id,
    login_server,
    acr_location,
    identity_id,
    client_id,
    principal_id,
    profile_name,
    environment_id,
    storage_id,
) = sys.argv[6:]
if (
    str(registry.get("id", "")).casefold() != acr_id.casefold()
    or (registry.get("properties") or {}).get("loginServer") != login_server
    or str(registry.get("location", "")).casefold() != acr_location.casefold()
):
    raise SystemExit("ACR physical binding changed")
identity_properties = identity.get("properties") or {}
if (
    str(identity.get("id", "")).casefold() != identity_id.casefold()
    or identity_properties.get("clientId") != client_id
    or identity_properties.get("principalId") != principal_id
):
    raise SystemExit("managed identity physical binding changed")
matches = [
    item for item in profiles
    if isinstance(item, dict)
    and item.get("name") == profile_name
    and (item.get("properties") or {}).get("workloadProfileType")
        == "Consumption"
]
if len(matches) != 1:
    raise SystemExit("Consumption workload profile is not exact")
roles = (
    (
        blob_roles,
        storage_id,
        "ba92f5b4-2d11-453d-a403-e96b0029c9fe",
    ),
    (
        acr_roles,
        acr_id,
        "7f951dda-4ed3-4680-a7ca-43fe172d538d",
    ),
)
for records, scope, role_id in roles:
    matches = [
        item for item in records
        if isinstance(item, dict)
        and str((item.get("properties") or {}).get("principalId", "")).casefold()
            == principal_id.casefold()
        and str((item.get("properties") or {}).get("scope", "")).casefold()
            == scope.casefold()
        and str((item.get("properties") or {}).get("roleDefinitionId", "")).casefold()
            .endswith("/" + role_id)
    ]
    if len(matches) != 1:
        raise SystemExit("managed identity role assignment is not exact")
PY
    local resolved_digest tag_write tag_delete manifest_write manifest_delete
    local refresh_token access_token config_digest authenticated_binding_sha256
    az rest --method get \
        --url "https://management.azure.com${ACR_BUILD_TASK_RUN_RESOURCE_ID}?api-version=2019-06-01-preview" \
        --output json >"$acr_task_run_file" || return 1
    resolved_digest="$(scalar az acr repository show \
        --name "$ACR_NAME" --image "${IMAGE_REPOSITORY}:${FINAL_IMAGE_TAG}" \
        --query digest -o tsv)" || return 1
    tag_write="$(scalar az acr repository show \
        --name "$ACR_NAME" --image "${IMAGE_REPOSITORY}:${FINAL_IMAGE_TAG}" \
        --query changeableAttributes.writeEnabled -o tsv)" || return 1
    tag_delete="$(scalar az acr repository show \
        --name "$ACR_NAME" --image "${IMAGE_REPOSITORY}:${FINAL_IMAGE_TAG}" \
        --query changeableAttributes.deleteEnabled -o tsv)" || return 1
    manifest_write="$(scalar az acr manifest show-metadata \
        --registry "$ACR_NAME" --name "${IMAGE_REPOSITORY}@${IMAGE_DIGEST}" \
        --query changeableAttributes.writeEnabled -o tsv)" || return 1
    manifest_delete="$(scalar az acr manifest show-metadata \
        --registry "$ACR_NAME" --name "${IMAGE_REPOSITORY}@${IMAGE_DIGEST}" \
        --query changeableAttributes.deleteEnabled -o tsv)" || return 1
    if ! command -v curl >/dev/null 2>&1; then
        echo "[FAIL] curl is required for live OCI provenance verification"
        exit 1
    fi
    if ! refresh_token="$(scalar az acr login \
        --name "$ACR_NAME" --expose-token --query refreshToken -o tsv \
        2>/dev/null)"; then
        echo "[FAIL] Live OCI registry token retrieval failed"
        exit 1
    fi
    if [[ ! "$refresh_token" =~ ^[A-Za-z0-9._~-]+$ ]]; then
        unset refresh_token
        echo "[FAIL] ACR exposed an invalid live registry refresh token"
        exit 1
    fi
    if ! access_token="$(
        {
            printf 'data-urlencode = "grant_type=refresh_token"\n'
            printf 'data-urlencode = "service=%s"\n' "$LOGIN_SERVER"
            printf 'data-urlencode = "scope=repository:%s:pull"\n' \
                "$IMAGE_REPOSITORY"
            printf 'data-urlencode = "refresh_token=%s"\n' "$refresh_token"
        } | curl --disable --config - --fail --silent --show-error \
            --proto '=https' --retry 0 --request POST \
            "https://${LOGIN_SERVER}/oauth2/token" \
        | python -c '
import json
import re
import sys

response = json.load(sys.stdin)
token = response.get("access_token") if isinstance(response, dict) else None
if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9._~-]+", token):
    raise SystemExit("ACR token exchange returned no valid access token")
print(token)
'
    )"; then
        unset refresh_token
        echo "[FAIL] Live OCI scoped registry token exchange failed"
        exit 1
    fi
    unset refresh_token
    if ! printf 'header = "Authorization: %s %s"\n' "Bearer" "$access_token" \
        | curl --disable --config - --fail --silent --show-error \
            --proto '=https' --proto-redir '=https' --location --max-redirs 3 \
            --retry 0 \
            --header "Accept: application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.v2+json" \
            "https://${LOGIN_SERVER}/v2/${IMAGE_REPOSITORY}/manifests/${IMAGE_DIGEST}" \
            --output "$oci_manifest_file"; then
        unset access_token
        echo "[FAIL] Live OCI manifest retrieval failed"
        exit 1
    fi
    config_digest="$(scalar python - "$oci_manifest_file" <<'PY'
import json
import pathlib
import re
import sys

manifest = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
config = manifest.get("config") if isinstance(manifest, dict) else None
digest = config.get("digest") if isinstance(config, dict) else None
if not isinstance(digest, str) or not re.fullmatch(
    r"sha256:[0-9a-f]{64}", digest
):
    raise SystemExit("live OCI manifest has no exact config digest")
print(digest)
PY
)" || return 1
    if ! printf 'header = "Authorization: %s %s"\n' "Bearer" "$access_token" \
        | curl --disable --config - --fail --silent --show-error \
            --proto '=https' --proto-redir '=https' --location --max-redirs 3 \
            --retry 0 \
            "https://${LOGIN_SERVER}/v2/${IMAGE_REPOSITORY}/blobs/${config_digest}" \
            --output "$oci_config_file"; then
        unset access_token
        echo "[FAIL] Live OCI config retrieval failed"
        exit 1
    fi
    unset access_token
    authenticated_binding_sha256="$(scalar python "$AZURE_HELPER" \
        validate-live-image-binding \
        --image-binding "$IMAGE_BINDING_SNAPSHOT_FILE" \
        --expected-sha256 "$IMAGE_BINDING_SHA256" \
        --task-run "$acr_task_run_file" --manifest "$oci_manifest_file" \
        --config "$oci_config_file" \
        --resolved-final-digest "$resolved_digest" \
        --tag-write-enabled "$tag_write" \
        --tag-delete-enabled "$tag_delete" \
        --manifest-write-enabled "$manifest_write" \
        --manifest-delete-enabled "$manifest_delete" \
        --expected-source-commit "$SOURCE_SHA" \
        --expected-acr-resource-id "$ACR_ID" \
        --expected-login-server "$LOGIN_SERVER" \
        --expected-repository "$IMAGE_REPOSITORY" \
        --output "$live_image_validation_file")" || return 1
    if [[ "$authenticated_binding_sha256" != "$IMAGE_BINDING_SHA256" ]]; then
        echo "[FAIL] Live ACR image provenance authentication failed"
        exit 1
    fi
}

authenticate_persisted_state() {
    local state="$1"
    local receipt_sha="$2"
    local output="$SCRATCH_DIR/bootstrap-auth-${state}.json"
    local -a prior_args=()
    reauthenticate_runtime_destination || return 1
    if [[ "$state" == "LATEST" ]]; then
        if [[ -n "$receipt_sha" ]]; then
            echo "[FAIL] Latest-state authentication derives its receipt hash"
            return 1
        fi
    elif [[ "$receipt_sha" =~ ^[0-9a-f]{64}$ ]]; then
        prior_args=(--prior-state-receipt-sha256 "$receipt_sha")
    else
        echo "[FAIL] Persisted state receipt hash is incomplete"
        return 1
    fi
    if [[ ! "$AUTHORIZATION_LOCK_SHA256" =~ ^[0-9a-f]{64}$ \
        || ! "$AUTHORIZATION_MANIFEST_SHA256" =~ ^[0-9a-f]{64}$ ]]; then
        echo "[FAIL] Persisted authorization hashes are incomplete"
        return 1
    fi
    verify_immutable_launch_inputs || return 1
    reauthenticate_runtime_destination || return 1
    JSPACE_LOCKED_EVAL_ROLE=custodian \
        python "$BOOTSTRAP" \
        --runtime-config-file "$RUNTIME_CONFIG_SNAPSHOT_FILE" \
        --runtime-config-sha256 "$CONFIG_SHA256" \
        --implementation-manifest-file \
        "$IMPLEMENTATION_MANIFEST_SNAPSHOT_FILE" \
        --implementation-manifest-sha256 "$IMPLEMENTATION_MANIFEST_SHA256" \
        --image-binding-file "$IMAGE_BINDING_SNAPSHOT_FILE" \
        --image-binding-sha256 "$IMAGE_BINDING_SHA256" \
        --helper-snapshot-set-sha256 "$HELPER_SNAPSHOT_SET_SHA256" \
        --authenticate-only-state "$state" \
        "${prior_args[@]}" \
        --authorization-lock-sha256 "$AUTHORIZATION_LOCK_SHA256" \
        --authorization-manifest-sha256 "$AUTHORIZATION_MANIFEST_SHA256" \
        >"$output" || return 1
    AUTHENTICATED_STATE_FILE="$output"
    python - "$output" "$state" "$IMAGE_DIGEST" \
        "$CONFIG_SHA256" "$AZURE_DESTINATION_SHA256" \
        "$IMAGE_BINDING_SHA256" "$HELPER_SNAPSHOT_SET_SHA256" \
        <<'PY' || return 1
import json
import pathlib
import sys

record = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
states = {
    "UNSEAL_AUTHORIZED",
    "INPUTS_READ",
    "PREDICTIONS_VERIFIED",
    "LABELS_READ",
    "SCORES_VERIFIED",
    "CLOSED",
}
if (
    record.get("status") != "PERSISTED_STATE_AUTHENTICATED"
    or record.get("state") not in states
    or (sys.argv[2] != "LATEST" and record.get("state") != sys.argv[2])
    or record.get("image_digest") != sys.argv[3]
    or record.get("runtime_config_sha256") != sys.argv[4]
    or record.get("azure_destination_sha256") != sys.argv[5]
    or record.get("image_binding_sha256") != sys.argv[6]
    or record.get("helper_snapshot_set_sha256") != sys.argv[7]
    or record.get("locked_input_payload_read") is not False
    or record.get("locked_labels_payload_read") is not False
    or not isinstance(record.get("score_payload_read"), bool)
    or (
        record.get("state") not in {"LABELS_READ", "SCORES_VERIFIED", "CLOSED"}
        and record.get("score_payload_read") is not False
    )
    or record.get("result_status") not in {"PENDING", "PASS", "FAIL", "INVALID"}
    or record.get("writes_performed") is not False
):
    raise SystemExit("custodian bootstrap authentication result is invalid")
PY
    AUTHENTICATED_STATE="$(scalar python "$AZURE_HELPER" get \
        --json "$output" --field state)" || return 1
    AUTHENTICATED_STATE_RECEIPT_SHA256="$(scalar python "$AZURE_HELPER" get \
        --json "$output" --field prior_state_receipt_sha256)" || return 1
    AUTHENTICATED_VERIFICATION_RETRY_EXECUTION_ID="$(scalar python - \
        "$output" <<'PY'
import json
import pathlib
import sys

value = json.loads(
    pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
).get("verification_retry_execution_id")
if value is None:
    print("")
elif (
    isinstance(value, str)
    and value
    and not any(ord(character) < 32 for character in value)
):
    print(value)
else:
    raise SystemExit("authenticated verification retry identity is invalid")
PY
    )" || return 1
    if [[ ! "$AUTHENTICATED_STATE_RECEIPT_SHA256" =~ ^[0-9a-f]{64}$ ]]; then
        echo "[FAIL] Authenticated persisted-state receipt hash is malformed"
        return 1
    fi
}

derive_effective_stage_bindings() {
    local candidate="$SCRATCH_DIR/stage_bindings_candidate.json"
    verify_immutable_launch_inputs || return 1
    rm -f "$candidate" || return 1
    python - "$CORE_FILE" "$RUNTIME_CONFIG_SNAPSHOT_FILE" \
        "$AUTHENTICATED_STATE_FILE" "$candidate" "$STAGE" "$VERIFY_ONLY" \
        "$CLOSE_INVALID_ONLY" "$VERIFICATION_STATE" "$RETRY_KIND" \
        "$EXECUTION_ID" "$ACTOR" \
        "${PARSER_EVAL_LOCKED_INPUT_SHA256:-}" \
        "${PARSER_EVAL_LOCKED_INPUT_MANIFEST_SHA256:-}" \
        "${PARSER_EVAL_PREDICTION_MANIFEST_SHA256:-}" \
        "${PARSER_EVAL_LABELS_SHA256:-}" \
        "${PARSER_EVAL_LABELS_MANIFEST_SHA256:-}" \
        "${PARSER_EVAL_SCORES_MANIFEST_SHA256:-}" \
        "${PARSER_EVAL_CLOSED_RECEIPT_SHA256:-}" \
        "$STAGE_PRIOR_RECEIPT_SHA256" <<'PY' || return 1
import importlib.util
import json
import pathlib
import re
import sys

(
    core_path,
    runtime_path,
    authenticated_path,
    output_path,
    stage,
    verify_only,
    close_invalid_only,
    verification_state,
    retry_kind,
    execution_id,
    actor,
    locked_input_sha,
    locked_input_manifest_sha,
    supplied_prediction_manifest_sha,
    supplied_labels_sha,
    supplied_labels_manifest_sha,
    supplied_scores_manifest_sha,
    supplied_closed_receipt_sha,
    supplied_prior_receipt_sha,
) = sys.argv[1:]
spec = importlib.util.spec_from_file_location(
    "_pv2_effective_attempt_core", core_path
)
if spec is None or spec.loader is None:
    raise SystemExit("cannot load verified locked-evaluation core")
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)
runtime = core.parse_json_strict(
    pathlib.Path(runtime_path).read_bytes(), "runtime configuration"
)
authenticated = core.parse_json_strict(
    pathlib.Path(authenticated_path).read_bytes(), "authenticated state"
)
bindings = runtime.get("bindings")
if not isinstance(bindings, dict):
    raise SystemExit("runtime authorization roots are missing")
roots = core.evaluation_prefixes(
    bindings.get("registered_parent_prefix"), bindings.get("authorization_id")
)
for leaf, expected in roots.items():
    if bindings.get(f"{leaf}_prefix") != expected:
        raise SystemExit("runtime configuration contains a non-root prefix")

sha_pattern = re.compile(r"[0-9a-f]{64}")


def require_sha(value, name, *, optional=False):
    if optional and value in (None, ""):
        return None
    if not isinstance(value, str) or sha_pattern.fullmatch(value) is None:
        raise SystemExit(f"{name} is not an exact SHA-256")
    return value


def check_prediction_attempt(value, *, pending=False):
    fields = {
        "stage",
        "retry_kind",
        "execution_id",
        "attempt_binding_sha256",
        "predictions_prefix",
        "predictions_prefix_sha256",
        "visibility_prefix",
        "visibility_prefix_sha256",
        "prediction_state_receipt_sha256",
        "prediction_manifest_sha256",
        "prediction_request_manifest_sha256",
        "prediction_seal_sha256",
        "input_manifest_sha256",
        "attempt_descriptor_sha256",
        "retry_receipt_sha256",
    }
    pending_fields = {
        "receipt_persisted",
        "expected_prediction_state_receipt_sha256",
    }
    expected_fields = fields | pending_fields if pending else fields
    if not isinstance(value, dict) or set(value) != expected_fields:
        raise SystemExit("authenticated prediction attempt shape is invalid")
    if pending and (
        value["receipt_persisted"] is not False
        or value["expected_prediction_state_receipt_sha256"]
        != value["prediction_state_receipt_sha256"]
    ):
        raise SystemExit("pending prediction receipt projection is invalid")
    kind = value["retry_kind"]
    identity = value["execution_id"]
    if value["stage"] != "P" or kind not in {
        "none",
        "infrastructure_pre_input",
    }:
        raise SystemExit("authenticated prediction attempt kind is invalid")
    expected = core.evaluation_attempt_prefixes(
        bindings["registered_parent_prefix"],
        bindings["authorization_id"],
        "P",
        kind,
        identity,
    )
    if (
        value["predictions_prefix"] != expected["predictions"]
        or value["visibility_prefix"] != expected["visibility"]
        or value["predictions_prefix_sha256"]
        != core.attempt_prefix_sha256(expected["predictions"])
        or value["visibility_prefix_sha256"]
        != core.attempt_prefix_sha256(expected["visibility"])
        or value["attempt_binding_sha256"]
        != core.attempt_binding_sha256("P", kind, identity)
    ):
        raise SystemExit("authenticated prediction attempt prefix differs")
    for name in (
        "attempt_binding_sha256",
        "predictions_prefix_sha256",
        "visibility_prefix_sha256",
        "prediction_state_receipt_sha256",
        "prediction_manifest_sha256",
        "prediction_request_manifest_sha256",
        "prediction_seal_sha256",
        "input_manifest_sha256",
        "attempt_descriptor_sha256",
    ):
        require_sha(value[name], f"authenticated prediction {name}")
    if pending:
        require_sha(
            value["expected_prediction_state_receipt_sha256"],
            "pending prediction receipt",
        )
    retry_sha = require_sha(
        value["retry_receipt_sha256"],
        "authenticated prediction retry receipt",
        optional=True,
    )
    if (kind == "none") != (retry_sha is None):
        raise SystemExit("authenticated prediction retry hash is inconsistent")
    return value


def check_scoring_attempt(value, prediction):
    fields = {
        "stage",
        "retry_kind",
        "execution_id",
        "attempt_binding_sha256",
        "scores_prefix",
        "scores_prefix_sha256",
        "visibility_prefix",
        "visibility_prefix_sha256",
        "score_manifest_sha256",
        "labels_manifest_sha256",
        "labels_sha256",
        "labels_open_transaction_sha256",
        "scoring_transaction_sha256",
        "scoring_attestation_sha256",
        "prediction_manifest_sha256",
        "prediction_request_manifest_sha256",
        "prediction_seal_sha256",
        "attempt_descriptor_sha256",
        "retry_receipt_sha256",
    }
    if not isinstance(value, dict) or set(value) != fields:
        raise SystemExit("authenticated scoring attempt shape is invalid")
    kind = value["retry_kind"]
    identity = value["execution_id"]
    if value["stage"] != "E" or kind not in {
        "none",
        "scorer_infrastructure",
    }:
        raise SystemExit("authenticated scoring attempt kind is invalid")
    expected = core.evaluation_attempt_prefixes(
        bindings["registered_parent_prefix"],
        bindings["authorization_id"],
        "E",
        kind,
        identity,
    )
    if (
        value["scores_prefix"] != expected["scores"]
        or value["visibility_prefix"] != expected["visibility"]
        or value["scores_prefix_sha256"]
        != core.attempt_prefix_sha256(expected["scores"])
        or value["visibility_prefix_sha256"]
        != core.attempt_prefix_sha256(expected["visibility"])
        or value["attempt_binding_sha256"]
        != core.attempt_binding_sha256("E", kind, identity)
        or value["prediction_manifest_sha256"]
        != prediction["prediction_manifest_sha256"]
        or value["prediction_request_manifest_sha256"]
        != prediction["prediction_request_manifest_sha256"]
        or value["prediction_seal_sha256"]
        != prediction["prediction_seal_sha256"]
    ):
        raise SystemExit("authenticated scoring attempt prefix differs")
    for name in fields - {
        "stage",
        "retry_kind",
        "execution_id",
        "scores_prefix",
        "visibility_prefix",
        "retry_receipt_sha256",
    }:
        require_sha(value[name], f"authenticated scoring {name}")
    retry_sha = require_sha(
        value["retry_receipt_sha256"],
        "authenticated scoring retry receipt",
        optional=True,
    )
    if (kind == "none") != (retry_sha is None):
        raise SystemExit("authenticated scoring retry hash is inconsistent")
    return value


def check_pending_scoring_attempt(value, prediction):
    fields = {
        "stage",
        "retry_kind",
        "execution_id",
        "actor",
        "attempt_binding_sha256",
        "scores_prefix",
        "scores_prefix_sha256",
        "visibility_prefix",
        "visibility_prefix_sha256",
        "labels_manifest_sha256",
        "labels_sha256",
        "labels_open_transaction_sha256",
        "prediction_manifest_sha256",
        "prediction_request_manifest_sha256",
        "prediction_seal_sha256",
        "expected_labels_state_receipt_sha256",
        "labels_state_receipt_persisted",
        "score_artifacts_authenticated",
        "closure_required",
        "retry_receipt_sha256",
    }
    if not isinstance(value, dict) or set(value) != fields:
        raise SystemExit("pending scoring attempt shape is invalid")
    kind = value["retry_kind"]
    identity = value["execution_id"]
    if (
        value["stage"] != "E"
        or kind not in {"none", "scorer_infrastructure"}
        or value["score_artifacts_authenticated"] is not False
        or value["closure_required"] is not True
        or type(value["labels_state_receipt_persisted"]) is not bool
        or not isinstance(value["actor"], str)
        or not value["actor"]
    ):
        raise SystemExit("pending scoring attempt controls are invalid")
    expected = core.evaluation_attempt_prefixes(
        bindings["registered_parent_prefix"],
        bindings["authorization_id"],
        "E",
        kind,
        identity,
    )
    if (
        value["scores_prefix"] != expected["scores"]
        or value["visibility_prefix"] != expected["visibility"]
        or value["scores_prefix_sha256"]
        != core.attempt_prefix_sha256(expected["scores"])
        or value["visibility_prefix_sha256"]
        != core.attempt_prefix_sha256(expected["visibility"])
        or value["attempt_binding_sha256"]
        != core.attempt_binding_sha256("E", kind, identity)
        or value["prediction_manifest_sha256"]
        != prediction["prediction_manifest_sha256"]
        or value["prediction_request_manifest_sha256"]
        != prediction["prediction_request_manifest_sha256"]
        or value["prediction_seal_sha256"]
        != prediction["prediction_seal_sha256"]
    ):
        raise SystemExit("pending scoring attempt binding differs")
    for name in fields - {
        "stage",
        "retry_kind",
        "execution_id",
        "actor",
        "scores_prefix",
        "visibility_prefix",
        "labels_state_receipt_persisted",
        "score_artifacts_authenticated",
        "closure_required",
        "retry_receipt_sha256",
    }:
        require_sha(value[name], f"pending scoring {name}")
    retry_sha = require_sha(
        value["retry_receipt_sha256"],
        "pending scoring retry receipt",
        optional=True,
    )
    if (kind == "none") != (retry_sha is None):
        raise SystemExit("pending scoring retry hash is inconsistent")
    return value


state_sequence = (
    "CREATED",
    "ARTIFACTS_FROZEN",
    "IMPLEMENTATION_FROZEN",
    "UNSEAL_AUTHORIZED",
    "INPUTS_READ",
    "PREDICTIONS_VERIFIED",
    "LABELS_READ",
    "SCORES_VERIFIED",
    "CLOSED",
)
state = authenticated.get("state")
if state not in state_sequence:
    raise SystemExit("authenticated persisted state is invalid")
state_index = state_sequence.index(state)
prediction_value = authenticated.get("prediction_attempt")
if state_index >= state_sequence.index("PREDICTIONS_VERIFIED"):
    prediction = check_prediction_attempt(prediction_value)
elif state == "INPUTS_READ" and retry_kind == "prediction_adoption":
    if prediction_value is not None:
        raise SystemExit("pending prediction aliases accepted prediction")
    prediction = check_prediction_attempt(
        authenticated.get("pending_prediction_attempt"), pending=True
    )
elif prediction_value is not None:
    raise SystemExit("premature authenticated prediction attempt")
else:
    prediction = None
scoring_value = authenticated.get("scoring_attempt")
pending_scoring_value = authenticated.get("pending_scoring_attempt")
invalid_scoring_value = authenticated.get("invalid_scoring_attempt")
result_status = authenticated.get("result_status")
if close_invalid_only == "true":
    if scoring_value is not None or prediction is None:
        raise SystemExit("INVALID closure has no pending scoring attempt")
    if state in {"PREDICTIONS_VERIFIED", "LABELS_READ"}:
        if result_status == "INVALID" or invalid_scoring_value is not None:
            raise SystemExit("pending closure aliases an INVALID result")
        closure_value = pending_scoring_value
    elif state == "CLOSED" and result_status == "INVALID":
        if pending_scoring_value is not None:
            raise SystemExit("INVALID result aliases pending scoring")
        closure_value = invalid_scoring_value
    else:
        raise SystemExit("INVALID closure has no pending scoring attempt")
    pending_scoring = check_pending_scoring_attempt(
        closure_value,
        prediction,
    )
    scoring = None
elif state_index >= state_sequence.index("LABELS_READ") and result_status != "INVALID":
    if prediction is None:
        raise SystemExit("authenticated scoring has no prediction attempt")
    scoring = check_scoring_attempt(scoring_value, prediction)
    if pending_scoring_value is not None:
        raise SystemExit("accepted scoring aliases a pending attempt")
    if invalid_scoring_value is not None:
        raise SystemExit("accepted scoring aliases an INVALID attempt")
    pending_scoring = None
elif scoring_value is not None:
    raise SystemExit("premature authenticated scoring attempt")
else:
    scoring = None
    if pending_scoring_value is not None:
        raise SystemExit("pending scoring requires closure-only routing")
    if invalid_scoring_value is not None:
        raise SystemExit("INVALID scoring requires closure-only routing")
    pending_scoring = None

effective = core.derive_effective_launcher_attempt_prefixes(
    parent_prefix=bindings["registered_parent_prefix"],
    authorization_id=bindings["authorization_id"],
    stage=stage,
    retry_kind=retry_kind,
    execution_id=execution_id,
    verification_only=verify_only == "true",
    authenticated_prediction_attempt=prediction,
    authenticated_scoring_attempt=(
        pending_scoring
        if close_invalid_only == "true"
        else scoring
    ),
)
current = core.evaluation_attempt_prefixes(
    bindings["registered_parent_prefix"],
    bindings["authorization_id"],
    stage,
    retry_kind,
    execution_id,
)
if stage == "P" and retry_kind == "prediction_adoption":
    if state != "INPUTS_READ" or prediction is None:
        raise SystemExit("prediction adoption lacks one pending producer")
    predictions_prefix = prediction["predictions_prefix"]
    scores_prefix = ""
    visibility_prefix = prediction["visibility_prefix"]
    prediction_manifest_sha = prediction["prediction_manifest_sha256"]
    labels_sha = ""
    labels_manifest_sha = ""
    scores_manifest_sha = ""
    producer_retry_kind = prediction["retry_kind"]
    producer_execution_id = prediction["execution_id"]
    expected_predictions_receipt_sha = prediction[
        "expected_prediction_state_receipt_sha256"
    ]
    supplied_prior_receipt_sha = authenticated[
        "prior_state_receipt_sha256"
    ]
    if locked_input_sha or locked_input_manifest_sha:
        raise SystemExit("prediction adoption received locked-input bindings")
elif stage == "P":
    predictions_prefix = current["predictions"]
    scores_prefix = ""
    visibility_prefix = current["visibility"]
    prediction_manifest_sha = ""
    labels_sha = ""
    labels_manifest_sha = ""
    scores_manifest_sha = ""
    producer_retry_kind = ""
    producer_execution_id = ""
    expected_predictions_receipt_sha = ""
    if not locked_input_sha or not locked_input_manifest_sha:
        raise SystemExit("Stage-P locked-input hash bindings are incomplete")
elif stage == "E" and prediction is not None:
    predictions_prefix = prediction["predictions_prefix"]
    producer_retry_kind = ""
    producer_execution_id = ""
    expected_predictions_receipt_sha = ""
    visibility_prefix = current["visibility"]
    prediction_manifest_sha = prediction["prediction_manifest_sha256"]
    if (
        supplied_prediction_manifest_sha
        and supplied_prediction_manifest_sha != prediction_manifest_sha
    ):
        raise SystemExit(
            "caller prediction manifest differs from authenticated state"
        )
    if supplied_prior_receipt_sha and (
        supplied_prior_receipt_sha
        != prediction["prediction_state_receipt_sha256"]
    ):
        raise SystemExit(
            "caller prediction receipt differs from authenticated state"
        )
    supplied_prior_receipt_sha = prediction[
        "prediction_state_receipt_sha256"
    ]
    if close_invalid_only == "true":
        if retry_kind != "verification_only" or pending_scoring is None:
            raise SystemExit(
                "INVALID closure requires an authenticated pending producer"
            )
        scores_prefix = pending_scoring["scores_prefix"]
        labels_sha = pending_scoring["labels_sha256"]
        labels_manifest_sha = pending_scoring[
            "labels_manifest_sha256"
        ]
        scores_manifest_sha = ""
        producer_retry_kind = pending_scoring["retry_kind"]
        producer_execution_id = pending_scoring["execution_id"]
        if supplied_scores_manifest_sha:
            raise SystemExit(
                "INVALID closure cannot accept a score manifest"
            )
        for supplied, expected, name in (
            (supplied_labels_sha, labels_sha, "labels"),
            (
                supplied_labels_manifest_sha,
                labels_manifest_sha,
                "labels manifest",
            ),
        ):
            if supplied and supplied != expected:
                raise SystemExit(
                    f"caller {name} differs from pending scoring"
                )
    elif verify_only == "true":
        if retry_kind != "verification_only" or scoring is None:
            raise SystemExit(
                "verification requires an authenticated scoring attempt"
            )
        scores_prefix = scoring["scores_prefix"]
        labels_sha = scoring["labels_sha256"]
        labels_manifest_sha = scoring["labels_manifest_sha256"]
        scores_manifest_sha = scoring["score_manifest_sha256"]
        comparisons = (
            (supplied_labels_sha, labels_sha, "labels"),
            (
                supplied_labels_manifest_sha,
                labels_manifest_sha,
                "labels manifest",
            ),
            (
                supplied_scores_manifest_sha,
                scores_manifest_sha,
                "scores manifest",
            ),
        )
        for supplied, expected, name in comparisons:
            if supplied and supplied != expected:
                raise SystemExit(
                    f"caller {name} differs from authenticated state"
                )
    else:
        if retry_kind not in {"none", "scorer_infrastructure"}:
            raise SystemExit("normal Stage E retry kind is invalid")
        scores_prefix = current["scores"]
        labels_sha = supplied_labels_sha
        labels_manifest_sha = supplied_labels_manifest_sha
        scores_manifest_sha = ""
        if not labels_sha or not labels_manifest_sha:
            raise SystemExit("Stage-E labels hash bindings are incomplete")
else:
    raise SystemExit("stage cannot derive its effective attempt prefixes")

closed_receipt_sha = supplied_closed_receipt_sha
if verify_only == "true" and verification_state == "CLOSED":
    authenticated_closed_sha = authenticated.get(
        "prior_state_receipt_sha256"
    )
    require_sha(authenticated_closed_sha, "authenticated CLOSED receipt")
    if closed_receipt_sha and closed_receipt_sha != authenticated_closed_sha:
        raise SystemExit(
            "caller CLOSED receipt differs from authenticated state"
        )
    closed_receipt_sha = authenticated_closed_sha

for value, name in (
    (locked_input_sha, "locked input"),
    (locked_input_manifest_sha, "locked input manifest"),
    (prediction_manifest_sha, "prediction manifest"),
    (labels_sha, "labels"),
    (labels_manifest_sha, "labels manifest"),
    (scores_manifest_sha, "scores manifest"),
    (closed_receipt_sha, "CLOSED receipt"),
    (supplied_prior_receipt_sha, "stage prior receipt"),
):
    require_sha(value, name, optional=not bool(value))

prefixes = {
    "predictions": predictions_prefix,
    "scores": scores_prefix,
    "visibility": visibility_prefix,
}
prefix_hashes = {
    leaf: (
        core.attempt_prefix_sha256(prefix) if prefix else ""
    )
    for leaf, prefix in prefixes.items()
}
if (
    predictions_prefix != effective["predictions_prefix"]
    or scores_prefix != effective["scores_prefix"]
    or visibility_prefix != effective["visibility_prefix"]
    or prefix_hashes["predictions"]
    != effective["predictions_attempt_prefix_sha256"]
    or prefix_hashes["scores"]
    != effective["scores_attempt_prefix_sha256"]
    or prefix_hashes["visibility"]
    != effective["visibility_attempt_prefix_sha256"]
):
    raise SystemExit("effective attempt prefixes differ from verified core")
record = {
    "stage": stage,
    "verify_only": verify_only,
    "close_invalid_only": close_invalid_only,
    "verification_state": verification_state,
    "retry_kind": retry_kind,
    "execution_id": execution_id,
    "actor": actor,
    "locked_input_sha256": locked_input_sha,
    "locked_input_manifest_sha256": locked_input_manifest_sha,
    "prediction_manifest_sha256": prediction_manifest_sha,
    "labels_sha256": labels_sha,
    "labels_manifest_sha256": labels_manifest_sha,
    "scores_manifest_sha256": scores_manifest_sha,
    "closed_receipt_sha256": closed_receipt_sha,
    "prior_receipt_sha256": supplied_prior_receipt_sha,
    "predictions_prefix": predictions_prefix,
    "scores_prefix": scores_prefix,
    "visibility_prefix": visibility_prefix,
    "predictions_attempt_prefix_sha256": prefix_hashes["predictions"],
    "scores_attempt_prefix_sha256": prefix_hashes["scores"],
    "visibility_attempt_prefix_sha256": prefix_hashes["visibility"],
    "current_attempt_binding_sha256": effective[
        "current_attempt_binding_sha256"
    ],
    "authenticated_prediction_retry_kind": effective[
        "authenticated_prediction_retry_kind"
    ],
    "authenticated_prediction_execution_id": effective[
        "authenticated_prediction_execution_id"
    ],
    "authenticated_scoring_retry_kind": effective[
        "authenticated_scoring_retry_kind"
    ],
    "authenticated_scoring_execution_id": effective[
        "authenticated_scoring_execution_id"
    ],
    "producer_retry_kind": producer_retry_kind,
    "producer_execution_id": producer_execution_id,
    "expected_predictions_receipt_sha256": expected_predictions_receipt_sha,
}
pathlib.Path(output_path).write_bytes(core.canonical_json_bytes(record))
PY
    if [[ -e "$STAGE_BINDINGS_FILE" ]]; then
        if ! cmp -s "$candidate" "$STAGE_BINDINGS_FILE"; then
            echo "[FAIL] Effective attempt prefixes changed after authentication"
            return 1
        fi
        rm -f "$candidate" || return 1
    else
        mv "$candidate" "$STAGE_BINDINGS_FILE" || return 1
        chmod 400 "$STAGE_BINDINGS_FILE" || return 1
    fi
}

authenticate_current_persisted_state() {
    if [[ "$RECOVERY_ONLY" == "true" ]]; then
        authenticate_persisted_state LATEST "" || return 1
    else
        authenticate_persisted_state "$AUTH_STATE" "$AUTH_RECEIPT_SHA256" \
            || return 1
    fi
    derive_effective_stage_bindings || return 1
}

reauthenticate_runtime_destination || exit 1
if [[ "$INITIAL_BOOTSTRAP" == "true" ]]; then
    BOOTSTRAP_RESULT="$SCRATCH_DIR/initial_bootstrap.json"
    BOOTSTRAP_HASHES_FILE="$SCRATCH_DIR/bootstrap_hashes.txt"
    reauthenticate_runtime_destination || exit 1
    verify_immutable_launch_inputs || exit 1
    JSPACE_LOCKED_EVAL_ROLE=custodian \
        python "$BOOTSTRAP" \
        --runtime-config-file "$RUNTIME_CONFIG_SNAPSHOT_FILE" \
        --runtime-config-sha256 "$CONFIG_SHA256" \
        --implementation-manifest-file \
        "$IMPLEMENTATION_MANIFEST_SNAPSHOT_FILE" \
        --implementation-manifest-sha256 "$IMPLEMENTATION_MANIFEST_SHA256" \
        --image-binding-file "$IMAGE_BINDING_SNAPSHOT_FILE" \
        --image-binding-sha256 "$IMAGE_BINDING_SHA256" \
        --helper-snapshot-set-sha256 "$HELPER_SNAPSHOT_SET_SHA256" \
        --execution-id "custodian-${INVOCATION_ID}" \
        --actor phase1-parser-v2-custodian >"$BOOTSTRAP_RESULT" || exit 1
    python - "$BOOTSTRAP_RESULT" <<'PY' | tr -d '\r' \
        >"$BOOTSTRAP_HASHES_FILE" || exit 1
import json
import pathlib
import sys

record = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
if record.get("status") != "UNSEAL_AUTHORIZED":
    raise SystemExit("custodian bootstrap did not authenticate UNSEAL")
for key in (
    "authorization_lock_sha256",
    "authorization_manifest_sha256",
    "unseal_receipt_sha256",
):
    print(record[key])
PY
    mapfile -t BOOTSTRAP_HASHES <"$BOOTSTRAP_HASHES_FILE" || exit 1
    AUTHORIZATION_LOCK_SHA256="${BOOTSTRAP_HASHES[0]}"
    AUTHORIZATION_MANIFEST_SHA256="${BOOTSTRAP_HASHES[1]}"
    STAGE_PRIOR_RECEIPT_SHA256="${BOOTSTRAP_HASHES[2]}"
    AUTH_RECEIPT_SHA256="${BOOTSTRAP_HASHES[2]}"
fi
if [[ ! "$AUTHORIZATION_LOCK_SHA256" =~ ^[0-9a-f]{64}$ \
    || ! "$AUTHORIZATION_MANIFEST_SHA256" =~ ^[0-9a-f]{64}$ \
    || ! "$AUTH_RECEIPT_SHA256" =~ ^[0-9a-f]{64}$ ]]; then
    echo "[FAIL] Complete persisted authorization bytes were not authenticated"
    exit 1
fi
authenticate_current_persisted_state || exit 1
EFFECTIVE_STAGE_HASHES_FILE="$SCRATCH_DIR/effective_stage_hashes.txt"
python - "$STAGE_BINDINGS_FILE" <<'PY' | tr -d '\r' \
    >"$EFFECTIVE_STAGE_HASHES_FILE" || exit 1
import json
import pathlib
import sys

record = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
for key in (
    "prior_receipt_sha256",
    "prediction_manifest_sha256",
    "labels_sha256",
    "labels_manifest_sha256",
    "scores_manifest_sha256",
    "closed_receipt_sha256",
):
    print(record[key])
PY
mapfile -t EFFECTIVE_STAGE_HASHES <"$EFFECTIVE_STAGE_HASHES_FILE" || exit 1
if [[ "${#EFFECTIVE_STAGE_HASHES[@]}" -ne 6 ]]; then
    echo "[FAIL] Effective stage hash extraction is incomplete"
    exit 1
fi
STAGE_PRIOR_RECEIPT_SHA256="${EFFECTIVE_STAGE_HASHES[0]}"
PARSER_EVAL_PREDICTION_MANIFEST_SHA256="${EFFECTIVE_STAGE_HASHES[1]}"
PARSER_EVAL_LABELS_SHA256="${EFFECTIVE_STAGE_HASHES[2]}"
PARSER_EVAL_LABELS_MANIFEST_SHA256="${EFFECTIVE_STAGE_HASHES[3]}"
PARSER_EVAL_SCORES_MANIFEST_SHA256="${EFFECTIVE_STAGE_HASHES[4]}"
PARSER_EVAL_CLOSED_RECEIPT_SHA256="${EFFECTIVE_STAGE_HASHES[5]}"
if [[ -n "$AUTHENTICATED_VERIFICATION_RETRY_EXECUTION_ID" ]]; then
    if [[ "${STAGE}:${VERIFY_ONLY}:${RETRY_KIND}:${RECOVERY_ONLY}" \
        != "E:true:verification_only:true" \
        || "$AUTHENTICATED_VERIFICATION_RETRY_EXECUTION_ID" \
            != "$EXECUTION_ID" ]]; then
        echo "[FAIL] Verification retry singleton belongs to another launch claim"
        exit 1
    fi
fi

printf '[]\n' >"$PRIOR_EXECUTION_NAMES_FILE"
printf '[]\n' >"$EXECUTIONS_FILE"
python "$AZURE_HELPER" execution-membership \
    --executions "$EXECUTIONS_FILE" --output "$DISPATCH_MEMBERSHIP_FILE"
CLAIM_PRIOR_EXECUTION_COUNT="$(scalar python "$AZURE_HELPER" get \
    --json "$DISPATCH_MEMBERSHIP_FILE" --field count)"
CLAIM_PRIOR_EXECUTION_NAMES_SHA256="$(scalar python "$AZURE_HELPER" get \
    --json "$DISPATCH_MEMBERSHIP_FILE" --field sha256)"
CLAIM_PRIOR_EXECUTION_NAMES_JSON="[]"
JOB_PRESENT="false"
JOB_BASELINE_GET_STATUS="transport-ambiguous"
if status="$(raw_arm_get_once "$JOB_URL" "$LIVE_JOB_FILE")"; then
    JOB_BASELINE_GET_STATUS="$status"
fi
case "$JOB_BASELINE_GET_STATUS" in
    200)
        JOB_PRESENT="true"
        python "$AZURE_HELPER" arm-list \
            --url "$EXECUTIONS_URL" --output "$EXECUTIONS_FILE"
        ;;
    404) ;;
    *)
        echo "[FAIL] Exact immutable Job baseline GET returned ${JOB_BASELINE_GET_STATUS}"
        exit 1
        ;;
esac
if [[ "$JOB_PRESENT" == "true" && "$RECOVERY_ONLY" != "true" ]]; then
    echo "[FAIL] Immutable Job exists without its deterministic launch TXT claim"
    exit 1
fi

verify_immutable_launch_inputs || exit 1
python - "$RUNTIME_CONFIG_SNAPSHOT_FILE" "$STAGE_BINDINGS_FILE" "$BODY_FILE" \
    "$CLAIM_NAME" "$INVOCATION_ID" "$EVALUATION_MODE" \
    "$AUTHORIZATION_LOCK_SHA256" "$AUTHORIZATION_MANIFEST_SHA256" \
    "$IMPLEMENTATION_MANIFEST_SHA256" "$JOB_ID" <<'PY'
import json
import pathlib
import sys

(
    runtime_path,
    stage_path,
    output_path,
    claim_name,
    invocation_id,
    evaluation_mode,
    lock_sha,
    authorization_manifest_sha,
    implementation_manifest_sha,
    job_resource_id,
) = sys.argv[1:]
runtime = json.loads(pathlib.Path(runtime_path).read_text(encoding="utf-8"))
stage = json.loads(pathlib.Path(stage_path).read_text(encoding="utf-8"))
d = runtime["azure_destination"]
b = runtime["bindings"]
n = d["network"]
common = [
    "--account-url", d["storage"]["blob_endpoint"],
]
for address in n["private_endpoint_nic_private_ips"]:
    common.extend(["--expected-private-endpoint-ip", address])
common.extend([
    "--container", d["storage"]["container"],
    "--parent-prefix", b["registered_parent_prefix"],
    "--authorization-id", b["authorization_id"],
    "--predictions-prefix", stage["predictions_prefix"],
    "--state-prefix", b["state_prefix"],
    "--visibility-prefix", stage["visibility_prefix"],
    "--implementation-commit", runtime["source_commit"],
    "--image-digest", d["image"]["digest"],
    "--image-binding-sha256", runtime["image_binding_sha256"],
    "--helper-snapshot-set-sha256", runtime["helper_snapshot_set_sha256"],
    "--config-sha256", implementation_manifest_sha and runtime["azure_destination"] and
        __import__("hashlib").sha256(pathlib.Path(runtime_path).read_bytes()).hexdigest(),
    "--authorization-lock-sha256", lock_sha,
    "--authorization-manifest-sha256", authorization_manifest_sha,
    "--launcher-sha256", runtime["launcher"]["sha256"],
    "--launcher-git-blob-oid", runtime["launcher"]["git_blob_oid"],
    "--retry-kind", stage["retry_kind"],
    "--execution-id", stage["execution_id"],
    "--actor", stage["actor"],
])
if (
    stage["stage"] == "P"
    and stage["retry_kind"] == "prediction_adoption"
):
    if (
        stage["locked_input_sha256"]
        or stage["locked_input_manifest_sha256"]
        or not stage["prediction_manifest_sha256"]
        or not stage["expected_predictions_receipt_sha256"]
        or stage["producer_retry_kind"] not in {
            "none",
            "infrastructure_pre_input",
        }
        or not stage["producer_execution_id"]
    ):
        raise SystemExit("prediction-adoption projection is incomplete")
    arguments = [
        *common,
        "--prediction-manifest-sha256",
        stage["prediction_manifest_sha256"],
        "--expected-predictions-receipt-sha256",
        stage["expected_predictions_receipt_sha256"],
        "--producer-retry-kind", stage["producer_retry_kind"],
        "--producer-execution-id", stage["producer_execution_id"],
        "--prior-state-receipt-blob",
        f"{b['state_prefix']}/08_inputs_read_receipt.json",
        "--prior-state-receipt-sha256", stage["prior_receipt_sha256"],
    ]
elif stage["stage"] == "P":
    arguments = [
        *common,
        "--locked-input-blob",
        f"{b['registered_parent_prefix']}/locked-inputs/locked_inputs.jsonl",
        "--locked-input-sha256", stage["locked_input_sha256"],
        "--locked-input-manifest-blob",
        f"{b['registered_parent_prefix']}/locked-inputs/locked_inputs_manifest.json",
        "--locked-input-manifest-sha256",
        stage["locked_input_manifest_sha256"],
        "--prior-state-receipt-blob",
        f"{b['state_prefix']}/07_unseal_authorized_receipt.json",
        "--prior-state-receipt-sha256", stage["prior_receipt_sha256"],
    ]
else:
    arguments = [
        *common,
        "--prediction-manifest-sha256", stage["prediction_manifest_sha256"],
        "--scores-prefix", stage["scores_prefix"],
        "--labels-blob",
        f"{b['registered_parent_prefix']}/locked-labels/locked_reference_labels.jsonl",
        "--labels-sha256", stage["labels_sha256"],
        "--labels-manifest-blob",
        f"{b['registered_parent_prefix']}/locked-labels/locked_labels_manifest.json",
        "--labels-manifest-sha256", stage["labels_manifest_sha256"],
        "--prior-state-receipt-blob",
        f"{b['state_prefix']}/09_predictions_verified_receipt.json",
        "--prior-state-receipt-sha256", stage["prior_receipt_sha256"],
    ]
    if stage["close_invalid_only"] == "true":
        if (
            stage["verify_only"] != "true"
            or stage["retry_kind"] != "verification_only"
            or stage["scores_manifest_sha256"]
            or stage["closed_receipt_sha256"]
            or stage["producer_retry_kind"] not in {
                "none",
                "scorer_infrastructure",
            }
            or not stage["producer_execution_id"]
        ):
            raise SystemExit("INVALID closure projection is incomplete")
        arguments.extend([
            "--verify-only",
            "--close-invalid-only",
            "--verification-state", stage["verification_state"],
            "--producer-retry-kind", stage["producer_retry_kind"],
            "--producer-execution-id", stage["producer_execution_id"],
        ])
    elif stage["verify_only"] == "true":
        if not stage["scores_manifest_sha256"]:
            raise SystemExit("verification-only score hash is missing")
        arguments.extend([
            "--verify-only",
            "--verification-state", stage["verification_state"],
            "--scores-manifest-sha256", stage["scores_manifest_sha256"],
        ])
        if stage["closed_receipt_sha256"]:
            arguments.extend([
                "--closed-receipt-sha256", stage["closed_receipt_sha256"],
            ])
command_key = (
    "P_ADOPT"
    if stage["stage"] == "P"
    and stage["retry_kind"] == "prediction_adoption"
    else stage["stage"]
)
command = runtime["stage_commands"][command_key]["command"]
body = {
    "location": d["location"],
    "identity": {
        "type": "UserAssigned",
        "userAssignedIdentities": {d["managed_identity"]["resource_id"]: {}},
    },
    "tags": {
        "project": "jspace-observation",
        "phase": "1.2B",
        "evaluation-stage": stage["stage"],
        "evaluation-mode": evaluation_mode,
        "invalid-closure-only": stage.get("close_invalid_only", "false"),
        "verification-state": stage["verification_state"],
        "authorization-id": b["authorization_id"],
        "registered-parent-prefix": b["registered_parent_prefix"],
        "implementation-commit": runtime["source_commit"],
        "image-digest": d["image"]["digest"],
        "image-binding-sha256": runtime["image_binding_sha256"],
        "helper-snapshot-set-sha256": runtime[
            "helper_snapshot_set_sha256"
        ],
        "config-sha256": __import__("hashlib").sha256(
            pathlib.Path(runtime_path).read_bytes()
        ).hexdigest(),
        "implementation-manifest-sha256": implementation_manifest_sha,
        "authorization-lock-sha256": lock_sha,
        "authorization-manifest-sha256": authorization_manifest_sha,
        "azure-destination-sha256": runtime["azure_destination_sha256"],
        "launcher-content-sha256": runtime["launcher"]["sha256"],
        "launcher-git-blob-oid": runtime["launcher"]["git_blob_oid"],
        "environment-resource-id": d["container_apps"]["environment_resource_id"],
        "job-resource-id": job_resource_id,
        "storage-resource-id": d["storage"]["resource_id"],
        "private-endpoint-id": n["private_endpoint_resource_id"],
        "private-endpoint-name": n["private_endpoint_name"],
        "private-endpoint-ips": ",".join(n["private_endpoint_nic_private_ips"]),
        "storage-private-endpoint-connection-id": n[
            "storage_private_endpoint_connection_resource_id"
        ],
        "private-dns-zone": n["private_dns_zone_name"],
        "private-dns-zone-group": n["private_dns_zone_group_name"],
        "registry-resource-id": d["registry"]["resource_id"],
        "launch-claim-name": claim_name,
        "launch-invocation-id": invocation_id,
        "launch-state": "claimed-for-start",
        "retry-kind": stage["retry_kind"],
        "predictions-attempt-prefix-sha256": stage[
            "predictions_attempt_prefix_sha256"
        ],
        "visibility-attempt-prefix-sha256": stage[
            "visibility_attempt_prefix_sha256"
        ],
        "current-attempt-binding-sha256": stage[
            "current_attempt_binding_sha256"
        ],
        "automatic-retry": "zero",
        "gpu": "none",
    },
    "properties": {
        "environmentId": d["container_apps"]["environment_resource_id"],
        "workloadProfileName": "Consumption",
        "configuration": {
            "triggerType": "Manual",
            "replicaTimeout": 3600,
            "replicaRetryLimit": 0,
            "manualTriggerConfig": {
                "replicaCompletionCount": 1,
                "parallelism": 1,
            },
            "registries": [{
                "server": d["registry"]["login_server"],
                "identity": d["managed_identity"]["resource_id"],
            }],
            "secrets": [],
        },
        "template": {
            "containers": [{
                "name": "parser-v2-locked-eval",
                "image": d["image"]["reference"],
                "command": command,
                "args": arguments,
                "env": [{
                    "name": "AZURE_CLIENT_ID",
                    "value": d["managed_identity"]["client_id"],
                }],
                "resources": {"cpu": 2.0, "memory": "4Gi"},
                "volumeMounts": [],
                "probes": [],
            }],
            "initContainers": [],
            "volumes": [],
        },
    },
}
if stage["scores_attempt_prefix_sha256"]:
    body["tags"]["scores-attempt-prefix-sha256"] = stage[
        "scores_attempt_prefix_sha256"
    ]
pathlib.Path(output_path).write_text(
    json.dumps(body, sort_keys=True, separators=(",", ":")) + "\n",
    encoding="utf-8",
)
PY

JOB_BODY_SHA256="$(scalar sha256sum "$BODY_FILE")"
JOB_BODY_SHA256="${JOB_BODY_SHA256%% *}"
chmod 400 "$BODY_FILE"
verify_immutable_launch_inputs || exit 1
EXPECTED_JOB_PROJECTION_SHA256="$(scalar python "$AZURE_HELPER" project-job \
    --live "$BODY_FILE" --expected "$BODY_FILE" \
    --output "$EXPECTED_PROJECTION_FILE")"

JOB_RESOURCE_ID_SHA256="$(printf '%s' "${JOB_ID,,}" \
    | sha256sum | awk '{print $1}')"
LAUNCH_CAPABILITY="false"
EXECUTION_NAME=""
CLAIM_JOB_BODY_SHA256="$JOB_BODY_SHA256"
CLAIM_JOB_PROJECTION_SHA256="$EXPECTED_JOB_PROJECTION_SHA256"
CLAIM_STATE_RECEIPT_SHA256="$AUTHENTICATED_STATE_RECEIPT_SHA256"

authenticate_launch_txt_record() {
    : >"$LAUNCH_TXT_LIVE_FILE" || return 1
    : >"$LAUNCH_TXT_EVIDENCE_FILE" || return 1
    az rest --method get --url "$LAUNCH_RECORD_URL" \
        --output json >"$LAUNCH_TXT_LIVE_FILE" || return 1
    python "$AZURE_HELPER" validate-txt-record \
        --record "$LAUNCH_TXT_LIVE_FILE" \
        --zone-resource-id "$COORDINATION_ZONE_RESOURCE_ID" \
        --record-name "$LAUNCH_RECORD_NAME" \
        --ttl "$COORDINATION_RECORD_TTL" \
        --expected-kind launch \
        --expected-domain-sha256 "$LAUNCH_DOMAIN_SHA256" \
        --output "$LAUNCH_TXT_EVIDENCE_FILE" || return 1
}

validate_launch_claim_static_bindings() {
    python - "$LAUNCH_TXT_EVIDENCE_FILE" "$AUTHORIZATION_ID" \
        "$INVOCATION_ID" "$EXECUTION_ID" "$JOB_NAME" \
        "$JOB_RESOURCE_ID_SHA256" "$CONFIG_SHA256" \
        "$IMAGE_BINDING_SHA256" "$HELPER_SNAPSHOT_SET_SHA256" \
        "$IMPLEMENTATION_MANIFEST_SHA256" "$AUTHORIZATION_LOCK_SHA256" \
        "$AUTHORIZATION_MANIFEST_SHA256" "$AZURE_DESTINATION_SHA256" \
        "$LAUNCHER_CONTENT_SHA256" "$LAUNCHER_GIT_BLOB_OID" \
        "$COORDINATION_BINDING_SHA256" \
        "$CLAIM_PRIOR_EXECUTION_NAMES_SHA256" \
        "$STAGE" "$EVALUATION_MODE" "$RETRY_KIND" <<'PY' || return 1
import json
import pathlib
import sys

evidence = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="ascii"))
claims = evidence["envelope"]["claims"]
keys = (
    "authorization_id",
    "claim_nonce",
    "execution_id",
    "job_name",
    "job_resource_id_sha256",
    "config_sha256",
    "image_binding_sha256",
    "helper_snapshot_set_sha256",
    "implementation_manifest_sha256",
    "authorization_lock_sha256",
    "authorization_manifest_sha256",
    "azure_destination_sha256",
    "launcher_sha256",
    "launcher_git_blob_oid",
    "coordination_binding_sha256",
    "baseline_execution_membership_sha256",
    "stage",
    "mode",
    "retry_kind",
)
expected = dict(zip(keys, sys.argv[2:]))
for key, value in expected.items():
    if claims[key] != value:
        raise SystemExit(f"launch TXT static binding differs: {key}")
if claims["baseline_execution_count"] != 0:
    raise SystemExit("unique launch Job baseline is not empty")
PY
}

authenticate_exact_execution_baseline() {
    local current_count current_sha256
    : >"$EXECUTIONS_FILE"
    : >"$CURRENT_EXECUTION_MEMBERSHIP_FILE"
    python "$AZURE_HELPER" arm-list \
        --url "$EXECUTIONS_URL" --output "$EXECUTIONS_FILE" || return 1
    python "$AZURE_HELPER" execution-membership \
        --executions "$EXECUTIONS_FILE" \
        --output "$CURRENT_EXECUTION_MEMBERSHIP_FILE" || return 1
    current_count="$(scalar python "$AZURE_HELPER" get \
        --json "$CURRENT_EXECUTION_MEMBERSHIP_FILE" --field count)" \
        || return 1
    current_sha256="$(scalar python "$AZURE_HELPER" get \
        --json "$CURRENT_EXECUTION_MEMBERSHIP_FILE" --field sha256)" \
        || return 1
    [[ "$current_count" == "$CLAIM_PRIOR_EXECUTION_COUNT" \
        && "$current_sha256" == "$CLAIM_PRIOR_EXECUTION_NAMES_SHA256" ]]
}

derive_dispatch_domain_binding() {
    LAUNCH_RECORD_ETAG_SHA256="$(scalar python "$AZURE_HELPER" get \
        --json "$LAUNCH_TXT_EVIDENCE_FILE" --field record_etag_sha256)" \
        || return 1
    LAUNCH_PAYLOAD_SHA256="$(scalar python "$AZURE_HELPER" get \
        --json "$LAUNCH_TXT_EVIDENCE_FILE" --field payload_sha256)" \
        || return 1
    python - "$DISPATCH_DOMAIN_BINDING_FILE" "$AUTHORIZATION_ID" \
        "$EXECUTION_ID" "$LAUNCH_RECORD_NAME" "$LAUNCH_DOMAIN_SHA256" \
        "$LAUNCH_RECORD_ETAG_SHA256" "$LAUNCH_PAYLOAD_SHA256" \
        "$JOB_RESOURCE_ID_SHA256" "$CLAIM_JOB_BODY_SHA256" \
        "$CLAIM_JOB_PROJECTION_SHA256" \
        "$CLAIM_PRIOR_EXECUTION_NAMES_SHA256" \
        "$CLAIM_STATE_RECEIPT_SHA256" "$CONFIG_SHA256" \
        "$IMAGE_BINDING_SHA256" "$HELPER_SNAPSHOT_SET_SHA256" \
        "$IMPLEMENTATION_MANIFEST_SHA256" "$AUTHORIZATION_LOCK_SHA256" \
        "$AUTHORIZATION_MANIFEST_SHA256" "$AZURE_DESTINATION_SHA256" \
        "$COORDINATION_BINDING_SHA256" <<'PY' || return 1
import json
import pathlib
import sys

keys = (
    "authorization_id",
    "execution_id",
    "launch_record_name",
    "launch_domain_sha256",
    "launch_record_etag_sha256",
    "launch_payload_sha256",
    "job_resource_id_sha256",
    "job_body_sha256",
    "job_projection_sha256",
    "baseline_execution_membership_sha256",
    "state_receipt_sha256",
    "config_sha256",
    "image_binding_sha256",
    "helper_snapshot_set_sha256",
    "implementation_manifest_sha256",
    "authorization_lock_sha256",
    "authorization_manifest_sha256",
    "azure_destination_sha256",
    "coordination_binding_sha256",
)
pathlib.Path(sys.argv[1]).write_text(
    json.dumps(
        dict(zip(keys, sys.argv[2:])),
        sort_keys=True,
        separators=(",", ":"),
    )
    + "\n",
    encoding="ascii",
)
PY
    DISPATCH_DOMAIN_SHA256="$(scalar python "$AZURE_HELPER" claim-domain \
        --kind dispatch --binding "$DISPATCH_DOMAIN_BINDING_FILE")" \
        || return 1
    DISPATCH_RECORD_NAME="dispatch-${DISPATCH_DOMAIN_SHA256:0:32}.${DISPATCH_DOMAIN_SHA256:32:32}"
    DISPATCH_RECORD_URL="https://management.azure.com${COORDINATION_ZONE_RESOURCE_ID}/TXT/${DISPATCH_RECORD_NAME}?api-version=${COORDINATION_DNS_API_VERSION}"
    [[ "$DISPATCH_DOMAIN_SHA256" =~ ^[0-9a-f]{64}$ ]]
}

authenticate_dispatch_txt_record() {
    : >"$DISPATCH_TXT_LIVE_FILE"
    : >"$DISPATCH_TXT_EVIDENCE_FILE"
    az rest --method get --url "$DISPATCH_RECORD_URL" \
        --output json >"$DISPATCH_TXT_LIVE_FILE" || return 1
    python "$AZURE_HELPER" validate-txt-record \
        --record "$DISPATCH_TXT_LIVE_FILE" \
        --zone-resource-id "$COORDINATION_ZONE_RESOURCE_ID" \
        --record-name "$DISPATCH_RECORD_NAME" \
        --ttl "$COORDINATION_RECORD_TTL" \
        --expected-kind dispatch \
        --expected-domain-sha256 "$DISPATCH_DOMAIN_SHA256" \
        --output "$DISPATCH_TXT_EVIDENCE_FILE" || return 1
}

validate_dispatch_claim_static_bindings() {
    python - "$DISPATCH_TXT_EVIDENCE_FILE" "$AUTHORIZATION_ID" \
        "$EXECUTION_ID" "$LAUNCH_RECORD_NAME" "$LAUNCH_DOMAIN_SHA256" \
        "$LAUNCH_RECORD_ETAG_SHA256" "$LAUNCH_PAYLOAD_SHA256" \
        "$JOB_NAME" "$JOB_RESOURCE_ID_SHA256" "$CLAIM_JOB_BODY_SHA256" \
        "$CLAIM_JOB_PROJECTION_SHA256" \
        "$CLAIM_PRIOR_EXECUTION_NAMES_SHA256" \
        "$CLAIM_PRIOR_EXECUTION_COUNT" "$CLAIM_STATE_RECEIPT_SHA256" \
        "$CONFIG_SHA256" "$IMAGE_BINDING_SHA256" \
        "$HELPER_SNAPSHOT_SET_SHA256" "$IMPLEMENTATION_MANIFEST_SHA256" \
        "$AUTHORIZATION_LOCK_SHA256" "$AUTHORIZATION_MANIFEST_SHA256" \
        "$AZURE_DESTINATION_SHA256" "$COORDINATION_BINDING_SHA256" \
        <<'PY' || return 1
import json
import pathlib
import sys

evidence = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="ascii"))
claims = evidence["envelope"]["claims"]
keys = (
    "authorization_id",
    "execution_id",
    "launch_record_name",
    "launch_domain_sha256",
    "launch_record_etag_sha256",
    "launch_payload_sha256",
    "job_name",
    "job_resource_id_sha256",
    "job_body_sha256",
    "job_projection_sha256",
    "baseline_execution_membership_sha256",
    "baseline_execution_count",
    "state_receipt_sha256",
    "config_sha256",
    "image_binding_sha256",
    "helper_snapshot_set_sha256",
    "implementation_manifest_sha256",
    "authorization_lock_sha256",
    "authorization_manifest_sha256",
    "azure_destination_sha256",
    "coordination_binding_sha256",
)
expected = dict(zip(keys, sys.argv[2:]))
expected["baseline_execution_count"] = int(
    expected["baseline_execution_count"]
)
for key, value in expected.items():
    if claims[key] != value:
        raise SystemExit(f"dispatch TXT static binding differs: {key}")
PY
}

wait_for_exact_ready_job() {
    local provisioning_state
    for _ in $(seq 1 120); do
        : >"$LIVE_JOB_FILE"
        : >"$LIVE_PROJECTION_FILE"
        if az rest --method get --url "$JOB_URL" \
            --output json >"$LIVE_JOB_FILE" 2>/dev/null; then
            if ! python "$AZURE_HELPER" project-job \
                --live "$LIVE_JOB_FILE" --expected "$BODY_FILE" \
                --output "$LIVE_PROJECTION_FILE" >/dev/null; then
                echo "[FAIL] Live immutable Job differs from the launch claim"
                return 1
            fi
            provisioning_state="$(scalar python "$AZURE_HELPER" get \
                --json "$LIVE_JOB_FILE" \
                --field properties.provisioningState)" || return 1
            case "$provisioning_state" in
                Succeeded)
                    python "$AZURE_HELPER" validate-live-job-projection \
                        --live "$LIVE_JOB_FILE" \
                        --expected-job-resource-id "$JOB_ID" \
                        --expected-job-name "$JOB_NAME" \
                        --expected-sha256 "$CLAIM_JOB_PROJECTION_SHA256" \
                        --output "$LIVE_PROJECTION_FILE" >/dev/null \
                        || return 1
                    return 0
                    ;;
                InProgress|Accepted|Creating|Updating) ;;
                *)
                    echo "[FAIL] Immutable Job provisioning did not succeed"
                    return 1
                    ;;
            esac
        fi
        sleep 5
    done
    return 1
}

if [[ "$RECOVERY_ONLY" == "true" ]]; then
    authenticate_launch_txt_record || exit 1
    validate_launch_claim_static_bindings || exit 1
    CLAIM_JOB_BODY_SHA256="$(scalar python "$AZURE_HELPER" get \
        --json "$LAUNCH_TXT_EVIDENCE_FILE" \
        --field envelope.claims.job_body_sha256)"
    CLAIM_JOB_PROJECTION_SHA256="$(scalar python "$AZURE_HELPER" get \
        --json "$LAUNCH_TXT_EVIDENCE_FILE" \
        --field envelope.claims.job_projection_sha256)"
    CLAIM_STATE_RECEIPT_SHA256="$(scalar python "$AZURE_HELPER" get \
        --json "$LAUNCH_TXT_EVIDENCE_FILE" \
        --field envelope.claims.state_receipt_sha256)"
else
    python - "$LAUNCH_CLAIM_VALUES_FILE" "$AUTHORIZATION_ID" \
        "$INVOCATION_ID" "$STAGE" "$EVALUATION_MODE" "$RETRY_KIND" \
        "$EXECUTION_ID" "$JOB_NAME" "$JOB_RESOURCE_ID_SHA256" \
        "$JOB_BODY_SHA256" "$EXPECTED_JOB_PROJECTION_SHA256" \
        "$CLAIM_PRIOR_EXECUTION_NAMES_SHA256" \
        "$CLAIM_PRIOR_EXECUTION_COUNT" \
        "$AUTHENTICATED_STATE_RECEIPT_SHA256" "$CONFIG_SHA256" \
        "$IMAGE_BINDING_SHA256" "$HELPER_SNAPSHOT_SET_SHA256" \
        "$IMPLEMENTATION_MANIFEST_SHA256" "$AUTHORIZATION_LOCK_SHA256" \
        "$AUTHORIZATION_MANIFEST_SHA256" "$AZURE_DESTINATION_SHA256" \
        "$LAUNCHER_CONTENT_SHA256" "$LAUNCHER_GIT_BLOB_OID" \
        "$COORDINATION_BINDING_SHA256" <<'PY'
import json
import pathlib
import sys

keys = (
    "authorization_id",
    "claim_nonce",
    "stage",
    "mode",
    "retry_kind",
    "execution_id",
    "job_name",
    "job_resource_id_sha256",
    "job_body_sha256",
    "job_projection_sha256",
    "baseline_execution_membership_sha256",
    "baseline_execution_count",
    "state_receipt_sha256",
    "config_sha256",
    "image_binding_sha256",
    "helper_snapshot_set_sha256",
    "implementation_manifest_sha256",
    "authorization_lock_sha256",
    "authorization_manifest_sha256",
    "azure_destination_sha256",
    "launcher_sha256",
    "launcher_git_blob_oid",
    "coordination_binding_sha256",
)
values = dict(zip(keys, sys.argv[2:]))
values["baseline_execution_count"] = int(
    values["baseline_execution_count"]
)
pathlib.Path(sys.argv[1]).write_text(
    json.dumps(values, sort_keys=True, separators=(",", ":")) + "\n",
    encoding="ascii",
)
PY
    python "$AZURE_HELPER" create-claim-envelope --kind launch \
        --domain-sha256 "$LAUNCH_DOMAIN_SHA256" \
        --claims "$LAUNCH_CLAIM_VALUES_FILE" \
        --output "$LAUNCH_CLAIM_ENVELOPE_FILE"
    RETURNED_LAUNCH_RECORD_NAME="$(scalar python "$AZURE_HELPER" \
        create-txt-record-body --envelope "$LAUNCH_CLAIM_ENVELOPE_FILE" \
        --ttl "$COORDINATION_RECORD_TTL" \
        --output "$LAUNCH_TXT_BODY_FILE" --print-name)"
    if [[ "$RETURNED_LAUNCH_RECORD_NAME" != "$LAUNCH_RECORD_NAME" ]]; then
        echo "[FAIL] Launch TXT body escaped its complete claim domain"
        exit 1
    fi
    chmod 400 "$LAUNCH_TXT_BODY_FILE"
    reauthenticate_runtime_destination || exit 1
    authenticate_current_persisted_state || exit 1
    if [[ "$AUTHENTICATED_STATE_RECEIPT_SHA256" \
        != "$CLAIM_STATE_RECEIPT_SHA256" ]]; then
        echo "[FAIL] Persisted state changed before launch TXT creation"
        exit 1
    fi
    LAUNCH_CREATE_STATUS="transport-ambiguous"
    if status="$(raw_arm_request_once PUT "$LAUNCH_RECORD_URL" \
        "$LAUNCH_TXT_BODY_FILE" "$LAUNCH_TXT_CREATE_RESPONSE_FILE" true)"; then
        LAUNCH_CREATE_STATUS="$status"
    fi
    if [[ "$LAUNCH_CREATE_STATUS" == "201" ]]; then
        python "$AZURE_HELPER" validate-txt-record \
            --record "$LAUNCH_TXT_CREATE_RESPONSE_FILE" \
            --zone-resource-id "$COORDINATION_ZONE_RESOURCE_ID" \
            --record-name "$LAUNCH_RECORD_NAME" \
            --ttl "$COORDINATION_RECORD_TTL" \
            --expected-envelope "$LAUNCH_CLAIM_ENVELOPE_FILE" \
            --output "$SCRATCH_DIR/launch_txt_create_evidence.json"
        authenticate_launch_txt_record || exit 1
        python - "$SCRATCH_DIR/launch_txt_create_evidence.json" \
            "$LAUNCH_TXT_EVIDENCE_FILE" <<'PY'
import json
import pathlib
import sys

created = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="ascii"))
reread = json.loads(pathlib.Path(sys.argv[2]).read_text(encoding="ascii"))
if (
    created["record_resource_id"].casefold()
    != reread["record_resource_id"].casefold()
    or created["record_etag"] != reread["record_etag"]
    or created["payload_sha256"] != reread["payload_sha256"]
):
    raise SystemExit("created/re-GET launch TXT evidence differs")
PY
        LAUNCH_CAPABILITY="dns-create-201:${INVOCATION_ID}:${LAUNCH_DOMAIN_SHA256}"
    else
        authenticate_launch_txt_record || exit 1
        validate_launch_claim_static_bindings || true
        echo "[FAIL] Launch TXT create returned ${LAUNCH_CREATE_STATUS}; GET cannot mint Job-PUT capability"
        exit 1
    fi
fi

if [[ "$RECOVERY_ONLY" == "true" ]]; then
    if [[ "$JOB_BODY_SHA256" != "$CLAIM_JOB_BODY_SHA256" \
        || "$EXPECTED_JOB_PROJECTION_SHA256" \
            != "$CLAIM_JOB_PROJECTION_SHA256" ]]; then
        echo "[FAIL] Recovery launch claim has no exact immutable Job"
        exit 1
    fi
    if ! wait_for_exact_ready_job; then
        echo "[FAIL] Recovery launch claim has no ready immutable Job"
        exit 1
    fi
    reauthenticate_runtime_destination || exit 1
    authenticate_launch_txt_record || exit 1
    validate_launch_claim_static_bindings || exit 1
    derive_dispatch_domain_binding || exit 1
    if ! authenticate_dispatch_txt_record; then
        echo "[FAIL] Recovery has no authenticated dispatch TXT record"
        exit 1
    fi
    validate_dispatch_claim_static_bindings || exit 1
    for _ in $(seq 1 120); do
        : >"$EXECUTIONS_FILE"
        python "$AZURE_HELPER" arm-list \
            --url "$EXECUTIONS_URL" --output "$EXECUTIONS_FILE"
        if python "$AZURE_HELPER" adopt-remove-one \
            --baseline "$PRIOR_EXECUTION_NAMES_FILE" \
            --executions "$EXECUTIONS_FILE" \
            --output "$ADOPTED_EXECUTION_FILE" 2>/dev/null; then
            EXECUTION_NAME="$(scalar python "$AZURE_HELPER" get \
                --json "$ADOPTED_EXECUTION_FILE" --field execution_name)"
            break
        fi
        sleep 5
    done
    if [[ -z "$EXECUTION_NAME" ]]; then
        echo "[FAIL] Recovery dispatch is stranded; no PUT or start is permitted"
        exit 1
    fi
fi

if [[ -z "$EXECUTION_NAME" && "$RECOVERY_ONLY" == "true" ]]; then
    echo "[FAIL] Recovery cannot reconstruct mutation capability"
    exit 1
fi

if [[ -z "$EXECUTION_NAME" ]]; then
    if [[ "$AUTHENTICATED_STATE_RECEIPT_SHA256" \
        != "$CLAIM_STATE_RECEIPT_SHA256" ]]; then
        echo "[FAIL] No execution exists and persisted state left the launch claim"
        exit 1
    fi
    if [[ "$JOB_BODY_SHA256" != "$CLAIM_JOB_BODY_SHA256" \
        || "$EXPECTED_JOB_PROJECTION_SHA256" \
            != "$CLAIM_JOB_PROJECTION_SHA256" ]]; then
        echo "[FAIL] Reconstructed immutable Job body differs from launch TXT"
        exit 1
    fi
    if [[ "$LAUNCH_CAPABILITY" == \
        "dns-create-201:${INVOCATION_ID}:${LAUNCH_DOMAIN_SHA256}" ]]; then
        PRE_JOB_PUT_GET_STATUS="transport-ambiguous"
        if status="$(raw_arm_get_once "$JOB_URL" "$PRE_JOB_PUT_GET_FILE")"; then
            PRE_JOB_PUT_GET_STATUS="$status"
        fi
        if [[ "$PRE_JOB_PUT_GET_STATUS" != "404" ]]; then
            echo "[FAIL] Immutable Job absence changed before its one-shot PUT"
            exit 1
        fi
        JOB_PUT_STATUS="transport-ambiguous"
        if status="$(raw_arm_request_once PUT "$JOB_URL" \
            "$BODY_FILE" "$JOB_PUT_RESPONSE_FILE" false)"; then
            JOB_PUT_STATUS="$status"
        fi
        echo "[INFO] One-shot immutable Job PUT result: ${JOB_PUT_STATUS}; only GET adoption follows"
    fi

    if ! wait_for_exact_ready_job; then
        echo "[FAIL] Launch claim has no exact Job; its one-shot PUT is stranded"
        exit 1
    fi
    reauthenticate_runtime_destination || exit 1
    authenticate_current_persisted_state || exit 1
    if [[ "$AUTHENTICATED_STATE_RECEIPT_SHA256" \
        != "$CLAIM_STATE_RECEIPT_SHA256" ]]; then
        echo "[FAIL] Persisted state changed before dispatch claim"
        exit 1
    fi
    if ! authenticate_exact_execution_baseline; then
        echo "[FAIL] Execution membership changed before dispatch claim"
        exit 1
    fi
    authenticate_launch_txt_record || exit 1
    validate_launch_claim_static_bindings || exit 1
    if [[ "$(scalar python "$AZURE_HELPER" get \
            --json "$LAUNCH_TXT_EVIDENCE_FILE" \
            --field envelope.claims.job_body_sha256)" \
            != "$CLAIM_JOB_BODY_SHA256" \
        || "$(scalar python "$AZURE_HELPER" get \
            --json "$LAUNCH_TXT_EVIDENCE_FILE" \
            --field envelope.claims.job_projection_sha256)" \
            != "$CLAIM_JOB_PROJECTION_SHA256" \
        || "$(scalar python "$AZURE_HELPER" get \
            --json "$LAUNCH_TXT_EVIDENCE_FILE" \
            --field envelope.claims.state_receipt_sha256)" \
            != "$CLAIM_STATE_RECEIPT_SHA256" ]]; then
        echo "[FAIL] Live launch TXT dynamic bindings changed before dispatch"
        exit 1
    fi

    derive_dispatch_domain_binding || exit 1
    DISPATCH_NONCE="$(scalar python "$AZURE_HELPER" new-id)"
    python - "$DISPATCH_CLAIM_VALUES_FILE" "$AUTHORIZATION_ID" \
        "$DISPATCH_NONCE" "$EXECUTION_ID" "$LAUNCH_RECORD_NAME" \
        "$LAUNCH_DOMAIN_SHA256" "$LAUNCH_RECORD_ETAG_SHA256" \
        "$LAUNCH_PAYLOAD_SHA256" "$JOB_NAME" "$JOB_RESOURCE_ID_SHA256" \
        "$CLAIM_JOB_BODY_SHA256" "$CLAIM_JOB_PROJECTION_SHA256" \
        "$CLAIM_PRIOR_EXECUTION_NAMES_SHA256" \
        "$CLAIM_PRIOR_EXECUTION_COUNT" "$CLAIM_STATE_RECEIPT_SHA256" \
        "$CONFIG_SHA256" "$IMAGE_BINDING_SHA256" \
        "$HELPER_SNAPSHOT_SET_SHA256" "$IMPLEMENTATION_MANIFEST_SHA256" \
        "$AUTHORIZATION_LOCK_SHA256" "$AUTHORIZATION_MANIFEST_SHA256" \
        "$AZURE_DESTINATION_SHA256" "$COORDINATION_BINDING_SHA256" <<'PY'
import json
import pathlib
import sys

keys = (
    "authorization_id",
    "claim_nonce",
    "execution_id",
    "launch_record_name",
    "launch_domain_sha256",
    "launch_record_etag_sha256",
    "launch_payload_sha256",
    "job_name",
    "job_resource_id_sha256",
    "job_body_sha256",
    "job_projection_sha256",
    "baseline_execution_membership_sha256",
    "baseline_execution_count",
    "state_receipt_sha256",
    "config_sha256",
    "image_binding_sha256",
    "helper_snapshot_set_sha256",
    "implementation_manifest_sha256",
    "authorization_lock_sha256",
    "authorization_manifest_sha256",
    "azure_destination_sha256",
    "coordination_binding_sha256",
)
values = dict(zip(keys, sys.argv[2:]))
values["baseline_execution_count"] = int(
    values["baseline_execution_count"]
)
pathlib.Path(sys.argv[1]).write_text(
    json.dumps(values, sort_keys=True, separators=(",", ":")) + "\n",
    encoding="ascii",
)
PY
    python "$AZURE_HELPER" create-claim-envelope --kind dispatch \
        --domain-sha256 "$DISPATCH_DOMAIN_SHA256" \
        --claims "$DISPATCH_CLAIM_VALUES_FILE" \
        --output "$DISPATCH_CLAIM_ENVELOPE_FILE"
    RETURNED_DISPATCH_RECORD_NAME="$(scalar python "$AZURE_HELPER" \
        create-txt-record-body --envelope "$DISPATCH_CLAIM_ENVELOPE_FILE" \
        --ttl "$COORDINATION_RECORD_TTL" \
        --output "$DISPATCH_TXT_BODY_FILE" --print-name)"
    if [[ "$RETURNED_DISPATCH_RECORD_NAME" \
        != "$DISPATCH_RECORD_NAME" ]]; then
        echo "[FAIL] Dispatch TXT body escaped its complete claim domain"
        exit 1
    fi
    DISPATCH_CAPABILITY="false"
    DISPATCH_CREATE_STATUS="transport-ambiguous"
    if status="$(raw_arm_request_once PUT "$DISPATCH_RECORD_URL" \
        "$DISPATCH_TXT_BODY_FILE" "$DISPATCH_TXT_CREATE_RESPONSE_FILE" true)"; then
        DISPATCH_CREATE_STATUS="$status"
    fi
    if [[ "$DISPATCH_CREATE_STATUS" == "201" ]]; then
        python "$AZURE_HELPER" validate-txt-record \
            --record "$DISPATCH_TXT_CREATE_RESPONSE_FILE" \
            --zone-resource-id "$COORDINATION_ZONE_RESOURCE_ID" \
            --record-name "$DISPATCH_RECORD_NAME" \
            --ttl "$COORDINATION_RECORD_TTL" \
            --expected-envelope "$DISPATCH_CLAIM_ENVELOPE_FILE" \
            --output "$SCRATCH_DIR/dispatch_txt_create_evidence.json"
        az rest --method get --url "$DISPATCH_RECORD_URL" \
            --output json >"$DISPATCH_TXT_LIVE_FILE"
        python "$AZURE_HELPER" validate-txt-record \
            --record "$DISPATCH_TXT_LIVE_FILE" \
            --zone-resource-id "$COORDINATION_ZONE_RESOURCE_ID" \
            --record-name "$DISPATCH_RECORD_NAME" \
            --ttl "$COORDINATION_RECORD_TTL" \
            --expected-envelope "$DISPATCH_CLAIM_ENVELOPE_FILE" \
            --output "$DISPATCH_TXT_EVIDENCE_FILE"
        if ! cmp -s "$SCRATCH_DIR/dispatch_txt_create_evidence.json" \
            "$DISPATCH_TXT_EVIDENCE_FILE"; then
            echo "[FAIL] Created/re-GET dispatch TXT evidence differs"
            exit 1
        fi
        DISPATCH_CAPABILITY="dns-create-201:${DISPATCH_NONCE}:${DISPATCH_DOMAIN_SHA256}"
    else
        if ! authenticate_dispatch_txt_record; then
            echo "[FAIL] Dispatch TXT ambiguity has no authenticated claim"
            exit 1
        fi
        validate_dispatch_claim_static_bindings || exit 1
        echo "[INFO] Dispatch TXT create returned ${DISPATCH_CREATE_STATUS}; GET cannot mint start capability"
    fi

    if [[ "$DISPATCH_CAPABILITY" == \
        "dns-create-201:${DISPATCH_NONCE}:${DISPATCH_DOMAIN_SHA256}" ]]; then
        printf '{}\n' >"$SCRATCH_DIR/start_body.json"
        reauthenticate_runtime_destination || exit 1
        authenticate_current_persisted_state || exit 1
        if [[ "$AUTHENTICATED_STATE_RECEIPT_SHA256" \
            != "$CLAIM_STATE_RECEIPT_SHA256" ]]; then
            echo "[FAIL] Persisted state changed before ACA start"
            exit 1
        fi
        if ! authenticate_exact_execution_baseline; then
            echo "[INFO] Execution appeared before ACA start; dispatch capability is consumed without starting"
        else
            az rest --method get --url "$JOB_URL" \
                --output json >"$LIVE_JOB_FILE"
            python "$AZURE_HELPER" validate-live-job-projection \
                --live "$LIVE_JOB_FILE" --expected-job-resource-id "$JOB_ID" \
                --expected-job-name "$JOB_NAME" \
                --expected-sha256 "$CLAIM_JOB_PROJECTION_SHA256" \
                --output "$LIVE_PROJECTION_FILE" >/dev/null
            verify_immutable_launch_inputs || exit 1
            START_STATUS="transport-ambiguous"
            if status="$(raw_arm_request_once POST \
                "https://management.azure.com${JOB_ID}/start?api-version=2024-03-01" \
                "$SCRATCH_DIR/start_body.json" "$START_RESPONSE_FILE" false)"; then
                START_STATUS="$status"
            fi
            echo "[INFO] Sole ACA start result: ${START_STATUS}; only execution GET/list adoption follows"
        fi
    fi

    for _ in $(seq 1 120); do
        python "$AZURE_HELPER" arm-list \
            --url "$EXECUTIONS_URL" --output "$EXECUTIONS_FILE"
        if python "$AZURE_HELPER" adopt-remove-one \
            --baseline "$PRIOR_EXECUTION_NAMES_FILE" \
            --executions "$EXECUTIONS_FILE" \
            --output "$ADOPTED_EXECUTION_FILE" 2>/dev/null; then
            EXECUTION_NAME="$(scalar python "$AZURE_HELPER" get \
                --json "$ADOPTED_EXECUTION_FILE" --field execution_name)"
            break
        fi
        sleep 5
    done
    if [[ -z "$EXECUTION_NAME" ]]; then
        echo "[FAIL] Dispatch is permanently stranded; start must never be retried"
        exit 1
    fi
fi

az rest --method get --url "$JOB_URL" --output json >"$LIVE_JOB_FILE"
python "$AZURE_HELPER" validate-live-job-projection \
    --live "$LIVE_JOB_FILE" --expected-job-resource-id "$JOB_ID" \
    --expected-job-name "$JOB_NAME" \
    --expected-sha256 "$CLAIM_JOB_PROJECTION_SHA256" \
    --output "$LIVE_PROJECTION_FILE" >/dev/null
EXECUTION_URL="https://management.azure.com${JOB_ID}/executions/${EXECUTION_NAME}?api-version=2024-03-01"
EXECUTION_STATUS=""
for _ in $(seq 1 120); do
    EXECUTION_STATUS="$(scalar az rest --method get --url "$EXECUTION_URL" \
        --query properties.status -o tsv)"
    case "$EXECUTION_STATUS" in
        Running|Succeeded|Failed|Stopped|Canceled|Cancelled) break ;;
        "") ;;
        *)
            echo "[FAIL] Durable execution returned an unknown status"
            exit 1
            ;;
    esac
    sleep 5
done
if [[ -z "$EXECUTION_STATUS" ]]; then
    echo "[FAIL] Execution did not become durably queryable"
    exit 1
fi
reauthenticate_runtime_destination || exit 1
verify_immutable_launch_inputs || exit 1

JOB_RECORD="$RECORD_DIR/job_${LAUNCH_RECORD_NAME}.json"
if [[ "$JOB_BODY_SHA256" == "$CLAIM_JOB_BODY_SHA256" ]]; then
    if [[ -f "$JOB_RECORD" ]] && ! cmp -s "$BODY_FILE" "$JOB_RECORD"; then
        echo "[FAIL] Existing immutable Job request record differs"
        exit 1
    elif [[ ! -f "$JOB_RECORD" ]]; then
        cp "$BODY_FILE" "$JOB_RECORD"
    fi
fi
python - "$RECORD_DIR/launch_${LAUNCH_RECORD_NAME}.json" \
    "$LAUNCH_TXT_EVIDENCE_FILE" "$DISPATCH_TXT_EVIDENCE_FILE" \
    "$STAGE" "$EVALUATION_MODE" "$VERIFICATION_STATE" \
    "$AUTHORIZATION_ID" "$EXECUTION_ID" "$EXECUTION_NAME" "$RETRY_KIND" \
    "$IMAGE_DIGEST" "$CONFIG_SHA256" "$IMPLEMENTATION_MANIFEST_SHA256" \
    "$AZURE_DESTINATION_SHA256" "$IMAGE_BINDING_SHA256" \
    "$HELPER_SNAPSHOT_SET_SHA256" "$CLAIM_JOB_BODY_SHA256" \
    "$CLAIM_JOB_PROJECTION_SHA256" \
    "$CLAIM_PRIOR_EXECUTION_NAMES_SHA256" "$EXECUTION_STATUS" <<'PY'
import json
import pathlib
import sys

output, launch_path, dispatch_path = sys.argv[1:4]
keys = (
    "stage",
    "mode",
    "verification_state",
    "authorization_id",
    "execution_id",
    "azure_execution_name",
    "retry_kind",
    "image_digest",
    "config_sha256",
    "implementation_manifest_sha256",
    "azure_destination_sha256",
    "image_binding_sha256",
    "helper_snapshot_set_sha256",
    "job_body_sha256",
    "job_projection_sha256",
    "baseline_execution_membership_sha256",
    "execution_status",
)
record = dict(zip(keys, sys.argv[4:]))
record.update(
    {
        "schema_version": "phase1-parser-v2-eval-launch/v3",
        "launch_txt": json.loads(
            pathlib.Path(launch_path).read_text(encoding="ascii")
        ),
        "dispatch_txt": (
            json.loads(pathlib.Path(dispatch_path).read_text(encoding="ascii"))
            if pathlib.Path(dispatch_path).is_file()
            else None
        ),
        "job_body_immutable": True,
        "job_patch_forbidden": True,
        "automatic_retry": 0,
        "cpu": 2,
        "memory": "4Gi",
        "gpu": False,
    }
)
data = (
    json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
).encode("ascii")
path = pathlib.Path(output)
if path.exists():
    if path.read_bytes() != data:
        raise SystemExit("existing immutable launch record differs")
else:
    path.write_bytes(data)
PY

echo "[OK] Stage $STAGE execution: $EXECUTION_NAME ($EXECUTION_STATUS)"
echo "[OK] DNS launch/dispatch claims; immutable Job; retry=0"
exit 0
