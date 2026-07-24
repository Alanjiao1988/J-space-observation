#!/bin/bash -p
set +x
set +v
# Build once from committed bytes, recover once, and lock the exact ACR digest.

set -euo pipefail

readonly CLEAN_PATH="/usr/local/bin:/usr/bin:/bin"
PATH="$CLEAN_PATH"
GIT_NO_REPLACE_OBJECTS=1
export PATH GIT_NO_REPLACE_OBJECTS
environment_is_clean=true
if [[ "${JSPACE_PV2_BUILD_CLEAN_REEXEC:-}" != "1" \
    || -n "$(builtin compgen -A function)" ]]; then
    environment_is_clean=false
fi
while IFS= builtin read -r -d '' environment_entry; do
    environment_name="${environment_entry%%=*}"
    case "$environment_name" in
        HOME|LANG|LC_ALL|PATH|PWD|SHLVL|_|MSYSTEM|SYSTEMROOT|WINDIR|\
        AZURE_CONFIG_DIR|GIT_NO_REPLACE_OBJECTS|\
        RESOURCE_GROUP|ACR_NAME|SOURCE_SHA|PARSER_EVAL_BASE_IMAGE|\
        PARSER_EVAL_BUILD_RECORD_DIR|JSPACE_PV2_BUILD_CLEAN_REEXEC|\
        JSPACE_PV2_BUILD_VERIFIED_REEXEC|JSPACE_PV2_BUILD_PROJECT_ROOT|\
        JSPACE_PV2_BUILD_SNAPSHOT_DIR|\
        PARSER_EVAL_COORDINATION_ZONE_NAME|\
        PARSER_EVAL_COORDINATION_ZONE_RESOURCE_ID|\
        PARSER_EVAL_COORDINATION_ZONE_INTERNAL_ID|\
        PARSER_EVAL_COORDINATION_ZONE_LOCATION|\
        PARSER_EVAL_COORDINATION_PRIVATE_DNS_API_VERSION|\
        PARSER_EVAL_COORDINATION_RECORD_TTL|\
        PARSER_EVAL_COORDINATION_EXPECTED_VNET_LINK_COUNT|\
        PARSER_EVAL_COORDINATION_LOCK_NAME|\
        PARSER_EVAL_COORDINATION_LOCK_RESOURCE_ID|\
        PARSER_EVAL_COORDINATION_LOCK_LEVEL|\
        PARSER_EVAL_COORDINATION_LOCK_API_VERSION) ;;
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
        "JSPACE_PV2_BUILD_CLEAN_REEXEC=1"
    )
    for name in \
        AZURE_CONFIG_DIR RESOURCE_GROUP ACR_NAME SOURCE_SHA \
        PARSER_EVAL_BASE_IMAGE PARSER_EVAL_BUILD_RECORD_DIR \
        JSPACE_PV2_BUILD_VERIFIED_REEXEC JSPACE_PV2_BUILD_PROJECT_ROOT \
        JSPACE_PV2_BUILD_SNAPSHOT_DIR \
        PARSER_EVAL_COORDINATION_ZONE_NAME \
        PARSER_EVAL_COORDINATION_ZONE_RESOURCE_ID \
        PARSER_EVAL_COORDINATION_ZONE_INTERNAL_ID \
        PARSER_EVAL_COORDINATION_ZONE_LOCATION \
        PARSER_EVAL_COORDINATION_PRIVATE_DNS_API_VERSION \
        PARSER_EVAL_COORDINATION_RECORD_TTL \
        PARSER_EVAL_COORDINATION_EXPECTED_VNET_LINK_COUNT \
        PARSER_EVAL_COORDINATION_LOCK_NAME \
        PARSER_EVAL_COORDINATION_LOCK_RESOURCE_ID \
        PARSER_EVAL_COORDINATION_LOCK_LEVEL \
        PARSER_EVAL_COORDINATION_LOCK_API_VERSION; do
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
if [[ "${JSPACE_PV2_BUILD_VERIFIED_REEXEC:-}" == "1" ]]; then
    PROJECT_ROOT="${JSPACE_PV2_BUILD_PROJECT_ROOT:?Verified build root is missing}"
    BUILD_SNAPSHOT_DIR="${JSPACE_PV2_BUILD_SNAPSHOT_DIR:?Verified build snapshot is missing}"
    SNAPSHOT_SOURCE_ROOT="$BUILD_SNAPSHOT_DIR/sources"
    expected_build_script="$SNAPSHOT_SOURCE_ROOT/infra/azure/scripts/09_build_parser_v2_eval.sh"
    current_build_script="$SCRIPT_DIR/$(basename "${BASH_SOURCE[0]}")"
    git_private_root="$(git -C "$PROJECT_ROOT" rev-parse --absolute-git-dir)"
    if [[ "$current_build_script" != "$expected_build_script" \
        || "$(cd "$(dirname "$BUILD_SNAPSHOT_DIR")" && pwd -P)" \
            != "$(cd "$git_private_root" && pwd -P)" \
        || ! "$(basename "$BUILD_SNAPSHOT_DIR")" \
            =~ ^parser-v2-build-inputs-[0-9a-f]{32}$ ]]; then
        echo "[FAIL] Verified build helper snapshot path is invalid"
        exit 1
    fi
else
    PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../" && pwd)"
    BUILD_SNAPSHOT_DIR=""
    SNAPSHOT_SOURCE_ROOT=""
