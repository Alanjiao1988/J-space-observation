#!/bin/bash -p
set +x
set +v
set -euo pipefail

while IFS= builtin read -r function_name; do
    builtin unset -f "$function_name"
done < <(builtin compgen -A function)
builtin unset BASH_ENV ENV CDPATH GLOBIGNORE PYTHONPATH PYTHONHOME PYTHONSTARTUP
builtin unset PYTHONWARNINGS PYTHONINSPECT PYTHONBREAKPOINT PYTHONUSERBASE
builtin unset PYTHONCASEOK PYTHONEXECUTABLE PYTHONCOERCECLOCALE PYTHONUTF8
builtin unset PYTHONMALLOC PYTHONPLATLIBDIR

client_id="${AZURE_CLIENT_ID:?AZURE_CLIENT_ID is required}"
identity_endpoint="${IDENTITY_ENDPOINT:?IDENTITY_ENDPOINT is required}"
identity_header="${IDENTITY_HEADER:?IDENTITY_HEADER is required}"
builtin exec /usr/bin/env -i \
    AZURE_CLIENT_ID="$client_id" \
    HOME=/nonexistent \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PATH=/usr/local/bin:/usr/bin:/bin \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=0 \
    TMPDIR=/runtime/work \
    IDENTITY_ENDPOINT="$identity_endpoint" \
    IDENTITY_HEADER="$identity_header" \
    /usr/local/bin/python3.11 -I \
    /workspace/scripts/run_parser_v3_locked_predictions.py "$@"