fi
SCRATCH_DIR=""
cleanup() {
    if [[ -n "$SCRATCH_DIR" ]]; then
        rm -rf -- "$SCRATCH_DIR"
    fi
    if [[ -n "$BUILD_SNAPSHOT_DIR" ]]; then
        chmod -R u+w "$BUILD_SNAPSHOT_DIR" 2>/dev/null || true
        rm -rf -- "$BUILD_SNAPSHOT_DIR"
    fi
}
trap cleanup EXIT
HELPER_ROOT="${SNAPSHOT_SOURCE_ROOT:-$PROJECT_ROOT}"
AZURE_HELPER="$HELPER_ROOT/scripts/parser_v2_azure_contract.py"
RESOURCE_GROUP="${RESOURCE_GROUP:-rg-jspace-observation-sea}"
ACR_NAME="${ACR_NAME:?Set ACR_NAME to the existing private registry name}"
COORDINATION_ZONE_NAME="${PARSER_EVAL_COORDINATION_ZONE_NAME:?Set PARSER_EVAL_COORDINATION_ZONE_NAME to the dedicated unlinked coordination zone}"
COORDINATION_ZONE_RESOURCE_ID="${PARSER_EVAL_COORDINATION_ZONE_RESOURCE_ID:?Set PARSER_EVAL_COORDINATION_ZONE_RESOURCE_ID}"
COORDINATION_ZONE_INTERNAL_ID="${PARSER_EVAL_COORDINATION_ZONE_INTERNAL_ID:?Set PARSER_EVAL_COORDINATION_ZONE_INTERNAL_ID}"
COORDINATION_ZONE_LOCATION="${PARSER_EVAL_COORDINATION_ZONE_LOCATION:-global}"
COORDINATION_DNS_API_VERSION="${PARSER_EVAL_COORDINATION_PRIVATE_DNS_API_VERSION:-2024-06-01}"
COORDINATION_RECORD_TTL="${PARSER_EVAL_COORDINATION_RECORD_TTL:-300}"
COORDINATION_EXPECTED_LINK_COUNT="${PARSER_EVAL_COORDINATION_EXPECTED_VNET_LINK_COUNT:-0}"
COORDINATION_LOCK_NAME="${PARSER_EVAL_COORDINATION_LOCK_NAME:?Set PARSER_EVAL_COORDINATION_LOCK_NAME}"
COORDINATION_LOCK_RESOURCE_ID="${PARSER_EVAL_COORDINATION_LOCK_RESOURCE_ID:?Set PARSER_EVAL_COORDINATION_LOCK_RESOURCE_ID}"
COORDINATION_LOCK_LEVEL="${PARSER_EVAL_COORDINATION_LOCK_LEVEL:-CanNotDelete}"
COORDINATION_LOCK_API_VERSION="${PARSER_EVAL_COORDINATION_LOCK_API_VERSION:-2016-09-01}"
SOURCE_SHA="${SOURCE_SHA:-$(git -C "$PROJECT_ROOT" rev-parse HEAD | tr -d '\r')}"
IMAGE_REPOSITORY="j-space-observation-parser-eval"
BUILD_PROVENANCE_LABEL="org.opencontainers.image.build-provenance-sha256"
PINNED_BASE_IMAGE="python:3.11.14-slim-bookworm@sha256:65a93d69fa75478d554f4ad27c85c1e69fa184956261b4301ebaf6dbb0a3543d"
APPROVED_ORIGIN_URL="https://github.com/Alanjiao1988/J-space-observation.git"
BASE_IMAGE="$PINNED_BASE_IMAGE"
FINAL_TAG="$SOURCE_SHA"
SNAPSHOT_INPUTS=(
    ".dockerignore"
    ".gitattributes"
    "Dockerfile.parser-v2-eval"
    "requirements-parser-v2-eval.txt"
    "infra/azure/scripts/09_build_parser_v2_eval.sh"
    "infra/azure/scripts/10_run_parser_v2_locked_eval.sh"
    "scripts/create_parser_v2_runtime_config.py"
    "scripts/bootstrap_parser_v2_locked_evaluation.py"
    "scripts/parser_v2_azure_contract.py"
    "scripts/parser_v2_process_worker.py"
    "scripts/run_parser_v2_locked_predictions.py"
    "scripts/finalize_parser_v2_locked_evaluation.py"
    "scripts/stage_p_entrypoint.sh"
    "scripts/stage_p_adopt_entrypoint.sh"
    "scripts/stage_e_entrypoint.sh"
    "src/jspace_observation/evaluator_validation.py"
    "src/jspace_observation/eval_parsing.py"
    "src/jspace_observation/eval_parsing_v2.py"
    "src/jspace_observation/parser_v2_locked_evaluation.py"
    "docs/phase1_parser_v2_protocol.md"
    "docs/phase1_evaluator_validation_set.md"
    "docs/phase1_parser_v2_acceptance_gates.json"
)
if [[ ! "$SOURCE_SHA" =~ ^[0-9a-f]{40}$ \
    || ! "$ACR_NAME" =~ ^[a-z0-9]{5,50}$ \
    || ! "$RESOURCE_GROUP" =~ ^[A-Za-z0-9._()-]{1,90}$ \
    || ! "$COORDINATION_ZONE_NAME" \
        =~ ^([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?[.])+[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$ \
    || "$COORDINATION_ZONE_LOCATION" != "global" \
    || "$COORDINATION_DNS_API_VERSION" != "2024-06-01" \
    || ! "$COORDINATION_RECORD_TTL" =~ ^[0-9]+$ \
    || "$COORDINATION_RECORD_TTL" -lt 60 \
    || "$COORDINATION_RECORD_TTL" -gt 3600 \
    || "$COORDINATION_EXPECTED_LINK_COUNT" != "0" \
    || "$COORDINATION_LOCK_LEVEL" != "CanNotDelete" \
    || "$COORDINATION_LOCK_API_VERSION" != "2016-09-01" \
    || "$BASE_IMAGE" != "$PINNED_BASE_IMAGE" \
    || ! "$BASE_IMAGE" =~ @sha256:[0-9a-f]{64}$ ]]; then
    echo "[FAIL] Build source or fixed infrastructure identity is malformed"
    exit 1
fi
PRE_SNAPSHOT_ORIGIN_URL="$(
    git -C "$PROJECT_ROOT" remote get-url origin | tr -d '\r'
)"
if [[ "$PRE_SNAPSHOT_ORIGIN_URL" != "$APPROVED_ORIGIN_URL" ]]; then
    echo "[FAIL] Refusing to contact an unapproved Git remote"
    exit 1
fi
git -C "$PROJECT_ROOT" fetch --quiet --no-tags \
    "$APPROVED_ORIGIN_URL" \
    "+refs/heads/main:refs/remotes/origin/main"
PRE_SNAPSHOT_HEAD="$(git -C "$PROJECT_ROOT" rev-parse HEAD | tr -d '\r')"
PRE_SNAPSHOT_ORIGIN_MAIN="$(
    git -C "$PROJECT_ROOT" rev-parse refs/remotes/origin/main | tr -d '\r'
)"
PRE_SNAPSHOT_WORKTREE="$(
    git -C "$PROJECT_ROOT" status --porcelain=v1 --untracked-files=all \
        | tr -d '\r'
)"
if [[ -n "$PRE_SNAPSHOT_WORKTREE" \
    || "$PRE_SNAPSHOT_HEAD" != "$SOURCE_SHA" \
    || "$PRE_SNAPSHOT_ORIGIN_MAIN" != "$SOURCE_SHA" \
    || "$PRE_SNAPSHOT_ORIGIN_URL" != "$APPROVED_ORIGIN_URL" ]]; then
    echo "[FAIL] Refusing to read or execute an unauthenticated source commit"
    exit 1
fi
if [[ "${JSPACE_PV2_BUILD_VERIFIED_REEXEC:-}" != "1" ]]; then
    snapshot_nonce="$(python -c 'import secrets; print(secrets.token_hex(16))')"
    git_private_root="$(git -C "$PROJECT_ROOT" rev-parse --absolute-git-dir)"
    BUILD_SNAPSHOT_DIR="$git_private_root/parser-v2-build-inputs-${snapshot_nonce}"
    SNAPSHOT_SOURCE_ROOT="$BUILD_SNAPSHOT_DIR/sources"
    mkdir -m 0700 "$BUILD_SNAPSHOT_DIR"
    python - "$PROJECT_ROOT" "$SOURCE_SHA" "$SNAPSHOT_SOURCE_ROOT" \
        "${SNAPSHOT_INPUTS[@]}" <<'PY'
import hashlib
import os
import pathlib
import subprocess
import sys

root = pathlib.Path(sys.argv[1]).resolve()
commit = sys.argv[2]
destination = pathlib.Path(sys.argv[3])
paths = sys.argv[4:]
destination.mkdir(mode=0o700)
for relative in paths:
    if pathlib.PurePosixPath(relative).is_absolute() or ".." in pathlib.PurePosixPath(relative).parts:
        raise SystemExit("registered build snapshot path is invalid")
    oid = subprocess.run(
        ["git", "-C", str(root), "rev-parse", f"{commit}:{relative}"],
        check=True,
        capture_output=True,
    ).stdout.decode("ascii").replace("\r", "").strip()
    data = subprocess.run(
        ["git", "-C", str(root), "cat-file", "blob", oid],
        check=True,
        capture_output=True,
    ).stdout
    if subprocess.run(
        ["git", "-C", str(root), "hash-object", "--stdin"],
        input=data,
        check=True,
        capture_output=True,
    ).stdout.decode("ascii").strip() != oid:
        raise SystemExit("registered build snapshot Git blob mismatch")
    target = destination.joinpath(*pathlib.PurePosixPath(relative).parts)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(data)
for directory in sorted(
    (item for item in destination.rglob("*") if item.is_dir()),
    key=lambda item: len(item.parts),
    reverse=True,
):
    directory.chmod(0o500)
destination.chmod(0o500)
PY
    snapshot_build_script="$SNAPSHOT_SOURCE_ROOT/infra/azure/scripts/09_build_parser_v2_eval.sh"
    build_snapshot_environment=(
        "HOME=${HOME:-/nonexistent}"
        "LANG=C.UTF-8"
        "LC_ALL=C.UTF-8"
        "PATH=$CLEAN_PATH"
        "GIT_NO_REPLACE_OBJECTS=1"
        "JSPACE_PV2_BUILD_CLEAN_REEXEC=1"
        "JSPACE_PV2_BUILD_VERIFIED_REEXEC=1"
        "JSPACE_PV2_BUILD_PROJECT_ROOT=$PROJECT_ROOT"
        "JSPACE_PV2_BUILD_SNAPSHOT_DIR=$BUILD_SNAPSHOT_DIR"
        "RESOURCE_GROUP=$RESOURCE_GROUP"
        "ACR_NAME=$ACR_NAME"
        "SOURCE_SHA=$SOURCE_SHA"
    )
    for name in \
        AZURE_CONFIG_DIR PARSER_EVAL_BASE_IMAGE \
        PARSER_EVAL_BUILD_RECORD_DIR \
        PARSER_EVAL_COORDINATION_ZONE_NAME \
        PARSER_EVAL_COORDINATION_ZONE_RESOURCE_ID \
        PARSER_EVAL_COORDINATION_ZONE_INTERNAL_ID \
        PARSER_EVAL_COORDINATION_ZONE_LOCATION \
        PARSER_EVAL_COORDINATION_PRIVATE_DNS_API_VERSION \
        PARSER_EVAL_COORDINATION_RECORD_TTL \
        PARSER_EVAL_COORDINATION_EXPECTED_VNET_LINK_COUNT \
        PARSER_EVAL_COORDINATION_LOCK_NAME \
        PARSER_EVAL_COORDINATION_LOCK_RESOURCE_ID \
        PARSER_EVAL_COORDINATION_LOCK_LEVEL \
        PARSER_EVAL_COORDINATION_LOCK_API_VERSION; do
        if [[ -v "$name" ]]; then
            build_snapshot_environment+=("$name=${!name}")
        fi
    done
    builtin exec /usr/bin/env -i "${build_snapshot_environment[@]}" \
        /bin/bash --noprofile --norc -p "$snapshot_build_script"
fi
python - "$PROJECT_ROOT" "$SOURCE_SHA" "$SNAPSHOT_SOURCE_ROOT" \
    "${SNAPSHOT_INPUTS[@]}" <<'PY'
import hashlib
import pathlib
import stat
import subprocess
import sys

root = pathlib.Path(sys.argv[1]).resolve()
commit = sys.argv[2]
snapshot_root = pathlib.Path(sys.argv[3]).resolve()
for relative in sys.argv[4:]:
    oid = subprocess.run(
        ["git", "-C", str(root), "rev-parse", f"{commit}:{relative}"],
        check=True,
        capture_output=True,
    ).stdout.decode("ascii").replace("\r", "").strip()
    committed = subprocess.run(
        ["git", "-C", str(root), "cat-file", "blob", oid],
        check=True,
        capture_output=True,
    ).stdout
    path = snapshot_root.joinpath(*pathlib.PurePosixPath(relative).parts)
    state = path.lstat()
    snapshot = path.read_bytes()
    if (
        not stat.S_ISREG(state.st_mode)
        or stat.S_ISLNK(state.st_mode)
        or snapshot != committed
        or hashlib.sha256(snapshot).digest() != hashlib.sha256(committed).digest()
    ):
        raise SystemExit("verified build helper differs from its Git blob")
PY
INVOCATION_ID="$(python "$AZURE_HELPER" new-id | tr -d '\r')"
STAGING_TAG=""
RECORD_DIR="${PARSER_EVAL_BUILD_RECORD_DIR:-$PROJECT_ROOT/results/runs/parser-v2-eval-build-${SOURCE_SHA}}"

scalar() {
    local value
    if ! value="$("$@" | tr -d '\r')"; then
        return 1
    fi
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
    if [[ "$method" != "PUT" || "$url" != https://management.azure.com/* \
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

if [[ -n "${PARSER_EVAL_BASE_IMAGE:-}" \
    && "$PARSER_EVAL_BASE_IMAGE" != "$PINNED_BASE_IMAGE" ]]; then
    echo "[FAIL] PARSER_EVAL_BASE_IMAGE differs from the repository pin"
    exit 1
fi
if [[ ! "$SOURCE_SHA" =~ ^[0-9a-f]{40}$ \
    || ! "$INVOCATION_ID" =~ ^[0-9a-f]{32}$ \
    || ! "$ACR_NAME" =~ ^[a-z0-9]{5,50}$ \
    || ! "$RESOURCE_GROUP" =~ ^[A-Za-z0-9._()-]{1,90}$ ]]; then
    echo "[FAIL] Source or invocation identity is malformed"
    exit 1
fi
if [[ "$BASE_IMAGE" != "$PINNED_BASE_IMAGE" \
    || ! "$BASE_IMAGE" =~ @sha256:[0-9a-f]{64}$ ]]; then
    echo "[FAIL] The one approved base image binding changed"
    exit 1
fi

HEAD_SHA="$(scalar git -C "$PROJECT_ROOT" rev-parse HEAD)"
ORIGIN_MAIN_SHA="$(scalar git -C "$PROJECT_ROOT" rev-parse refs/remotes/origin/main)"
ORIGIN_URL="$(scalar git -C "$PROJECT_ROOT" remote get-url origin)"
WORKTREE_STATUS="$(git -C "$PROJECT_ROOT" status --porcelain=v1 --untracked-files=all | tr -d '\r')"
if [[ -n "$WORKTREE_STATUS" \
    || "$HEAD_SHA" != "$SOURCE_SHA" \
    || "$ORIGIN_MAIN_SHA" != "$SOURCE_SHA" \
    || "$ORIGIN_URL" != "$APPROVED_ORIGIN_URL" ]]; then
    echo "[FAIL] Build requires the registered origin and clean HEAD == SOURCE_SHA == origin/main"
    exit 1
fi
REMOTE_SOURCE_LOCATION="$(scalar python "$AZURE_HELPER" exact-remote-source \
    --repository-url "$ORIGIN_URL" --source-commit "$SOURCE_SHA")"
if [[ "$REMOTE_SOURCE_LOCATION" \
    != "${APPROVED_ORIGIN_URL}#${SOURCE_SHA}" ]]; then
    echo "[FAIL] Exact remote Git source binding is invalid"
    exit 1
fi

BUILD_INPUTS=(
    ".dockerignore"
    ".gitattributes"
    "Dockerfile.parser-v2-eval"
    "requirements-parser-v2-eval.txt"
    "infra/azure/scripts/09_build_parser_v2_eval.sh"
    "infra/azure/scripts/10_run_parser_v2_locked_eval.sh"
    "scripts/create_parser_v2_runtime_config.py"
    "scripts/bootstrap_parser_v2_locked_evaluation.py"
    "scripts/parser_v2_azure_contract.py"
    "scripts/parser_v2_process_worker.py"
    "scripts/run_parser_v2_locked_predictions.py"
    "scripts/finalize_parser_v2_locked_evaluation.py"
    "scripts/stage_p_entrypoint.sh"
    "scripts/stage_p_adopt_entrypoint.sh"
    "scripts/stage_e_entrypoint.sh"
    "src/jspace_observation/evaluator_validation.py"
    "src/jspace_observation/eval_parsing.py"
    "src/jspace_observation/eval_parsing_v2.py"
    "src/jspace_observation/parser_v2_locked_evaluation.py"
    "docs/phase1_parser_v2_protocol.md"
    "docs/phase1_evaluator_validation_set.md"
    "docs/phase1_parser_v2_acceptance_gates.json"
)
if [[ "${BUILD_INPUTS[*]}" != "${SNAPSHOT_INPUTS[*]}" ]]; then
    echo "[FAIL] Verified build snapshot membership is not exact"
    exit 1
fi
for input in "${BUILD_INPUTS[@]}"; do
    if ! git -C "$PROJECT_ROOT" ls-files --error-unmatch -- "$input" >/dev/null \
        || git -C "$PROJECT_ROOT" check-ignore -q -- "$input"; then
        echo "[FAIL] Every build input must be tracked and non-ignored"
        exit 1
    fi
done
for script in \
    "infra/azure/scripts/09_build_parser_v2_eval.sh" \
    "infra/azure/scripts/10_run_parser_v2_locked_eval.sh" \
    "scripts/stage_p_entrypoint.sh" \
    "scripts/stage_p_adopt_entrypoint.sh" \
    "scripts/stage_e_entrypoint.sh"; do
    if [[ "$(scalar git -C "$PROJECT_ROOT" check-attr eol -- "$script")" \
        != "$script: eol: lf" ]]; then
        echo "[FAIL] Every runtime shell script must be committed as LF"
        exit 1
    fi
done

mkdir -p "$RECORD_DIR"
SCRATCH_DIR="$RECORD_DIR/build-${INVOCATION_ID}"
umask 077
mkdir "$SCRATCH_DIR"
SOURCE_BINDING_FILE="$SCRATCH_DIR/source_binding.json"
CONTEXT_DIR="$SCRATCH_DIR/context"
COORDINATION_BINDING_FILE="$SCRATCH_DIR/coordination_binding.json"
COORDINATION_ZONE_FILE="$SCRATCH_DIR/coordination_zone.json"
COORDINATION_LINKS_FILE="$SCRATCH_DIR/coordination_links.json"
COORDINATION_LOCK_FILE="$SCRATCH_DIR/coordination_lock.json"
COORDINATION_VALIDATION_FILE="$SCRATCH_DIR/coordination_validation.json"
BUILD_DOMAIN_BINDING_FILE="$SCRATCH_DIR/build_domain_binding.json"
BUILD_CLAIM_VALUES_FILE="$SCRATCH_DIR/build_claim_values.json"
BUILD_CLAIM_ENVELOPE_FILE="$SCRATCH_DIR/build_claim_envelope.json"
BUILD_TXT_BODY_FILE="$SCRATCH_DIR/build_txt_body.json"
BUILD_TXT_CREATE_RESPONSE_FILE="$SCRATCH_DIR/build_txt_create_response.json"
BUILD_TXT_LIVE_FILE="$SCRATCH_DIR/build_txt_live.json"
BUILD_TXT_EVIDENCE_FILE="$SCRATCH_DIR/build_txt_evidence.json"
BUILD_PROVENANCE_SCRATCH="$SCRATCH_DIR/build_provenance.json"
BUILD_PROVENANCE_FILE="$RECORD_DIR/build_provenance.json"
TASK_RUN_BODY="$SCRATCH_DIR/acr_task_run_body.json"
TASK_RUN_FILE="$SCRATCH_DIR/acr_task_run.json"
TASK_RUN_RESPONSE_BODY="$SCRATCH_DIR/acr_task_run_response.json"
TASK_RUN_PRE_PUT_GET_FILE="$SCRATCH_DIR/acr_task_run_pre_put_get.json"
TASK_RUN_VALIDATION_FILE="$SCRATCH_DIR/acr_task_run_validation.json"
OCI_VALIDATION_FILE="$SCRATCH_DIR/oci_validation.json"
OCI_REVALIDATION_FILE="$SCRATCH_DIR/oci_revalidation.json"
IMAGE_BINDING_FILE="$RECORD_DIR/image_binding.json"
IMAGE_BINDING_SHA256_FILE="$RECORD_DIR/image_binding.sha256"
IMAGE_BINDING_VALIDATION_FILE="$SCRATCH_DIR/image_binding_validation.json"

python - "$PROJECT_ROOT" "$SOURCE_SHA" "$BASE_IMAGE" \
    "$IMAGE_REPOSITORY" "$ORIGIN_URL" "$REMOTE_SOURCE_LOCATION" \
    "$SOURCE_BINDING_FILE" "${BUILD_INPUTS[@]}" <<'PY'
import hashlib
import json
import pathlib
import subprocess
import sys

root = pathlib.Path(sys.argv[1])
commit, base_image, repository = sys.argv[2:5]
repository_url, remote_source_location = sys.argv[5:7]
output = pathlib.Path(sys.argv[7])
paths = sys.argv[8:]
files = {}
for path in paths:
    oid_result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", f"{commit}:{path}"],
        check=True,
        capture_output=True,
    )
    oid = oid_result.stdout.decode("ascii").replace("\r", "").strip()
    if "\n" in oid:
        raise SystemExit("Git blob ID is not scalar")
    data = subprocess.run(
        ["git", "-C", str(root), "cat-file", "blob", oid],
        check=True,
        capture_output=True,
    ).stdout
    files[path] = {
        "git_blob_oid": oid,
        "sha256": hashlib.sha256(data).hexdigest(),
        "size": len(data),
    }
record = {
    "schema_version": "phase1-parser-v2-build-source-binding/v2",
    "source_commit": commit,
    "source_repository_url": repository_url,
    "remote_source_location": remote_source_location,
    "base_image": base_image,
    "image_repository": repository,
    "files": files,
}
output.write_bytes(
    (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode()
)
PY
SOURCE_BINDING_SHA256="$(scalar sha256sum "$SOURCE_BINDING_FILE")"
SOURCE_BINDING_SHA256="${SOURCE_BINDING_SHA256%% *}"
if [[ ! "$SOURCE_BINDING_SHA256" =~ ^[0-9a-f]{64}$ ]]; then
    echo "[FAIL] Build source binding hash is malformed"
    exit 1
fi

SUBSCRIPTION_ID="$(scalar az account show --query id -o tsv)"
LOGIN_SERVER="$(scalar az acr show \
    --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" \
    --query loginServer -o tsv)"
ACR_ID="$(scalar az acr show \
    --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" --query id -o tsv)"
ACR_LOCATION="$(scalar az acr show \
    --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" \
    --query location -o tsv)"
if [[ ! "$SUBSCRIPTION_ID" =~ ^[0-9a-fA-F-]{36}$ \
    || "$LOGIN_SERVER" != "${ACR_NAME}.azurecr.io" \
    || ! "$ACR_LOCATION" =~ ^[a-z0-9][a-z0-9-]{0,62}$ \
    || "${ACR_ID,,}" != "/subscriptions/${SUBSCRIPTION_ID,,}/resourcegroups/${RESOURCE_GROUP,,}/providers/microsoft.containerregistry/registries/${ACR_NAME}" ]]; then
    echo "[FAIL] Exact ACR destination binding is invalid"
    exit 1
fi
ACR_ID="${ACR_ID,,}"

python - "$COORDINATION_BINDING_FILE" \
    "$COORDINATION_ZONE_NAME" "$COORDINATION_ZONE_RESOURCE_ID" \
    "$COORDINATION_ZONE_LOCATION" "$COORDINATION_ZONE_INTERNAL_ID" \
    "$COORDINATION_DNS_API_VERSION" "$COORDINATION_RECORD_TTL" \
    "$COORDINATION_EXPECTED_LINK_COUNT" "$COORDINATION_LOCK_NAME" \
    "$COORDINATION_LOCK_RESOURCE_ID" "$COORDINATION_LOCK_LEVEL" \
    "$COORDINATION_LOCK_API_VERSION" <<'PY'
import json
import pathlib
import sys

(
    output,
    zone_name,
    zone_resource_id,
    zone_location,
    zone_internal_id,
    dns_api_version,
    record_ttl,
    expected_link_count,
    lock_name,
    lock_resource_id,
    lock_level,
    lock_api_version,
) = sys.argv[1:]
record = {
    "schema_version": "phase1-parser-v2-dns-coordination/v1",
    "zone_name": zone_name,
    "zone_resource_id": zone_resource_id,
    "zone_location": zone_location,
    "zone_internal_id": zone_internal_id,
    "private_dns_api_version": dns_api_version,
    "record_ttl": int(record_ttl),
    "expected_vnet_link_count": int(expected_link_count),
    "lock_name": lock_name,
    "lock_resource_id": lock_resource_id,
    "lock_level": lock_level,
    "management_lock_api_version": lock_api_version,
}
pathlib.Path(output).write_text(
    json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n",
    encoding="ascii",
)
PY
COORDINATION_ZONE_URL="https://management.azure.com${COORDINATION_ZONE_RESOURCE_ID}?api-version=${COORDINATION_DNS_API_VERSION}"
COORDINATION_LINKS_URL="https://management.azure.com${COORDINATION_ZONE_RESOURCE_ID}/virtualNetworkLinks?api-version=${COORDINATION_DNS_API_VERSION}"
COORDINATION_LOCK_URL="https://management.azure.com${COORDINATION_LOCK_RESOURCE_ID}?api-version=${COORDINATION_LOCK_API_VERSION}"
authenticate_coordination_zone() {
    local authenticated_sha256
    : >"$COORDINATION_ZONE_FILE"
    : >"$COORDINATION_LINKS_FILE"
    : >"$COORDINATION_LOCK_FILE"
    : >"$COORDINATION_VALIDATION_FILE"
    az rest --method get --url "$COORDINATION_ZONE_URL" \
        --output json >"$COORDINATION_ZONE_FILE" || return 1
    python "$AZURE_HELPER" arm-list --url "$COORDINATION_LINKS_URL" \
        --output "$COORDINATION_LINKS_FILE" || return 1
    az rest --method get --url "$COORDINATION_LOCK_URL" \
        --output json >"$COORDINATION_LOCK_FILE" || return 1
    authenticated_sha256="$(scalar python "$AZURE_HELPER" \
        validate-coordination-zone \
        --binding "$COORDINATION_BINDING_FILE" \
        --zone "$COORDINATION_ZONE_FILE" --links "$COORDINATION_LINKS_FILE" \
        --lock "$COORDINATION_LOCK_FILE" \
        --output "$COORDINATION_VALIDATION_FILE")" || return 1
    printf '%s' "$authenticated_sha256"
}
if ! COORDINATION_BINDING_SHA256="$(authenticate_coordination_zone)"; then
    echo "[FAIL] Dedicated coordination zone validation failed"
    exit 1
fi
if [[ ! "$COORDINATION_BINDING_SHA256" =~ ^[0-9a-f]{64}$ ]]; then
    echo "[FAIL] Dedicated coordination zone validation failed"
    exit 1
fi

BUILD_PROVENANCE_SHA256="$(scalar python "$AZURE_HELPER" build-provenance \
    --source-binding "$SOURCE_BINDING_FILE" \
    --acr-resource-id "$ACR_ID" \
    --login-server "$LOGIN_SERVER" \
    --acr-location "$ACR_LOCATION" \
    --coordination-binding "$COORDINATION_BINDING_FILE" \
    --output "$BUILD_PROVENANCE_SCRATCH")"
if [[ ! "$BUILD_PROVENANCE_SHA256" =~ ^[0-9a-f]{64}$ ]]; then
    echo "[FAIL] Canonical build provenance hash is malformed"
    exit 1
fi
if [[ "$(scalar python "$AZURE_HELPER" get \
        --json "$BUILD_PROVENANCE_SCRATCH" \
        --field source_binding_sha256)" != "$SOURCE_BINDING_SHA256" ]]; then
    echo "[FAIL] Canonical build provenance lost its source binding"
    exit 1
fi
python - "$BUILD_PROVENANCE_SCRATCH" "$BUILD_PROVENANCE_FILE" <<'PY'
import pathlib
import sys

source = pathlib.Path(sys.argv[1]).read_bytes()
destination = pathlib.Path(sys.argv[2])
try:
    with destination.open("xb") as stream:
        stream.write(source)
except FileExistsError:
    if destination.read_bytes() != source:
        raise SystemExit("existing canonical build provenance differs")
PY

BUILD_DOMAIN_SHA256="$(scalar python "$AZURE_HELPER" get \
    --json "$BUILD_PROVENANCE_FILE" \
    --field coordination.build_slot.domain_sha256)"
BUILD_RECORD_NAME="$(scalar python "$AZURE_HELPER" get \
    --json "$BUILD_PROVENANCE_FILE" \
    --field coordination.build_slot.record_name)"
if [[ ! "$BUILD_DOMAIN_SHA256" =~ ^[0-9a-f]{64}$ \
    || "$BUILD_RECORD_NAME" \
        != "build-${BUILD_DOMAIN_SHA256:0:32}.${BUILD_DOMAIN_SHA256:32:32}" ]]; then
    echo "[FAIL] Canonical build TXT slot is malformed"
    exit 1
fi
TASK_RUN_NAME="pv2tr-${BUILD_DOMAIN_SHA256:0:20}"
TASK_RUN_RESOURCE_ID="${ACR_ID}/taskRuns/${TASK_RUN_NAME}"
TASK_RUN_URL="https://management.azure.com${TASK_RUN_RESOURCE_ID}?api-version=2019-06-01-preview"
BUILD_RECORD_URL="https://management.azure.com${COORDINATION_ZONE_RESOURCE_ID}/TXT/${BUILD_RECORD_NAME}?api-version=${COORDINATION_DNS_API_VERSION}"
BUILD_CAPABILITY="false"
authenticate_build_txt_record() {
    az rest --method get --url "$BUILD_RECORD_URL" \
        --output json >"$BUILD_TXT_LIVE_FILE"
    python "$AZURE_HELPER" validate-txt-record \
        --record "$BUILD_TXT_LIVE_FILE" \
        --zone-resource-id "$COORDINATION_ZONE_RESOURCE_ID" \
        --record-name "$BUILD_RECORD_NAME" \
        --ttl "$COORDINATION_RECORD_TTL" \
        --expected-kind build \
        --expected-domain-sha256 "$BUILD_DOMAIN_SHA256" \
        --output "$BUILD_TXT_EVIDENCE_FILE"
}

authenticate_oci_provenance_label() {
    local digest="$1"
    local expected_evidence_sha256="${2:-}"
    local refresh_token
    local access_token
    local manifest_file="$SCRATCH_DIR/oci_manifest.json"
    local config_file="$SCRATCH_DIR/oci_config.json"
    local config_digest
    local calculated_evidence_sha256
    if ! command -v curl >/dev/null 2>&1; then
        echo "[FAIL] curl is required for OCI provenance verification"
        exit 1
    fi
    if ! refresh_token="$(scalar az acr login \
        --name "$ACR_NAME" --expose-token --query refreshToken -o tsv \
        2>/dev/null)"; then
        echo "[FAIL] OCI registry token retrieval failed"
        exit 1
    fi
    if [[ ! "$refresh_token" =~ ^[A-Za-z0-9._~-]+$ ]]; then
        unset refresh_token
        echo "[FAIL] ACR exposed an invalid registry refresh token"
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
        echo "[FAIL] OCI scoped registry token exchange failed"
        exit 1
    fi
    unset refresh_token
    if ! printf 'header = "Authorization: Bearer %s"\n' "$access_token" \
        | curl --disable --config - --fail --silent --show-error \
            --proto '=https' --proto-redir '=https' --location --max-redirs 3 \
            --retry 0 \
            --header "Accept: application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.v2+json" \
            "https://${LOGIN_SERVER}/v2/${IMAGE_REPOSITORY}/manifests/${digest}" \
            --output "$manifest_file"; then
        unset access_token
        echo "[FAIL] OCI manifest retrieval failed"
        exit 1
    fi
    if [[ ! -s "$manifest_file" ]]; then
        echo "[FAIL] OCI manifest retrieval returned no evidence"
        exit 1
    fi
    config_digest="$(scalar python - "$manifest_file" <<'PY'
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
    raise SystemExit("OCI manifest has no exact image config digest")
print(digest)
PY
)"
    if ! printf 'header = "Authorization: Bearer %s"\n' "$access_token" \
        | curl --disable --config - --fail --silent --show-error \
            --proto '=https' --proto-redir '=https' --location --max-redirs 3 \
            --retry 0 \
            "https://${LOGIN_SERVER}/v2/${IMAGE_REPOSITORY}/blobs/${config_digest}" \
            --output "$config_file"; then
        unset access_token
        echo "[FAIL] OCI config retrieval failed"
        exit 1
    fi
    unset access_token
    if [[ ! -s "$config_file" ]]; then
        echo "[FAIL] OCI config retrieval returned no evidence"
        exit 1
    fi
    calculated_evidence_sha256="$(scalar python "$AZURE_HELPER" validate-oci-image \
        --manifest "$manifest_file" \
        --config "$config_file" \
        --expected-manifest-digest "$digest" \
        --expected-provenance-sha256 "$BUILD_PROVENANCE_SHA256" \
        --output "$OCI_VALIDATION_FILE")"
    if [[ ! "$calculated_evidence_sha256" =~ ^[0-9a-f]{64}$ \
        || ! -s "$OCI_VALIDATION_FILE" ]]; then
        echo "[FAIL] OCI verification produced no exact evidence"
        exit 1
    fi
    if [[ -n "$expected_evidence_sha256" \
        && "$calculated_evidence_sha256" != "$expected_evidence_sha256" ]]; then
        echo "[FAIL] OCI verification evidence differs from the durable claim"
        exit 1
    fi
    OCI_VERIFICATION_SHA256="$calculated_evidence_sha256"
}

mkdir "$CONTEXT_DIR"
git -C "$PROJECT_ROOT" archive --format=tar "$SOURCE_SHA" \
    -- "${BUILD_INPUTS[@]}" \
    | tar -xf - -C "$CONTEXT_DIR"
python - "$PROJECT_ROOT" "$CONTEXT_DIR" "$SOURCE_BINDING_FILE" <<'PY'
import hashlib
import json
import pathlib
import subprocess
import sys

project = pathlib.Path(sys.argv[1])
root = pathlib.Path(sys.argv[2])
record = json.loads(pathlib.Path(sys.argv[3]).read_text(encoding="utf-8"))
actual = sorted(
    path.relative_to(root).as_posix()
    for path in root.rglob("*")
    if path.is_file() or path.is_symlink()
)
if actual != sorted(record["files"]):
    raise SystemExit("archive context membership differs from source binding")
for name, binding in record["files"].items():
    path = root / name
    if path.is_symlink() or not path.is_file():
        raise SystemExit(f"archive path is not a regular file: {name}")
    data = path.read_bytes()
    oid = subprocess.run(
        ["git", "-C", str(project), "hash-object", "--stdin"],
        input=data,
        check=True,
        capture_output=True,
    ).stdout.decode("ascii").replace("\r", "").strip()
    if (
        len(data) != binding["size"]
        or hashlib.sha256(data).hexdigest() != binding["sha256"]
        or oid != binding["git_blob_oid"]
    ):
        raise SystemExit(f"archive byte binding mismatch: {name}")
PY
if [[ -n "$(git -C "$PROJECT_ROOT" status --porcelain=v1 --untracked-files=all | tr -d '\r')" \
    || "$(scalar git -C "$PROJECT_ROOT" rev-parse HEAD)" != "$SOURCE_SHA" \
    || "$(scalar git -C "$PROJECT_ROOT" rev-parse refs/remotes/origin/main)" \
        != "$SOURCE_SHA" \
    || "$(scalar git -C "$PROJECT_ROOT" remote get-url origin)" \
        != "$APPROVED_ORIGIN_URL" ]]; then
    echo "[FAIL] Source changed while the exact remote commit was prepared"
    exit 1
fi

CANDIDATE_STAGING_TAG="staging-${SOURCE_SHA}-${INVOCATION_ID}"
CANDIDATE_BUILD_RUN_REQUEST_SHA256="$(scalar python "$AZURE_HELPER" \
    create-acr-task-run \
    --build-provenance "$BUILD_PROVENANCE_FILE" \
    --build-provenance-sha256 "$BUILD_PROVENANCE_SHA256" \
    --staging-tag "$CANDIDATE_STAGING_TAG" --output "$TASK_RUN_BODY")"
TASK_RUN_RESOURCE_ID_SHA256="$(printf '%s' "${TASK_RUN_RESOURCE_ID,,}" \
    | sha256sum | awk '{print $1}')"
python - "$BUILD_CLAIM_VALUES_FILE" "$INVOCATION_ID" "$SOURCE_SHA" \
    "$TASK_RUN_NAME" "$CANDIDATE_STAGING_TAG" \
    "$TASK_RUN_RESOURCE_ID_SHA256" "$CANDIDATE_BUILD_RUN_REQUEST_SHA256" \
    "$SOURCE_BINDING_SHA256" "$BUILD_PROVENANCE_SHA256" \
    "$COORDINATION_BINDING_SHA256" <<'PY'
import json
import pathlib
import sys

keys = (
    "claim_nonce",
    "source_commit",
    "task_run_name",
    "staging_tag",
    "task_run_resource_id_sha256",
    "build_run_request_sha256",
    "source_binding_sha256",
    "build_provenance_sha256",
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
python "$AZURE_HELPER" create-claim-envelope --kind build \
    --domain-sha256 "$BUILD_DOMAIN_SHA256" \
    --claims "$BUILD_CLAIM_VALUES_FILE" \
    --output "$BUILD_CLAIM_ENVELOPE_FILE"
RETURNED_BUILD_RECORD_NAME="$(scalar python "$AZURE_HELPER" \
    create-txt-record-body --envelope "$BUILD_CLAIM_ENVELOPE_FILE" \
    --ttl "$COORDINATION_RECORD_TTL" --output "$BUILD_TXT_BODY_FILE" \
    --print-name)"
if [[ "$RETURNED_BUILD_RECORD_NAME" != "$BUILD_RECORD_NAME" ]]; then
    echo "[FAIL] Build TXT request escaped its complete claim domain"
    exit 1
fi
chmod 400 "$BUILD_TXT_BODY_FILE" "$TASK_RUN_BODY"

if ! CURRENT_COORDINATION_BINDING_SHA256="$(authenticate_coordination_zone)"; then
    echo "[FAIL] Coordination zone could not be reauthenticated before build claim"
    exit 1
fi
if [[ "$CURRENT_COORDINATION_BINDING_SHA256" \
    != "$COORDINATION_BINDING_SHA256" ]]; then
    echo "[FAIL] Coordination zone changed before build claim"
    exit 1
fi
BUILD_CREATE_STATUS="transport-ambiguous"
if status="$(raw_arm_request_once PUT "$BUILD_RECORD_URL" \
    "$BUILD_TXT_BODY_FILE" "$BUILD_TXT_CREATE_RESPONSE_FILE" true)"; then
    BUILD_CREATE_STATUS="$status"
fi
if [[ "$BUILD_CREATE_STATUS" == "201" ]]; then
    python "$AZURE_HELPER" validate-txt-record \
        --record "$BUILD_TXT_CREATE_RESPONSE_FILE" \
        --zone-resource-id "$COORDINATION_ZONE_RESOURCE_ID" \
        --record-name "$BUILD_RECORD_NAME" \
        --ttl "$COORDINATION_RECORD_TTL" \
        --expected-envelope "$BUILD_CLAIM_ENVELOPE_FILE" \
        --output "$SCRATCH_DIR/build_txt_create_evidence.json"
    authenticate_build_txt_record
    python - "$SCRATCH_DIR/build_txt_create_evidence.json" \
        "$BUILD_TXT_EVIDENCE_FILE" <<'PY'
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
    raise SystemExit("created/re-GET build TXT evidence differs")
PY
    BUILD_CAPABILITY="dns-create-201:${INVOCATION_ID}:${BUILD_DOMAIN_SHA256}"
else
    echo "[INFO] Build TXT create returned ${BUILD_CREATE_STATUS}; GET-only recovery"
    authenticate_build_txt_record
fi

START_INVOCATION_ID="$(scalar python "$AZURE_HELPER" get \
    --json "$BUILD_TXT_EVIDENCE_FILE" --field envelope.claims.claim_nonce)"
STAGING_TAG="$(scalar python "$AZURE_HELPER" get \
    --json "$BUILD_TXT_EVIDENCE_FILE" --field envelope.claims.staging_tag)"
CLAIM_TASK_RUN_NAME="$(scalar python "$AZURE_HELPER" get \
    --json "$BUILD_TXT_EVIDENCE_FILE" --field envelope.claims.task_run_name)"
CLAIM_TASK_RUN_RESOURCE_ID_SHA256="$(scalar python "$AZURE_HELPER" get \
    --json "$BUILD_TXT_EVIDENCE_FILE" \
    --field envelope.claims.task_run_resource_id_sha256)"
CLAIM_BUILD_RUN_REQUEST_SHA256="$(scalar python "$AZURE_HELPER" get \
    --json "$BUILD_TXT_EVIDENCE_FILE" \
    --field envelope.claims.build_run_request_sha256)"
if [[ ! "$START_INVOCATION_ID" =~ ^[0-9a-f]{32}$ \
    || "$STAGING_TAG" != "staging-${SOURCE_SHA}-${START_INVOCATION_ID}" \
    || "$CLAIM_TASK_RUN_NAME" != "$TASK_RUN_NAME" \
    || "$CLAIM_TASK_RUN_RESOURCE_ID_SHA256" \
        != "$TASK_RUN_RESOURCE_ID_SHA256" ]]; then
    echo "[FAIL] Authenticated build TXT winner is malformed"
    exit 1
fi
BUILD_RUN_REQUEST_SHA256="$(scalar python "$AZURE_HELPER" \
    create-acr-task-run \
    --build-provenance "$BUILD_PROVENANCE_FILE" \
    --build-provenance-sha256 "$BUILD_PROVENANCE_SHA256" \
    --staging-tag "$STAGING_TAG" --output "$TASK_RUN_BODY")"
chmod 400 "$TASK_RUN_BODY"
if [[ ! "$TASK_RUN_NAME" =~ ^[a-z0-9][a-z0-9-]{3,48}[a-z0-9]$ \
    || ! "$BUILD_RUN_REQUEST_SHA256" =~ ^[0-9a-f]{64}$ \
    || "$BUILD_RUN_REQUEST_SHA256" \
        != "$CLAIM_BUILD_RUN_REQUEST_SHA256" ]]; then
    echo "[FAIL] Deterministic ACR TaskRun request is malformed"
    exit 1
fi

if [[ "$BUILD_CAPABILITY" == \
    "dns-create-201:${INVOCATION_ID}:${BUILD_DOMAIN_SHA256}" ]]; then
    if az acr repository show --name "$ACR_NAME" \
        --image "${IMAGE_REPOSITORY}:${FINAL_TAG}" --output none 2>/dev/null; then
        echo "[FAIL] Source tag exists without an authenticated durable build winner"
        exit 1
    fi
    if az acr repository show --name "$ACR_NAME" \
        --image "${IMAGE_REPOSITORY}:latest" --output none 2>/dev/null; then
        echo "[FAIL] Mutable latest is forbidden for the evaluation repository"
        exit 1
    fi
    TASK_RUN_PRE_PUT_GET_STATUS="transport-ambiguous"
    if status="$(raw_arm_get_once "$TASK_RUN_URL" \
        "$TASK_RUN_PRE_PUT_GET_FILE")"; then
        TASK_RUN_PRE_PUT_GET_STATUS="$status"
    fi
    if [[ "$TASK_RUN_PRE_PUT_GET_STATUS" != "404" ]]; then
        echo "[FAIL] ACR TaskRun absence changed before its one-shot PUT"
        exit 1
    fi
    TASK_RUN_PUT_STATUS="transport-ambiguous"
    if status="$(raw_arm_request_once PUT "$TASK_RUN_URL" \
        "$TASK_RUN_BODY" "$TASK_RUN_RESPONSE_BODY" false)"; then
        TASK_RUN_PUT_STATUS="$status"
    fi
    echo "[INFO] One-shot TaskRun PUT result: ${TASK_RUN_PUT_STATUS}; only GET adoption follows"
fi

    TASK_RUN_DISCOVERED="false"
    STATUS=""
    for _ in $(seq 1 360); do
        if az rest --method get --url "$TASK_RUN_URL" \
            --output json >"$TASK_RUN_FILE" 2>/dev/null; then
            if ! python "$AZURE_HELPER" validate-acr-task-run \
                --task-run "$TASK_RUN_FILE" \
                --expected-task-run-name "$TASK_RUN_NAME" \
                --expected-acr-resource-id "$ACR_ID" \
                --build-provenance "$BUILD_PROVENANCE_FILE" \
                --build-provenance-sha256 "$BUILD_PROVENANCE_SHA256" \
                --staging-tag "$STAGING_TAG" \
                --expected-run-request-sha256 \
                    "$BUILD_RUN_REQUEST_SHA256" \
                --output "$TASK_RUN_VALIDATION_FILE"; then
                echo "[FAIL] Deterministic ACR TaskRun provenance is invalid"
                exit 1
            fi
            TASK_RUN_DISCOVERED="true"
            STATUS="$(scalar python "$AZURE_HELPER" get \
                --json "$TASK_RUN_VALIDATION_FILE" --field status)"
            case "$STATUS" in
                Succeeded) break ;;
                Failed|Canceled|Cancelled|Error|Timeout)
                    echo "[FAIL] ACR TaskRun child build ended in $STATUS"
                    exit 1
                    ;;
            esac
        fi
        sleep 5
    done
    if [[ "$TASK_RUN_DISCOVERED" != "true" ]]; then
        echo "[FAIL] Build TXT claim has no TaskRun; the one-shot build is permanently stranded"
        exit 1
    fi
    if [[ "$STATUS" != "Succeeded" ]]; then
        echo "[FAIL] ACR TaskRun child build did not reach Succeeded"
        exit 1
    fi
    az rest --method get \
        --url "$TASK_RUN_URL" --output json >"$TASK_RUN_FILE"
    if ! python "$AZURE_HELPER" validate-acr-task-run \
        --task-run "$TASK_RUN_FILE" \
        --expected-task-run-name "$TASK_RUN_NAME" \
        --expected-acr-resource-id "$ACR_ID" \
        --build-provenance "$BUILD_PROVENANCE_FILE" \
        --build-provenance-sha256 "$BUILD_PROVENANCE_SHA256" \
        --staging-tag "$STAGING_TAG" \
        --require-succeeded \
        --expected-run-request-sha256 "$BUILD_RUN_REQUEST_SHA256" \
        --output "$TASK_RUN_VALIDATION_FILE"; then
        echo "[FAIL] ACR TaskRun request/child output provenance is not exact"
        exit 1
    fi
    RUN_ID="$(scalar python "$AZURE_HELPER" get \
        --json "$TASK_RUN_VALIDATION_FILE" --field run_id)"
    DIGEST="$(scalar python "$AZURE_HELPER" get \
        --json "$TASK_RUN_VALIDATION_FILE" --field output_digest)"
    if [[ ! "$DIGEST" =~ ^sha256:[0-9a-f]{64}$ \
        || ! "$RUN_ID" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$ \
        || ! "$BUILD_RUN_REQUEST_SHA256" =~ ^[0-9a-f]{64}$ ]]; then
        echo "[FAIL] TaskRun returned no authenticated immutable output"
        exit 1
    fi
    authenticate_oci_provenance_label "$DIGEST"

authenticate_build_txt_record
if [[ "$(authenticate_coordination_zone)" \
    != "$COORDINATION_BINDING_SHA256" ]]; then
    echo "[FAIL] Coordination zone changed before finalization"
    exit 1
fi
if [[ "$(scalar python "$AZURE_HELPER" get \
        --json "$BUILD_TXT_EVIDENCE_FILE" \
        --field envelope.claims.claim_nonce)" != "$START_INVOCATION_ID" \
    || "$(scalar python "$AZURE_HELPER" get \
        --json "$BUILD_TXT_EVIDENCE_FILE" \
        --field envelope.claims.build_run_request_sha256)" \
        != "$BUILD_RUN_REQUEST_SHA256" ]]; then
    echo "[FAIL] Authenticated build TXT winner changed before finalization"
    exit 1
fi
python "$AZURE_HELPER" validate-oci-evidence \
    --evidence "$OCI_VALIDATION_FILE" \
    --expected-image-digest "$DIGEST" \
    --expected-provenance-sha256 "$BUILD_PROVENANCE_SHA256" \
    --expected-sha256 "$OCI_VERIFICATION_SHA256" \
    --output "$OCI_REVALIDATION_FILE" >/dev/null
if [[ -e "$IMAGE_BINDING_FILE" ]]; then
    python "$AZURE_HELPER" validate-image-binding-oci \
        --image-binding "$IMAGE_BINDING_FILE" \
        --expected-image-digest "$DIGEST" \
        --expected-provenance-sha256 "$BUILD_PROVENANCE_SHA256" \
        --expected-evidence-sha256 "$OCI_VERIFICATION_SHA256" \
        --output "$SCRATCH_DIR/existing_image_binding_oci.json"
fi

FINAL_DIGEST=""
if az acr repository show --name "$ACR_NAME" \
    --image "${IMAGE_REPOSITORY}:${FINAL_TAG}" \
    --query digest -o tsv >"$SCRATCH_DIR/final_digest.txt" 2>/dev/null; then
    FINAL_DIGEST="$(tr -d '\r\n' <"$SCRATCH_DIR/final_digest.txt")"
    if [[ "$FINAL_DIGEST" != "$DIGEST" ]]; then
        echo "[FAIL] Existing source tag has different provenance"
        exit 1
    fi
else
    az acr import \
        --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" \
        --source "${LOGIN_SERVER}/${IMAGE_REPOSITORY}@${DIGEST}" \
        --image "${IMAGE_REPOSITORY}:${FINAL_TAG}" --output none
fi
FINAL_DIGEST="$(scalar az acr repository show \
    --name "$ACR_NAME" --image "${IMAGE_REPOSITORY}:${FINAL_TAG}" \
    --query digest -o tsv)"
if [[ "$FINAL_DIGEST" != "$DIGEST" ]]; then
    echo "[FAIL] Final source tag does not resolve to the winning digest"
    exit 1
fi

if az acr repository show --name "$ACR_NAME" \
    --image "${IMAGE_REPOSITORY}:latest" --output none 2>/dev/null; then
    echo "[FAIL] Mutable latest is forbidden for the evaluation repository"
    exit 1
fi

# Lock the manifest first, then the exact source tag. Recovery only repeats
# write=false/delete=false; it never unlocks, overwrites, or retags.
CURRENT_MANIFEST_WRITE="$(scalar az acr manifest show-metadata \
    --registry "$ACR_NAME" --name "${IMAGE_REPOSITORY}@${DIGEST}" \
    --query changeableAttributes.writeEnabled -o tsv)"
CURRENT_MANIFEST_DELETE="$(scalar az acr manifest show-metadata \
    --registry "$ACR_NAME" --name "${IMAGE_REPOSITORY}@${DIGEST}" \
    --query changeableAttributes.deleteEnabled -o tsv)"
if [[ "${CURRENT_MANIFEST_WRITE,,}" != "false" \
    || "${CURRENT_MANIFEST_DELETE,,}" != "false" ]]; then
    az acr repository update \
        --name "$ACR_NAME" --image "${IMAGE_REPOSITORY}@${DIGEST}" \
        --write-enabled false --delete-enabled false --output none
fi
CURRENT_TAG_WRITE="$(scalar az acr repository show \
    --name "$ACR_NAME" --image "${IMAGE_REPOSITORY}:${FINAL_TAG}" \
    --query changeableAttributes.writeEnabled -o tsv)"
CURRENT_TAG_DELETE="$(scalar az acr repository show \
    --name "$ACR_NAME" --image "${IMAGE_REPOSITORY}:${FINAL_TAG}" \
    --query changeableAttributes.deleteEnabled -o tsv)"
if [[ "${CURRENT_TAG_WRITE,,}" != "false" \
    || "${CURRENT_TAG_DELETE,,}" != "false" ]]; then
    az acr repository update \
        --name "$ACR_NAME" --image "${IMAGE_REPOSITORY}:${FINAL_TAG}" \
        --write-enabled false --delete-enabled false --output none
fi
FINAL_DIGEST="$(scalar az acr repository show \
    --name "$ACR_NAME" --image "${IMAGE_REPOSITORY}:${FINAL_TAG}" \
    --query digest -o tsv)"
TAG_WRITE="$(scalar az acr repository show \
    --name "$ACR_NAME" --image "${IMAGE_REPOSITORY}:${FINAL_TAG}" \
    --query changeableAttributes.writeEnabled -o tsv)"
TAG_DELETE="$(scalar az acr repository show \
    --name "$ACR_NAME" --image "${IMAGE_REPOSITORY}:${FINAL_TAG}" \
    --query changeableAttributes.deleteEnabled -o tsv)"
MANIFEST_WRITE="$(scalar az acr manifest show-metadata \
    --registry "$ACR_NAME" --name "${IMAGE_REPOSITORY}@${DIGEST}" \
    --query changeableAttributes.writeEnabled -o tsv)"
MANIFEST_DELETE="$(scalar az acr manifest show-metadata \
    --registry "$ACR_NAME" --name "${IMAGE_REPOSITORY}@${DIGEST}" \
    --query changeableAttributes.deleteEnabled -o tsv)"
if [[ "$FINAL_DIGEST" != "$DIGEST" \
    || "${TAG_WRITE,,}" != "false" || "${TAG_DELETE,,}" != "false" \
    || "${MANIFEST_WRITE,,}" != "false" \
    || "${MANIFEST_DELETE,,}" != "false" ]]; then
    echo "[FAIL] changeableAttributes.* immutable lock verification failed"
    exit 1
fi
az rest --method get --url "$TASK_RUN_URL" \
    --output json >"$TASK_RUN_FILE"
python "$AZURE_HELPER" validate-acr-task-run \
    --task-run "$TASK_RUN_FILE" \
    --expected-task-run-name "$TASK_RUN_NAME" \
    --expected-acr-resource-id "$ACR_ID" \
    --build-provenance "$BUILD_PROVENANCE_FILE" \
    --build-provenance-sha256 "$BUILD_PROVENANCE_SHA256" \
    --staging-tag "$STAGING_TAG" --require-succeeded \
    --expected-run-id "$RUN_ID" --expected-digest "$DIGEST" \
    --expected-run-request-sha256 "$BUILD_RUN_REQUEST_SHA256" \
    --output "$TASK_RUN_VALIDATION_FILE" >/dev/null

python - "$SOURCE_BINDING_FILE" "$BUILD_PROVENANCE_FILE" \
    "$OCI_REVALIDATION_FILE" "$COORDINATION_BINDING_FILE" \
    "$BUILD_TXT_EVIDENCE_FILE" "$IMAGE_BINDING_FILE" \
    "$BUILD_PROVENANCE_SHA256" "$BUILD_RUN_REQUEST_SHA256" \
    "$OCI_VERIFICATION_SHA256" "$BUILD_PROVENANCE_LABEL" \
    "$LOGIN_SERVER" "$STAGING_TAG" "$FINAL_TAG" \
    "$DIGEST" "$TASK_RUN_NAME" "$TASK_RUN_RESOURCE_ID" \
    "$RUN_ID" "$COORDINATION_BINDING_SHA256" \
    "$TAG_WRITE" "$TAG_DELETE" \
    "$MANIFEST_WRITE" "$MANIFEST_DELETE" <<'PY'
import hashlib
import json
import pathlib
import sys

(
    source_path,
    provenance_path,
    oci_evidence_path,
    coordination_path,
    build_slot_evidence_path,
    output_path,
    provenance_sha256,
    run_request_sha256,
    oci_evidence_sha256,
    provenance_label,
    login_server,
    staging_tag,
    final_tag,
    digest,
    task_run_name,
    task_run_resource_id,
    run_id,
    coordination_sha256,
    tag_write,
    tag_delete,
    manifest_write,
    manifest_delete,
) = sys.argv[1:]
source_bytes = pathlib.Path(source_path).read_bytes()
source = json.loads(source_bytes)
provenance_bytes = pathlib.Path(provenance_path).read_bytes()
provenance = json.loads(provenance_bytes)
oci_evidence_bytes = pathlib.Path(oci_evidence_path).read_bytes()
oci_evidence = json.loads(oci_evidence_bytes)
coordination = json.loads(pathlib.Path(coordination_path).read_bytes())
build_slot_evidence = json.loads(
    pathlib.Path(build_slot_evidence_path).read_bytes()
)
envelope = build_slot_evidence["envelope"]
if (
    hashlib.sha256(provenance_bytes).hexdigest() != provenance_sha256
    or provenance["source_binding"] != source
    or provenance["source_binding_sha256"]
    != hashlib.sha256(source_bytes).hexdigest()
    or hashlib.sha256(oci_evidence_bytes).hexdigest() != oci_evidence_sha256
    or oci_evidence["image_digest"] != digest
    or oci_evidence["manifest_sha256"] != digest.removeprefix("sha256:")
    or oci_evidence["config_sha256"]
    != oci_evidence["config_digest"].removeprefix("sha256:")
    or oci_evidence["provenance_label"]
    != {"name": provenance_label, "value": provenance_sha256}
):
    raise SystemExit("final build/OCI provenance record is not exact")
record = {
    **source,
    "schema_version": "phase1-parser-v2-eval-image-binding/v6",
    "source_binding_sha256": hashlib.sha256(source_bytes).hexdigest(),
    "build_provenance": provenance,
    "build_provenance_sha256": provenance_sha256,
    "build_run_request_sha256": run_request_sha256,
    "oci_verification_sha256": oci_evidence_sha256,
    "oci_verification": oci_evidence,
    "staging_image_tag": staging_tag,
    "image_tag": final_tag,
    "image_digest": digest,
    "image_digest_ref": (
        f"{login_server}/{source['image_repository']}@{digest}"
    ),
    "acr_build_task_run_name": task_run_name,
    "acr_build_task_run_resource_id": task_run_resource_id,
    "acr_build_run_id": run_id,
    "coordination_binding": coordination,
    "coordination_binding_sha256": coordination_sha256,
    "build_slot": {
        "domain_sha256": build_slot_evidence["domain_sha256"],
        "record_name": build_slot_evidence["record_name"],
        "record_resource_id": build_slot_evidence["record_resource_id"],
        "record_etag": build_slot_evidence["record_etag"],
        "record_etag_sha256": build_slot_evidence["record_etag_sha256"],
        "payload_sha256": build_slot_evidence["payload_sha256"],
        "claim_nonce": envelope["claims"]["claim_nonce"],
        "record_ttl": build_slot_evidence["record_ttl"],
    },
    "historical_finalization_supported": True,
    "changeable_attributes": {
        "tag_write_enabled": tag_write.lower() == "true",
        "tag_delete_enabled": tag_delete.lower() == "true",
        "manifest_write_enabled": manifest_write.lower() == "true",
        "manifest_delete_enabled": manifest_delete.lower() == "true",
    },
    "cpu_only": True,
    "gpu": False,
    "stage_p_and_e_same_digest": True,
    "mutable_latest_forbidden": True,
}
data = (
    json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
).encode()
path = pathlib.Path(output_path)
try:
    with path.open("xb") as stream:
        stream.write(data)
except FileExistsError:
    if path.read_bytes() != data:
        raise SystemExit("existing finalization record differs")
PY

IMAGE_BINDING_SHA256="$(scalar sha256sum "$IMAGE_BINDING_FILE")"
IMAGE_BINDING_SHA256="${IMAGE_BINDING_SHA256%% *}"
if [[ ! "$IMAGE_BINDING_SHA256" =~ ^[0-9a-f]{64}$ \
    || "$(scalar python "$AZURE_HELPER" validate-image-binding \
        --image-binding "$IMAGE_BINDING_FILE" \
        --expected-sha256 "$IMAGE_BINDING_SHA256" \
        --expected-source-commit "$SOURCE_SHA" \
        --expected-acr-resource-id "$ACR_ID" \
        --expected-login-server "$LOGIN_SERVER" \
        --expected-repository "$IMAGE_REPOSITORY" \
        --output "$IMAGE_BINDING_VALIDATION_FILE")" \
        != "$IMAGE_BINDING_SHA256" ]]; then
    echo "[FAIL] Final immutable image binding validation failed"
    exit 1
fi
python - "$IMAGE_BINDING_SHA256_FILE" "$IMAGE_BINDING_SHA256" <<'PY'
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
data = (sys.argv[2] + "\n").encode("ascii")
try:
    with path.open("xb") as stream:
        stream.write(data)
except FileExistsError:
    if path.read_bytes() != data:
        raise SystemExit("existing image-binding hash differs")
PY

echo "[OK] ${LOGIN_SERVER}/${IMAGE_REPOSITORY}@${DIGEST}"
echo "[OK] Image binding SHA-256: ${IMAGE_BINDING_SHA256}"
echo "[OK] CPU-only image and source tag are immutable; no latest tag"
